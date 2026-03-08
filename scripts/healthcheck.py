"""Container health check script for docker healthcheck command."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_trader.config.settings import load_settings
from quant_trader.market_data.models import Market, Quote
from quant_trader.ops.health import HealthChecker


if __name__ == "__main__":
    settings = load_settings()
    checker = HealthChecker(settings)

    # Minimal local probe inputs; production would wire real dependencies.
    quote = Quote(
        symbol="HEALTH",
        market=Market.US,
        timestamp=datetime.now(timezone.utc),
        bid=1.0,
        ask=1.0,
        last=1.0,
    )
    status = checker.check(db_ok=True, broker_ok=True, latest_quote=quote)

    if not status.ok:
        raise SystemExit(1)
