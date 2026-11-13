
import os
import uuid

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

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
staff_headers = {}
officer_headers = {}

airport_id = None
terminal_id = None
ground_staff_id = None

counter = 0


def unique_value():
    return uuid.uuid4().hex[:10].upper()


def create_user(role=UserRole.BAGGAGE_HANDLING_STAFF):
    value = unique_value()

    db = SessionLocal()

    user = User(
        full_name=f"Ground Task User {value}",
        email=f"groundtask_{value.lower()}@example.com",
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_active=True,
        is_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    user_id = user.id
    email = user.email

    db.close()

    return user_id, email


def login_headers(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def setup_module():
    global admin_headers
    global staff_headers
    global officer_headers
    global airport_id
    global terminal_id
    global ground_staff_id
    global counter

    counter = 0

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _, admin_email = create_user(UserRole.SUPER_ADMIN)
    _, officer_email = create_user(
        UserRole.FLIGHT_OPERATIONS_OFFICER
    )

    admin_headers = login_headers(admin_email)
    officer_headers = login_headers(officer_email)

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

    terminal_response = client.post(
        "/api/v1/terminals/",
        headers=admin_headers,
        json={
            "airport_id": airport_id,
            "code": "T1",
            "name": "Terminal 1",
            "description": "Hyderabad main terminal",
        },
    )

    assert terminal_response.status_code == 201, terminal_response.text
    terminal_id = terminal_response.json()["id"]

    staff_user_id, staff_email = create_user(
        UserRole.BAGGAGE_HANDLING_STAFF
    )

    staff_headers = login_headers(staff_email)

    staff_response = client.post(
        "/api/v1/ground-staff/",
        headers=admin_headers,
        json={
            "user_id": str(staff_user_id),
            "employee_number": f"EMP-{unique_value()}",
            "department": "baggage_handling",
            "designation": "Baggage Handler",
            "phone": "9876543210",
            "shift": "morning",
            "airport_id": airport_id,
            "terminal_id": terminal_id,
            "date_of_joining": "2024-01-01",
        },
    )

    assert staff_response.status_code == 201, staff_response.text
    ground_staff_id = staff_response.json()["id"]


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def task_payload(**overrides):
    global counter
    counter += 1

    payload = {
        "task_number": f"TASK-{counter}-{unique_value()}",
        "title": "Prepare baggage handling area",
        "description": "Prepare the baggage handling area before arrival",
        "category": "baggage_handling",
        "priority": "normal",
        "ground_staff_id": ground_staff_id,
        "airport_id": airport_id,
        "terminal_id": terminal_id,
        "location": "Baggage Area",
    }

    payload.update(overrides)
    return payload


def create_task(**overrides):
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(**overrides),
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_admin_can_create_ground_task():
    task = create_task()

    assert task["title"] == "Prepare baggage handling area"
    assert task["status"] == "assigned"
    assert task["priority"] == "normal"
    assert task["ground_staff_id"] == ground_staff_id


def test_ground_task_can_be_created_without_terminal():
    task = create_task(terminal_id=None)

    assert task["terminal_id"] is None


def test_duplicate_task_number_is_rejected():
    payload = task_payload()

    first = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201

    second = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=payload,
    )

    assert second.status_code == 409


def test_nonexistent_ground_staff_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(ground_staff_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404


def test_nonexistent_airport_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(airport_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404

def test_staff_from_another_airport_is_rejected():
    second_airport_response = client.post(
        "/api/v1/airports/",
        headers=admin_headers,
        json={
            "code": f"HY{unique_value()[:3]}",
            "name": "Second Test Airport",
            "city": "Bengaluru",
            "country": "India",
            "address": "Bengaluru, Karnataka",
            "timezone": "Asia/Kolkata",
        },
    )

    assert second_airport_response.status_code == 201

    second_airport_id = second_airport_response.json()["id"]

    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(
            airport_id=second_airport_id
        ),
    )

    assert response.status_code == 400

def test_nonexistent_terminal_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(terminal_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404


def test_invalid_category_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(category="invalid_category"),
    )

    assert response.status_code == 422


def test_invalid_priority_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(priority="critical"),
    )

    assert response.status_code == 422


def test_invalid_schedule_is_rejected():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        json=task_payload(
            scheduled_start="2026-11-11T12:00:00+05:30",
            scheduled_end="2026-11-11T11:00:00+05:30",
        ),
    )

    assert response.status_code == 422


def test_admin_can_get_ground_task():
    task = create_task()

    response = client.get(
        f"/api/v1/ground-tasks/{task['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


def test_nonexistent_ground_task_returns_404():
    response = client.get(
        f"/api/v1/ground-tasks/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_admin_can_list_ground_tasks():
    create_task()
    create_task()

    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 2
    assert len(response.json()["items"]) >= 2


def test_ground_task_filter_by_status():
    task = create_task()

    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        params={"status": "assigned"},
    )

    assert response.status_code == 200
    assert all(item["status"] == "assigned" for item in response.json()["items"])


def test_ground_task_filter_by_priority():
    create_task(priority="urgent")

    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        params={"priority": "urgent"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert all(item["priority"] == "urgent" for item in response.json()["items"])


def test_ground_task_filter_by_category():
    create_task(category="aircraft_cleaning")

    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        params={"category": "aircraft_cleaning"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_ground_task_pagination():
    for _ in range(3):
        create_task()

    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        params={"page": 1, "page_size": 2},
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["page"] == 1


def test_invalid_pagination_is_rejected():
    response = client.get(
        "/api/v1/ground-tasks/",
        headers=admin_headers,
        params={"page": 0},
    )

    assert response.status_code == 422


def test_admin_can_update_ground_task():
    task = create_task()

    response = client.patch(
        f"/api/v1/ground-tasks/{task['id']}",
        headers=admin_headers,
        json={
            "title": "Updated baggage preparation task",
            "priority": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated baggage preparation task"
    assert response.json()["priority"] == "high"


def test_assigned_staff_can_start_own_task():
    task = create_task()

    response = client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=staff_headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["started_at"] is not None


def test_assigned_staff_can_complete_own_task():
    task = create_task()

    start = client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=staff_headers,
        json={"status": "in_progress"},
    )

    assert start.status_code == 200

    complete = client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=staff_headers,
        json={"status": "completed"},
    )

    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert complete.json()["completed_at"] is not None


def test_invalid_status_transition_is_rejected():
    task = create_task()

    response = client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=admin_headers,
        json={"status": "completed"},
    )

    assert response.status_code == 400


def test_completed_task_cannot_be_reopened():
    task = create_task()

    client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=admin_headers,
        json={"status": "completed"},
    )

    response = client.patch(
        f"/api/v1/ground-tasks/{task['id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 400


def test_ground_task_requires_authentication():
    response = client.get("/api/v1/ground-tasks/")

    assert response.status_code == 401


def test_flight_officer_cannot_manage_ground_tasks():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=officer_headers,
        json=task_payload(),
    )

    assert response.status_code == 403


def test_ground_staff_cannot_manage_task_assignments():
    response = client.post(
        "/api/v1/ground-tasks/",
        headers=staff_headers,
        json=task_payload(),
    )

    assert response.status_code == 403
