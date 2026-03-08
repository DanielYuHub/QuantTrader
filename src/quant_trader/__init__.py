"""QuantTrader package root for Phase 1 architecture foundation.

This module intentionally avoids importing optional runtime dependencies at
module import time. Consumers that need application settings should call
``load_settings`` (or use ``AppSettings`` for typing) explicitly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quant_trader.config.settings import AppSettings as AppSettings


def load_settings() -> "AppSettings":
    """Load and return application settings lazily."""

    from quant_trader.config.settings import load_settings as _load_settings

    return _load_settings()


def __getattr__(name: str) -> Any:
    """Provide lazy access to public package attributes."""

    if name == "AppSettings":
        from quant_trader.config.settings import AppSettings as settings_type

        return settings_type
    msg = f"module 'quant_trader' has no attribute '{name}'"
    raise AttributeError(msg)


__all__ = ["AppSettings", "load_settings"]
