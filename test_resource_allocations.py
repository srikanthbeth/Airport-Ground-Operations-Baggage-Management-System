
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
    GroundStaffDepartment,
    GroundStaffShift,
    GroundStaffStatus,
    GroundEquipmentType,
    GroundEquipmentStatus,
)

from core.security import hash_password

from models.user import User
from models.airport import Airport
from models.terminal import Terminal
from models.flight import Flight
from models.gate import Gate
from models.checkin_counter import CheckInCounter
from models.ground_staff import GroundStaff
from models.ground_equipment import GroundEquipment

import models
from main import app


client = TestClient(app)

PASSWORD = "AirportTest@12345"
ALLOCATION_COUNTER = 0

MANAGER_EMAIL = None
FLIGHT_ID = None
GATE_ID = None
COUNTER_ID = None
STAFF_ID = None
EQUIPMENT_ID = None


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        manager = User(
            full_name="Allocation Manager",
            email="allocation_manager@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.AIRPORT_OPERATIONS_MANAGER,
            is_active=True,
            is_verified=True,
        )

        staff_user = User(
            full_name="Allocation Staff",
            email="allocation_staff@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.GROUND_STAFF_SUPERVISOR,
            is_active=True,
            is_verified=True,
        )

        db.add_all([manager, staff_user])
        db.flush()

        origin = Airport(
            code=unique_value()[:8],
            name="Allocation Origin Airport",
            city="Hyderabad",
            country="India",
            address="Hyderabad, Telangana",
            timezone="Asia/Kolkata",
        )

        destination = Airport(
            code=unique_value()[:8],
            name="Allocation Destination Airport",
            city="Delhi",
            country="India",
            address="Delhi, India",
            timezone="Asia/Kolkata",
        )

        db.add_all([origin, destination])
        db.flush()

        terminal = Terminal(
            airport_id=origin.id,
            name="Allocation Terminal",
            code=unique_value()[:8],
            description="Resource allocation test terminal",
        )

        db.add(terminal)
        db.flush()

        now = datetime.now(timezone.utc)

        flight = Flight(
            flight_number=f"AL{unique_value()[:6]}",
            airline="Allocation Airlines",
            flight_type=FlightType.DOMESTIC,
            origin_airport_id=origin.id,
            destination_airport_id=destination.id,
            departure_terminal_id=terminal.id,
            scheduled_departure=now + timedelta(days=5),
            scheduled_arrival=now + timedelta(days=5, hours=3),
            aircraft_type="Airbus A320",
            capacity=180,
            status=FlightStatus.SCHEDULED,
        )

        gate = Gate(
            terminal_id=terminal.id,
            gate_number=901,
            name="Allocation Gate",
            status=GateStatus.ACTIVE,
        )

        counter = CheckInCounter(
            terminal_id=terminal.id,
            counter_number=901,
            name="Allocation Counter",
            status=CounterStatus.ACTIVE,
        )

        ground_staff = GroundStaff(
            user_id=staff_user.id,
            employee_number=f"EMP-{unique_value()}",
            department=GroundStaffDepartment.GATE_OPERATIONS,
            designation="Ground Operations Officer",
            phone="9876543210",
            shift=GroundStaffShift.MORNING,
            status=GroundStaffStatus.ACTIVE,
            airport_id=origin.id,
            terminal_id=terminal.id,
            date_of_joining=datetime.now(timezone.utc).date(),
        )

        db.add_all([flight, gate, counter, ground_staff])
        db.flush()

        equipment = GroundEquipment(
            equipment_code=f"EQ-{unique_value()}",
            name="Allocation Baggage Cart",
            equipment_type=GroundEquipmentType.BAGGAGE_CART,
            airport_id=origin.id,
            status=GroundEquipmentStatus.AVAILABLE,
            created_by=manager.id,
        )

        db.add(equipment)
        db.commit()

        global MANAGER_EMAIL
        global FLIGHT_ID
        global GATE_ID
        global COUNTER_ID
        global STAFF_ID
        global EQUIPMENT_ID

        MANAGER_EMAIL = manager.email
        FLIGHT_ID = str(flight.id)
        GATE_ID = str(gate.id)
        COUNTER_ID = str(counter.id)
        STAFF_ID = str(ground_staff.id)
        EQUIPMENT_ID = str(equipment.id)

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


def allocation_payload(resource_type, resource_id, start=None, end=None):
    now = datetime.now(timezone.utc)

    return {
        "flight_id": FLIGHT_ID,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "starts_at": (
            start or now + timedelta(days=5)
        ).isoformat(),
        "ends_at": (
            end or now + timedelta(days=5, hours=1)
        ).isoformat(),
        "notes": "Allocation test",
    }


def create_allocation(resource_type, resource_id, start=None, end=None):
    global ALLOCATION_COUNTER

    ALLOCATION_COUNTER += 1

    if start is None:
        start = datetime.now(timezone.utc) + timedelta(
            days=30,
            minutes=ALLOCATION_COUNTER * 120,
        )

    if end is None:
        end = start + timedelta(hours=1)

    return client.post(
        "/api/v1/resource-allocations",
        json=allocation_payload(
            resource_type,
            resource_id,
            start,
            end,
        ),
        headers=headers(),
    )


def test_create_gate_allocation():
    response = create_allocation("gate", GATE_ID)

    assert response.status_code == 201, response.text
    assert response.json()["resource_type"] == "gate"
    assert response.json()["gate_id"] == GATE_ID


def test_create_counter_allocation():
    response = create_allocation("counter", COUNTER_ID)

    assert response.status_code == 201, response.text
    assert response.json()["counter_id"] == COUNTER_ID


def test_create_ground_staff_allocation():
    response = create_allocation("ground_staff", STAFF_ID)

    assert response.status_code == 201, response.text
    assert response.json()["ground_staff_id"] == STAFF_ID


def test_create_equipment_allocation():
    response = create_allocation("ground_equipment", EQUIPMENT_ID)

    assert response.status_code == 201, response.text
    assert response.json()["equipment_id"] == EQUIPMENT_ID


def test_prevent_overlapping_gate_allocation():
    start = datetime.now(timezone.utc) + timedelta(days=10)
    end = start + timedelta(hours=2)

    first = create_allocation("gate", GATE_ID, start, end)

    second = create_allocation(
        "gate",
        GATE_ID,
        start + timedelta(minutes=30),
        end + timedelta(minutes=30),
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text


def test_allow_non_overlapping_gate_allocation():
    start = datetime.now(timezone.utc) + timedelta(days=15)
    end = start + timedelta(hours=1)

    first = create_allocation("gate", GATE_ID, start, end)

    second = create_allocation(
        "gate",
        GATE_ID,
        end,
        end + timedelta(hours=1),
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


def test_get_allocation():
    created = create_allocation("gate", GATE_ID)

    assert created.status_code == 201, created.text

    allocation_id = created.json()["id"]

    response = client.get(
        f"/api/v1/resource-allocations/{allocation_id}",
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == allocation_id


def test_list_allocations():
    response = client.get(
        "/api/v1/resource-allocations",
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_filter_allocations_by_flight():
    response = client.get(
        f"/api/v1/resource-allocations?flight_id={FLIGHT_ID}",
        headers=headers(),
    )

    assert response.status_code == 200, response.text

    assert all(
        item["flight_id"] == FLIGHT_ID
        for item in response.json()
    )


def test_update_allocation():
    created = create_allocation("gate", GATE_ID)

    assert created.status_code == 201, created.text

    allocation_id = created.json()["id"]

    start = datetime.now(timezone.utc) + timedelta(days=20)
    end = start + timedelta(hours=2)

    response = client.patch(
        f"/api/v1/resource-allocations/{allocation_id}",
        json={
            "starts_at": start.isoformat(),
            "ends_at": end.isoformat(),
            "notes": "Updated allocation",
        },
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["notes"] == "Updated allocation"


def test_activate_allocation():
    created = create_allocation("gate", GATE_ID)

    assert created.status_code == 201, created.text

    allocation_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/resource-allocations/{allocation_id}/activate",
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"


def test_complete_allocation():
    created = create_allocation("gate", GATE_ID)

    assert created.status_code == 201, created.text

    allocation_id = created.json()["id"]

    activated = client.patch(
        f"/api/v1/resource-allocations/{allocation_id}/activate",
        headers=headers(),
    )

    assert activated.status_code == 200, activated.text

    response = client.patch(
        f"/api/v1/resource-allocations/{allocation_id}/complete",
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


def test_cancel_allocation():
    created = create_allocation("gate", GATE_ID)

    assert created.status_code == 201, created.text

    allocation_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/resource-allocations/{allocation_id}/cancel",
        headers=headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"


def test_reject_invalid_schedule():
    start = datetime.now(timezone.utc) + timedelta(days=5)
    end = start - timedelta(hours=1)

    response = create_allocation("gate", GATE_ID, start, end)

    assert response.status_code == 422, response.text


def test_reject_unknown_allocation():
    response = client.get(
        f"/api/v1/resource-allocations/{uuid.uuid4()}",
        headers=headers(),
    )

    assert response.status_code == 404, response.text


def test_reject_unauthenticated_request():
    response = client.get("/api/v1/resource-allocations")

    assert response.status_code in (401, 403)
