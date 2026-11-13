from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.constants import FlightStatus, FlightType


class FlightCreate(BaseModel):
    flight_number: str = Field(min_length=2, max_length=20)
    airline: str = Field(min_length=2, max_length=120)

    flight_type: FlightType = FlightType.DOMESTIC

    origin_airport_id: UUID
    destination_airport_id: UUID

    departure_terminal_id: UUID | None = None
    arrival_terminal_id: UUID | None = None

    scheduled_departure: datetime
    scheduled_arrival: datetime

    aircraft_type: str = Field(min_length=2, max_length=100)
    capacity: int = Field(gt=0)

    @field_validator("flight_number")
    @classmethod
    def normalize_flight_number(cls, value):
        return value.strip().upper()

    @field_validator("airline", "aircraft_type")
    @classmethod
    def normalize_text(cls, value):
        return value.strip()

    @field_validator("scheduled_departure", "scheduled_arrival")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_flight(self):
        if self.origin_airport_id == self.destination_airport_id:
            raise ValueError("Origin and destination airports must be different")

        if self.scheduled_arrival <= self.scheduled_departure:
            raise ValueError("Scheduled arrival must be after departure")

        return self


class FlightUpdate(BaseModel):
    flight_number: str | None = Field(default=None, min_length=2, max_length=20)
    airline: str | None = Field(default=None, min_length=2, max_length=120)
    flight_type: FlightType | None = None

    origin_airport_id: UUID | None = None
    destination_airport_id: UUID | None = None

    departure_terminal_id: UUID | None = None
    arrival_terminal_id: UUID | None = None

    scheduled_departure: datetime | None = None
    scheduled_arrival: datetime | None = None

    actual_departure: datetime | None = None
    actual_arrival: datetime | None = None

    aircraft_type: str | None = Field(default=None, min_length=2, max_length=100)
    capacity: int | None = Field(default=None, gt=0)

    @field_validator("flight_number")
    @classmethod
    def normalize_flight_number(cls, value):
        return value.strip().upper() if value is not None else value

    @field_validator("airline", "aircraft_type")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value is not None else value

    @field_validator(
        "scheduled_departure",
        "scheduled_arrival",
        "actual_departure",
        "actual_arrival",
    )
    @classmethod
    def require_timezone(cls, value):
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Datetime must include a timezone")
        return value


class FlightStatusUpdate(BaseModel):
    status: FlightStatus


class FlightResponse(BaseModel):
    id: UUID
    flight_number: str
    airline: str
    flight_type: FlightType

    origin_airport_id: UUID
    destination_airport_id: UUID

    departure_terminal_id: UUID | None
    arrival_terminal_id: UUID | None

    scheduled_departure: datetime
    scheduled_arrival: datetime

    actual_departure: datetime | None
    actual_arrival: datetime | None

    aircraft_type: str
    capacity: int
    status: FlightStatus

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)