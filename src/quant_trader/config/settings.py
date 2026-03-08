"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration values."""

    model_config = SettingsConfigDict(env_prefix="QT_DB_", env_file=".env", extra="ignore")

    url: str = Field(default="sqlite:///quant_trader.db", description="Database URL.")
    pool_size: PositiveInt = Field(default=5, description="Database pool size.")


class LoggingSettings(BaseSettings):
    """Logging configuration values."""

    model_config = SettingsConfigDict(env_prefix="QT_LOG_", env_file=".env", extra="ignore")

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(env_prefix="QT_", env_file=".env", extra="ignore")

    app_name: str = "QuantTrader"
    environment: Literal["dev", "test", "paper", "live"] = "dev"
    timezone: str = "UTC"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    """Return cached application settings for the current process."""

    return AppSettings()
