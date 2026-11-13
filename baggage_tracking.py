from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import BaggageTrackingStatus


class BaggageTrackingCreate(BaseModel):
    status: BaggageTrackingStatus
    location: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class BaggageTrackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    baggage_id: UUID
    status: BaggageTrackingStatus
    location: str
    description: str | None
    recorded_by: UUID | None
    created_at: datetime


class BaggageTrackingListResponse(BaseModel):
    items: list[BaggageTrackingResponse]
    total: int
    page: int
    page_size: int
    pages: int