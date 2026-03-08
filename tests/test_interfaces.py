"""Tests for interface-level contracts with concrete in-test implementations."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_trader.interfaces.portfolio import PortfolioInterface
from quant_trader.interfaces.risk import RiskManagerInterface
from quant_trader.models.common import MarketQuote, OrderRequest, OrderType, Position, RiskDecision, Side, Signal


class SimpleRiskManager(RiskManagerInterface):
    """Simple risk manager used to verify interface behavior."""

    def __init__(self) -> None:
        self._kill_switch = False

    def evaluate_order(
        self,
        order_request: OrderRequest,
        positions: list[Position],
        latest_quote: MarketQuote | None,
        now: datetime,
    ) -> RiskDecision:
        _ = now
        if self._kill_switch:
            return RiskDecision(allowed=False, reason="kill switch active")
        if latest_quote is None:
            return RiskDecision(allowed=False, reason="missing quote")
        position_qty = next((p.quantity for p in positions if p.instrument_id == order_request.instrument_id), 0)
        if position_qty + int(order_request.quantity) > 100:
            return RiskDecision(allowed=False, reason="position limit exceeded")
        return RiskDecision(allowed=True)

    def max_loss_breached(self, realized_pnl: float, unrealized_pnl: float) -> bool:
        return (realized_pnl + unrealized_pnl) < -1000.0

    def trigger_kill_switch(self, reason: str) -> None:
        _ = reason
        self._kill_switch = True

    def kill_switch_active(self) -> bool:
        return self._kill_switch


class SimplePortfolio(PortfolioInterface):
    """Simple portfolio implementation for contract tests."""

    def build_orders(self, signals: list[Signal], positions: list[Position]) -> list[OrderRequest]:
        _ = positions
        return [
            OrderRequest(
                idempotency_key=f"{signal.strategy_id}-{signal.instrument_id}",
                instrument_id=signal.instrument_id,
                side=signal.direction,
                quantity=1,
                order_type=OrderType.MARKET,
            )
            for signal in signals
        ]

    def mark_to_market(self, positions: list[Position]) -> float:
        return float(sum(position.quantity * position.average_price for position in positions))



def test_risk_manager_rejects_large_position() -> None:
    """Risk manager should reject orders breaching limit."""

    manager = SimpleRiskManager()
    order = OrderRequest(
        idempotency_key="k1",
        instrument_id="AAPL",
        side=Side.BUY,
        quantity=20,
        order_type=OrderType.MARKET,
    )
    quote = MarketQuote(
        instrument_id="AAPL",
        timestamp=datetime.now(timezone.utc),
        bid=99.0,
        ask=100.0,
        last=99.5,
    )
    decision = manager.evaluate_order(
        order,
        [Position(instrument_id="AAPL", quantity=90, average_price=100.0)],
        latest_quote=quote,
        now=datetime.now(timezone.utc),
    )

    assert not decision.allowed
    assert decision.reason is not None



def test_portfolio_builds_order_from_signal() -> None:
    """Portfolio should convert incoming signals into order requests."""

    portfolio = SimplePortfolio()
    signals = [
        Signal(
            strategy_id="s1",
            instrument_id="AAPL",
            timestamp=datetime.now(timezone.utc),
            direction=Side.BUY,
            confidence=0.9,
        )
    ]

    orders = portfolio.build_orders(signals, [])

    assert len(orders) == 1
    assert orders[0].instrument_id == "AAPL"
    assert orders[0].idempotency_key == "s1-AAPL"
