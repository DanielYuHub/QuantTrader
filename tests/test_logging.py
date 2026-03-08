"""Tests for centralized logging configuration."""

from __future__ import annotations

import logging

from quant_trader.config.settings import LoggingSettings
from quant_trader.core.logging import JsonFormatter, configure_logging



def test_json_formatter_outputs_json_fields() -> None:
    """JSON formatter should include standard keys."""

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )

    message = formatter.format(record)

    assert '"logger": "test"' in message
    assert '"message": "hello"' in message



def test_configure_logging_sets_root_level() -> None:
    """Configuring logging should set root level according to settings."""

    configure_logging(LoggingSettings(level="DEBUG", json_logs=False))
    assert logging.getLogger().level == logging.DEBUG
