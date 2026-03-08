"""Alerting integration points for operations incidents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quant_trader.core.logging import get_logger


class AlertSink(Protocol):
    """Alert sink protocol for pluggable integrations (webhook/pager/email)."""

    def send(self, title: str, message: str, severity: str) -> None:
        """Send alert payload to destination."""


@dataclass
class LoggingAlertSink:
    """Default alert sink that emits to structured logs."""

    def send(self, title: str, message: str, severity: str) -> None:
        logger = get_logger(__name__)
        logger.warning("ALERT severity=%s title=%s message=%s", severity, title, message)
