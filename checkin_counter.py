from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import CounterStatus


class CounterCreate(BaseModel):
    terminal_id: UUID
    counter_number: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=100)
    airline: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "airline")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value is not None else value


class CounterUpdate(BaseModel):
    counter_number: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=100)
    airline: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    status: CounterStatus | None = None

    @field_validator("name", "airline")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value is not None else value


class CounterResponse(BaseModel):
    id: UUID
    terminal_id: UUID
    counter_number: int
    name: str
    airline: str | None
    description: str | None
    status: CounterStatus

    model_config = ConfigDict(from_attributes=True)