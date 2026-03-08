"""Strategy interface abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from quant_trader.models.common import MarketQuote, Signal


class StrategyInterface(ABC):
    """Base strategy contract for all strategies."""

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Return unique strategy identifier."""

    @abstractmethod
    def on_quote(self, quote: MarketQuote) -> list[Signal]:
        """Handle new quote and emit zero or more signals."""
