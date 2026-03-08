"""Order manager interface abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from quant_trader.models.common import MarketQuote, Order, OrderRequest, TradeFill


class OrderManagerInterface(ABC):
    """Order management system contract."""

    @abstractmethod
    def create_order(self, order_request: OrderRequest, latest_quote: MarketQuote | None = None) -> Order:
        """Create and route an order through execution path."""

    @abstractmethod
    def replace_order(
        self, order_id: str, order_request: OrderRequest, latest_quote: MarketQuote | None = None
    ) -> Order:
        """Replace an existing order with a modified request."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order."""

    @abstractmethod
    def process_fill(self, fill: TradeFill) -> Order:
        """Apply fill to order state and return updated order."""

    @abstractmethod
    def get_order(self, order_id: str) -> Order | None:
        """Fetch order by identifier."""
