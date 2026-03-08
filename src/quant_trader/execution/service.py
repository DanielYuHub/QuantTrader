"""Execution service that delegates order actions to broker adapters."""

from __future__ import annotations

from quant_trader.interfaces.broker import BrokerInterface
from quant_trader.models.common import Order, OrderRequest, TradeFill


class ExecutionService:
    """Thin execution layer responsible for broker interaction."""

    def __init__(self, broker: BrokerInterface) -> None:
        """Create execution service with broker dependency."""

        self._broker = broker

    def submit(self, order_request: OrderRequest) -> Order:
        """Submit order to broker."""

        return self._broker.submit_order(order_request)

    def replace(self, order_id: str, order_request: OrderRequest) -> Order:
        """Replace broker order."""

        return self._broker.replace_order(order_id, order_request)

    def cancel(self, order_id: str) -> Order:
        """Cancel broker order."""

        return self._broker.cancel_order(order_id)

    def poll_fills(self) -> list[TradeFill]:
        """Poll fills from broker."""

        return self._broker.poll_fills()

    def get_order(self, order_id: str) -> Order | None:
        """Return current broker-side order state."""

        return self._broker.get_order(order_id)
