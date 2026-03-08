"""Minimal local compatibility shim for required pydantic-settings APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


SettingsConfigDict = dict[str, Any]


class BaseSettings(BaseModel):
    """Lightweight BaseSettings placeholder for local test environments."""

    model_config: SettingsConfigDict = {}
