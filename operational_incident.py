from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.constants import (
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)


class OperationalIncidentCreate(BaseModel):
    incident_number: str = Field(min_length=3, max_length=30)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    category: IncidentCategory
    severity: IncidentSeverity = IncidentSeverity.MEDIUM

    airport_id: UUID
    flight_id: UUID | None = None

    location: str | None = Field(default=None, max_length=200)
    occurred_at: datetime

    @model_validator(mode="after")
    def validate_occurred_at(self):
        if self.occurred_at > datetime.now(timezone.utc):
            raise ValueError("Incident occurrence time cannot be in the future")
        return self


class OperationalIncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=5)
    category: IncidentCategory | None = None
    severity: IncidentSeverity | None = None
    flight_id: UUID | None = None
    location: str | None = Field(default=None, max_length=200)


class IncidentAssignment(BaseModel):
    assigned_to_id: UUID


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    resolution_notes: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self):
        if self.status == IncidentStatus.RESOLVED:
            if not self.resolution_notes or not self.resolution_notes.strip():
                raise ValueError("Resolution notes are required to resolve an incident")
        return self


class OperationalIncidentResponse(BaseModel):
    id: UUID
    incident_number: str
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus

    airport_id: UUID
    flight_id: UUID | None

    reported_by_id: UUID
    assigned_to_id: UUID | None

    location: str | None

    occurred_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None

    resolution_notes: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationalIncidentListResponse(BaseModel):
    items: list[OperationalIncidentResponse]
    total: int
    skip: int
    limit: int