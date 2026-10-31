"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Smart Roster Management System"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "local"  # local | test | production

    # Database
    DATABASE_URL: str = "postgresql+psycopg://rosterops:rosterops@localhost:5432/rosterops"

    # Auth & Security
    JWT_SECRET: str = "dev-insecure-secret-key-change-in-production-1234567890"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str | list[str] = "http://localhost:5173"

    # Solver
    SOLVER_TIME_LIMIT_S: int = 20
    SOLVER_SEED: int = 42

    # Observability & Seed
    LOG_LEVEL: str = "INFO"
    SEED_ON_START: bool = False
    DEMO_PASSWORD: str = "change-me-at-deploy-time"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
