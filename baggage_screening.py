
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import (
    BaggageScreeningStatus,
    ScreeningMethod,
)


class BaggageScreeningStart(BaseModel):
    screening_method: ScreeningMethod
    notes: str | None = Field(default=None, max_length=2000)


class BaggageScreeningComplete(BaseModel):
    status: BaggageScreeningStatus
    notes: str | None = Field(default=None, max_length=2000)


class BaggageScreeningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    baggage_id: UUID
    screening_method: ScreeningMethod
    status: BaggageScreeningStatus
    notes: str | None
    screened_by: UUID | None
    started_at: datetime
    completed_at: datetime | None


class BaggageScreeningListResponse(BaseModel):
    items: list[BaggageScreeningResponse]
    total: int
    page: int
    page_size: int
    pages: int
