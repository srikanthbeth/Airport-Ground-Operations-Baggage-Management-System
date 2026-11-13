
import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from db.base import Base
from db.session import engine, SessionLocal
from core.constants import UserRole
from core.security import hash_password
from models.user import User
import models
from main import app


client = TestClient(app)

PASSWORD = "TurnaroundTest@12345"

admin_headers = {}
officer_headers = {}

airport_id = None
terminal_id = None


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def create_user(role=UserRole.SUPER_ADMIN):
    value = unique_value()

    db = SessionLocal()

    user = User(
        full_name=f"Turnaround User {value}",
        email=f"turnaround_{value.lower()}@example.com",
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_active=True,
        is_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    email = user.email
    user_id = user.id

    db.close()

    return user_id, email


def login_headers(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def create_airport(headers, code=None):
    suffix = unique_value()

    response = client.post(
        "/api/v1/airports/",
        headers=headers,
        json={
            "code": code or f"A{suffix[:5]}",
            "name": f"Test Airport {suffix}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_terminal(headers, airport):
    suffix = unique_value()

    response = client.post(
        "/api/v1/terminals/",
        headers=headers,
        json={
            "airport_id": airport["id"],
            "name": f"Terminal {suffix}",
            "code": f"T{suffix[:5]}",
            "description": "Aircraft turnaround terminal",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def setup_module():
    global admin_headers
    global officer_headers
    global airport_id
    global terminal_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _, admin_email = create_user(UserRole.SUPER_ADMIN)

    _, officer_email = create_user(
        UserRole.FLIGHT_OPERATIONS_OFFICER
    )

    admin_headers = login_headers(admin_email)
    officer_headers = login_headers(officer_email)

    airport = create_airport(
        admin_headers,
        code="HYD",
    )

    airport_id = airport["id"]

    terminal = create_terminal(
        admin_headers,
        airport,
    )

    terminal_id = terminal["id"]


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def turnaround_payload(**overrides):
    arrival = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

    departure = arrival + timedelta(hours=2)

    payload = {
        "turnaround_number": f"TRN-{unique_value()}",
        "airport_id": airport_id,
        "aircraft_registration": "VT-ABC",
        "aircraft_type": "Airbus A320",
        "scheduled_arrival": arrival.isoformat(),
        "scheduled_departure": departure.isoformat(),
        "notes": "Regular domestic turnaround",
    }

    payload.update(overrides)

    return payload


def create_turnaround(**overrides):
    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=turnaround_payload(**overrides),
    )

    assert response.status_code == 201, response.text

    return response.json()


# --------------------------------------------------
# CREATE TESTS
# --------------------------------------------------

def test_admin_can_create_turnaround():
    payload = turnaround_payload()

    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["turnaround_number"] == payload["turnaround_number"]
    assert data["airport_id"] == airport_id
    assert data["aircraft_registration"] == "VT-ABC"
    assert data["aircraft_type"] == "Airbus A320"
    assert data["status"] == "scheduled"


def test_turnaround_can_be_created_with_terminal():
    # Create a new airport
    airport = create_airport(admin_headers)

    # Create a terminal belonging to that airport
    terminal = create_terminal(admin_headers, airport)

    # Use the matching airport and terminal IDs
    turnaround = create_turnaround(
        airport_id=airport["id"],
        terminal_id=terminal["id"],
    )

    assert turnaround["airport_id"] == airport["id"]
    assert turnaround["terminal_id"] == terminal["id"]


def test_duplicate_turnaround_number_is_rejected():
    payload = turnaround_payload()

    first = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=payload,
    )

    assert second.status_code == 409


def test_turnaround_rejects_missing_airport():
    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=turnaround_payload(
            airport_id=str(uuid.uuid4())
        ),
    )

    assert response.status_code == 404


def test_turnaround_rejects_missing_terminal():
    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=turnaround_payload(
            terminal_id=str(uuid.uuid4())
        ),
    )

    assert response.status_code == 404


def test_turnaround_rejects_terminal_from_another_airport():
    second_airport = create_airport(admin_headers)

    wrong_terminal = create_terminal(
        admin_headers,
        second_airport,
    )

    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=turnaround_payload(
            terminal_id=wrong_terminal["id"]
        ),
    )

    assert response.status_code == 400


def test_turnaround_rejects_arrival_after_departure():
    arrival = datetime(
        2030, 5, 10, 12, 0, tzinfo=timezone.utc
    )

    departure = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=turnaround_payload(
            scheduled_arrival=arrival.isoformat(),
            scheduled_departure=departure.isoformat(),
        ),
    )

    assert response.status_code == 422


def test_turnaround_requires_aircraft_registration():
    payload = turnaround_payload()
    payload.pop("aircraft_registration")

    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 422


# --------------------------------------------------
# GET AND LIST TESTS
# --------------------------------------------------

def test_admin_can_get_turnaround():
    turnaround = create_turnaround()

    response = client.get(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == turnaround["id"]


def test_nonexistent_turnaround_returns_404():
    response = client.get(
        f"/api/v1/aircraft-turnarounds/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_list_turnarounds():
    create_turnaround()
    create_turnaround()

    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 2
    assert len(response.json()["items"]) >= 2


def test_turnaround_filter_by_status():
    create_turnaround()

    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        params={"status": "scheduled"},
    )

    assert response.status_code == 200
    assert all(
        item["status"] == "scheduled"
        for item in response.json()["items"]
    )


def test_turnaround_filter_by_airport():
    create_turnaround()

    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        params={"airport_id": airport_id},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_turnaround_pagination():
    for _ in range(3):
        create_turnaround()

    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 2,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) <= 2
    assert response.json()["page"] == 1


def test_invalid_turnaround_pagination():
    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        params={"page": 0},
    )

    assert response.status_code == 422


def test_invalid_turnaround_status_filter():
    response = client.get(
        "/api/v1/aircraft-turnarounds/",
        headers=admin_headers,
        params={"status": "invalid_status"},
    )

    assert response.status_code == 422


# --------------------------------------------------
# UPDATE TESTS
# --------------------------------------------------

def test_admin_can_update_turnaround():
    turnaround = create_turnaround()

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}",
        headers=admin_headers,
        json={
            "aircraft_type": "Airbus A321",
            "notes": "Updated turnaround notes",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["aircraft_type"] == "Airbus A321"
    assert response.json()["notes"] == "Updated turnaround notes"


def test_update_nonexistent_turnaround_returns_404():
    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{uuid.uuid4()}",
        headers=admin_headers,
        json={"notes": "Updated notes"},
    )

    assert response.status_code == 404


# --------------------------------------------------
# STATUS TESTS
# --------------------------------------------------

def test_turnaround_can_be_started():
    turnaround = create_turnaround()

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["actual_arrival"] is not None


def test_turnaround_can_be_marked_delayed():
    turnaround = create_turnaround()

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "delayed"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "delayed"


def test_delayed_turnaround_can_resume():
    turnaround = create_turnaround()

    delayed = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "delayed"},
    )

    assert delayed.status_code == 200, delayed.text

    resumed = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "in_progress"


def test_turnaround_cannot_be_completed_without_departure():
    turnaround = create_turnaround()

    client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "completed"},
    )

    assert response.status_code == 400


def test_cancelled_turnaround_cannot_be_reopened():
    turnaround = create_turnaround()

    cancelled = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "cancelled"},
    )

    assert cancelled.status_code == 200, cancelled.text

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 400


def test_invalid_turnaround_status_is_rejected():
    turnaround = create_turnaround()

    response = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "invalid_status"},
    )

    assert response.status_code == 422


# --------------------------------------------------
# MILESTONE TESTS
# --------------------------------------------------

def test_milestone_requires_in_progress_turnaround():
    turnaround = create_turnaround()

    response = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "cleaning_completed"},
    )

    assert response.status_code == 400


def test_admin_can_record_cleaning_milestone():
    turnaround = create_turnaround()

    started = client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert started.status_code == 200, started.text

    response = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "cleaning_completed"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["cleaning_completed_at"] is not None


def test_duplicate_milestone_is_rejected():
    turnaround = create_turnaround()

    client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    first = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "baggage_unloaded"},
    )

    assert first.status_code == 200, first.text

    second = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "baggage_unloaded"},
    )

    assert second.status_code == 409


def test_chocks_off_records_actual_departure():
    turnaround = create_turnaround()

    client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    response = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "chocks_off"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["chocks_off_at"] is not None
    assert response.json()["actual_departure"] is not None


def test_invalid_milestone_is_rejected():
    turnaround = create_turnaround()

    client.patch(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    response = client.post(
        f"/api/v1/aircraft-turnarounds/{turnaround['id']}/milestones",
        headers=admin_headers,
        json={"milestone": "invalid_milestone"},
    )

    assert response.status_code == 422


# --------------------------------------------------
# AUTHORIZATION TESTS
# --------------------------------------------------

def test_turnaround_requires_authentication():
    response = client.get(
        "/api/v1/aircraft-turnarounds/"
    )

    assert response.status_code == 401


def test_flight_officer_cannot_create_turnaround():
    response = client.post(
        "/api/v1/aircraft-turnarounds/",
        headers=officer_headers,
        json=turnaround_payload(),
    )

    assert response.status_code == 403
