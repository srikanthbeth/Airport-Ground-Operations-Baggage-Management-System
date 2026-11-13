import os
import uuid

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

PASSWORD = "CounterTest@12345"
ADMIN_EMAIL = "counteradmin@airport.example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.add(User(
        full_name="Counter Test Admin",
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
            "name": f"Counter Airport {suffix}",
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
            "name": f"Counter Terminal {suffix}",
            "code": f"T{suffix}",
            "description": "Counter testing terminal",
        },
        headers=headers,
    )
    assert terminal.status_code == 201, terminal.text
    return terminal.json()


def create_counter(headers, terminal_id=None):
    if terminal_id is None:
        terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Check-in Counter A1",
            "airline": "Air India",
            "description": "Domestic check-in counter",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_can_create_counter():
    headers = admin_headers()
    counter = create_counter(headers)
    assert counter["counter_number"] == 1
    assert counter["status"] == "active"


def test_duplicate_counter_number_in_terminal():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]
    create_counter(headers, terminal_id)

    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 1,
            "name": "Duplicate Counter",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_counter_rejects_invalid_terminal():
    headers = admin_headers()
    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": str(uuid.uuid4()),
            "counter_number": 2,
            "name": "Invalid Counter",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_counter_number_must_be_positive():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 0,
            "name": "Invalid Counter",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_counter_name_validation():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 2,
            "name": "A",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_admin_can_list_counters():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]
    create_counter(headers, terminal_id)

    response = client.get(
        f"/api/v1/counters/?terminal_id={terminal_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_admin_can_get_counter():
    headers = admin_headers()
    counter = create_counter(headers)

    response = client.get(
        f"/api/v1/counters/{counter['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == counter["id"]


def test_get_nonexistent_counter():
    headers = admin_headers()
    response = client.get(
        f"/api/v1/counters/{uuid.uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


def test_admin_can_update_counter():
    headers = admin_headers()
    counter = create_counter(headers)

    response = client.patch(
        f"/api/v1/counters/{counter['id']}",
        json={"airline": "Updated Airline"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["airline"] == "Updated Airline"


def test_admin_can_deactivate_counter():
    headers = admin_headers()
    counter = create_counter(headers)

    response = client.patch(
        f"/api/v1/counters/{counter['id']}",
        json={"status": "inactive"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"


def test_normal_user_cannot_create_counter():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Regular User",
            "email": email,
            "password": PASSWORD,
        },
    )
    assert registration.status_code == 201, registration.text

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text

    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }
    admin = admin_headers()
    terminal_id = create_terminal(admin)["id"]

    response = client.post(
        "/api/v1/counters/",
        json={
            "terminal_id": terminal_id,
            "counter_number": 5,
            "name": "Restricted Counter",
        },
        headers=headers,
    )
    assert response.status_code == 403