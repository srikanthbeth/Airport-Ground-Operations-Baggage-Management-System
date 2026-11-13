
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

from core.constants import (
    UserRole,
    FlightType,
    FlightStatus,
    GateStatus,
    CounterStatus,
)

from core.security import hash_password

from models.user import User
from models.airport import Airport
from models.terminal import Terminal
from models.flight import Flight
from models.gate import Gate
from models.checkin_counter import CheckInCounter

import models
from main import app


client = TestClient(app)

PASSWORD = "AirportTest@12345"
MANAGER_EMAIL = "dashboard_manager@example.com"


def unique_value():
    return uuid.uuid4().hex[:8].upper()


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        manager = User(
            full_name="Dashboard Manager",
            email=MANAGER_EMAIL,
            hashed_password=hash_password(PASSWORD),
            role=UserRole.AIRPORT_OPERATIONS_MANAGER,
            is_active=True,
            is_verified=True,
        )

        db.add(manager)
        db.flush()

        airport = Airport(
            code=unique_value(),
            name="Dashboard Test Airport",
            city="Hyderabad",
            country="India",
            address="Hyderabad, Telangana",
            timezone="Asia/Kolkata",
        )

        db.add(airport)
        db.flush()

        terminal = Terminal(
            airport_id=airport.id,
            name="Dashboard Terminal",
            code=unique_value(),
            description="Dashboard test terminal",
        )

        db.add(terminal)
        db.flush()

        now = datetime.now(timezone.utc)

        flight = Flight(
            flight_number=f"DB{unique_value()[:6]}",
            airline="Dashboard Airlines",
            flight_type=FlightType.DOMESTIC,
            origin_airport_id=airport.id,
            destination_airport_id=airport.id,
            departure_terminal_id=terminal.id,
            scheduled_departure=now + timedelta(days=2),
            scheduled_arrival=now + timedelta(days=2, hours=2),
            aircraft_type="Airbus A320",
            capacity=180,
            status=FlightStatus.SCHEDULED,
        )

        gate = Gate(
            terminal_id=terminal.id,
            gate_number=901,
            name="Dashboard Gate",
            status=GateStatus.ACTIVE,
        )

        counter = CheckInCounter(
            terminal_id=terminal.id,
            counter_number=901,
            name="Dashboard Counter",
            status=CounterStatus.ACTIVE,
        )

        db.add_all([flight, gate, counter])
        db.commit()

    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def get_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": MANAGER_EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def headers():
    return {
        "Authorization": f"Bearer {get_token()}"
    }


def test_dashboard_overview_success():
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=headers(),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "flights" in data
    assert "baggage" in data
    assert "ground_operations" in data


def test_dashboard_flight_metrics():
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=headers(),
    )

    assert response.status_code == 200

    flights = response.json()["flights"]

    assert flights["total_flights"] == 1
    assert flights["scheduled_flights"] == 1
    assert flights["delayed_flights"] == 0
    assert flights["cancelled_flights"] == 0
    assert flights["arrived_flights"] == 0
    assert flights["departed_flights"] == 0


def test_dashboard_ground_resource_metrics():
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=headers(),
    )

    assert response.status_code == 200

    ground = response.json()["ground_operations"]

    assert ground["active_checkin_counters"] == 1
    assert ground["available_gates"] == 1
    assert ground["pending_ground_tasks"] == 0


def test_dashboard_baggage_metrics():
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=headers(),
    )

    assert response.status_code == 200

    baggage = response.json()["baggage"]

    assert baggage["baggage_processed"] == 0
    assert baggage["delayed_baggage"] == 0
    assert baggage["missing_baggage"] == 0


def test_dashboard_turnaround_and_incident_metrics():
    response = client.get(
        "/api/v1/dashboard/overview",
        headers=headers(),
    )

    assert response.status_code == 200

    ground = response.json()["ground_operations"]

    assert ground["average_turnaround_duration_minutes"] is None
    assert ground["total_operational_incidents"] == 0
    assert ground["active_operational_incidents"] == 0


def test_dashboard_rejects_unauthenticated_request():
    response = client.get("/api/v1/dashboard/overview")

    assert response.status_code in (401, 403)
