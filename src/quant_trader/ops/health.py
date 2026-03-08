"""Operational health checks for readiness/liveness style probes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from quant_trader.config.settings import AppSettings
from quant_trader.core.logging import get_logger
from quant_trader.market_data.models import Quote


@dataclass
class HealthStatus:
    """Health status result with component details."""

    ok: bool
    details: dict[str, str]


class HealthChecker:
    """Checks key dependencies for deployment readiness."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._logger = get_logger(__name__)

    def check(self, db_ok: bool, broker_ok: bool, latest_quote: Quote | None, stale_threshold_seconds: int = 30) -> HealthStatus:
        """Evaluate critical subsystem health and return status summary."""

        details: dict[str, str] = {
            "database": "ok" if db_ok else "down",
            "broker": "ok" if broker_ok else "down",
            "environment": self._settings.environment,
        }

        market_data_ok = True
        if latest_quote is None:
            market_data_ok = False
            details["market_data"] = "missing"
        else:
            ts = latest_quote.timestamp if latest_quote.timestamp.tzinfo else latest_quote.timestamp.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > stale_threshold_seconds:
                market_data_ok = False
                details["market_data"] = f"stale:{age:.1f}s"
            else:
                details["market_data"] = f"fresh:{age:.1f}s"

        overall = db_ok and broker_ok and market_data_ok
        if not overall:
            self._logger.warning("Health check degraded: %s", details)
        return HealthStatus(ok=overall, details=details)
