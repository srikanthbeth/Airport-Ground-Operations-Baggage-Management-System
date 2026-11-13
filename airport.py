from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import AirportStatus


class AirportCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=3, max_length=10)
    city: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    address: str | None = None
    timezone: str = Field(min_length=2, max_length=100)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper()


class AirportUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=100)
    status: AirportStatus | None = None


class AirportResponse(BaseModel):
    id: UUID
    name: str
    code: str
    city: str
    country: str
    address: str | None
    timezone: str
    status: AirportStatus
    is_active: bool

    model_config = ConfigDict(from_attributes=True)