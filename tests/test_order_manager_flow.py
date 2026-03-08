"""Tests for order manager, execution service, fills, and portfolio updates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from quant_trader.adapters.broker.in_memory import InMemoryBroker
from quant_trader.execution.service import ExecutionService
from quant_trader.models.common import (
    AssetClass,
    MarketQuote,
    OrderRequest,
    OrderStatus,
    OrderType,
    Side,
)
from quant_trader.oms.order_manager import DuplicateEventError, OrderManager
from quant_trader.portfolio.updater import PortfolioPositionUpdater
from quant_trader.risk.manager import RiskLimits, RiskManager



def _quote(fresh: bool = True) -> MarketQuote:
    ts = datetime.now(timezone.utc)
    if not fresh:
        ts = ts - timedelta(seconds=30)
    return MarketQuote(instrument_id="AAPL", timestamp=ts, bid=100.0, ask=100.2, last=100.1)



def _build_manager() -> tuple[OrderManager, InMemoryBroker, PortfolioPositionUpdater]:
    broker = InMemoryBroker()
    execution = ExecutionService(broker)
    risk = RiskManager(
        RiskLimits(
            max_position_size=500,
            max_order_notional=100_000,
            daily_loss_limit=10_000,
            max_orders_per_minute=50,
            max_stale_quote_seconds=5,
        )
    )
    updater = PortfolioPositionUpdater()
    manager = OrderManager(execution_service=execution, risk_manager=risk, position_updater=updater)
    return manager, broker, updater



def test_signal_to_order_to_partial_fill_to_position_update() -> None:
    """OMS should process fills and update position quantity/average cost."""

    manager, broker, updater = _build_manager()
    request = OrderRequest(
        idempotency_key="sig-1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
        asset_class=AssetClass.EQUITY,
    )

    order = manager.create_order(request, latest_quote=_quote(fresh=True))
    assert order.status == OrderStatus.ACKNOWLEDGED

    fill1 = broker.add_fill(order.order_id, quantity=4, price=100.0)
    fill2 = broker.add_fill(order.order_id, quantity=6, price=101.0)

    update1 = manager.process_fill(fill1)
    update2 = manager.process_fill(fill2)

    assert update1.status == OrderStatus.PARTIALLY_FILLED
    assert update2.status == OrderStatus.FILLED
    position = updater.get_position("AAPL")
    assert position.quantity == 10
    assert position.average_price == pytest.approx(100.6)



def test_duplicate_order_prevention_by_idempotency_key() -> None:
    """Duplicate idempotency keys should be blocked before broker submission."""

    manager, _, _ = _build_manager()
    request = OrderRequest(
        idempotency_key="dup-1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
    )

    manager.create_order(request, latest_quote=_quote())
    with pytest.raises(DuplicateEventError):
        manager.create_order(request, latest_quote=_quote())



def test_duplicate_fill_event_rejected() -> None:
    """Duplicate fill events should be rejected for idempotent processing."""

    manager, broker, _ = _build_manager()
    request = OrderRequest(
        idempotency_key="fill-dup",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=2,
        order_type=OrderType.MARKET,
    )

    order = manager.create_order(request, latest_quote=_quote())
    fill = broker.add_fill(order.order_id, quantity=1, price=100.0)

    manager.process_fill(fill)
    with pytest.raises(DuplicateEventError):
        manager.process_fill(fill)



def test_rejected_order_from_stale_quote_protection() -> None:
    """Stale quote should cause pre-trade rejection and REJECTED order status."""

    manager, _, _ = _build_manager()
    request = OrderRequest(
        idempotency_key="stale-reject",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
    )

    order = manager.create_order(request, latest_quote=_quote(fresh=False))
    assert order.status == OrderStatus.REJECTED
    assert order.reject_reason == "stale quote"



def test_cancel_replace_flow_for_limit_to_stop_order() -> None:
    """OMS should support replace and cancel transitions."""

    manager, _, _ = _build_manager()
    initial = OrderRequest(
        idempotency_key="rep-1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=5,
        order_type=OrderType.LIMIT,
        limit_price=99.5,
    )
    replacement = OrderRequest(
        idempotency_key="rep-2",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=5,
        order_type=OrderType.STOP,
        stop_price=101.0,
    )

    created = manager.create_order(initial, latest_quote=_quote())
    replaced = manager.replace_order(created.order_id, replacement)
    canceled = manager.cancel_order(created.order_id)

    assert replaced.status == OrderStatus.REPLACED
    assert replaced.request.order_type == OrderType.STOP
    assert canceled.status == OrderStatus.CANCELED



def test_option_order_supported_and_updates_position() -> None:
    """Option orders should use same OMS lifecycle and update position book."""

    manager, broker, updater = _build_manager()
    request = OrderRequest(
        idempotency_key="opt-1",
        instrument_id="AAPL250117C00100000",
        side=Side.BUY,
        quantity=1,
        order_type=OrderType.LIMIT,
        limit_price=2.5,
        asset_class=AssetClass.OPTION,
    )

    order = manager.create_order(request, latest_quote=MarketQuote(
        instrument_id=request.instrument_id,
        timestamp=datetime.now(timezone.utc),
        bid=2.4,
        ask=2.6,
        last=2.5,
    ))
    fill = broker.add_fill(order.order_id, quantity=1, price=2.5)
    manager.process_fill(fill)

    option_position = updater.get_position(request.instrument_id)
    assert option_position.quantity == 1
    assert option_position.average_price == pytest.approx(2.5)


def test_replace_order_rejects_duplicate_idempotency_key() -> None:
    """Replace should reject idempotency keys already used by prior orders."""

    manager, _, _ = _build_manager()
    initial = OrderRequest(
        idempotency_key="rep-d1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=5,
        order_type=OrderType.LIMIT,
        limit_price=99.5,
    )
    replacement = OrderRequest(
        idempotency_key="rep-d1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=5,
        order_type=OrderType.STOP,
        stop_price=101.0,
    )

    created = manager.create_order(initial, latest_quote=_quote())

    with pytest.raises(DuplicateEventError):
        manager.replace_order(created.order_id, replacement)


def test_overfill_is_rejected() -> None:
    """OMS should reject fills that exceed requested quantity."""

    manager, broker, _ = _build_manager()
    request = OrderRequest(
        idempotency_key="ovf-1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
    )

    order = manager.create_order(request, latest_quote=_quote())
    fill = broker.add_fill(order.order_id, quantity=6, price=100.0)

    with pytest.raises(ValueError, match="Overfill"):
        manager.process_fill(fill)
