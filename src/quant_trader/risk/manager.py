"""Concrete risk manager with pre-trade and safety guard checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from quant_trader.interfaces.risk import RiskManagerInterface
from quant_trader.models.common import MarketQuote, OrderRequest, Position, RiskDecision, Side


@dataclass(frozen=True)
class RiskLimits:
    """Risk constraints for order and portfolio safety."""

    max_position_size: int = 1_000
    max_order_notional: float = 100_000.0
    daily_loss_limit: float = 5_000.0
    max_orders_per_minute: int = 60
    max_stale_quote_seconds: int = 5


class RiskManager(RiskManagerInterface):
    """Stateful risk manager implementing required safety guards."""

    def __init__(self, limits: RiskLimits) -> None:
        """Initialize risk manager with configured limits."""

        self._limits = limits
        self._kill_switch: bool = False
        self._order_window_minute: tuple[int, int, int, int, int] | None = None
        self._orders_in_window = 0
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

    def evaluate_order(
        self,
        order_request: OrderRequest,
        positions: list[Position],
        latest_quote: MarketQuote | None,
        now: datetime,
    ) -> RiskDecision:
        """Run pre-trade checks and return decision."""

        if self._kill_switch:
            return RiskDecision(allowed=False, reason="kill switch active")

        self._roll_minute_window(now)
        if self._orders_in_window >= self._limits.max_orders_per_minute:
            return RiskDecision(allowed=False, reason="order rate limit exceeded")

        if self.max_loss_breached(self._realized_pnl, self._unrealized_pnl):
            return RiskDecision(allowed=False, reason="daily loss guard breached")

        if latest_quote is None:
            return RiskDecision(allowed=False, reason="missing quote")

        if latest_quote.is_stale(self._limits.max_stale_quote_seconds, now):
            return RiskDecision(allowed=False, reason="stale quote")

        reference_price = latest_quote.last or (latest_quote.bid + latest_quote.ask) / 2
        notional = float(order_request.quantity) * reference_price
        if notional > self._limits.max_order_notional:
            return RiskDecision(allowed=False, reason="max order notional exceeded")

        current_qty = next((p.quantity for p in positions if p.instrument_id == order_request.instrument_id), 0)
        proposed_qty = current_qty + int(order_request.quantity if order_request.side is Side.BUY else -order_request.quantity)
        if abs(proposed_qty) > self._limits.max_position_size:
            return RiskDecision(allowed=False, reason="max position size exceeded")

        self._orders_in_window += 1
        return RiskDecision(allowed=True)

    def max_loss_breached(self, realized_pnl: float, unrealized_pnl: float) -> bool:
        """Return whether total PnL is below configured daily loss guard."""

        total = realized_pnl + unrealized_pnl
        return total <= -abs(self._limits.daily_loss_limit)

    def update_daily_pnl(self, realized_pnl: float, unrealized_pnl: float) -> None:
        """Update risk manager PnL view for daily loss checks."""

        self._realized_pnl = realized_pnl
        self._unrealized_pnl = unrealized_pnl

    def trigger_kill_switch(self, reason: str) -> None:
        """Activate emergency stop state."""

        _ = reason
        self._kill_switch = True

    def kill_switch_active(self) -> bool:
        """Return current kill switch state."""

        return self._kill_switch

    def _roll_minute_window(self, now: datetime) -> None:
        """Reset per-minute order counter when minute window changes."""

        key = (now.year, now.month, now.day, now.hour, now.minute)
        if key != self._order_window_minute:
            self._order_window_minute = key
            self._orders_in_window = 0
