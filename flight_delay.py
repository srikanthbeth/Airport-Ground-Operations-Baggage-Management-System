from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import (
    FlightDelayReason,
    FlightDelayStatus,
    FlightDelayImpact,
)


class FlightDelayCreate(BaseModel):
    flight_id: UUID

    reason: FlightDelayReason
    impact: FlightDelayImpact = FlightDelayImpact.MEDIUM

    description: str = Field(min_length=5, max_length=5000)

    revised_departure: datetime
    revised_arrival: datetime

    assigned_to_id: UUID | None = None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Description cannot be empty")

        return value

    @field_validator("revised_departure", "revised_arrival")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a timezone")

        return value

    @model_validator(mode="after")
    def validate_revised_times(self):
        if self.revised_arrival <= self.revised_departure:
            raise ValueError(
                "Revised arrival must be after revised departure"
            )

        return self


class FlightDelayAssignment(BaseModel):
    assigned_to_id: UUID


class FlightDelayReview(BaseModel):
    status: FlightDelayStatus
    resolution_notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("resolution_notes")
    @classmethod
    def normalize_notes(cls, value):
        return value.strip() if value is not None else value


class FlightDelayResponse(BaseModel):
    id: UUID
    flight_id: UUID
    reported_by_id: UUID
    assigned_to_id: UUID | None

    reason: FlightDelayReason
    impact: FlightDelayImpact
    status: FlightDelayStatus

    description: str

    original_departure: datetime
    revised_departure: datetime

    original_arrival: datetime
    revised_arrival: datetime

    delay_duration_minutes: int

    resolution_notes: str | None

    reported_at: datetime
    approved_at: datetime | None
    resolved_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlightDelayListResponse(BaseModel):
    items: list[FlightDelayResponse]
    total: int
    page: int
    size: int
    pages: int

class FlightDelayResolve(BaseModel):
    resolution_notes: str = Field(min_length=5, max_length=5000)

    @field_validator("resolution_notes")
    @classmethod
    def normalize_resolution_notes(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Resolution notes cannot be empty")

        return value