
import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from db.base import Base
from db.session import engine, SessionLocal
import models

from main import app
from models.audit_log import AuditLog
from services.audit_log_service import AuditLogService


client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def create_log(
    db,
    *,
    user_id="101",
    action="update",
    entity_type="flight",
    entity_id="500",
    previous_value=None,
    new_value=None,
):
    return AuditLogService(db).create_log(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
    )


def test_create_audit_log():
    db = SessionLocal()
    try:
        log = create_log(
            db,
            previous_value={"status": "scheduled"},
            new_value={"status": "delayed"},
        )
        db.commit()

        saved = db.query(AuditLog).filter(AuditLog.id == log.id).first()

        assert saved is not None
        assert saved.user_id == "101"
        assert saved.action == "update"
        assert saved.entity_type == "flight"
        assert saved.entity_id == "500"
        assert saved.previous_value == {"status": "scheduled"}
        assert saved.new_value == {"status": "delayed"}
        assert saved.timestamp is not None
    finally:
        db.close()


def test_create_log_normalizes_action_and_entity():
    db = SessionLocal()
    try:
        log = create_log(
            db,
            action="  UPDATE  ",
            entity_type="  Flight  ",
        )
        db.commit()

        assert log.action == "update"
        assert log.entity_type == "flight"
    finally:
        db.close()


def test_get_logs_filters_by_user():
    db = SessionLocal()
    try:
        create_log(db, user_id="user-A", entity_id="101")
        create_log(db, user_id="user-B", entity_id="102")
        db.commit()

        total, items = AuditLogService(db).get_logs(user_id="user-A")

        assert total == 1
        assert items[0].user_id == "user-A"
    finally:
        db.close()


def test_get_logs_filters_by_entity():
    db = SessionLocal()
    try:
        create_log(db, entity_type="baggage", entity_id="B-100")
        create_log(db, entity_type="flight", entity_id="F-100")
        db.commit()

        total, items = AuditLogService(db).get_logs(
            entity_type="baggage",
            entity_id="B-100",
        )

        assert total == 1
        assert items[0].entity_type == "baggage"
        assert items[0].entity_id == "B-100"
    finally:
        db.close()



def test_get_logs_pagination():
    db = SessionLocal()
    try:
        # Remove records created by previous tests.
        db.query(AuditLog).delete()
        db.commit()

        # Insert exactly five records for this test.
        for number in range(5):
            create_log(db, entity_id=str(number))

        db.commit()

        total, first_page = AuditLogService(db).get_logs(
            page=1,
            page_size=2,
        )

        _, second_page = AuditLogService(db).get_logs(
            page=2,
            page_size=2,
        )

        assert total == 5
        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id

    finally:
        db.close()


def test_audit_logs_endpoint_requires_authentication():
    response = client.get("/api/v1/audit-logs/")

    assert response.status_code in (401, 403)


def test_audit_log_detail_requires_authentication():
    response = client.get("/api/v1/audit-logs/1")

    assert response.status_code in (401, 403)
