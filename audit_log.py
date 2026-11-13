
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text

from db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String(100), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)

    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)

    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    description = Column(Text, nullable=True)

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_entity_timestamp", "entity_type", "entity_id", "timestamp"),
        Index("ix_audit_user_timestamp", "user_id", "timestamp"),
    )
