from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file.

    Loads settings via BaseSettings, which automatically reads from:
    1. Environment variables
    2. .env file in current directory
    """

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: int = 0
    LOG_FILE_PATH: Optional[str] = None

    ENVIRONMENT: str = "DEVELOPMENT"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if isinstance(v, str) and v.upper() in allowed:
            return v.upper()
        raise ValueError(f"LOG_LEVEL must be one of {'/'.join(allowed)}")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _validate_environment(cls, v: str) -> str:
        allowed = {"DEVELOPMENT", "PRODUCTION"}
        if isinstance(v, str) and v.upper() in allowed:
            return v.upper()
        raise ValueError(f"ENVIRONMENT must be one of {'/'.join(allowed)}")

    @property
    def database_url(self) -> str:
        user = urllib.parse.quote_plus(self.DB_USER)
        password = urllib.parse.quote_plus(self.DB_PASSWORD)
        host_port = f"{self.DB_HOST}:{self.DB_PORT}"
        return f"postgresql+psycopg://{user}:{password}@{host_port}/{self.DB_NAME}"

    @property
    def log_to_file(self) -> bool:
        return bool(self.LOG_TO_FILE)


settings = Settings()
