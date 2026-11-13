import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

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
airport_id = None
terminal_id = None


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def setup_module(module):
    global admin_token, flight_id, airport_id, terminal_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create Super Admin directly in the test database.
    db = SessionLocal()

    try:
        admin = User(
            full_name="Airport Test Admin",
            email="admin@airport.com",
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
            "email": "admin@airport.com",
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    admin_token = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Create origin airport.
    airport_response = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Passenger Test Airport {unique_value()}",
            "code": unique_value()[:3],
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
        headers=admin_token,
    )

    assert airport_response.status_code == 201, airport_response.text
    airport_id = airport_response.json()["id"]

    # Create origin terminal.
    terminal_response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport_id,
            "name": f"Passenger Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Passenger testing terminal",
        },
        headers=admin_token,
    )

    assert terminal_response.status_code == 201, terminal_response.text
    terminal_id = terminal_response.json()["id"]

    # Create destination airport.
    destination_airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Destination Airport {unique_value()}",
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
            "description": "Destination testing terminal",
        },
        headers=admin_token,
    )

    assert destination_terminal.status_code == 201, destination_terminal.text

    departure = datetime(2030, 5, 10, 10, 0, tzinfo=timezone.utc)

    flight_response = client.post(
        "/api/v1/flights/",
        json={
            "flight_number": f"AI{unique_value()[:6]}",
            "airline": "Air India",
            "flight_type": "domestic",
            "origin_airport_id": airport_id,
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

    assert flight_response.status_code == 201, flight_response.text
    flight_id = flight_response.json()["id"]

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


def test_admin_can_register_passenger():
    response = create_passenger()

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["full_name"] == "Rahul Sharma"
    assert data["flight_id"] == flight_id
    assert data["status"] == "active"


def test_passenger_name_is_trimmed():
    response = create_passenger(full_name="  Rahul Sharma  ")

    assert response.status_code == 201
    assert response.json()["full_name"] == "Rahul Sharma"


def test_duplicate_identification_for_same_flight_rejected():
    identification = f"P{unique_value()}"

    first = create_passenger(identification_number=identification)
    assert first.status_code == 201

    second = create_passenger(identification_number=identification)

    assert second.status_code == 409


def test_same_identification_allowed_for_different_flight():
    identification = f"P{unique_value()}"

    first = create_passenger(identification_number=identification)
    assert first.status_code == 201

    # Create another flight using the same origin terminal.
    destination_airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Second Destination {unique_value()}",
            "code": unique_value()[:3],
            "city": "Mumbai",
            "country": "India",
            "address": "Mumbai, Maharashtra",
            "timezone": "Asia/Kolkata",
        },
        headers=admin_token,
    )
    assert destination_airport.status_code == 201

    destination_terminal = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": destination_airport.json()["id"],
            "name": f"Second Destination Terminal {unique_value()}",
            "code": unique_value()[:3],
            "description": "Second destination terminal",
        },
        headers=admin_token,
    )
    assert destination_terminal.status_code == 201

    departure = datetime(2030, 5, 11, 10, 0, tzinfo=timezone.utc)

    second_flight = client.post(
        "/api/v1/flights/",
        json={
            "flight_number": f"AI{unique_value()[:6]}",
            "airline": "Air India",
            "flight_type": "domestic",
            "origin_airport_id": airport_id,
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
    assert second_flight.status_code == 201, second_flight.text

    response = create_passenger(
        flight_id=second_flight.json()["id"],
        identification_number=identification,
    )

    assert response.status_code == 201, response.text


def test_passenger_requires_valid_flight():
    response = create_passenger(flight_id=str(uuid.uuid4()))

    assert response.status_code == 404


def test_passenger_requires_full_name():
    response = create_passenger(full_name="")

    assert response.status_code == 422


def test_passenger_rejects_invalid_email():
    response = create_passenger(email="invalid-email")

    assert response.status_code == 422


def test_passenger_rejects_invalid_date_of_birth():
    response = create_passenger(
        date_of_birth=(date.today() + timedelta(days=1)).isoformat()
    )

    assert response.status_code == 422


def test_admin_can_list_passengers():
    create_passenger()

    response = client.get(
        "/api/v1/passengers/",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_passenger_list_search():
    name = f"Passenger {unique_value()}"

    created = create_passenger(full_name=name)
    assert created.status_code == 201

    response = client.get(
        "/api/v1/passengers/",
        params={"search": name},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert any(item["full_name"] == name for item in response.json())


def test_passenger_list_filter_by_flight():
    create_passenger()

    response = client.get(
        "/api/v1/passengers/",
        params={"flight_id": flight_id},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert all(item["flight_id"] == flight_id for item in response.json())


def test_passenger_list_pagination():
    response = client.get(
        "/api/v1/passengers/",
        params={"skip": 0, "limit": 2},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert len(response.json()) <= 2


def test_invalid_passenger_pagination():
    response = client.get(
        "/api/v1/passengers/",
        params={"skip": -1},
        headers=admin_token,
    )

    assert response.status_code == 422


def test_admin_can_get_passenger():
    created = create_passenger()
    assert created.status_code == 201

    response = client.get(
        f"/api/v1/passengers/{created.json()['id']}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created.json()["id"]


def test_get_nonexistent_passenger():
    response = client.get(
        f"/api/v1/passengers/{uuid.uuid4()}",
        headers=admin_token,
    )

    assert response.status_code == 404


def test_admin_can_update_passenger():
    created = create_passenger()
    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/passengers/{created.json()['id']}",
        json={"full_name": "Updated Passenger"},
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Passenger"


def test_cancelled_passenger_cannot_be_updated():
    created = create_passenger()
    assert created.status_code == 201

    passenger_id = created.json()["id"]

    cancelled = client.patch(
        f"/api/v1/passengers/{passenger_id}/cancel",
        headers=admin_token,
    )
    assert cancelled.status_code == 200

    updated = client.patch(
        f"/api/v1/passengers/{passenger_id}",
        json={"full_name": "Changed Name"},
        headers=admin_token,
    )

    assert updated.status_code == 400


def test_admin_can_cancel_passenger():
    created = create_passenger()
    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/passengers/{created.json()['id']}/cancel",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_passenger_cannot_be_cancelled_twice():
    created = create_passenger()
    assert created.status_code == 201

    passenger_id = created.json()["id"]

    first = client.patch(
        f"/api/v1/passengers/{passenger_id}/cancel",
        headers=admin_token,
    )
    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/passengers/{passenger_id}/cancel",
        headers=admin_token,
    )

    assert second.status_code == 400


def test_passenger_history_by_identification():
    identification = f"P{unique_value()}"

    created = create_passenger(identification_number=identification)
    assert created.status_code == 201

    response = client.get(
        f"/api/v1/passengers/history/passport/{identification}",
        headers=admin_token,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["identification_number"] == identification


def test_passenger_endpoints_require_authentication():
    response = client.get("/api/v1/passengers/")

    assert response.status_code == 401