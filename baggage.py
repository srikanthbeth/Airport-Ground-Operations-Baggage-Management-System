from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import BaggageStatus, BaggageType


class BaggageCreate(BaseModel):
    passenger_id: UUID
    flight_id: UUID
    checkin_id: UUID

    baggage_type: BaggageType = BaggageType.CHECKED

    weight_kg: float = Field(
        gt=0,
        le=100,
        allow_inf_nan=False,
    )


class BaggageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    baggage_tag: str
    passenger_id: UUID
    flight_id: UUID
    checkin_id: UUID
    baggage_type: BaggageType
    weight_kg: float
    status: BaggageStatus
    registered_at: datetime
    created_at: datetime
    updated_at: datetime


class BaggageCancelResponse(BaseModel):
    message: str
    baggage_id: UUID
    status: BaggageStatus