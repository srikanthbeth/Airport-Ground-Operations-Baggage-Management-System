from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import GateStatus


class GateCreate(BaseModel):
    terminal_id: UUID
    gate_number: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value):
        return value.strip()


class GateUpdate(BaseModel):
    gate_number: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: GateStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value):
        return value.strip() if value is not None else value


class GateResponse(BaseModel):
    id: UUID
    terminal_id: UUID
    gate_number: int
    name: str
    description: str | None
    status: GateStatus

    model_config = ConfigDict(from_attributes=True)