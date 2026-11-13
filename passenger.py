from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from core.constants import PassengerStatus, IdentificationType


class PassengerCreate(BaseModel):
    flight_id: UUID

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str = Field(min_length=7, max_length=20)

    date_of_birth: date
    nationality: str = Field(min_length=2, max_length=100)

    identification_type: IdentificationType = IdentificationType.PASSPORT
    identification_number: str = Field(min_length=3, max_length=100)

    @field_validator("full_name", "nationality", "identification_number")
    @classmethod
    def strip_text(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        value = value.strip()

        if not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Invalid phone number")

        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value):
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")

        return value


class PassengerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, min_length=2, max_length=100)
    identification_type: IdentificationType | None = None
    identification_number: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    @field_validator("full_name", "nationality", "identification_number")
    @classmethod
    def strip_optional_text(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("phone")
    @classmethod
    def validate_optional_phone(cls, value):
        if value is None:
            return value

        value = value.strip()

        if not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Invalid phone number")

        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_optional_date_of_birth(cls, value):
        if value is not None and value >= date.today():
            raise ValueError("Date of birth must be in the past")

        return value


class PassengerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flight_id: UUID
    full_name: str
    email: str | None
    phone: str
    date_of_birth: date
    nationality: str
    identification_type: IdentificationType
    identification_number: str
    status: PassengerStatus
    created_at: datetime
    updated_at: datetime