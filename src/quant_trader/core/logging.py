"""Centralized logging configuration utilities."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from quant_trader.config.settings import LoggingSettings


class JsonFormatter(logging.Formatter):
    """Render log records as JSON for machine-readable observability."""

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record into a JSON string."""

        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: LoggingSettings) -> None:
    """Configure root logger once using application logging settings."""

    root_logger: logging.Logger = logging.getLogger()
    root_logger.setLevel(settings.level)

    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if settings.json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""

    return logging.getLogger(name)
