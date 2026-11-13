import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from db.base import Base
from db.session import engine
from main import app
from core.constants import UserRole
from core.security import hash_password
from db.session import SessionLocal
from models.user import User

client = TestClient(app)

PASSWORD = "AirportTest@12345"

admin_token = None
flight_id = None
terminal_id = None
counter_id = None


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def setup_module(module):
    global admin_token, flight_id, terminal_id, counter_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = User(
            full_name="Airport Check-in Test Admin",
            email="checkin_admin@airport.com",
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
            "email": "checkin_admin@airport.com",
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    admin_token = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Check-in Test Airport {unique_value()}",
            "code": unique_value()[:3],
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
        headers=admin_token,
    )

    assert airport.status_code == 201, airport.text

    terminal = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport.json()["id"],
            "name": f"Check-in Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Check-in testing terminal",
        },
        headers=admin_token,
    )

    assert terminal.status_code == 201, terminal.text
    terminal_id = terminal.json()["id"]

    destination_airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Check-in Destination {unique_value()}",
            "code": unique_value()[:3],
            "city": "Delhi",
            "country": "India",
            "address": "Delhi, India",
            "timezone": "Asia/Kolkata",
        },
        headers=admin_token,
    )

    assert destination_airport.status_code == 201, destination_airport.text

    destination_terminal = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": destination_airport.json()["id"],
            "name": f"Destination Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Destination terminal",
        },
        headers=admin_token,
    )

    assert destination_terminal.status_code == 201, destination_terminal.text

    departure = datetime(2030, 5, 10, 10, 0, tzinfo=timezone.utc)

    flight = client.post(
        "/api/v1/flights/",
        json={
            "flight_number": f"AI{unique_value()[:6]}",
            "airline": "Air India",
            "flight_type": "domestic",
            "origin_airport_id": airport.json()["id"],
            "destination_airport_id": destination_airport.json()["id"],
            "departure_terminal_id": terminal_id,
            "arrival_terminal_id": destination_terminal.json()["id"],
            "scheduled_departure": departure.isoformat(),
            "scheduled_arrival": (
                departure + timedelta(hours=2)
            ).isoformat(),
            "aircraft_type": "Airbus A320",
            "capacity": 180,
        },
        headers=admin_token,
    )

    assert flight.status_code == 201, flight.text
    flight_id = flight.json()["id"]

    counter = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Check-in Counter A1",
            "airline": "Air India",
            "description": "Level 6 test counter",
        },
        headers=admin_token,
    )

    assert counter.status_code == 201, counter.text
    counter_id = counter.json()["id"]


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def passenger_payload(**overrides):
    payload = {
        "flight_id": flight_id,
        "full_name": "Rahul Sharma",
        "email": f"rahul_{unique_value()}@example.com",
        "phone": "+919876543210",
        "date_of_birth": "1995-05-15",
        "nationality": "Indian",
        "identification_type": "passport",
        "identification_number": f"P{unique_value()}",
    }

    payload.update(overrides)
    return payload


def create_passenger(**overrides):
    return client.post(
        "/api/v1/passengers/",
        json=passenger_payload(**overrides),
        headers=admin_token,
    )


def checkin_payload(passenger_id, **overrides):
    payload = {
        "passenger_id": passenger_id,
        "flight_id": flight_id,
        "counter_id": counter_id,
        "seat_number": f"{unique_value()[:2]}1",
    }

    payload.update(overrides)
    return payload


def create_checkin(passenger_id, **overrides):
    return client.post(
        "/api/v1/checkins/",
        json=checkin_payload(passenger_id, **overrides),
        headers=admin_token,
    )


def test_admin_can_check_in_passenger():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    response = create_checkin(passenger.json()["id"])

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["passenger_id"] == passenger.json()["id"]
    assert data["flight_id"] == flight_id
    assert data["counter_id"] == counter_id
    assert data["status"] == "completed"
    assert data["seat_number"]


def test_checkin_seat_number_is_normalized():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    response = create_checkin(
        passenger.json()["id"],
        seat_number="  12a  ",
    )

    assert response.status_code == 201, response.text
    assert response.json()["seat_number"] == "12A"


def test_duplicate_checkin_for_same_passenger_and_flight_rejected():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    first = create_checkin(
        passenger.json()["id"],
        seat_number="10A",
    )
    assert first.status_code == 201, first.text

    second = create_checkin(
        passenger.json()["id"],
        seat_number="10B",
    )

    assert second.status_code == 409


def test_duplicate_seat_on_same_flight_rejected():
    first_passenger = create_passenger()
    second_passenger = create_passenger()

    assert first_passenger.status_code == 201, first_passenger.text
    assert second_passenger.status_code == 201, second_passenger.text

    first = create_checkin(
        first_passenger.json()["id"],
        seat_number="15A",
    )
    assert first.status_code == 201, first.text

    second = create_checkin(
        second_passenger.json()["id"],
        seat_number="15A",
    )

    assert second.status_code == 409


def test_checkin_requires_valid_passenger():
    response = client.post(
        "/api/v1/checkins/",
        json=checkin_payload(str(uuid.uuid4())),
        headers=admin_token,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Passenger not found"


def test_checkin_requires_valid_flight():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    response = create_checkin(
        passenger.json()["id"],
        flight_id=str(uuid.uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Flight not found"


def test_checkin_requires_valid_counter():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    response = create_checkin(
        passenger.json()["id"],
        counter_id=str(uuid.uuid4()),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Check-in counter not found"


def test_checkin_requires_seat_number():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    response = client.post(
        "/api/v1/checkins/",
        json=checkin_payload(
            passenger.json()["id"],
            seat_number="",
        ),
        headers=admin_token,
    )

    assert response.status_code == 422


def test_admin_can_list_checkins():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    created = create_checkin(passenger.json()["id"])
    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/checkins/",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(
        item["id"] == created.json()["id"]
        for item in response.json()
    )


def test_checkin_list_can_filter_by_flight():
    response = client.get(
        "/api/v1/checkins/",
        params={"flight_id": flight_id},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert all(
        item["flight_id"] == flight_id
        for item in response.json()
    )


def test_checkin_list_can_filter_by_passenger():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    created = create_checkin(passenger.json()["id"])
    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/checkins/",
        params={"passenger_id": passenger.json()["id"]},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert all(
        item["passenger_id"] == passenger.json()["id"]
        for item in response.json()
    )


def test_admin_can_get_checkin():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    created = create_checkin(passenger.json()["id"])
    assert created.status_code == 201, created.text

    response = client.get(
        f"/api/v1/checkins/{created.json()['id']}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created.json()["id"]


def test_get_nonexistent_checkin():
    response = client.get(
        f"/api/v1/checkins/{uuid.uuid4()}",
        headers=admin_token,
    )

    assert response.status_code == 404


def test_admin_can_cancel_checkin():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    created = create_checkin(passenger.json()["id"])
    assert created.status_code == 201, created.text

    response = client.patch(
        f"/api/v1/checkins/{created.json()['id']}/cancel",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Check-in cancelled successfully"
    assert response.json()["status"] == "cancelled"


def test_checkin_cannot_be_cancelled_twice():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    created = create_checkin(passenger.json()["id"])
    assert created.status_code == 201, created.text

    checkin_id = created.json()["id"]

    first = client.patch(
        f"/api/v1/checkins/{checkin_id}/cancel",
        headers=admin_token,
    )
    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/checkins/{checkin_id}/cancel",
        headers=admin_token,
    )

    assert second.status_code == 400


def test_checkin_endpoints_require_authentication():
    response = client.get("/api/v1/checkins/")

    assert response.status_code == 401


def test_checkin_rejects_invalid_pagination():
    response = client.get(
        "/api/v1/checkins/",
        params={"skip": -1},
        headers=admin_token,
    )

    assert response.status_code == 422