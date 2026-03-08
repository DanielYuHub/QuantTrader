"""Portfolio interface abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from quant_trader.models.common import OrderRequest, Position, Signal


class PortfolioInterface(ABC):
    """Portfolio contract to convert signals into target orders."""

    @abstractmethod
    def build_orders(self, signals: list[Signal], positions: list[Position]) -> list[OrderRequest]:
        """Create order requests from incoming signals and current positions."""

    @abstractmethod
    def mark_to_market(self, positions: list[Position]) -> float:
        """Return portfolio market value estimate."""
