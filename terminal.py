from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import TerminalStatus


class TerminalCreate(BaseModel):
    airport_id: UUID
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=1, max_length=10)
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper()


class TerminalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    status: TerminalStatus | None = None


class TerminalResponse(BaseModel):
    id: UUID
    airport_id: UUID
    name: str
    code: str
    description: str | None
    status: TerminalStatus

    model_config = ConfigDict(from_attributes=True)