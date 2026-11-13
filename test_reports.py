
import os

import pytest
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
MANAGER_EMAIL = "reports_manager@example.com"

REPORT_TYPES = [
    "daily-flight-operations",
    "monthly-flight-performance",
    "baggage-handling",
    "missing-baggage",
    "ground-staff-performance",
    "equipment-utilization",
    "flight-delay-analysis",
    "aircraft-turnaround",
]


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        manager = User(
            full_name="Reports Manager",
            email=MANAGER_EMAIL,
            hashed_password=hash_password(PASSWORD),
            role=UserRole.AIRPORT_OPERATIONS_MANAGER,
            is_active=True,
            is_verified=True,
        )
        db.add(manager)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def get_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": MANAGER_EMAIL,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers():
    return {
        "Authorization": f"Bearer {get_token()}"
    }


def test_all_report_types_return_success():
    headers = auth_headers()

    for report_type in REPORT_TYPES:
        response = client.get(
            f"/api/v1/reports/{report_type}",
            headers=headers,
        )

        assert response.status_code == 200, (
            report_type,
            response.text,
        )

        data = response.json()
        assert data["report_type"] == report_type
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["items"] == []


def test_report_supports_date_range():
    response = client.get(
        "/api/v1/reports/daily-flight-operations",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_report_supports_pagination():
    response = client.get(
        "/api/v1/reports/daily-flight-operations",
        params={
            "page": 1,
            "page_size": 10,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 10


def test_report_rejects_invalid_date():
    response = client.get(
        "/api/v1/reports/daily-flight-operations",
        params={
            "date_from": "not-a-date",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 400


def test_report_rejects_reversed_date_range():
    response = client.get(
        "/api/v1/reports/daily-flight-operations",
        params={
            "date_from": "2026-12-31",
            "date_to": "2026-01-01",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 400


def test_report_rejects_unknown_report_type():
    response = client.get(
        "/api/v1/reports/unknown-report",
        headers=auth_headers(),
    )

    assert response.status_code == 400


def test_report_rejects_invalid_page_size():
    response = client.get(
        "/api/v1/reports/daily-flight-operations",
        params={"page_size": 500},
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_report_csv_export():
    response = client.get(
        "/api/v1/reports/daily-flight-operations/export",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "No records found" in response.text


def test_csv_export_supports_date_range():
    response = client.get(
        "/api/v1/reports/baggage-handling/export",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


def test_reports_reject_unauthenticated_request():
    response = client.get(
        "/api/v1/reports/daily-flight-operations"
    )

    assert response.status_code in (401, 403)
