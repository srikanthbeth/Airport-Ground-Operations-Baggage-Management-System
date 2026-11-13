import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient


load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from main import app
from db.base import Base
from db.session import engine
from db.session import SessionLocal
from models import User
from core.constants import UserRole
from core.security import hash_password


client = TestClient(app)

PASSWORD = "FlightTest@12345"
ADMIN_EMAIL = "flightadmin@airport.example.com"


def unique_email():
    return f"flight_{uuid.uuid4().hex[:10]}@example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    admin = User(
        full_name="Flight Test Admin",
        email=ADMIN_EMAIL,
        hashed_password=hash_password(PASSWORD),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )

    db.add(admin)
    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def admin_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_airports(headers):
    suffix = uuid.uuid4().hex[:5].upper()

    origin_response = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Origin Airport {suffix}",
            "code": f"O{suffix}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert origin_response.status_code == 201, origin_response.text

    destination_response = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Destination Airport {suffix}",
            "code": f"D{suffix}",
            "city": "Delhi",
            "country": "India",
            "address": "Delhi, India",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert destination_response.status_code == 201, destination_response.text

    return origin_response.json(), destination_response.json()


def create_terminal(headers, airport_id):
    suffix = uuid.uuid4().hex[:5].upper()

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport_id,
            "name": f"Terminal {suffix}",
            "code": f"T{suffix}",
            "description": "Flight operations terminal",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def flight_payload(headers):
    origin, destination = create_airports(headers)

    departure_terminal = create_terminal(
        headers,
        origin["id"],
    )

    arrival_terminal = create_terminal(
        headers,
        destination["id"],
    )

    departure = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

    arrival = departure + timedelta(hours=2)

    return {
        "flight_number": f"AI{uuid.uuid4().hex[:6].upper()}",
        "airline": "Air India",
        "flight_type": "domestic",
        "origin_airport_id": origin["id"],
        "destination_airport_id": destination["id"],
        "departure_terminal_id": departure_terminal["id"],
        "arrival_terminal_id": arrival_terminal["id"],
        "scheduled_departure": departure.isoformat(),
        "scheduled_arrival": arrival.isoformat(),
        "aircraft_type": "Airbus A320",
        "capacity": 180,
    }


def create_flight(headers):
    payload = flight_payload(headers)

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json(), payload


def register_regular_user():
    email = unique_email()

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Regular Flight User",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert registration.status_code == 201, registration.text

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert login.status_code == 200, login.text

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def test_admin_can_create_flight():
    headers = admin_headers()
    payload = flight_payload(headers)

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["flight_number"] == payload["flight_number"]
    assert response.json()["status"] == "scheduled"


def test_flight_number_is_normalized():
    headers = admin_headers()
    payload = flight_payload(headers)
    payload["flight_number"] = "  ai123  "

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["flight_number"] == "AI123"


def test_duplicate_flight_not_allowed():
    headers = admin_headers()
    payload = flight_payload(headers)

    first = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert second.status_code == 409


def test_same_flight_number_allowed_for_different_departure():
    headers = admin_headers()
    payload = flight_payload(headers)

    first = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 201, first.text

    payload["scheduled_departure"] = (
        datetime(2030, 5, 11, 10, 0, tzinfo=timezone.utc).isoformat()
    )
    payload["scheduled_arrival"] = (
        datetime(2030, 5, 11, 12, 0, tzinfo=timezone.utc).isoformat()
    )

    second = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert second.status_code == 201, second.text


def test_flight_requires_flight_number():
    headers = admin_headers()
    payload = flight_payload(headers)
    payload.pop("flight_number")

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_flight_rejects_same_origin_and_destination():
    headers = admin_headers()
    payload = flight_payload(headers)
    payload["destination_airport_id"] = payload["origin_airport_id"]

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_flight_rejects_arrival_before_departure():
    headers = admin_headers()
    payload = flight_payload(headers)
    payload["scheduled_arrival"] = (
        datetime(2030, 5, 10, 9, 0, tzinfo=timezone.utc).isoformat()
    )

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_flight_rejects_invalid_airport():
    headers = admin_headers()
    payload = flight_payload(headers)
    payload["origin_airport_id"] = str(uuid.uuid4())

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 404


def test_flight_rejects_terminal_from_wrong_airport():
    headers = admin_headers()
    payload = flight_payload(headers)

    wrong_terminal = create_terminal(
        headers,
        payload["destination_airport_id"],
    )

    payload["departure_terminal_id"] = wrong_terminal["id"]

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 400


def test_admin_can_list_flights():
    headers = admin_headers()
    create_flight(headers)

    response = client.get(
        "/api/v1/flights/",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_flight_list_pagination():
    headers = admin_headers()
    create_flight(headers)

    response = client.get(
        "/api/v1/flights/?skip=0&limit=5",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_invalid_flight_pagination():
    headers = admin_headers()

    response = client.get(
        "/api/v1/flights/?skip=-1",
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_get_flight():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    response = client.get(
        f"/api/v1/flights/{flight['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == flight["id"]


def test_get_nonexistent_flight():
    headers = admin_headers()

    response = client.get(
        f"/api/v1/flights/{uuid.uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_admin_can_update_flight():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    response = client.patch(
        f"/api/v1/flights/{flight['id']}",
        json={"airline": "Updated Airlines"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["airline"] == "Updated Airlines"


def test_flight_update_rejects_invalid_schedule():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    response = client.patch(
        f"/api/v1/flights/{flight['id']}",
        json={
            "scheduled_arrival": (
                datetime(2030, 5, 9, 9, 0, tzinfo=timezone.utc).isoformat()
            )
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_mark_flight_as_departed():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    response = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "departed"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "departed"
    assert response.json()["actual_departure"] is not None


def test_flight_cannot_arrive_before_departure():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    response = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "arrived"},
        headers=headers,
    )

    assert response.status_code == 400


def test_departed_flight_can_be_marked_arrived():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    departed = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "departed"},
        headers=headers,
    )

    assert departed.status_code == 200, departed.text

    arrived = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "arrived"},
        headers=headers,
    )

    assert arrived.status_code == 200, arrived.text
    assert arrived.json()["status"] == "arrived"
    assert arrived.json()["actual_arrival"] is not None


def test_cancelled_flight_cannot_change_status():
    headers = admin_headers()
    flight, _ = create_flight(headers)

    cancelled = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "cancelled"},
        headers=headers,
    )

    assert cancelled.status_code == 200, cancelled.text

    response = client.patch(
        f"/api/v1/flights/{flight['id']}/status",
        json={"status": "boarding"},
        headers=headers,
    )

    assert response.status_code == 400


def test_normal_user_cannot_create_flight():
    headers = register_regular_user()
    payload = flight_payload(admin_headers())

    response = client.post(
        "/api/v1/flights/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403