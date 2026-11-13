
import os
import uuid
from datetime import date

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from db.base import Base
from db.session import engine, SessionLocal
from core.constants import (
    UserRole,
    GroundStaffDepartment,
    GroundStaffShift,
    GroundStaffStatus,
)
from core.security import hash_password
from models.user import User
import models  # noqa: F401
from main import app


client = TestClient(app)

PASSWORD = "GroundStaffTest@12345"

admin_headers = {}
flight_officer_headers = {}

airport_id = None
destination_airport_id = None
terminal_id = None
destination_terminal_id = None


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def create_user(
    role=UserRole.BAGGAGE_HANDLING_STAFF,
    is_active=True,
):
    value = unique_value()
    email = f"staff_{value.lower()}@airport.com"

    db = SessionLocal()

    try:
        user = User(
            full_name=f"Ground Staff {value}",
            email=email,
            hashed_password=hash_password(PASSWORD),
            role=role,
            is_active=is_active,
            is_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_id = user.id

    finally:
        db.close()

    return {
        "id": str(user_id),
        "email": email,
    }


def login_headers(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def setup_module(module):
    global admin_headers, flight_officer_headers
    global airport_id, destination_airport_id
    global terminal_id, destination_terminal_id

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    admin = create_user(
        role=UserRole.SUPER_ADMIN,
    )

    flight_officer = create_user(
        role=UserRole.FLIGHT_OPERATIONS_OFFICER,
    )

    admin_headers = login_headers(admin["email"])
    flight_officer_headers = login_headers(
        flight_officer["email"]
    )

    # Create first airport.
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

    # Create second airport.
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

    # Create first terminal.
    response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": airport_id,
            "code": "T1",
            "name": "Terminal 1",
            "description": "Hyderabad main terminal",
        },
    )

    assert response.status_code == 201, response.text
    terminal_id = response.json()["id"]

    # Create second terminal.
    response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": destination_airport_id,
            "code": "T2",
            "name": "Terminal 2",
            "description": "Mumbai terminal",
        },
    )

    assert response.status_code == 201, response.text
    destination_terminal_id = response.json()["id"]


def staff_payload(
    user_id=None,
    employee_number=None,
    department="baggage_handling",
    shift="morning",
    status=None,
    selected_airport_id=None,
    selected_terminal_id=None,
):
    payload = {
        "user_id": user_id or create_user()["id"],
        "employee_number": employee_number or f"EMP-{unique_value()}",
        "department": department,
        "designation": "Ground Operations Executive",
        "phone": "9876543210",
        "shift": shift,
        "airport_id": selected_airport_id or airport_id,
        "terminal_id": selected_terminal_id,
        "date_of_joining": "2025-01-15",
    }

    if status is not None:
        payload["status"] = status

    return payload


def create_staff(payload=None):
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=payload or staff_payload(),
    )

    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------
# CREATE GROUND STAFF TESTS
# ---------------------------------------------------------

def test_admin_can_create_ground_staff():
    payload = staff_payload()

    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == payload["user_id"]
    assert response.json()["employee_number"] == payload["employee_number"]
    assert response.json()["department"] == "baggage_handling"
    assert response.json()["shift"] == "morning"
    assert response.json()["status"] == "active"


def test_ground_staff_can_be_assigned_to_terminal():
    payload = staff_payload(
        selected_terminal_id=terminal_id,
    )

    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json()["terminal_id"] == terminal_id


def test_all_ground_staff_roles_are_supported():
    roles = [
        UserRole.GROUND_STAFF_SUPERVISOR,
        UserRole.BAGGAGE_HANDLING_STAFF,
        UserRole.CHECK_IN_AGENT,
        UserRole.GATE_AGENT,
        UserRole.MAINTENANCE_STAFF,
    ]

    for role in roles:
        user = create_user(role=role)

        response = client.post(
            "/api/v1/ground-staff/",
            headers=admin_headers,
            json=staff_payload(user_id=user["id"]),
        )

        assert response.status_code == 201, response.text


def test_duplicate_user_profile_is_rejected():
    payload = staff_payload()

    first = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=payload,
    )

    assert second.status_code == 409


def test_duplicate_employee_number_is_rejected():
    employee_number = f"EMP-{unique_value()}"

    first = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(
            employee_number=employee_number,
        ),
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(
            employee_number=employee_number,
        ),
    )

    assert second.status_code == 409


def test_non_staff_user_role_is_rejected():
    user = create_user(
        role=UserRole.FLIGHT_OPERATIONS_OFFICER,
    )

    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(user_id=user["id"]),
    )

    assert response.status_code == 400


def test_inactive_user_cannot_be_registered_as_staff():
    user = create_user(is_active=False)

    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(user_id=user["id"]),
    )

    assert response.status_code == 400


def test_nonexistent_user_is_rejected():
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(user_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404


def test_nonexistent_airport_is_rejected():
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(
            selected_airport_id=str(uuid.uuid4()),
        ),
    )

    assert response.status_code == 404


def test_terminal_from_another_airport_is_rejected():
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(
            selected_airport_id=airport_id,
            selected_terminal_id=destination_terminal_id,
        ),
    )

    assert response.status_code == 400


def test_invalid_department_is_rejected():
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(department="invalid_department"),
    )

    assert response.status_code == 422


def test_invalid_shift_is_rejected():
    response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json=staff_payload(shift="invalid_shift"),
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# GET GROUND STAFF TESTS
# ---------------------------------------------------------

def test_admin_can_get_ground_staff_record():
    staff = create_staff()

    response = client.get(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == staff["id"]


def test_get_nonexistent_ground_staff():
    response = client.get(
        f"/api/v1/ground-staff/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_list_ground_staff():
    create_staff()
    create_staff()

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 2
    assert len(response.json()["items"]) >= 2


def test_ground_staff_list_pagination():
    for _ in range(3):
        create_staff()

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 2,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    assert len(response.json()["items"]) == 2
    assert response.json()["total"] >= 3


def test_ground_staff_filter_by_department():
    create_staff(
        staff_payload(department="baggage_handling")
    )

    create_staff(
        staff_payload(department="maintenance")
    )

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={"department": "maintenance"},
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) >= 1

    for item in response.json()["items"]:
        assert item["department"] == "maintenance"


def test_ground_staff_filter_by_shift():
    create_staff(
        staff_payload(shift="night")
    )

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={"shift": "night"},
    )

    assert response.status_code == 200, response.text

    for item in response.json()["items"]:
        assert item["shift"] == "night"


def test_ground_staff_filter_by_status():
    staff = create_staff()

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={"status": "on_leave"},
    )

    assert response.status_code == 200, response.text

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={"status": "on_leave"},
    )

    assert response.status_code == 200, response.text

    for item in response.json()["items"]:
        assert item["status"] == "on_leave"


def test_ground_staff_filter_by_airport():
    create_staff()

    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={"airport_id": airport_id},
    )

    assert response.status_code == 200, response.text

    for item in response.json()["items"]:
        assert item["airport_id"] == airport_id


def test_invalid_pagination_is_rejected():
    response = client.get(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        params={
            "page": 0,
            "page_size": 0,
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# UPDATE GROUND STAFF TESTS
# ---------------------------------------------------------

def test_admin_can_update_ground_staff():
    staff = create_staff()

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={
            "designation": "Senior Ground Operations Executive",
            "phone": "9123456789",
            "shift": "evening",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["designation"] == (
        "Senior Ground Operations Executive"
    )
    assert response.json()["phone"] == "9123456789"
    assert response.json()["shift"] == "evening"


def test_admin_can_update_staff_status():
    staff = create_staff()

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={"status": "on_leave"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "on_leave"


def test_admin_can_remove_terminal_assignment():
    staff = create_staff(
        staff_payload(selected_terminal_id=terminal_id)
    )

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={"terminal_id": None},
    )

    assert response.status_code == 200, response.text
    assert response.json()["terminal_id"] is None


def test_update_rejects_duplicate_employee_number():
    first = create_staff()
    second = create_staff()

    response = client.patch(
        f"/api/v1/ground-staff/{second['id']}",
        headers=admin_headers,
        json={
            "employee_number": first["employee_number"],
        },
    )

    assert response.status_code == 409


def test_update_nonexistent_ground_staff():
    response = client.patch(
        f"/api/v1/ground-staff/{uuid.uuid4()}",
        headers=admin_headers,
        json={"designation": "Updated Designation"},
    )

    assert response.status_code == 404


def test_update_rejects_terminal_from_another_airport():
    staff = create_staff(
        staff_payload(selected_terminal_id=terminal_id)
    )

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={
            "terminal_id": destination_terminal_id,
        },
    )

    assert response.status_code == 400


def test_invalid_update_status_is_rejected():
    staff = create_staff()

    response = client.patch(
        f"/api/v1/ground-staff/{staff['id']}",
        headers=admin_headers,
        json={"status": "invalid_status"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# AUTHORIZATION TESTS
# ---------------------------------------------------------

def test_ground_staff_endpoint_requires_authentication():
    response = client.get("/api/v1/ground-staff/")

    assert response.status_code in (401, 403)


def test_flight_officer_cannot_manage_ground_staff():
    response = client.get(
        "/api/v1/ground-staff/",
        headers=flight_officer_headers,
    )

    assert response.status_code == 403


def test_ground_staff_creation_requires_authorization():
    user = create_user()

    response = client.post(
        "/api/v1/ground-staff/",
        json=staff_payload(user_id=user["id"]),
    )

    assert response.status_code in (401, 403)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)
