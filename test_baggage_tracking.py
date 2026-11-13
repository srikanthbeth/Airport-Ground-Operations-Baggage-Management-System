
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
from main import app
from core.constants import UserRole
from core.security import hash_password
from models.user import User
import models


client = TestClient(app)

PASSWORD = "AirportTest@12345"

admin_headers = {}

airport_id = None
terminal_id = None
destination_airport_id = None
destination_terminal_id = None
flight_id = None
counter_id = None

# Sequential unique seat numbers for this test run.
seat_counter = 0


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def setup_module(module):
    global admin_headers
    global airport_id
    global terminal_id
    global destination_airport_id
    global destination_terminal_id
    global flight_id
    global counter_id
    global seat_counter

    seat_counter = 0

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = User(
            full_name="Baggage Tracking Test Admin",
            email="tracking_admin@airport.com",
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
            "email": "tracking_admin@airport.com",
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    admin_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Origin airport
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

    # Origin terminal
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

    # Destination airport
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

    # Destination terminal
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

    # Flight
    departure = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

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
            "scheduled_departure": departure.isoformat(),
            "scheduled_arrival": (
                departure + timedelta(hours=2)
            ).isoformat(),
            "aircraft_type": "Airbus A320",
            "capacity": 180,
        },
    )

    assert response.status_code == 201, response.text
    flight_id = response.json()["id"]

    # Check-in counter
    response = client.post(
        "/api/v1/counters/",
        headers=admin_headers,
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Baggage Tracking Test Counter",
            "airline": "Air India",
            "description": "Test counter",
        },
    )

    assert response.status_code == 201, response.text
    counter_id = response.json()["id"]


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def create_passenger():
    value = unique_value()

    response = client.post(
        "/api/v1/passengers/",
        headers=admin_headers,
        json={
            "flight_id": flight_id,
            "full_name": "Rahul Sharma",
            "email": f"rahul_{value}@example.com",
            "phone": "+919876543210",
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


def create_tracking(baggage_id, tracking_status="received"):
    return client.post(
        f"/api/v1/baggage-tracking/{baggage_id}",
        headers=admin_headers,
        json={
            "status": tracking_status,
            "location": "Hyderabad Airport",
            "description": "Baggage tracking test event",
        },
    )


def create_received_baggage():
    baggage = create_baggage()

    response = create_tracking(
        baggage["id"],
        "received",
    )

    assert response.status_code == 201, response.text

    return baggage, response.json()


def test_admin_can_record_initial_received_status():
    baggage = create_baggage()

    response = create_tracking(baggage["id"], "received")

    assert response.status_code == 201
    assert response.json()["status"] == "received"
    assert response.json()["baggage_id"] == baggage["id"]
    assert response.json()["recorded_by"] is not None


def test_first_tracking_status_must_be_received():
    baggage = create_baggage()

    response = create_tracking(baggage["id"], "sorted")

    assert response.status_code == 400


def test_admin_can_move_baggage_to_sorted():
    baggage, _ = create_received_baggage()

    response = create_tracking(baggage["id"], "sorted")

    assert response.status_code == 201
    assert response.json()["status"] == "sorted"


def test_admin_can_complete_tracking_lifecycle():
    baggage, _ = create_received_baggage()

    lifecycle = [
        "sorted",
        "loaded",
        "in_transit",
        "unloaded",
        "arrived",
        "claimed",
    ]

    for tracking_status in lifecycle:
        response = create_tracking(
            baggage["id"],
            tracking_status,
        )

        assert response.status_code == 201, response.text
        assert response.json()["status"] == tracking_status


def test_baggage_cannot_skip_tracking_status():
    baggage, _ = create_received_baggage()

    response = create_tracking(baggage["id"], "loaded")

    assert response.status_code == 409


def test_baggage_cannot_move_backwards():
    baggage, _ = create_received_baggage()

    sorted_response = create_tracking(
        baggage["id"],
        "sorted",
    )

    assert sorted_response.status_code == 201

    response = create_tracking(
        baggage["id"],
        "received",
    )

    assert response.status_code == 409


def test_claimed_baggage_cannot_be_tracked_again():
    baggage, _ = create_received_baggage()

    for tracking_status in [
        "sorted",
        "loaded",
        "in_transit",
        "unloaded",
        "arrived",
        "claimed",
    ]:
        response = create_tracking(
            baggage["id"],
            tracking_status,
        )

        assert response.status_code == 201, response.text

    response = create_tracking(
        baggage["id"],
        "loaded",
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "tracking_status",
    ["lost", "damaged"],
)
def test_baggage_can_be_marked_as_exception(tracking_status):
    baggage, _ = create_received_baggage()

    response = create_tracking(
        baggage["id"],
        tracking_status,
    )

    assert response.status_code == 201
    assert response.json()["status"] == tracking_status


def test_exception_status_is_terminal():
    baggage, _ = create_received_baggage()

    response = create_tracking(baggage["id"], "lost")
    assert response.status_code == 201

    response = create_tracking(baggage["id"], "sorted")
    assert response.status_code == 409


def test_tracking_requires_valid_baggage():
    response = create_tracking(
        str(uuid.uuid4()),
        "received",
    )

    assert response.status_code == 404


def test_tracking_requires_authentication():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-tracking/{baggage['id']}",
        json={
            "status": "received",
            "location": "Hyderabad Airport",
        },
    )

    assert response.status_code == 401


def test_tracking_rejects_invalid_status():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-tracking/{baggage['id']}",
        headers=admin_headers,
        json={
            "status": "unknown",
            "location": "Hyderabad Airport",
        },
    )

    assert response.status_code == 422


def test_tracking_requires_location():
    baggage = create_baggage()

    response = client.post(
        f"/api/v1/baggage-tracking/{baggage['id']}",
        headers=admin_headers,
        json={
            "status": "received",
            "location": "",
        },
    )

    assert response.status_code == 422


def test_admin_can_get_tracking_history():
    baggage, _ = create_received_baggage()

    create_tracking(baggage["id"], "sorted")
    create_tracking(baggage["id"], "loaded")

    response = client.get(
        f"/api/v1/baggage-tracking/{baggage['id']}/history",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 3


def test_admin_can_get_latest_tracking():
    baggage, _ = create_received_baggage()

    create_tracking(baggage["id"], "sorted")

    response = client.get(
        f"/api/v1/baggage-tracking/{baggage['id']}/latest",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sorted"


def test_admin_can_get_tracking_record():
    baggage, tracking = create_received_baggage()

    response = client.get(
        f"/api/v1/baggage-tracking/record/{tracking['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == tracking["id"]


def test_get_nonexistent_tracking_record():
    response = client.get(
        f"/api/v1/baggage-tracking/record/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_get_history_for_nonexistent_baggage():
    response = client.get(
        f"/api/v1/baggage-tracking/{uuid.uuid4()}/history",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_tracking_history_pagination():
    baggage, _ = create_received_baggage()

    create_tracking(baggage["id"], "sorted")
    create_tracking(baggage["id"], "loaded")

    response = client.get(
        f"/api/v1/baggage-tracking/{baggage['id']}/history",
        headers=admin_headers,
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    assert len(response.json()["items"]) == 2


def test_tracking_history_rejects_invalid_pagination():
    baggage, _ = create_received_baggage()

    response = client.get(
        f"/api/v1/baggage-tracking/{baggage['id']}/history",
        headers=admin_headers,
        params={"page": 0, "page_size": 200},
    )

    assert response.status_code == 422
