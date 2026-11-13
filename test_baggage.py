
# tests/test_baggage.py

import os
import uuid

from datetime import datetime, timedelta, timezone

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


client = TestClient(app)

PASSWORD = "AirportTest@12345"

admin_headers = {}

airport_id = None
terminal_id = None
destination_airport_id = None
destination_terminal_id = None
flight_id = None
counter_id = None


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

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = User(
            full_name="Baggage Test Admin",
            email="baggage_admin@airport.com",
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
            "email": "baggage_admin@airport.com",
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    admin_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Create origin airport
    airport_response = client.post(
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

    assert airport_response.status_code == 201, airport_response.text
    airport_id = airport_response.json()["id"]

    # Create origin terminal
    terminal_response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": airport_id,
            "code": "T1",
            "name": "Terminal 1",
            "description": "Main departure terminal",
        },
    )

    assert terminal_response.status_code == 201, terminal_response.text
    terminal_id = terminal_response.json()["id"]

    # Create destination airport
    destination_response = client.post(
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

    assert destination_response.status_code == 201, destination_response.text
    destination_airport_id = destination_response.json()["id"]

    # Create destination terminal
    destination_terminal_response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": destination_airport_id,
            "code": "T2",
            "name": "Terminal 2",
            "description": "Destination terminal",
        },
    )

    assert destination_terminal_response.status_code == 201, destination_terminal_response.text
    destination_terminal_id = destination_terminal_response.json()["id"]

    # Create flight
    now = datetime.now(timezone.utc)

    flight_response = client.post(
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
            "scheduled_departure": (now + timedelta(days=30)).isoformat(),
            "scheduled_arrival": (now + timedelta(days=30, hours=2)).isoformat(),
            "aircraft_type": "Airbus A320",
            "capacity": 180,
        },
    )

    assert flight_response.status_code == 201, flight_response.text
    flight_id = flight_response.json()["id"]

    # Create check-in counter
    counter_response = client.post(
        "/api/v1/counters/",
        headers=admin_headers,
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Baggage Test Counter",
            "airline": "Air India",
            "description": "Counter for baggage tests",
        },
    )

    assert counter_response.status_code == 201, counter_response.text
    counter_id = counter_response.json()["id"]


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
    value = unique_value()

    response = client.post(
        "/api/v1/checkins/",
        headers=admin_headers,
        json={
            "passenger_id": passenger_id,
            "flight_id": flight_id,
            "counter_id": counter_id,
            "seat_number": f"{value[:2]}1",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_baggage(
    passenger_id=None,
    checkin_id=None,
    baggage_type="checked",
    weight_kg=23.5,
    selected_flight_id=None,
):
    if passenger_id is None:
        passenger = create_passenger()
        passenger_id = passenger["id"]

    if checkin_id is None:
        checkin = create_checkin(passenger_id)
        checkin_id = checkin["id"]

    response = client.post(
        "/api/v1/baggage/",
        headers=admin_headers,
        json={
            "passenger_id": passenger_id,
            "flight_id": selected_flight_id or flight_id,
            "checkin_id": checkin_id,
            "baggage_type": baggage_type,
            "weight_kg": weight_kg,
        },
    )

    return response


def test_admin_can_register_baggage():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    response = create_baggage(
        passenger_id=passenger["id"],
        checkin_id=checkin["id"],
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["passenger_id"] == passenger["id"]
    assert data["flight_id"] == flight_id
    assert data["checkin_id"] == checkin["id"]
    assert data["baggage_type"] == "checked"
    assert data["weight_kg"] == 23.5
    assert data["status"] == "registered"
    assert data["baggage_tag"].startswith("BAG-")


def test_baggage_tag_is_generated_automatically():
    response = create_baggage()

    assert response.status_code == 201, response.text
    assert response.json()["baggage_tag"]
    assert response.json()["baggage_tag"].startswith("BAG-")


def test_baggage_tags_are_unique():
    first = create_baggage()
    second = create_baggage()

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    assert (
        first.json()["baggage_tag"]
        != second.json()["baggage_tag"]
    )


def test_admin_can_register_cabin_baggage():
    response = create_baggage(
        baggage_type="cabin",
        weight_kg=7.5,
    )

    assert response.status_code == 201, response.text
    assert response.json()["baggage_type"] == "cabin"


def test_admin_can_register_special_baggage():
    response = create_baggage(
        baggage_type="special",
        weight_kg=15,
    )

    assert response.status_code == 201, response.text
    assert response.json()["baggage_type"] == "special"


def test_baggage_requires_valid_passenger():
    response = create_baggage(
        passenger_id=str(uuid.uuid4()),
        checkin_id=str(uuid.uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Passenger not found"


def test_baggage_requires_valid_flight():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    response = client.post(
        "/api/v1/baggage/",
        headers=admin_headers,
        json={
            "passenger_id": passenger["id"],
            "flight_id": str(uuid.uuid4()),
            "checkin_id": checkin["id"],
            "baggage_type": "checked",
            "weight_kg": 20,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Flight not found"


def test_baggage_requires_valid_checkin():
    passenger = create_passenger()

    response = client.post(
        "/api/v1/baggage/",
        headers=admin_headers,
        json={
            "passenger_id": passenger["id"],
            "flight_id": flight_id,
            "checkin_id": str(uuid.uuid4()),
            "baggage_type": "checked",
            "weight_kg": 20,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Check-in not found"


def test_checkin_must_belong_to_passenger():
    first_passenger = create_passenger()
    second_passenger = create_passenger()

    checkin = create_checkin(first_passenger["id"])

    response = create_baggage(
        passenger_id=second_passenger["id"],
        checkin_id=checkin["id"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Check-in does not belong to this passenger and flight"
    )


def test_baggage_requires_completed_checkin():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    cancel_response = client.patch(
        f"/api/v1/checkins/{checkin['id']}/cancel",
        headers=admin_headers,
    )

    assert cancel_response.status_code == 200, cancel_response.text

    response = create_baggage(
        passenger_id=passenger["id"],
        checkin_id=checkin["id"],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Passenger must have a completed check-in"
    )


def test_baggage_rejects_zero_weight():
    response = create_baggage(weight_kg=0)

    assert response.status_code == 422


def test_baggage_rejects_negative_weight():
    response = create_baggage(weight_kg=-5)

    assert response.status_code == 422


def test_baggage_rejects_weight_above_100_kg():
    response = create_baggage(weight_kg=101)

    assert response.status_code == 422


def test_baggage_rejects_invalid_baggage_type():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    response = client.post(
        "/api/v1/baggage/",
        headers=admin_headers,
        json={
            "passenger_id": passenger["id"],
            "flight_id": flight_id,
            "checkin_id": checkin["id"],
            "baggage_type": "unknown",
            "weight_kg": 20,
        },
    )

    assert response.status_code == 422


def test_admin_can_list_baggage():
    create_baggage()
    create_baggage()

    response = client.get(
        "/api/v1/baggage/",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) >= 2


def test_baggage_list_can_filter_by_flight():
    create_baggage()

    response = client.get(
        "/api/v1/baggage/",
        headers=admin_headers,
        params={"flight_id": flight_id},
    )

    assert response.status_code == 200, response.text
    assert all(
        item["flight_id"] == flight_id
        for item in response.json()
    )


def test_baggage_list_can_filter_by_passenger():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    create_baggage(
        passenger_id=passenger["id"],
        checkin_id=checkin["id"],
    )

    response = client.get(
        "/api/v1/baggage/",
        headers=admin_headers,
        params={"passenger_id": passenger["id"]},
    )

    assert response.status_code == 200, response.text
    assert all(
        item["passenger_id"] == passenger["id"]
        for item in response.json()
    )


def test_baggage_list_can_filter_by_checkin():
    passenger = create_passenger()
    checkin = create_checkin(passenger["id"])

    create_baggage(
        passenger_id=passenger["id"],
        checkin_id=checkin["id"],
    )

    response = client.get(
        "/api/v1/baggage/",
        headers=admin_headers,
        params={"checkin_id": checkin["id"]},
    )

    assert response.status_code == 200, response.text
    assert all(
        item["checkin_id"] == checkin["id"]
        for item in response.json()
    )


def test_admin_can_get_baggage_by_id():
    created = create_baggage()
    baggage_id = created.json()["id"]

    response = client.get(
        f"/api/v1/baggage/{baggage_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == baggage_id


def test_admin_can_get_baggage_by_tag():
    created = create_baggage()
    baggage_tag = created.json()["baggage_tag"]

    response = client.get(
        f"/api/v1/baggage/tag/{baggage_tag}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["baggage_tag"] == baggage_tag


def test_get_nonexistent_baggage():
    response = client.get(
        f"/api/v1/baggage/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Baggage not found"


def test_get_nonexistent_baggage_tag():
    response = client.get(
        "/api/v1/baggage/tag/BAG-NOT-FOUND",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Baggage not found"


def test_admin_can_cancel_baggage():
    created = create_baggage()
    baggage_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/baggage/{baggage_id}/cancel",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert response.json()["baggage_id"] == baggage_id


def test_baggage_cannot_be_cancelled_twice():
    created = create_baggage()
    baggage_id = created.json()["id"]

    first = client.patch(
        f"/api/v1/baggage/{baggage_id}/cancel",
        headers=admin_headers,
    )

    assert first.status_code == 200, first.text

    second = client.patch(
        f"/api/v1/baggage/{baggage_id}/cancel",
        headers=admin_headers,
    )

    assert second.status_code == 400
    assert second.json()["detail"] == "Baggage is already cancelled"


def test_baggage_endpoints_require_authentication():
    response = client.get("/api/v1/baggage/")

    assert response.status_code == 401


def test_baggage_rejects_invalid_pagination():
    response = client.get(
        "/api/v1/baggage/",
        headers=admin_headers,
        params={"skip": -1},
    )

    assert response.status_code == 422
