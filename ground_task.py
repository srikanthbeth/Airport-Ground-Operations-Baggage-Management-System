
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.constants import (
    GroundTaskCategory,
    GroundTaskPriority,
    GroundTaskStatus,
)


class GroundTaskCreate(BaseModel):
    task_number: str = Field(min_length=3, max_length=50)
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None

    category: GroundTaskCategory
    priority: GroundTaskPriority = GroundTaskPriority.NORMAL

    ground_staff_id: UUID
    airport_id: UUID
    terminal_id: UUID | None = None
    flight_id: UUID | None = None

    location: str | None = Field(default=None, max_length=200)

    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if (
            self.scheduled_start
            and self.scheduled_end
            and self.scheduled_end <= self.scheduled_start
        ):
            raise ValueError("Scheduled end must be after scheduled start")
        return self


class GroundTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None

    category: GroundTaskCategory | None = None
    priority: GroundTaskPriority | None = None
    ground_staff_id: UUID | None = None
    airport_id: UUID | None = None
    terminal_id: UUID | None = None
    flight_id: UUID | None = None

    location: str | None = Field(default=None, max_length=200)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if (
            self.scheduled_start
            and self.scheduled_end
            and self.scheduled_end <= self.scheduled_start
        ):
            raise ValueError("Scheduled end must be after scheduled start")
        return self


class GroundTaskStatusUpdate(BaseModel):
    status: GroundTaskStatus


class GroundTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_number: str
    title: str
    description: str | None
    category: GroundTaskCategory
    priority: GroundTaskPriority
    status: GroundTaskStatus

    ground_staff_id: UUID
    airport_id: UUID
    terminal_id: UUID | None
    flight_id: UUID | None

    location: str | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    created_by: UUID
    created_at: datetime
    updated_at: datetime


class GroundTaskListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GroundTaskResponse]
    