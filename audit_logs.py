
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    previous_value: dict[str, Any] | list[Any] | None = None
    new_value: dict[str, Any] | list[Any] | None = None
    description: str | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    previous_value: Any | None
    new_value: Any | None
    description: str | None
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AuditLogResponse]
