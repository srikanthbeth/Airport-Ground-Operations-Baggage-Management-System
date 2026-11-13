
import os
import uuid

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from main import app
from db.base import Base
from db.session import engine, SessionLocal
from models.user import User
from core.constants import UserRole
from core.security import hash_password


client = TestClient(app)

PASSWORD = "AirportTest@12345"


def unique_email():
    return f"airport_{uuid.uuid4().hex[:12]}@test.com"


def create_user(
    role=UserRole.BAGGAGE_HANDLING_STAFF,
    is_active=True
):

    db = SessionLocal()

    user = User(
        full_name="Airport Test User",
        email=unique_email(),
        hashed_password=hash_password(PASSWORD),
        role=role,
        is_active=is_active,
        is_verified=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    db.close()

    return user


def get_token(email, password=PASSWORD):

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    return response.json()["access_token"]


def setup_module(module):

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module(module):

    Base.metadata.drop_all(bind=engine)


def test_user_registration():

    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Airport Staff",
            "email": email,
            "password": PASSWORD
        }
    )

    assert response.status_code == 201
    assert response.json()["email"] == email
    assert response.json()["role"] == "baggage_handling_staff"


def test_public_registration_cannot_select_admin_role():

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Fake Admin",
            "email": unique_email(),
            "password": PASSWORD,
            "role": "super_admin"
        }
    )

    assert response.status_code == 201
    assert response.json()["role"] == "baggage_handling_staff"


def test_duplicate_email_registration():

    email = unique_email()

    payload = {
        "full_name": "Airport Staff",
        "email": email,
        "password": PASSWORD
    }

    first = client.post(
        "/api/v1/auth/register",
        json=payload
    )

    second = client.post(
        "/api/v1/auth/register",
        json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 400


def test_successful_login():

    user = create_user()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": PASSWORD
        }
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


def test_invalid_password():

    user = create_user()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "WrongPassword@123"
        }
    )

    assert response.status_code == 401


def test_nonexistent_user_login():

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email(),
            "password": PASSWORD
        }
    )

    assert response.status_code == 401


def test_inactive_user_cannot_login():

    user = create_user(is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": PASSWORD
        }
    )

    assert response.status_code == 401


def test_current_user_endpoint():

    user = create_user()

    token = get_token(user.email)

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_current_user_without_token():

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_access_token():

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        }
    )

    assert response.status_code == 401


def test_refresh_token():

    user = create_user()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": PASSWORD
        }
    )

    refresh_token = login.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token
        }
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


def test_access_token_cannot_be_used_as_refresh_token():

    user = create_user()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": PASSWORD
        }
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": login.json()["access_token"]
        }
    )

    assert response.status_code == 401


def test_password_reset():

    from core.config import settings

    settings.DEBUG = True

    user = create_user()

    request = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": user.email}
    )

    assert request.status_code == 200

    reset_token = request.json()["reset_token"]

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "NewAirport@12345"
        }
    )

    assert confirm.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "NewAirport@12345"
        }
    )

    assert login.status_code == 200


def test_password_reset_token_cannot_be_reused():

    from core.config import settings

    settings.DEBUG = True

    user = create_user()

    request = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": user.email}
    )

    token = request.json()["reset_token"]

    payload = {
        "token": token,
        "new_password": "NewAirport@12345"
    }

    first = client.post(
        "/api/v1/auth/password-reset/confirm",
        json=payload
    )

    second = client.post(
        "/api/v1/auth/password-reset/confirm",
        json=payload
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_password_hashing():

    user = create_user()

    assert user.hashed_password != PASSWORD


def test_weak_password_registration():

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Weak User",
            "email": unique_email(),
            "password": "weak"
        }
    )

    assert response.status_code == 422


def test_admin_can_create_user():

    admin = create_user(role=UserRole.SUPER_ADMIN)

    token = get_token(admin.email)

    response = client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Checkin Agent",
            "email": unique_email(),
            "password": PASSWORD,
            "role": "checkin_agent"
        }
    )

    assert response.status_code == 201
    assert response.json()["role"] == "checkin_agent"


def test_normal_user_cannot_create_staff():

    user = create_user()

    token = get_token(user.email)

    response = client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Unauthorized User",
            "email": unique_email(),
            "password": PASSWORD,
            "role": "gate_agent"
        }
    )

    assert response.status_code == 403


def test_admin_can_list_users():

    admin = create_user(role=UserRole.SUPER_ADMIN)

    token = get_token(admin.email)

    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_admin_can_deactivate_user():

    admin = create_user(role=UserRole.SUPER_ADMIN)
    staff = create_user()

    token = get_token(admin.email)

    response = client.patch(
        f"/api/v1/users/{staff.id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_can_activate_user():

    admin = create_user(role=UserRole.SUPER_ADMIN)
    staff = create_user(is_active=False)

    token = get_token(admin.email)

    response = client.patch(
        f"/api/v1/users/{staff.id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_admin_cannot_deactivate_self():

    admin = create_user(role=UserRole.SUPER_ADMIN)

    token = get_token(admin.email)

    response = client.patch(
        f"/api/v1/users/{admin.id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
