
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.constants import (
    AircraftTurnaroundStatus,
    TurnaroundMilestone,
)


class AircraftTurnaroundCreate(BaseModel):
    turnaround_number: str = Field(min_length=3, max_length=40)

    flight_id: uuid.UUID | None = None
    airport_id: uuid.UUID
    terminal_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None

    aircraft_registration: str = Field(min_length=2, max_length=30)
    aircraft_type: str = Field(min_length=2, max_length=80)

    scheduled_arrival: datetime
    scheduled_departure: datetime

    notes: str | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scheduled_departure <= self.scheduled_arrival:
            raise ValueError(
                "Scheduled departure must be after scheduled arrival"
            )
        return self


class AircraftTurnaroundUpdate(BaseModel):
    terminal_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None

    aircraft_registration: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
    )

    aircraft_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
    )

    scheduled_arrival: datetime | None = None
    scheduled_departure: datetime | None = None

    notes: str | None = None


class AircraftTurnaroundStatusUpdate(BaseModel):
    status: AircraftTurnaroundStatus


class TurnaroundMilestoneUpdate(BaseModel):
    milestone: TurnaroundMilestone
    completed_at: datetime | None = None


class AircraftTurnaroundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    turnaround_number: str

    flight_id: uuid.UUID | None = None
    airport_id: uuid.UUID
    terminal_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None

    aircraft_registration: str
    aircraft_type: str
    status: AircraftTurnaroundStatus

    scheduled_arrival: datetime
    scheduled_departure: datetime

    actual_arrival: datetime | None = None
    actual_departure: datetime | None = None

    passengers_disembarked_at: datetime | None = None
    baggage_unloaded_at: datetime | None = None
    cleaning_completed_at: datetime | None = None
    catering_completed_at: datetime | None = None
    refuelling_completed_at: datetime | None = None
    baggage_loaded_at: datetime | None = None
    boarding_completed_at: datetime | None = None
    chocks_off_at: datetime | None = None

    notes: str | None = None

    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AircraftTurnaroundListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AircraftTurnaroundResponse]
