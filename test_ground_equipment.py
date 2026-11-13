
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
from core.constants import UserRole
from core.security import hash_password
from models.user import User
import models
from main import app


client = TestClient(app)

PASSWORD = "AirportTest@12345"

admin_headers = {}
officer_headers = {}
airport_id = None


def unique_value(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def login(email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def setup_module():
    global admin_headers, officer_headers, airport_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = User(
            full_name="Equipment Admin",
            email="equipment_admin@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )

        officer = User(
            full_name="Equipment Flight Officer",
            email="equipment_officer@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.FLIGHT_OPERATIONS_OFFICER,
            is_active=True,
            is_verified=True,
        )

        db.add_all([admin, officer])
        db.commit()
    finally:
        db.close()

    admin_headers = login("equipment_admin@example.com")
    officer_headers = login("equipment_officer@example.com")

    airport_response = client.post(
        "/api/v1/airports/",
        headers=admin_headers,
        json={
            "code": f"E{uuid.uuid4().hex[:8].upper()}",
            "name": "Equipment Test Airport",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad, Telangana",
            "timezone": "Asia/Kolkata",
        },
    )

    assert airport_response.status_code == 201, airport_response.text
    airport_id = airport_response.json()["id"]


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def equipment_payload(**overrides):
    payload = {
        "equipment_code": unique_value("EQ"),
        "name": "Test Baggage Cart",
        "equipment_type": "baggage_cart",
        "airport_id": airport_id,
        "manufacturer": "Airport Equipment Ltd",
        "model_number": "BC-100",
        "serial_number": unique_value("SERIAL"),
        "status": "available",
        "notes": "Test equipment",
    }

    payload.update(overrides)
    return payload


def create_equipment(**overrides):
    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(**overrides),
    )

    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------
# CREATE TESTS
# ---------------------------------------------------------

def test_admin_can_create_ground_equipment():
    equipment = create_equipment()

    assert equipment["id"]
    assert equipment["equipment_type"] == "baggage_cart"
    assert equipment["status"] == "available"
    assert equipment["airport_id"] == airport_id


def test_create_ground_power_unit():
    equipment = create_equipment(
        equipment_type="ground_power_unit",
        name="Ground Power Unit",
    )

    assert equipment["equipment_type"] == "ground_power_unit"


def test_create_aircraft_tug():
    equipment = create_equipment(
        equipment_type="aircraft_tug",
        name="Aircraft Tug",
    )

    assert equipment["equipment_type"] == "aircraft_tug"


def test_create_passenger_stairs():
    equipment = create_equipment(
        equipment_type="passenger_stairs",
        name="Passenger Stairs",
    )

    assert equipment["equipment_type"] == "passenger_stairs"


def test_create_loading_equipment():
    equipment = create_equipment(
        equipment_type="loading_equipment",
        name="Loading Equipment",
    )

    assert equipment["equipment_type"] == "loading_equipment"


def test_duplicate_equipment_code_is_rejected():
    code = unique_value("DUP")
    create_equipment(equipment_code=code)

    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(equipment_code=code),
    )

    assert response.status_code == 409


def test_duplicate_serial_number_is_rejected():
    serial = unique_value("SERIAL")
    create_equipment(serial_number=serial)

    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(serial_number=serial),
    )

    assert response.status_code == 409


def test_create_equipment_rejects_missing_airport():
    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(airport_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404


def test_create_equipment_rejects_invalid_type():
    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(equipment_type="invalid_type"),
    )

    assert response.status_code == 422


def test_create_equipment_rejects_invalid_status():
    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(status="broken"),
    )

    assert response.status_code == 422


def test_create_equipment_rejects_invalid_maintenance_dates():
    now = datetime.now(timezone.utc)

    response = client.post(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
        json=equipment_payload(
            last_maintenance_at=(now + timedelta(days=2)).isoformat(),
            next_maintenance_at=now.isoformat(),
        ),
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# GET TESTS
# ---------------------------------------------------------

def test_admin_can_get_ground_equipment():
    equipment = create_equipment()

    response = client.get(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == equipment["id"]


def test_nonexistent_equipment_returns_404():
    response = client.get(
        f"/api/v1/ground-equipment/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_list_ground_equipment():
    create_equipment()

    response = client.get(
        "/api/v1/ground-equipment/",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert "items" in response.json()


def test_filter_equipment_by_type():
    create_equipment(equipment_type="aircraft_tug")

    response = client.get(
        "/api/v1/ground-equipment/?equipment_type=aircraft_tug",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert all(
        item["equipment_type"] == "aircraft_tug"
        for item in response.json()["items"]
    )


def test_filter_equipment_by_status():
    equipment = create_equipment()

    client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "maintenance"},
    )

    response = client.get(
        "/api/v1/ground-equipment/?status=maintenance",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert all(
        item["status"] == "maintenance"
        for item in response.json()["items"]
    )


def test_filter_equipment_by_airport():
    create_equipment()

    response = client.get(
        f"/api/v1/ground-equipment/?airport_id={airport_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert all(
        item["airport_id"] == airport_id
        for item in response.json()["items"]
    )


def test_equipment_pagination():
    response = client.get(
        "/api/v1/ground-equipment/?page=1&page_size=2",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    assert len(response.json()["items"]) <= 2


def test_invalid_pagination_is_rejected():
    response = client.get(
        "/api/v1/ground-equipment/?page=0",
        headers=admin_headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# UPDATE TESTS
# ---------------------------------------------------------

def test_admin_can_update_equipment():
    equipment = create_equipment()

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
        json={"name": "Updated Baggage Cart"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Baggage Cart"


def test_update_equipment_rejects_duplicate_code():
    first = create_equipment()
    second = create_equipment()

    response = client.patch(
        f"/api/v1/ground-equipment/{second['id']}",
        headers=admin_headers,
        json={"equipment_code": first["equipment_code"]},
    )

    assert response.status_code == 409


def test_update_nonexistent_equipment_returns_404():
    response = client.patch(
        f"/api/v1/ground-equipment/{uuid.uuid4()}",
        headers=admin_headers,
        json={"name": "Unknown Equipment"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# STATUS TESTS
# ---------------------------------------------------------

def test_equipment_can_be_moved_to_maintenance():
    equipment = create_equipment()

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "maintenance"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"


def test_equipment_can_return_from_maintenance():
    equipment = create_equipment()

    client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "maintenance"},
    )

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "available"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "available"


def test_equipment_can_be_marked_out_of_service():
    equipment = create_equipment()

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "out_of_service"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "out_of_service"


def test_invalid_equipment_status_transition_is_rejected():
    equipment = create_equipment()

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "in_use"},
    )

    assert response.status_code == 200

    response = client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "maintenance"},
    )

    assert response.status_code == 409


# ---------------------------------------------------------
# USAGE TESTS
# ---------------------------------------------------------

def test_admin_can_record_equipment_usage():
    equipment = create_equipment()

    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc) - timedelta(hours=1)

    response = client.post(
        f"/api/v1/ground-equipment/{equipment['id']}/usage",
        headers=admin_headers,
        json={
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "notes": "Baggage handling operation",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["equipment_id"] == equipment["id"]
    assert response.json()["notes"] == "Baggage handling operation"


def test_equipment_usage_rejects_invalid_time_range():
    equipment = create_equipment()
    now = datetime.now(timezone.utc)

    response = client.post(
        f"/api/v1/ground-equipment/{equipment['id']}/usage",
        headers=admin_headers,
        json={
            "started_at": now.isoformat(),
            "ended_at": (now - timedelta(hours=1)).isoformat(),
        },
    )

    assert response.status_code == 422


def test_equipment_usage_updates_last_used_at():
    equipment = create_equipment()

    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc) - timedelta(hours=1)

    response = client.post(
        f"/api/v1/ground-equipment/{equipment['id']}/usage",
        headers=admin_headers,
        json={
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
        },
    )

    assert response.status_code == 201, response.text

    details = client.get(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
    )

    assert details.status_code == 200
    assert details.json()["last_used_at"] is not None


def test_admin_can_view_equipment_usage_history():
    equipment = create_equipment()

    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = datetime.now(timezone.utc) - timedelta(hours=1)

    client.post(
        f"/api/v1/ground-equipment/{equipment['id']}/usage",
        headers=admin_headers,
        json={
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
        },
    )

    response = client.get(
        f"/api/v1/ground-equipment/{equipment['id']}/usage",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_usage_history_for_missing_equipment_returns_404():
    response = client.get(
        f"/api/v1/ground-equipment/{uuid.uuid4()}/usage",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# DELETE TESTS
# ---------------------------------------------------------

def test_admin_can_delete_equipment():
    equipment = create_equipment()

    response = client.delete(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    details = client.get(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
    )

    assert details.status_code == 404


def test_equipment_in_use_cannot_be_deleted():
    equipment = create_equipment()

    client.patch(
        f"/api/v1/ground-equipment/{equipment['id']}/status",
        headers=admin_headers,
        json={"status": "in_use"},
    )

    response = client.delete(
        f"/api/v1/ground-equipment/{equipment['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 409


# ---------------------------------------------------------
# AUTHORIZATION TESTS
# ---------------------------------------------------------

def test_ground_equipment_requires_authentication():
    response = client.get("/api/v1/ground-equipment/")

    assert response.status_code == 401


def test_flight_officer_cannot_create_ground_equipment():
    response = client.post(
        "/api/v1/ground-equipment/",
        headers=officer_headers,
        json=equipment_payload(),
    )

    assert response.status_code == 403
