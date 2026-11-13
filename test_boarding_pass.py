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
            full_name="Boarding Pass Test Admin",
            email="boarding_admin@airport.com",
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
            "email": "boarding_admin@airport.com",
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
            "name": f"Boarding Test Airport {unique_value()}",
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
            "name": f"Boarding Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Boarding pass testing terminal",
        },
        headers=admin_token,
    )

    assert terminal.status_code == 201, terminal.text
    terminal_id = terminal.json()["id"]

    destination_airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Boarding Destination {unique_value()}",
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
            "name": f"Boarding Destination Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Boarding destination terminal",
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
            "name": "Boarding Test Counter",
            "airline": "Air India",
            "description": "Boarding pass test counter",
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
        "full_name": "Ananya Rao",
        "email": f"ananya_{unique_value()}@example.com",
        "phone": "+919876543210",
        "date_of_birth": "1996-08-20",
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


def create_checkin(passenger_id, seat_number=None):
    if seat_number is None:
        seat_number = f"{unique_value()[:2]}1"

    return client.post(
        "/api/v1/checkins/",
        json={
            "passenger_id": passenger_id,
            "flight_id": flight_id,
            "counter_id": counter_id,
            "seat_number": seat_number,
        },
        headers=admin_token,
    )


def create_checkin_with_boarding_pass():
    passenger = create_passenger()
    assert passenger.status_code == 201, passenger.text

    checkin = create_checkin(passenger.json()["id"])
    assert checkin.status_code == 201, checkin.text

    boarding_pass = client.get(
        f"/api/v1/boarding-passes/checkin/{checkin.json()['id']}",
        headers=admin_token,
    )

    assert boarding_pass.status_code == 200, boarding_pass.text

    return checkin.json(), boarding_pass.json()


def test_checkin_automatically_generates_boarding_pass():
    checkin, boarding_pass = create_checkin_with_boarding_pass()

    assert boarding_pass["checkin_id"] == checkin["id"]
    assert boarding_pass["boarding_pass_number"]
    assert boarding_pass["status"] == "active"
    assert boarding_pass["issued_at"]


def test_admin_can_get_boarding_pass_by_checkin_id():
    checkin, boarding_pass = create_checkin_with_boarding_pass()

    response = client.get(
        f"/api/v1/boarding-passes/checkin/{checkin['id']}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["id"] == boarding_pass["id"]
    assert response.json()["checkin_id"] == checkin["id"]


def test_admin_can_get_boarding_pass_by_number():
    checkin, boarding_pass = create_checkin_with_boarding_pass()

    response = client.get(
        f"/api/v1/boarding-passes/number/"
        f"{boarding_pass['boarding_pass_number']}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["id"] == boarding_pass["id"]
    assert response.json()["checkin_id"] == checkin["id"]


def test_boarding_pass_numbers_are_unique():
    _, first_pass = create_checkin_with_boarding_pass()
    _, second_pass = create_checkin_with_boarding_pass()

    assert (
        first_pass["boarding_pass_number"]
        != second_pass["boarding_pass_number"]
    )


def test_get_nonexistent_boarding_pass_by_number():
    response = client.get(
        "/api/v1/boarding-passes/number/INVALID-BOARDING-PASS",
        headers=admin_token,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Boarding pass not found"


def test_get_nonexistent_boarding_pass_by_checkin_id():
    response = client.get(
        f"/api/v1/boarding-passes/checkin/{uuid.uuid4()}",
        headers=admin_token,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Boarding pass not found"


def test_cancelled_checkin_voids_boarding_pass():
    checkin, boarding_pass = create_checkin_with_boarding_pass()

    cancellation = client.patch(
        f"/api/v1/checkins/{checkin['id']}/cancel",
        headers=admin_token,
    )

    assert cancellation.status_code == 200, cancellation.text
    assert cancellation.json()["status"] == "cancelled"

    response = client.get(
        f"/api/v1/boarding-passes/checkin/{checkin['id']}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["id"] == boarding_pass["id"]
    assert response.json()["status"] == "void"


def test_boarding_pass_endpoints_require_authentication():
    response = client.get(
        "/api/v1/boarding-passes/number/INVALID-BOARDING-PASS"
    )

    assert response.status_code == 401