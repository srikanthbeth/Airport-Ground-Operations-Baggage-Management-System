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

PASSWORD = "GateTest@12345"
ADMIN_EMAIL = "gateadmin@airport.example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    db.add(User(
        full_name="Gate Test Admin",
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

    airport_response = client.post(
        "/api/v1/airports/",
        json={
            "name": f"Gate Airport {suffix}",
            "code": f"A{suffix}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )
    assert airport_response.status_code == 201, airport_response.text

    terminal_response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport_response.json()["id"],
            "name": f"Gate Terminal {suffix}",
            "code": f"T{suffix}",
            "description": "Gate testing terminal",
        },
        headers=headers,
    )
    assert terminal_response.status_code == 201, terminal_response.text
    return terminal_response.json()


def create_gate(headers, terminal_id=None):
    if terminal_id is None:
        terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": terminal_id,
            "gate_number": 1,
            "name": "Gate A1",
            "description": "International boarding gate",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_can_create_gate():
    headers = admin_headers()
    gate = create_gate(headers)
    assert gate["gate_number"] == 1
    assert gate["status"] == "active"


def test_duplicate_gate_number_in_terminal():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]
    create_gate(headers, terminal_id)

    response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": terminal_id,
            "gate_number": 1,
            "name": "Duplicate Gate",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_gate_rejects_invalid_terminal():
    headers = admin_headers()
    response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": str(uuid.uuid4()),
            "gate_number": 1,
            "name": "Invalid Gate",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_gate_number_must_be_positive():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": terminal_id,
            "gate_number": 0,
            "name": "Invalid Gate",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_gate_name_validation():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]

    response = client.post(
        "/api/v1/gates/",
        json={
            "terminal_id": terminal_id,
            "gate_number": 2,
            "name": "A",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_admin_can_list_gates():
    headers = admin_headers()
    terminal_id = create_terminal(headers)["id"]
    create_gate(headers, terminal_id)

    response = client.get(
        f"/api/v1/gates/?terminal_id={terminal_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_admin_can_get_gate():
    headers = admin_headers()
    gate = create_gate(headers)

    response = client.get(
        f"/api/v1/gates/{gate['id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == gate["id"]


def test_get_nonexistent_gate():
    headers = admin_headers()
    response = client.get(
        f"/api/v1/gates/{uuid.uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


def test_admin_can_update_gate():
    headers = admin_headers()
    gate = create_gate(headers)

    response = client.patch(
        f"/api/v1/gates/{gate['id']}",
        json={"name": "Updated Gate"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Gate"


def test_admin_can_deactivate_gate():
    headers = admin_headers()
    gate = create_gate(headers)

    response = client.patch(
        f"/api/v1/gates/{gate['id']}",
        json={"status": "inactive"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"


def test_normal_user_cannot_create_gate():
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
        "/api/v1/gates/",
        json={
            "terminal_id": terminal_id,
            "gate_number": 5,
            "name": "Restricted Gate",
        },
        headers=headers,
    )
    assert response.status_code == 403