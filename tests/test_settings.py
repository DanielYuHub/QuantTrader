"""Tests for configuration loading."""

from __future__ import annotations

import pytest

from quant_trader.config.settings import load_settings


def test_load_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should read environment variables via pydantic settings."""

    monkeypatch.setenv("QT_APP_NAME", "QT-Test")
    monkeypatch.setenv("QT_ENVIRONMENT", "paper")
    monkeypatch.setenv("QT_DB_URL", "sqlite:///tmp/test.db")
    load_settings.cache_clear()

    settings = load_settings()

    assert settings.app_name == "QT-Test"
    assert settings.environment == "paper"
    assert settings.database.url == "sqlite:///tmp/test.db"
