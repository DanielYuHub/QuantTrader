"""Tests for deployment/ops health and scheduler components."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quant_trader.config.settings import AppSettings
from quant_trader.market_data.models import Market, Quote
from quant_trader.ops.health import HealthChecker
from quant_trader.ops.scheduler import TaskScheduler



def test_health_checker_detects_stale_quote() -> None:
    """Health checker should mark status unhealthy when market data is stale."""

    checker = HealthChecker(AppSettings())
    stale_quote = Quote(
        symbol="AAPL",
        market=Market.US,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=100),
        bid=100.0,
        ask=100.1,
        last=100.05,
    )

    status = checker.check(db_ok=True, broker_ok=True, latest_quote=stale_quote, stale_threshold_seconds=5)

    assert not status.ok
    assert "stale" in status.details["market_data"]



def test_task_scheduler_executes_registered_tasks() -> None:
    """Scheduler should execute due tasks on tick."""

    scheduler = TaskScheduler()
    calls = {"count": 0}

    def _task() -> None:
        calls["count"] += 1

    scheduler.register("sample", interval_seconds=10, func=_task)

    executed = scheduler.tick(datetime.now(timezone.utc))

    assert "sample" in executed
    assert calls["count"] == 1


def test_task_scheduler_rejects_non_positive_interval() -> None:
    """Scheduler should reject invalid non-positive intervals."""

    scheduler = TaskScheduler()

    with pytest.raises(ValueError, match="greater than 0"):
        scheduler.register("bad", interval_seconds=0, func=lambda: None)
