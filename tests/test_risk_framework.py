"""Tests for production-focused risk framework controls."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quant_trader.models.common import AssetClass, MarketQuote, OrderRequest, OrderType, Side
from quant_trader.risk.framework import (
    InstrumentRiskInfo,
    OptionGreekExposure,
    ProductionRiskEngine,
    ProductionRiskLimits,
    RiskSnapshot,
)



def _quote(ts: datetime | None = None, price: float = 100.0) -> MarketQuote:
    t = ts or datetime.now(timezone.utc)
    return MarketQuote(instrument_id="AAPL", timestamp=t, bid=price - 0.1, ask=price + 0.1, last=price)



def _snapshot(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(
        timestamp=now,
        positions={"AAPL": 0},
        quotes={"AAPL": _quote(now)},
        instruments={
            "AAPL": InstrumentRiskInfo(
                instrument_id="AAPL",
                asset_class=AssetClass.EQUITY,
                sector="TECH",
                group="US_EQ",
            )
        },
        exposure_by_sector={"TECH": 0.0},
        exposure_by_group={"US_EQ": 0.0},
        gross_exposure=0.0,
        net_exposure=0.0,
        realized_pnl_today=0.0,
        unrealized_pnl=0.0,
        strategy_drawdown={"strat": 0.0},
        option_greeks=OptionGreekExposure(delta=0.0, gamma=0.0, vega=0.0),
        broker_connected=True,
    )



def _order(key: str = "strat:1", qty: int = 10, asset: AssetClass = AssetClass.EQUITY) -> OrderRequest:
    return OrderRequest(
        idempotency_key=key,
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=qty,
        order_type=OrderType.MARKET,
        asset_class=asset,
    )



def test_blocks_position_limit_breach() -> None:
    """Risk engine should block orders that exceed instrument position limits."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits(max_position_per_instrument=5))
    snapshot = _snapshot(now)

    decision = engine.evaluate_order(_order(qty=10), snapshot, now)

    assert not decision.allowed
    assert decision.reason is not None and "position limit" in decision.reason



def test_blocks_stale_market_data() -> None:
    """Risk engine should reject trading on stale quotes."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits(max_stale_quote_seconds=1))
    snapshot = _snapshot(now)
    snapshot.quotes["AAPL"] = _quote(now - timedelta(seconds=10))

    decision = engine.evaluate_order(_order(), snapshot, now)

    assert not decision.allowed
    assert decision.reason is not None and "stale market data" in decision.reason



def test_blocks_broker_connectivity_failure() -> None:
    """Risk engine should block all orders when broker health is down."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits())
    snapshot = _snapshot(now)
    snapshot.broker_connected = False

    decision = engine.evaluate_order(_order(), snapshot, now)

    assert not decision.allowed
    assert decision.reason is not None and "broker connectivity" in decision.reason



def test_emergency_stop_workflow_blocks_then_clears() -> None:
    """Emergency stop should block trading until cleared."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits())
    snapshot = _snapshot(now)

    engine.trigger_emergency_stop("ops drill")
    blocked = engine.evaluate_order(_order("strat:es1"), snapshot, now)
    engine.clear_emergency_stop()
    allowed = engine.evaluate_order(_order("strat:es2"), snapshot, now)

    assert not blocked.allowed
    assert allowed.allowed



def test_blocks_option_greek_and_expiration_risk() -> None:
    """Option checks should block when greek or expiry thresholds are violated."""

    now = datetime.now(timezone.utc)
    limits = ProductionRiskLimits(max_option_delta=10, min_days_to_option_expiry=3)
    engine = ProductionRiskEngine(limits)
    snapshot = _snapshot(now)
    snapshot.instruments["AAPL"] = InstrumentRiskInfo(
        instrument_id="AAPL",
        asset_class=AssetClass.OPTION,
        sector="TECH",
        group="US_OPT",
        expiry=now + timedelta(days=1),
    )
    snapshot.option_greeks = OptionGreekExposure(delta=50, gamma=0, vega=0)

    decision = engine.evaluate_order(_order(key="strat:opt", asset=AssetClass.OPTION), snapshot, now)

    assert not decision.allowed
    assert decision.reason is not None
    assert "option delta exposure" in decision.reason
    assert "option expiration risk" in decision.reason



def test_duplicate_and_rate_limit_guards() -> None:
    """Engine should block duplicate idempotency key and per-minute order-rate breaches."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits(max_orders_per_minute=1))
    snapshot = _snapshot(now)

    first = engine.evaluate_order(_order(key="strat:dup"), snapshot, now)
    duplicate = engine.evaluate_order(_order(key="strat:dup"), snapshot, now)
    second_key = engine.evaluate_order(_order(key="strat:next"), snapshot, now)

    assert first.allowed
    assert not duplicate.allowed
    assert duplicate.reason is not None and "duplicate order" in duplicate.reason
    assert not second_key.allowed
    assert second_key.reason is not None and "max order rate" in second_key.reason



def test_audit_logging_records_allow_and_block_events() -> None:
    """Audit records should contain both approved and blocked decisions."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits(max_position_per_instrument=1))
    snapshot = _snapshot(now)

    engine.evaluate_order(_order(key="strat:a1", qty=1), snapshot, now)
    engine.evaluate_order(_order(key="strat:a2", qty=2), snapshot, now)

    audit = engine.audit_log()

    assert len(audit) == 2
    assert audit[0]["allowed"] is True
    assert audit[1]["allowed"] is False


def test_blocks_group_exposure_breach() -> None:
    """Risk engine should block orders that breach group exposure limits."""

    now = datetime.now(timezone.utc)
    engine = ProductionRiskEngine(ProductionRiskLimits(max_group_exposure=500.0))
    snapshot = _snapshot(now)
    snapshot.exposure_by_group["US_EQ"] = 450.0

    decision = engine.evaluate_order(_order(qty=1), snapshot, now)

    assert not decision.allowed
    assert decision.reason is not None and "group exposure" in decision.reason
