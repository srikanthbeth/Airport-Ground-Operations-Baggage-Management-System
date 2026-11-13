
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    APP_NAME: str = "Airport Ground Operations & Baggage Management System"

    ENVIRONMENT: str = "development"

    DEBUG: bool = True

    DATABASE_URL: str

    TEST_DATABASE_URL: str

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    BOOTSTRAP_ADMIN_EMAIL: str = "admin@airport.com"

    BOOTSTRAP_ADMIN_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore"
    )


settings = Settings()
