import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from main import app
from db.base import Base
from db.session import engine, SessionLocal
from models import User
from core.constants import UserRole
from core.security import hash_password

client = TestClient(app)

PASSWORD = "AssignmentTest@12345"
ADMIN_EMAIL = "assignmentadmin@airport.example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.add(User(
        full_name="Assignment Test Admin",
        email=ADMIN_EMAIL,
        hashed_password=hash_password(PASSWORD),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    ))
    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def admin_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def create_terminal(headers):
    suffix = uuid.uuid4().hex[:5].upper()

    airport = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Assignment Airport {suffix}",
            "code": f"A{suffix}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )
    assert airport.status_code == 201, airport.text

    terminal = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport.json()["id"],
            "name": f"Assignment Terminal {suffix}",
            "code": f"T{suffix}",
            "description": "Assignment testing terminal",
        },
        headers=headers,
    )
    assert terminal.status_code == 201, terminal.text

    return terminal.json()


def create_flight_and_resources(headers):
    origin_terminal = create_terminal(headers)
    destination_terminal = create_terminal(headers)

    departure = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

    flight_payload = {
        "flight_number": f"AI{uuid.uuid4().hex[:6].upper()}",
        "airline": "Air India",
        "flight_type": "domestic",
        "origin_airport_id": get_airport_id(headers, origin_terminal),
        "destination_airport_id": get_airport_id(headers, destination_terminal),
        "departure_terminal_id": origin_terminal["id"],
        "arrival_terminal_id": destination_terminal["id"],
        "scheduled_departure": departure.isoformat(),
        "scheduled_arrival": (
            departure + timedelta(hours=2)
        ).isoformat(),
        "aircraft_type": "Airbus A320",
        "capacity": 180,
    }

    flight_response = client.post(
        "/api/v1/flights/",
        json=flight_payload,
        headers=headers,
    )
    assert flight_response.status_code == 201, flight_response.text
    flight = flight_response.json()

    gate_response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": origin_terminal["id"],
            "gate_number": 1,
            "name": "Gate A1",
        },
        headers=headers,
    )
    assert gate_response.status_code == 201, gate_response.text

    counter_response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": origin_terminal["id"],
            "counter_number": 1,
            "name": "Counter A1",
            "airline": "Air India",
        },
        headers=headers,
    )
    assert counter_response.status_code == 201, counter_response.text

    return flight, gate_response.json(), counter_response.json()


def get_airport_id(headers, terminal):
    response = client.get(
        f"/api/v1/terminals/{terminal['id']}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["airport_id"]

def create_flight_for_terminal(headers, departure_terminal_id):
    """
    Create a new flight using an existing departure terminal.
    This allows tests to verify resource conflicts correctly.
    """

    terminal_response = client.get(
        f"/api/v1/terminals/{departure_terminal_id}",
        headers=headers,
    )
    assert terminal_response.status_code == 200, terminal_response.text

    departure_airport_id = terminal_response.json()["airport_id"]

    destination_terminal = create_terminal(headers)
    destination_airport_id = get_airport_id(
        headers,
        destination_terminal,
    )

    departure = datetime(
        2030, 5, 10, 10, 0, tzinfo=timezone.utc
    )

    flight_payload = {
        "flight_number": f"AI{uuid.uuid4().hex[:6].upper()}",
        "airline": "Air India",
        "flight_type": "domestic",
        "origin_airport_id": departure_airport_id,
        "destination_airport_id": destination_airport_id,
        "departure_terminal_id": departure_terminal_id,
        "arrival_terminal_id": destination_terminal["id"],
        "scheduled_departure": departure.isoformat(),
        "scheduled_arrival": (
            departure + timedelta(hours=2)
        ).isoformat(),
        "aircraft_type": "Airbus A320",
        "capacity": 180,
    }

    response = client.post(
        "/api/v1/flights/",
        json=flight_payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def assign_gate(headers, gate_id, flight_id):
    return client.post(
        f"/api/v1/resource-assignments/gates/{gate_id}",
        json={"flight_id": flight_id},
        headers=headers,
    )


def assign_counter(headers, counter_id, flight_id):
    return client.post(
        f"/api/v1/resource-assignments/counters/{counter_id}",
        json={"flight_id": flight_id},
        headers=headers,
    )


def test_admin_can_assign_gate_to_flight():
    headers = admin_headers()
    flight, gate, _ = create_flight_and_resources(headers)

    response = assign_gate(headers, gate["id"], flight["id"])

    assert response.status_code == 201, response.text
    assert response.json()["flight_id"] == flight["id"]
    assert response.json()["gate_id"] == gate["id"]
    assert response.json()["status"] == "active"


def test_gate_cannot_be_assigned_to_two_flights():
    headers = admin_headers()

    flight1, gate, _ = create_flight_and_resources(headers)

    flight2 = create_flight_for_terminal(
        headers,
        flight1["departure_terminal_id"],
    )

    first = assign_gate(
        headers,
        gate["id"],
        flight1["id"],
    )
    assert first.status_code == 201, first.text

    second = assign_gate(
        headers,
        gate["id"],
        flight2["id"],
    )

    assert second.status_code == 409

def test_flight_cannot_have_two_active_gate_assignments():
    headers = admin_headers()
    flight, gate1, _ = create_flight_and_resources(headers)

    second_gate_response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": flight["departure_terminal_id"],
            "gate_number": 2,
            "name": "Gate A2",
        },
        headers=headers,
    )
    assert second_gate_response.status_code == 201, second_gate_response.text

    first = assign_gate(headers, gate1["id"], flight["id"])
    assert first.status_code == 201, first.text

    second = assign_gate(
        headers,
        second_gate_response.json()["id"],
        flight["id"],
    )
    assert second.status_code == 409


def test_gate_assignment_rejects_wrong_terminal():
    headers = admin_headers()
    flight, _, _ = create_flight_and_resources(headers)

    other_terminal = create_terminal(headers)

    gate_response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": other_terminal["id"],
            "gate_number": 1,
            "name": "Wrong Terminal Gate",
        },
        headers=headers,
    )
    assert gate_response.status_code == 201, gate_response.text

    response = assign_gate(
        headers,
        gate_response.json()["id"],
        flight["id"],
    )
    assert response.status_code == 400


def test_released_gate_can_be_assigned_again():
    headers = admin_headers()

    flight1, gate, _ = create_flight_and_resources(headers)

    flight2 = create_flight_for_terminal(
        headers,
        flight1["departure_terminal_id"],
    )

    first = assign_gate(
        headers,
        gate["id"],
        flight1["id"],
    )
    assert first.status_code == 201, first.text

    release = client.patch(
        f"/api/v1/resource-assignments/{first.json()['id']}/release",
        headers=headers,
    )

    assert release.status_code == 200, release.text
    assert release.json()["status"] == "released"

    second = assign_gate(
        headers,
        gate["id"],
        flight2["id"],
    )

    assert second.status_code == 201, second.text



def test_gate_assignment_history():
    headers = admin_headers()
    flight, gate, _ = create_flight_and_resources(headers)

    assignment = assign_gate(headers, gate["id"], flight["id"])
    assert assignment.status_code == 201, assignment.text

    response = client.get(
        f"/api/v1/resource-assignments/gates/{gate['id']}/history",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_can_assign_counter_to_flight():
    headers = admin_headers()
    flight, _, counter = create_flight_and_resources(headers)

    response = assign_counter(
        headers,
        counter["id"],
        flight["id"],
    )

    assert response.status_code == 201, response.text
    assert response.json()["flight_id"] == flight["id"]
    assert response.json()["counter_id"] == counter["id"]
    assert response.json()["status"] == "active"

def test_counter_cannot_be_assigned_to_two_flights():
    headers = admin_headers()

    flight1, _, counter = create_flight_and_resources(headers)

    flight2 = create_flight_for_terminal(
        headers,
        flight1["departure_terminal_id"],
    )

    first = assign_counter(
        headers,
        counter["id"],
        flight1["id"],
    )
    assert first.status_code == 201, first.text

    second = assign_counter(
        headers,
        counter["id"],
        flight2["id"],
    )

    assert second.status_code == 409

def test_flight_cannot_have_two_active_counter_assignments():
    headers = admin_headers()
    flight, _, counter1 = create_flight_and_resources(headers)

    second_counter_response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": flight["departure_terminal_id"],
            "counter_number": 2,
            "name": "Counter A2",
        },
        headers=headers,
    )
    assert second_counter_response.status_code == 201, second_counter_response.text

    first = assign_counter(headers, counter1["id"], flight["id"])
    assert first.status_code == 201, first.text

    second = assign_counter(
        headers,
        second_counter_response.json()["id"],
        flight["id"],
    )
    assert second.status_code == 409


def test_counter_assignment_history():
    headers = admin_headers()
    flight, _, counter = create_flight_and_resources(headers)

    assignment = assign_counter(
        headers,
        counter["id"],
        flight["id"],
    )
    assert assignment.status_code == 201, assignment.text

    response = client.get(
        f"/api/v1/resource-assignments/counters/{counter['id']}/history",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_assignment_cannot_be_released_twice():
    headers = admin_headers()
    flight, gate, _ = create_flight_and_resources(headers)

    assignment = assign_gate(headers, gate["id"], flight["id"])
    assert assignment.status_code == 201, assignment.text

    assignment_id = assignment.json()["id"]

    first_release = client.patch(
        f"/api/v1/resource-assignments/{assignment_id}/release",
        headers=headers,
    )
    assert first_release.status_code == 200

    second_release = client.patch(
        f"/api/v1/resource-assignments/{assignment_id}/release",
        headers=headers,
    )
    assert second_release.status_code == 400