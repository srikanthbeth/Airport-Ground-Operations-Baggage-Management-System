
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from db.base import Base
from db.session import engine, SessionLocal
from core.constants import UserRole
from core.security import hash_password
from models.user import User
import models  # noqa: F401
from main import app


client = TestClient(app)

PASSWORD = "ScreeningTest@12345"

admin_headers = {}
airport_id = None
destination_airport_id = None
terminal_id = None
destination_terminal_id = None
flight_id = None
counter_id = None

seat_counter = 0
passenger_counter = 0


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def setup_module(module):
    global admin_headers
    global airport_id, destination_airport_id
    global terminal_id, destination_terminal_id
    global flight_id, counter_id
    global seat_counter, passenger_counter

    seat_counter = 0
    passenger_counter = 0

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = User(
            full_name="Screening Test Admin",
            email="screening_admin@airport.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )

        db.add(admin)
        db.commit()

    finally:
        db.close()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "screening_admin@airport.com",
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    admin_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Create origin airport.
    response = client.post(
        "/api/v1/airports/",
        headers=admin_headers,
        json={
            "code": "HYD",
            "name": "Hyderabad International Airport",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 201, response.text
    airport_id = response.json()["id"]

    # Create destination airport.
    response = client.post(
        "/api/v1/airports/",
        headers=admin_headers,
        json={
            "code": "BOM",
            "name": "Mumbai International Airport",
            "city": "Mumbai",
            "country": "India",
            "address": "Mumbai, Maharashtra",
            "timezone": "Asia/Kolkata",
        },
    )

    assert response.status_code == 201, response.text
    destination_airport_id = response.json()["id"]

    # Create origin terminal.
    response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": airport_id,
            "code": "T1",
            "name": "Terminal 1",
            "description": "Main departure terminal",
        },
    )

    assert response.status_code == 201, response.text
    terminal_id = response.json()["id"]

    # Create destination terminal.
    response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": destination_airport_id,
            "code": "T2",
            "name": "Terminal 2",
            "description": "Destination terminal",
        },
    )

    assert response.status_code == 201, response.text
    destination_terminal_id = response.json()["id"]

    # Create flight.
    response = client.post(
        "/api/v1/flights/",
        headers=admin_headers,
        json={
            "flight_number": f"AI{unique_value()[:4]}",
            "airline": "Air India",
            "flight_type": "domestic",
            "origin_airport_id": airport_id,
            "destination_airport_id": destination_airport_id,
            "departure_terminal_id": terminal_id,
            "arrival_terminal_id": destination_terminal_id,
            "scheduled_departure": (
                datetime.now(timezone.utc) + timedelta(days=2)
            ).isoformat(),
            "scheduled_arrival": (
                datetime.now(timezone.utc) + timedelta(days=2, hours=3)
            ).isoformat(),
            "aircraft_type": "Airbus A320",
            "capacity": 180,
        },
    )

    assert response.status_code == 201, response.text
    flight_id = response.json()["id"]

    # Create check-in counter.
    response = client.post(
        "/api/v1/counters/",
        headers=admin_headers,
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Screening Test Counter",
            "airline": "Air India",
            "description": "Test counter",
        },
    )

    assert response.status_code == 201, response.text
    counter_id = response.json()["id"]


def create_passenger():
    global passenger_counter

    passenger_counter += 1
    value = unique_value()

    phone_number = f"9{passenger_counter:09d}"

    response = client.post(
        "/api/v1/passengers/",
        headers=admin_headers,
        json={
            "flight_id": flight_id,
            "full_name": f"Screening Passenger {value}",
            "email": f"screening_{value.lower()}@example.com",
            "phone": phone_number,
            "date_of_birth": "1995-05-15",
            "nationality": "Indian",
            "identification_type": "passport",
            "identification_number": f"P{value}",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_checkin(passenger_id):
    global seat_counter

    seat_counter += 1

    response = client.post(
        "/api/v1/checkins/",
        headers=admin_headers,
        json={
            "passenger_id": passenger_id,
            "flight_id": flight_id,
            "counter_id": counter_id,
            "seat_number": f"{seat_counter}A",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_baggage():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    response = client.post(
        "/api/v1/baggage/",
        headers=admin_headers,
        json={
            "passenger_id": passenger["id"],
            "flight_id": flight_id,
            "checkin_id": checkin["id"],
            "baggage_type": "checked",
            "weight_kg": 20.5,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def start_screening(baggage_id, method="x_ray"):
    return client.post(
        f"/api/v1/baggage-screenings/{baggage_id}/start",
        headers=admin_headers,
        json={
            "screening_method": method,
            "notes": "Initial baggage screening",
        },
    )


def complete_screening(screening_id, result="cleared"):
    return client.patch(
        f"/api/v1/baggage-screenings/{screening_id}/complete",
        headers=admin_headers,
        json={
            "status": result,
            "notes": "Screening completed",
        },
    )


# ---------------------------------------------------------
# START SCREENING TESTS
# ---------------------------------------------------------

def test_admin_can_start_baggage_screening():
    baggage = create_baggage()

    response = start_screening(baggage["id"])

    assert response.status_code == 201, response.text
    assert response.json()["baggage_id"] == baggage["id"]
    assert response.json()["screening_method"] == "x_ray"
    assert response.json()["status"] == "in_progress"
    assert response.json()["screened_by"] is not None


@pytest.mark.parametrize(
    "method",
    ["x_ray", "ct_scan", "etd", "physical"],
)
def test_all_screening_methods_are_supported(method):
    baggage = create_baggage()

    response = start_screening(baggage["id"], method)

    assert response.status_code == 201, response.text
    assert response.json()["screening_method"] == method


def test_screening_requires_valid_baggage():
    response = start_screening(str(uuid.uuid4()))

    assert response.status_code == 404


def test_screening_requires_authentication():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-screenings/{baggage['id']}/start",
        json={
            "screening_method": "x_ray",
            "notes": "Test",
        },
    )

    assert response.status_code in (401, 403)


def test_screening_rejects_invalid_method():
    baggage = create_baggage()

    response = start_screening(
        baggage["id"],
        "invalid_method",
    )

    assert response.status_code == 422


def test_screening_rejects_missing_method():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-screenings/{baggage['id']}/start",
        headers=admin_headers,
        json={"notes": "Missing method"},
    )

    assert response.status_code == 422


def test_screening_rejects_empty_notes_only_if_method_missing():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-screenings/{baggage['id']}/start",
        headers=admin_headers,
        json={"notes": "Valid notes"},
    )

    assert response.status_code == 422


def test_screening_rejects_long_notes():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-screenings/{baggage['id']}/start",
        headers=admin_headers,
        json={
            "screening_method": "x_ray",
            "notes": "A" * 2001,
        },
    )

    assert response.status_code == 422


def test_duplicate_active_screening_is_rejected():
    baggage = create_baggage()

    first = start_screening(baggage["id"])
    assert first.status_code == 201, first.text

    second = start_screening(baggage["id"])

    assert second.status_code == 409


# ---------------------------------------------------------
# COMPLETE SCREENING TESTS
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "result",
    ["cleared", "rejected", "manual_inspection"],
)
def test_admin_can_complete_screening_with_valid_result(result):
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    assert start.status_code == 201, start.text

    screening_id = start.json()["id"]

    response = complete_screening(screening_id, result)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == result
    assert response.json()["completed_at"] is not None


def test_cannot_complete_screening_with_in_progress_status():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    response = complete_screening(
        screening_id,
        "in_progress",
    )

    assert response.status_code == 400


def test_cannot_complete_nonexistent_screening():
    response = complete_screening(
        str(uuid.uuid4()),
        "cleared",
    )

    assert response.status_code == 404


def test_completed_screening_cannot_be_completed_again():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    first = complete_screening(screening_id, "cleared")
    assert first.status_code == 200, first.text

    second = complete_screening(screening_id, "rejected")

    assert second.status_code == 409


def test_cleared_baggage_cannot_be_screened_again():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    completed = complete_screening(screening_id, "cleared")
    assert completed.status_code == 200, completed.text

    second = start_screening(baggage["id"])

    assert second.status_code == 409


def test_rejected_baggage_cannot_be_screened_again():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    completed = complete_screening(screening_id, "rejected")
    assert completed.status_code == 200, completed.text

    second = start_screening(baggage["id"])

    assert second.status_code == 409


def test_manual_inspection_allows_another_screening():
    baggage = create_baggage()

    first = start_screening(baggage["id"])
    assert first.status_code == 201, first.text

    completed = complete_screening(
        first.json()["id"],
        "manual_inspection",
    )
    assert completed.status_code == 200, completed.text

    second = start_screening(
        baggage["id"],
        "physical",
    )

    assert second.status_code == 201, second.text
    assert second.json()["status"] == "in_progress"
    assert second.json()["screening_method"] == "physical"


# ---------------------------------------------------------
# GET SCREENING AND HISTORY TESTS
# ---------------------------------------------------------

def test_admin_can_get_screening_record():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    response = client.get(
        f"/api/v1/baggage-screenings/record/{screening_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == screening_id


def test_get_nonexistent_screening_record():
    response = client.get(
        f"/api/v1/baggage-screenings/record/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_get_baggage_screening_history():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    assert start.status_code == 201, start.text

    complete = complete_screening(
        start.json()["id"],
        "manual_inspection",
    )
    assert complete.status_code == 200, complete.text

    second = start_screening(
        baggage["id"],
        "physical",
    )
    assert second.status_code == 201, second.text

    response = client.get(
        f"/api/v1/baggage-screenings/{baggage['id']}/history",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2


def test_get_history_for_nonexistent_baggage():
    response = client.get(
        f"/api/v1/baggage-screenings/{uuid.uuid4()}/history",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_screening_history_pagination():
    baggage = create_baggage()

    first = start_screening(baggage["id"])
    assert first.status_code == 201, first.text

    complete = complete_screening(
        first.json()["id"],
        "manual_inspection",
    )
    assert complete.status_code == 200, complete.text

    second = start_screening(
        baggage["id"],
        "physical",
    )
    assert second.status_code == 201, second.text

    response = client.get(
        f"/api/v1/baggage-screenings/{baggage['id']}/history",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 1,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["pages"] == 2


def test_screening_history_rejects_invalid_pagination():
    baggage = create_baggage()

    response = client.get(
        f"/api/v1/baggage-screenings/{baggage['id']}/history",
        headers=admin_headers,
        params={
            "page": 0,
            "page_size": 0,
        },
    )

    assert response.status_code == 422


def test_screening_history_requires_authentication():
    baggage = create_baggage()

    response = client.get(
        f"/api/v1/baggage-screenings/{baggage['id']}/history"
    )

    assert response.status_code in (401, 403)


# ---------------------------------------------------------
# AUTHORIZATION AND VALIDATION TESTS
# ---------------------------------------------------------

def test_complete_screening_requires_authentication():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    response = client.patch(
        f"/api/v1/baggage-screenings/{screening_id}/complete",
        json={"status": "cleared"},
    )

    assert response.status_code in (401, 403)


def test_complete_screening_rejects_invalid_status():
    baggage = create_baggage()

    start = start_screening(baggage["id"])
    screening_id = start.json()["id"]

    response = client.patch(
        f"/api/v1/baggage-screenings/{screening_id}/complete",
        headers=admin_headers,
        json={"status": "invalid_status"},
    )

    assert response.status_code == 422


def test_screening_response_contains_timestamps():
    baggage = create_baggage()

    response = start_screening(baggage["id"])

    assert response.status_code == 201, response.text
    assert response.json()["started_at"] is not None
    assert response.json()["completed_at"] is None


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
