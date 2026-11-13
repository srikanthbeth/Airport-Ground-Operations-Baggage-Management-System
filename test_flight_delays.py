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

admin_token = None
reporter_token = None
officer_token = None

origin_airport_id = None
destination_airport_id = None


def unique_email():
    return f"delay_{uuid.uuid4().hex[:10]}@example.com"


def create_user(email, role):
    db = SessionLocal()

    user = User(
        full_name=f"Delay Test {role.value}",
        email=email,
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_active=True,
        is_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    db.close()

    return user


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


def create_airport(token, code):
    response = client.post(
        "/api/v1/airports/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "code": code,
            "name": f"Delay Test Airport {code}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()["id"]


def create_flight(token):
    departure = datetime.now(timezone.utc) + timedelta(days=3)
    arrival = departure + timedelta(hours=2)

    response = client.post(
        "/api/v1/flights/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "flight_number": f"AI{uuid.uuid4().hex[:6].upper()}",
            "airline": "Air India",
            "flight_type": "domestic",
            "origin_airport_id": origin_airport_id,
            "destination_airport_id": destination_airport_id,
            "scheduled_departure": departure.isoformat(),
            "scheduled_arrival": arrival.isoformat(),
            "aircraft_type": "Airbus A320",
            "capacity": 180,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def delay_payload(flight):
    original_departure = datetime.fromisoformat(
        flight["scheduled_departure"].replace("Z", "+00:00")
    )
    original_arrival = datetime.fromisoformat(
        flight["scheduled_arrival"].replace("Z", "+00:00")
    )

    return {
        "flight_id": flight["id"],
        "reason": "weather",
        "impact": "high",
        "description": "Flight delayed due to heavy weather conditions",
        "revised_departure": (
            original_departure + timedelta(minutes=90)
        ).isoformat(),
        "revised_arrival": (
            original_arrival + timedelta(minutes=90)
        ).isoformat(),
    }


def create_delay(token, flight):
    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {token}"},
        json=delay_payload(flight),
    )

    assert response.status_code == 201, response.text

    return response.json()


def setup_module():
    global admin_token
    global reporter_token
    global officer_token
    global origin_airport_id
    global destination_airport_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    admin_email = unique_email()
    reporter_email = unique_email()
    officer_email = unique_email()

    create_user(admin_email, UserRole.SUPER_ADMIN)
    create_user(reporter_email, UserRole.GROUND_STAFF_SUPERVISOR)
    create_user(officer_email, UserRole.FLIGHT_OPERATIONS_OFFICER)

    admin_token = login(admin_email)
    reporter_token = login(reporter_email)
    officer_token = login(officer_email)

    origin_airport_id = create_airport(
        admin_token,
        f"O{uuid.uuid4().hex[:7].upper()}",
    )

    destination_airport_id = create_airport(
        admin_token,
        f"D{uuid.uuid4().hex[:7].upper()}",
    )


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def test_create_flight_delay():
    flight = create_flight(admin_token)

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=delay_payload(flight),
    )

    assert response.status_code == 201
    data = response.json()

    assert data["flight_id"] == flight["id"]
    assert data["reason"] == "weather"
    assert data["status"] == "pending"
    assert data["delay_duration_minutes"] == 90


def test_create_delay_with_different_reason():
    flight = create_flight(admin_token)
    payload = delay_payload(flight)
    payload["reason"] = "technical"

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["reason"] == "technical"


def test_create_delay_with_assignment():
    flight = create_flight(admin_token)

    db = SessionLocal()
    assigned_user = db.query(User).filter(
        User.role == UserRole.FLIGHT_OPERATIONS_OFFICER
    ).first()
    assigned_user_id = str(assigned_user.id)
    db.close()

    payload = delay_payload(flight)
    payload["assigned_to_id"] = assigned_user_id

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["assigned_to_id"] == assigned_user_id


def test_create_delay_invalid_flight():
    flight = create_flight(admin_token)
    payload = delay_payload(flight)
    payload["flight_id"] = str(uuid.uuid4())

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 404


def test_create_delay_requires_authentication():
    flight = create_flight(admin_token)

    response = client.post(
        "/api/v1/flight-delays/",
        json=delay_payload(flight),
    )

    assert response.status_code == 401




def test_revised_departure_must_be_later():
    flight = create_flight(admin_token)
    payload = delay_payload(flight)
    payload["revised_departure"] = flight["scheduled_departure"]

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_revised_arrival_must_be_after_revised_departure():
    flight = create_flight(admin_token)
    payload = delay_payload(flight)
    payload["revised_arrival"] = payload["revised_departure"]

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_delay_description_required():
    flight = create_flight(admin_token)
    payload = delay_payload(flight)
    payload["description"] = "   "

    response = client.post(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json=payload,
    )

    assert response.status_code == 422


def test_list_flight_delays():
    flight = create_flight(admin_token)
    create_delay(reporter_token, flight)

    response = client.get(
        "/api/v1/flight-delays/",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert len(response.json()["items"]) >= 1


def test_filter_delays_by_flight():
    flight = create_flight(admin_token)
    create_delay(reporter_token, flight)

    response = client.get(
        f"/api/v1/flight-delays/?flight_id={flight['id']}",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_delays_by_status():
    flight = create_flight(admin_token)
    create_delay(reporter_token, flight)

    response = client.get(
        "/api/v1/flight-delays/?delay_status=pending",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_filter_delays_by_reason():
    flight = create_flight(admin_token)
    create_delay(reporter_token, flight)

    response = client.get(
        "/api/v1/flight-delays/?reason=weather",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_flight_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.get(
        f"/api/v1/flight-delays/{delay['id']}",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == delay["id"]


def test_get_nonexistent_delay():
    response = client.get(
        f"/api/v1/flight-delays/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {reporter_token}"},
    )

    assert response.status_code == 404


def test_assign_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    db = SessionLocal()
    assigned_user = db.query(User).filter(
        User.role == UserRole.FLIGHT_OPERATIONS_OFFICER
    ).first()
    assigned_user_id = str(assigned_user.id)
    db.close()

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/assign",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"assigned_to_id": assigned_user_id},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_id"] == assigned_user_id


def test_approve_delay_updates_flight_status():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    flight_response = client.get(
        f"/api/v1/flights/{flight['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert flight_response.status_code == 200
    assert flight_response.json()["status"] == "delayed"


def test_reject_delay_requires_notes():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "rejected"},
    )

    assert response.status_code == 422


def test_reject_delay_with_notes():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "status": "rejected",
            "resolution_notes": "The reported delay was not approved",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_resolve_approved_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    approve_response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "approved"},
    )

    assert approve_response.status_code == 200

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/resolve",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "resolution_notes": "Weather conditions have improved",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["resolved_at"] is not None


def test_cannot_resolve_pending_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/resolve",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "resolution_notes": "Attempt to resolve pending delay",
        },
    )

    assert response.status_code == 409


def test_cannot_review_delay_twice():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    first = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "approved"},
    )

    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"status": "rejected", "resolution_notes": "Changed decision"},
    )

    assert second.status_code == 409


def test_delete_pending_delay_not_allowed():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    response = client.delete(
        f"/api/v1/flight-delays/{delay['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 409


def test_delete_rejected_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    reject_response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "status": "rejected",
            "resolution_notes": "Duplicate delay report",
        },
    )

    assert reject_response.status_code == 200

    response = client.delete(
        f"/api/v1/flight-delays/{delay['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200

def test_reporter_cannot_assign_delay():
    flight = create_flight(admin_token)
    delay = create_delay(reporter_token, flight)

    db = SessionLocal()
    assigned_user = db.query(User).filter(
        User.role == UserRole.FLIGHT_OPERATIONS_OFFICER
    ).first()
    assigned_user_id = str(assigned_user.id)
    db.close()

    response = client.patch(
        f"/api/v1/flight-delays/{delay['id']}/assign",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json={"assigned_to_id": assigned_user_id},
    )

    assert response.status_code == 403