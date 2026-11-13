
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from uuid import UUID
from core.constants import UserRole

class RegisterRequest(BaseModel):

    full_name: str = Field(min_length=2, max_length=150)

    email: EmailStr

    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain uppercase letter")

        if not any(c.islower() for c in value):
            raise ValueError("Password must contain lowercase letter")

        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a number")

        if not any(not c.isalnum() for c in value):
            raise ValueError("Password must contain a special character")

        return value


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


class RefreshTokenRequest(BaseModel):

    refresh_token: str


class PasswordResetRequest(BaseModel):

    email: EmailStr


class PasswordResetConfirm(BaseModel):

    token: str

    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value):

        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain uppercase letter")

        if not any(c.islower() for c in value):
            raise ValueError("Password must contain lowercase letter")

        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a number")

        if not any(not c.isalnum() for c in value):
            raise ValueError("Password must contain a special character")

        return value


class TokenResponse(BaseModel):

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):

    access_token: str

    refresh_token: str

    token_type: str = "bearer"

    user: UserResponse


class MessageResponse(BaseModel):

    message: str


class PasswordResetResponse(BaseModel):

    message: str

    reset_token: str | None = None
