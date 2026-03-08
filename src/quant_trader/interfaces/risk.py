"""Risk manager interface abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from quant_trader.models.common import MarketQuote, OrderRequest, Position, RiskDecision


class RiskManagerInterface(ABC):
    """Risk checks used before and after order placement."""

    @abstractmethod
    def evaluate_order(
        self,
        order_request: OrderRequest,
        positions: list[Position],
        latest_quote: MarketQuote | None,
        now: datetime,
    ) -> RiskDecision:
        """Evaluate whether an order is allowed under current risk limits."""

    @abstractmethod
    def max_loss_breached(self, realized_pnl: float, unrealized_pnl: float) -> bool:
        """Return whether max loss thresholds are breached."""

    @abstractmethod
    def trigger_kill_switch(self, reason: str) -> None:
        """Enable emergency kill switch."""

    @abstractmethod
    def kill_switch_active(self) -> bool:
        """Return kill switch state."""
