from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import CheckInStatus


class CheckInCreate(BaseModel):
    passenger_id: UUID
    flight_id: UUID
    counter_id: UUID
    seat_number: str = Field(min_length=1, max_length=10)


class CheckInResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    passenger_id: UUID
    flight_id: UUID
    counter_id: UUID
    seat_number: str
    status: CheckInStatus
    checked_in_at: datetime
    created_at: datetime
    updated_at: datetime


class CheckInCancelResponse(BaseModel):
    message: str
    checkin_id: UUID
    status: CheckInStatus