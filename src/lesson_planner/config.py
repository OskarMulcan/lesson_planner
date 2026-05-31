from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from dotenv import load_dotenv
import logging
import urllib.parse

load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from the environment and .env file.

    Args:
        None

    Returns:
        Settings instance available at module level as `settings`.
    """

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: int = 0
    LOG_FILE_PATH: Optional[str] = None

    ENVIRONMENT: str = "development"

    @field_validator("LOG_LEVEL")
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if isinstance(v, str) and v.upper() in allowed:
            return v.upper()
        raise ValueError("LOG_LEVEL must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL")

    @field_validator("ENVIRONMENT")
    def _validate_environment(cls, v: str) -> str:
        if v not in ("development", "production"):
            raise ValueError('ENVIRONMENT must be "development" or "production"')
        return v

    @model_validator(mode="after")
    def _check_log_file(self):
        if int(self.LOG_TO_FILE) == 1 and not self.LOG_FILE_PATH:
            raise ValueError("LOG_FILE_PATH is required when LOG_TO_FILE is 1")
        return self

    @property
    def database_url(self) -> str:
        user = urllib.parse.quote_plus(self.DB_USER)
        password = urllib.parse.quote_plus(self.DB_PASSWORD)
        host_port = f"{self.DB_HOST}:{self.DB_PORT}"
        return f"postgresql+psycopg://{user}:{password}@{host_port}/{self.DB_NAME}"

    @property
    def log_to_file(self) -> bool:
        return bool(int(self.LOG_TO_FILE))


settings = Settings()
