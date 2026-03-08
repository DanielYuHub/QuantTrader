"""Broker interface abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from quant_trader.models.common import Order, OrderRequest, Position, TradeFill


class BrokerInterface(ABC):
    """Abstract broker gateway used by execution and OMS layers."""

    @abstractmethod
    def submit_order(self, order_request: OrderRequest) -> Order:
        """Submit an order to the broker and return current order state."""

    @abstractmethod
    def replace_order(self, order_id: str, order_request: OrderRequest) -> Order:
        """Cancel/replace an order and return updated order state."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order and return updated order state."""

    @abstractmethod
    def get_order(self, order_id: str) -> Order | None:
        """Return one broker-side order by identifier."""

    @abstractmethod
    def poll_fills(self) -> list[TradeFill]:
        """Return newly available fills since last poll."""

    @abstractmethod
    def list_positions(self) -> list[Position]:
        """Return current broker-side positions."""
