from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.constants import ResourceAssignmentStatus


class ResourceAssignmentCreate(BaseModel):
    flight_id: UUID


class ResourceAssignmentResponse(BaseModel):
    id: UUID
    flight_id: UUID
    gate_id: UUID | None
    counter_id: UUID | None
    status: ResourceAssignmentStatus
    assigned_at: datetime
    released_at: datetime | None

    model_config = ConfigDict(from_attributes=True)