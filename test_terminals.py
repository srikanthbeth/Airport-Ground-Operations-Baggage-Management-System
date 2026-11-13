
import os
import uuid

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from main import app
from db.base import Base
from db.session import engine, SessionLocal
from models.user import User
from core.constants import UserRole
from core.security import hash_password


client = TestClient(app)

PASSWORD = "TerminalTest@12345"
ADMIN_EMAIL = "terminaladmin@airport.example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    admin = User(
        full_name="Terminal Test Admin",
        email=ADMIN_EMAIL,
        hashed_password=hash_password(PASSWORD),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
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


def unique_email():
    return f"terminal_{uuid.uuid4().hex[:10]}@example.com"


def create_airport(headers):
    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "Terminal Test Airport",
            "code": f"A{uuid.uuid4().hex[:5].upper()}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Shamshabad, Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_terminal(headers, airport_id=None):
    if airport_id is None:
        airport = create_airport(headers)
        airport_id = airport["id"]

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport_id,
            "name": "Terminal One",
            "code": f"T{uuid.uuid4().hex[:5].upper()}",
            "description": "International passenger terminal",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def register_regular_user():
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Regular Terminal User",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert login_response.status_code == 200, login_response.text

    return {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }


def test_admin_can_create_terminal():
    headers = admin_headers()
    terminal = create_terminal(headers)

    assert terminal["name"] == "Terminal One"
    assert terminal["status"] == "active"


def test_terminal_code_is_normalized():
    headers = admin_headers()
    airport = create_airport(headers)

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport["id"],
            "name": "Terminal Two",
            "code": f"lower{uuid.uuid4().hex[:3]}",
            "description": "Test terminal",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["code"].isupper()


def test_duplicate_terminal_code_in_same_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    code = f"T{uuid.uuid4().hex[:5].upper()}"

    payload = {
        "airport_id": airport["id"],
        "name": "Duplicate Terminal",
        "code": code,
        "description": "Duplicate terminal test",
    }

    first = client.post(
        "/api/v1/terminals/",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/terminals/",
        json=payload,
        headers=headers,
    )

    assert second.status_code == 409, second.text


def test_same_terminal_code_allowed_in_different_airports():
    headers = admin_headers()

    airport_one = create_airport(headers)
    airport_two = create_airport(headers)

    code = f"T{uuid.uuid4().hex[:5].upper()}"

    payload_one = {
        "airport_id": airport_one["id"],
        "name": "Terminal A",
        "code": code,
        "description": "First airport terminal",
    }

    payload_two = {
        "airport_id": airport_two["id"],
        "name": "Terminal B",
        "code": code,
        "description": "Second airport terminal",
    }

    first = client.post(
        "/api/v1/terminals/",
        json=payload_one,
        headers=headers,
    )

    second = client.post(
        "/api/v1/terminals/",
        json=payload_two,
        headers=headers,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


def test_terminal_requires_airport_id():
    headers = admin_headers()

    response = client.post(
        "/api/v1/terminals/",
        json={
            "name": "Missing Airport Terminal",
            "code": f"T{uuid.uuid4().hex[:5].upper()}",
            "description": "Missing airport ID",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_terminal_rejects_invalid_airport_id():
    headers = admin_headers()

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": str(uuid.uuid4()),
            "name": "Invalid Airport Terminal",
            "code": f"T{uuid.uuid4().hex[:5].upper()}",
            "description": "Invalid airport",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_terminal_name_validation():
    headers = admin_headers()
    airport = create_airport(headers)

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport["id"],
            "name": "A",
            "code": f"T{uuid.uuid4().hex[:5].upper()}",
            "description": "Invalid terminal name",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_list_terminals_by_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    create_terminal(headers, airport["id"])

    response = client.get(
        f"/api/v1/terminals/?airport_id={airport['id']}",
        headers=headers,
    )

    assert response.status_code == 200, response.text


def test_terminal_list_pagination():
    headers = admin_headers()
    airport = create_airport(headers)

    create_terminal(headers, airport["id"])

    response = client.get(
        f"/api/v1/terminals/?airport_id={airport['id']}&skip=0&limit=5",
        headers=headers,
    )

    assert response.status_code == 200, response.text


def test_admin_can_get_terminal():
    headers = admin_headers()
    terminal = create_terminal(headers)

    response = client.get(
        f"/api/v1/terminals/{terminal['id']}",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == terminal["id"]


def test_get_nonexistent_terminal():
    headers = admin_headers()

    response = client.get(
        f"/api/v1/terminals/{uuid.uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_admin_can_update_terminal():
    headers = admin_headers()
    terminal = create_terminal(headers)

    response = client.patch(
        f"/api/v1/terminals/{terminal['id']}",
        json={
            "name": "Updated Terminal Name",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Terminal Name"


def test_admin_can_deactivate_terminal():
    headers = admin_headers()
    terminal = create_terminal(headers)

    response = client.patch(
        f"/api/v1/terminals/{terminal['id']}/deactivate",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"


def test_deactivate_nonexistent_terminal():
    headers = admin_headers()

    response = client.patch(
        f"/api/v1/terminals/{uuid.uuid4()}/deactivate",
        headers=headers,
    )

    assert response.status_code == 404


def test_normal_user_cannot_create_terminal():
    admin = admin_headers()
    airport = create_airport(admin)

    user_headers = register_regular_user()

    response = client.post(
        "/api/v1/terminals/",
        json={
            "airport_id": airport["id"],
            "name": "Unauthorized Terminal",
            "code": f"T{uuid.uuid4().hex[:5].upper()}",
            "description": "Unauthorized terminal",
        },
        headers=user_headers,
    )

    assert response.status_code == 403
