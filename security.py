
import hashlib
import secrets

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash

from core.config import settings
from core.constants import TokenType


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hasher.verify(
        plain_password,
        hashed_password
    )


def create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta
):

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": subject,
        "type": token_type.value,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(user_id: str):

    return create_token(
        subject=user_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


def create_refresh_token(user_id: str):

    return create_token(
        subject=user_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )


def create_password_reset_token(user_id: str):

    return create_token(
        subject=user_id,
        token_type=TokenType.PASSWORD_RESET,
        expires_delta=timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
    )


def decode_token(token: str):

    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

    except JWTError:
        return None


def hash_reset_token(token: str) -> str:

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def generate_secure_reference() -> str:

    return secrets.token_urlsafe(32)
