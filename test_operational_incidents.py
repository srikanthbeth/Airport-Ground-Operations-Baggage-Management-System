import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is missing from .env")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from db.base import Base
from db.session import engine, SessionLocal
from core.constants import UserRole
from core.security import hash_password
from models.user import User
import models
from main import app


client = TestClient(app)

PASSWORD = "AirportTest@12345"

ADMIN_EMAIL = "incident_admin@example.com"
MANAGER_EMAIL = "incident_manager@example.com"
REPORTER_EMAIL = "incident_reporter@example.com"
OFFICER_EMAIL = "incident_officer@example.com"

admin_token = None
manager_token = None
reporter_token = None
officer_token = None
airport_id = None


def create_user(email, role):
    db = SessionLocal()
    try:
        user = User(
            full_name=email.split("@")[0],
            email=email,
            hashed_password=hash_password(PASSWORD),
            role=role,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return str(user.id)
    finally:
        db.close()


def login(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def headers(token=None):
    return {
        "Authorization": f"Bearer {token or admin_token}"
    }


def unique_code(prefix="INC"):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def incident_payload(**overrides):
    payload = {
        "incident_number": unique_code(),
        "title": "Baggage handling delay",
        "description": "Baggage loading was delayed during aircraft turnaround.",
        "category": "baggage",
        "severity": "medium",
        "airport_id": airport_id,
        "flight_id": None,
        "location": "Terminal 1, Gate 4",
        "occurred_at": (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat(),
    }
    payload.update(overrides)
    return payload


def create_incident(**overrides):
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(**overrides),
        headers=headers(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def setup_module():
    global admin_token
    global manager_token
    global reporter_token
    global officer_token
    global airport_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    create_user(ADMIN_EMAIL, UserRole.SUPER_ADMIN)
    create_user(MANAGER_EMAIL, UserRole.AIRPORT_OPERATIONS_MANAGER)
    create_user(REPORTER_EMAIL, UserRole.BAGGAGE_HANDLING_STAFF)
    create_user(OFFICER_EMAIL, UserRole.FLIGHT_OPERATIONS_OFFICER)

    admin_token = login(ADMIN_EMAIL)
    manager_token = login(MANAGER_EMAIL)
    reporter_token = login(REPORTER_EMAIL)
    officer_token = login(OFFICER_EMAIL)

    airport_response = client.post(
        "/api/v1/airports/",
        json={
            "code": f"E{uuid.uuid4().hex[:8].upper()}",
            "name": "Incident Test Airport",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
        headers=headers(),
    )

    assert airport_response.status_code == 201, airport_response.text
    airport_id = airport_response.json()["id"]


def teardown_module():
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------
# CREATE INCIDENT TESTS
# ---------------------------------------------------------

def test_admin_can_create_incident():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(),
        headers=headers(),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "open"


def test_ground_staff_can_report_incident():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(),
        headers=headers(reporter_token),
    )
    assert response.status_code == 201
    assert response.json()["category"] == "baggage"


def test_create_safety_incident():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(category="safety", severity="high"),
        headers=headers(),
    )
    assert response.status_code == 201
    assert response.json()["severity"] == "high"


def test_create_critical_security_incident():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(
            category="security",
            severity="critical",
        ),
        headers=headers(),
    )
    assert response.status_code == 201
    assert response.json()["category"] == "security"


def test_duplicate_incident_number_is_rejected():
    number = unique_code()
    create_incident(incident_number=number)

    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(incident_number=number),
        headers=headers(),
    )
    assert response.status_code == 409


def test_create_incident_rejects_missing_airport():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(airport_id=str(uuid.uuid4())),
        headers=headers(),
    )
    assert response.status_code == 404


def test_create_incident_rejects_invalid_category():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(category="invalid_category"),
        headers=headers(),
    )
    assert response.status_code == 422


def test_create_incident_rejects_invalid_severity():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(severity="urgent"),
        headers=headers(),
    )
    assert response.status_code == 422


def test_create_incident_rejects_future_occurrence_time():
    response = client.post(
        "/api/v1/operational-incidents/",
        json=incident_payload(
            occurred_at=(
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat()
        ),
        headers=headers(),
    )
    assert response.status_code == 422


# ---------------------------------------------------------
# READ AND FILTER TESTS
# ---------------------------------------------------------

def test_admin_can_get_incident():
    incident = create_incident()

    response = client.get(
        f"/api/v1/operational-incidents/{incident['id']}",
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["id"] == incident["id"]


def test_nonexistent_incident_returns_404():
    response = client.get(
        f"/api/v1/operational-incidents/{uuid.uuid4()}",
        headers=headers(),
    )
    assert response.status_code == 404


def test_admin_can_list_incidents():
    create_incident()

    response = client.get(
        "/api/v1/operational-incidents/",
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert isinstance(response.json()["items"], list)


def test_filter_incidents_by_category():
    create_incident(category="equipment")

    response = client.get(
        "/api/v1/operational-incidents/?category=equipment",
        headers=headers(),
    )
    assert response.status_code == 200
    assert all(
        item["category"] == "equipment"
        for item in response.json()["items"]
    )


def test_filter_incidents_by_severity():
    create_incident(severity="critical")

    response = client.get(
        "/api/v1/operational-incidents/?severity=critical",
        headers=headers(),
    )
    assert response.status_code == 200
    assert all(
        item["severity"] == "critical"
        for item in response.json()["items"]
    )


def test_filter_incidents_by_status():
    create_incident()

    response = client.get(
        "/api/v1/operational-incidents/?status=open",
        headers=headers(),
    )
    assert response.status_code == 200
    assert all(
        item["status"] == "open"
        for item in response.json()["items"]
    )


def test_filter_incidents_by_airport():
    create_incident()

    response = client.get(
        f"/api/v1/operational-incidents/?airport_id={airport_id}",
        headers=headers(),
    )
    assert response.status_code == 200
    assert all(
        item["airport_id"] == airport_id
        for item in response.json()["items"]
    )


def test_incident_pagination():
    response = client.get(
        "/api/v1/operational-incidents/?skip=0&limit=2",
        headers=headers(),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) <= 2


def test_invalid_incident_pagination_is_rejected():
    response = client.get(
        "/api/v1/operational-incidents/?skip=-1",
        headers=headers(),
    )
    assert response.status_code == 422


# ---------------------------------------------------------
# UPDATE AND ASSIGNMENT TESTS
# ---------------------------------------------------------

def test_admin_can_update_incident():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}",
        json={
            "title": "Updated baggage incident",
            "severity": "high",
        },
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated baggage incident"
    assert response.json()["severity"] == "high"


def test_update_nonexistent_incident_returns_404():
    response = client.patch(
        f"/api/v1/operational-incidents/{uuid.uuid4()}",
        json={"title": "Updated incident"},
        headers=headers(),
    )
    assert response.status_code == 404


def test_admin_can_assign_incident():
    incident = create_incident()

    db = SessionLocal()
    try:
        assigned_user = db.query(User).filter(
            User.email == MANAGER_EMAIL
        ).first()
        assigned_user_id = str(assigned_user.id)
    finally:
        db.close()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/assign",
        json={"assigned_to_id": assigned_user_id},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["assigned_to_id"] == assigned_user_id


def test_assign_incident_rejects_missing_user():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/assign",
        json={"assigned_to_id": str(uuid.uuid4())},
        headers=headers(),
    )
    assert response.status_code == 404


def test_assign_nonexistent_incident_returns_404():
    response = client.patch(
        f"/api/v1/operational-incidents/{uuid.uuid4()}/assign",
        json={"assigned_to_id": str(uuid.uuid4())},
        headers=headers(),
    )
    assert response.status_code == 404


# ---------------------------------------------------------
# INCIDENT STATUS TESTS
# ---------------------------------------------------------

def test_incident_can_be_acknowledged():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "acknowledged"},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    assert response.json()["acknowledged_at"] is not None


def test_incident_can_be_started():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "in_progress"},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_incident_can_be_resolved():
    incident = create_incident()

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "in_progress"},
        headers=headers(),
    )

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={
            "status": "resolved",
            "resolution_notes": "Baggage loading delay resolved.",
        },
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["resolved_at"] is not None


def test_resolving_incident_requires_resolution_notes():
    incident = create_incident()

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "in_progress"},
        headers=headers(),
    )

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "resolved"},
        headers=headers(),
    )
    assert response.status_code == 422


def test_resolved_incident_can_be_closed():
    incident = create_incident()

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "in_progress"},
        headers=headers(),
    )

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={
            "status": "resolved",
            "resolution_notes": "Issue fixed.",
        },
        headers=headers(),
    )

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "closed"},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    assert response.json()["closed_at"] is not None


def test_invalid_incident_status_transition_is_rejected():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "closed"},
        headers=headers(),
    )
    assert response.status_code == 409


def test_incident_can_be_rejected():
    incident = create_incident()

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "rejected"},
        headers=headers(),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_closed_incident_cannot_be_updated():
    incident = create_incident()

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "in_progress"},
        headers=headers(),
    )

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={
            "status": "resolved",
            "resolution_notes": "Issue fixed.",
        },
        headers=headers(),
    )

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "closed"},
        headers=headers(),
    )

    response = client.patch(
        f"/api/v1/operational-incidents/{incident['id']}",
        json={"title": "Changed after closure"},
        headers=headers(),
    )
    assert response.status_code == 409


# ---------------------------------------------------------
# DELETE AND AUTHORIZATION TESTS
# ---------------------------------------------------------

def test_admin_can_delete_closed_incident():
    incident = create_incident()

    client.patch(
        f"/api/v1/operational-incidents/{incident['id']}/status",
        json={"status": "rejected"},
        headers=headers(),
    )

    response = client.delete(
        f"/api/v1/operational-incidents/{incident['id']}",
        headers=headers(),
    )
    assert response.status_code == 200


def test_open_incident_cannot_be_deleted():
    incident = create_incident()

    response = client.delete(
        f"/api/v1/operational-incidents/{incident['id']}",
        headers=headers(),
    )
    assert response.status_code == 409


def test_incident_routes_require_authentication():
    response = client.get("/api/v1/operational-incidents/")
    assert response.status_code in (401, 403)


def test_baggage_staff_cannot_list_all_incidents():
    response = client.get(
        "/api/v1/operational-incidents/",
        headers=headers(reporter_token),
    )
    assert response.status_code == 403


def test_flight_officer_can_list_incidents():
    response = client.get(
        "/api/v1/operational-incidents/",
        headers=headers(officer_token),
    )
    assert response.status_code == 200