
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User
from models.password_reset import PasswordResetToken
from core.constants import UserRole, TokenType
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
    hash_reset_token,
)


def register_user(db: Session, data):

    email = str(data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise ValueError("Email already registered")

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        hashed_password=hash_password(data.password),
        role=UserRole.BAGGAGE_HANDLING_STAFF,
        is_active=True,
        is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str):

    normalized_email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if not user or not verify_password(
        password,
        user.hashed_password
    ):
        raise ValueError("Invalid email or password")

    if not user.is_active:
        raise ValueError("User account is inactive")

    return user


def generate_auth_tokens(user: User):

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer"
    }


def refresh_access_token(db: Session, refresh_token: str):

    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != TokenType.REFRESH.value:
        raise ValueError("Invalid refresh token")

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise ValueError("Invalid refresh token")

    user = db.get(User, user_id)

    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer"
    }


def request_password_reset(db: Session, email: str):

    normalized_email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if not user or not user.is_active:
        return None

    raw_token = create_password_reset_token(str(user.id))

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=(
            datetime.now(timezone.utc) +
            timedelta(minutes=15)
        )
    )

    db.add(reset_record)
    db.commit()

    return raw_token


def confirm_password_reset(
    db: Session,
    token: str,
    new_password: str
):

    payload = decode_token(token)

    if (
        not payload
        or payload.get("type") != TokenType.PASSWORD_RESET.value
    ):
        raise ValueError("Invalid or expired reset token")

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise ValueError("Invalid reset token")

    token_hash = hash_reset_token(token)

    reset_record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None)
        )
    )

    if not reset_record:
        raise ValueError("Invalid or already used reset token")

    expires_at = reset_record.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("Password reset token has expired")

    user = db.get(User, user_id)

    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    user.hashed_password = hash_password(new_password)

    reset_record.used_at = datetime.now(timezone.utc)

    db.commit()

    return True
