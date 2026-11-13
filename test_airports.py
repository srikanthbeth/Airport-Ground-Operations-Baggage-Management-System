
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

PASSWORD = "AirportTest@12345"
ADMIN_EMAIL = "admin@airport.example.com"


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    admin = User(
        full_name="Airport Test Admin",
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
    return f"airport_{uuid.uuid4().hex[:10]}@example.com"


def create_airport(headers=None):
    if headers is None:
        headers = admin_headers()

    payload = {
        "name": "Rajiv Gandhi International Airport",
        "code": f"A{uuid.uuid4().hex[:5].upper()}",
        "city": "Hyderabad",
        "country": "India",
        "address": "Shamshabad, Hyderabad",
        "timezone": "Asia/Kolkata",
    }

    response = client.post(
        "/api/v1/airports/",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def register_regular_user():
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Regular Airport User",
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


def test_admin_can_create_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    assert airport["name"] == "Rajiv Gandhi International Airport"
    assert airport["city"] == "Hyderabad"
    assert airport["country"] == "India"
    assert airport["status"] == "active"


def test_airport_code_is_normalized():
    headers = admin_headers()

    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "Airport Two",
            "code": f"lower{uuid.uuid4().hex[:3]}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["code"].isupper()


def test_duplicate_airport_code_not_allowed():
    headers = admin_headers()
    code = f"D{uuid.uuid4().hex[:5].upper()}"

    payload = {
        "name": "Duplicate Airport",
        "code": code,
        "city": "Hyderabad",
        "country": "India",
        "address": "Hyderabad",
        "timezone": "Asia/Kolkata",
    }

    first = client.post(
        "/api/v1/airports/",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/airports/",
        json=payload,
        headers=headers,
    )

    assert second.status_code == 409, second.text


def test_airport_code_required():
    headers = admin_headers()

    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "Missing Code Airport",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_airport_name_validation():
    headers = admin_headers()

    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "A",
            "code": f"A{uuid.uuid4().hex[:5].upper()}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_airport_code_validation():
    headers = admin_headers()

    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "Invalid Code Airport",
            "code": "A",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_list_airports():
    headers = admin_headers()
    create_airport(headers)

    response = client.get(
        "/api/v1/airports/",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) >= 1


def test_airport_list_pagination():
    headers = admin_headers()
    create_airport(headers)

    response = client.get(
        "/api/v1/airports/?skip=0&limit=5",
        headers=headers,
    )

    assert response.status_code == 200, response.text


def test_invalid_pagination_limit():
    headers = admin_headers()

    response = client.get(
        "/api/v1/airports/?skip=0&limit=0",
        headers=headers,
    )

    assert response.status_code == 422


def test_admin_can_get_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    response = client.get(
        f"/api/v1/airports/{airport['id']}",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == airport["id"]


def test_get_nonexistent_airport():
    headers = admin_headers()

    response = client.get(
        f"/api/v1/airports/{uuid.uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_admin_can_update_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    response = client.patch(
        f"/api/v1/airports/{airport['id']}",
        json={
            "name": "Updated Airport Name",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Airport Name"


def test_admin_can_deactivate_airport():
    headers = admin_headers()
    airport = create_airport(headers)

    response = client.patch(
        f"/api/v1/airports/{airport['id']}/deactivate",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"


def test_deactivate_nonexistent_airport():
    headers = admin_headers()

    response = client.patch(
        f"/api/v1/airports/{uuid.uuid4()}/deactivate",
        headers=headers,
    )

    assert response.status_code == 404


def test_normal_user_cannot_create_airport():
    headers = register_regular_user()

    response = client.post(
        "/api/v1/airports/",
        json={
            "name": "Unauthorized Airport",
            "code": f"U{uuid.uuid4().hex[:5].upper()}",
            "city": "Hyderabad",
            "country": "India",
            "address": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )

    assert response.status_code == 403
