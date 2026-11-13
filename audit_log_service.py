
from typing import Any

from sqlalchemy.orm import Session

from models.audit_log import AuditLog


class AuditLogService:

    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        *,
        user_id: int | str | None,
        action: str,
        entity_type: str,
        entity_id: int | str,
        previous_value: dict[str, Any] | list[Any] | None = None,
        new_value: dict[str, Any] | list[Any] | None = None,
        description: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=str(user_id) if user_id is not None else None,
            action=action.strip().lower(),
            entity_type=entity_type.strip().lower(),
            entity_id=str(entity_id),
            previous_value=previous_value,
            new_value=new_value,
            description=description,
        )

        self.db.add(log)
        self.db.flush()

        return log

    def get_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        user_id: int | str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: int | str | None = None,
    ) -> tuple[int, list[AuditLog]]:

        query = self.db.query(AuditLog)

        if user_id is not None:
            query = query.filter(AuditLog.user_id == str(user_id))

        if action:
            query = query.filter(AuditLog.action == action.strip().lower())

        if entity_type:
            query = query.filter(
                AuditLog.entity_type == entity_type.strip().lower()
            )

        if entity_id is not None:
            query = query.filter(AuditLog.entity_id == str(entity_id))

        total = query.count()

        items = (
            query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items
