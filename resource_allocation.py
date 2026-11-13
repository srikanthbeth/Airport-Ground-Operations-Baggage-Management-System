
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.constants import (
    AllocationResourceType,
    ResourceAllocationStatus,
)


class ResourceAllocationCreate(BaseModel):
    flight_id: UUID
    resource_type: AllocationResourceType
    resource_id: UUID
    starts_at: datetime
    ends_at: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("starts_at must include a timezone")

        if self.ends_at.tzinfo is None or self.ends_at.utcoffset() is None:
            raise ValueError("ends_at must include a timezone")

        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")

        return self


class ResourceAllocationUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_schedule(self):
        for field_name in ("starts_at", "ends_at"):
            value = getattr(self, field_name)
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise ValueError(f"{field_name} must include a timezone")

        if self.starts_at and self.ends_at:
            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be later than starts_at")

        return self


class ResourceAllocationResponse(BaseModel):
    id: UUID
    flight_id: UUID
    resource_type: AllocationResourceType
    gate_id: UUID | None
    counter_id: UUID | None
    ground_staff_id: UUID | None
    equipment_id: UUID | None
    starts_at: datetime
    ends_at: datetime
    status: ResourceAllocationStatus
    notes: str | None
    assigned_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
