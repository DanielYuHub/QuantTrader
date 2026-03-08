"""Tests for concrete risk manager guards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quant_trader.models.common import MarketQuote, OrderRequest, OrderType, Position, Side
from quant_trader.risk.manager import RiskLimits, RiskManager



def _quote(age_seconds: int = 0, last: float = 100.0) -> MarketQuote:
    now = datetime.now(timezone.utc)
    return MarketQuote(
        instrument_id="AAPL",
        timestamp=now - timedelta(seconds=age_seconds),
        bid=last - 0.1,
        ask=last + 0.1,
        last=last,
    )



def _market_order(quantity: int, key: str = "k") -> OrderRequest:
    return OrderRequest(
        idempotency_key=key,
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=quantity,
        order_type=OrderType.MARKET,
    )



def test_stale_quote_rejected() -> None:
    """Risk manager should reject orders when quote age exceeds threshold."""

    manager = RiskManager(RiskLimits(max_stale_quote_seconds=1))
    decision = manager.evaluate_order(
        _market_order(1),
        positions=[],
        latest_quote=_quote(age_seconds=5),
        now=datetime.now(timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "stale quote"



def test_max_notional_guard_rejects() -> None:
    """Risk manager should block orders beyond notional limits."""

    manager = RiskManager(RiskLimits(max_order_notional=1_000.0))
    decision = manager.evaluate_order(
        _market_order(20),
        positions=[],
        latest_quote=_quote(last=100.0),
        now=datetime.now(timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "max order notional exceeded"



def test_kill_switch_blocks_all_orders() -> None:
    """Emergency kill switch should prevent all new order approvals."""

    manager = RiskManager(RiskLimits())
    manager.trigger_kill_switch("manual emergency")
    decision = manager.evaluate_order(
        _market_order(1),
        positions=[],
        latest_quote=_quote(),
        now=datetime.now(timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "kill switch active"



def test_daily_loss_guard_blocks() -> None:
    """Daily loss guard should reject orders after configured drawdown."""

    manager = RiskManager(RiskLimits(daily_loss_limit=500.0))
    manager.update_daily_pnl(realized_pnl=-600.0, unrealized_pnl=0.0)

    decision = manager.evaluate_order(
        _market_order(1),
        positions=[],
        latest_quote=_quote(),
        now=datetime.now(timezone.utc),
    )

    assert not decision.allowed
    assert decision.reason == "daily loss guard breached"



def test_rate_limit_guard_blocks_excess_orders() -> None:
    """Risk manager should enforce per-minute order rate limits."""

    manager = RiskManager(RiskLimits(max_orders_per_minute=1))
    now = datetime.now(timezone.utc)

    first = manager.evaluate_order(_market_order(1, key="k1"), [], _quote(), now)
    second = manager.evaluate_order(_market_order(1, key="k2"), [], _quote(), now)

    assert first.allowed
    assert not second.allowed
    assert second.reason == "order rate limit exceeded"



def test_position_limit_guard_blocks_excess_position() -> None:
    """Risk manager should block orders that exceed max position size."""

    manager = RiskManager(RiskLimits(max_position_size=100))
    decision = manager.evaluate_order(
        _market_order(20),
        positions=[Position(instrument_id="AAPL", quantity=90, average_price=100.0)],
        latest_quote=_quote(),
        now=datetime.now(timezone.utc),
    )

    assert not decision.allowed
    assert decision.reason == "max position size exceeded"
