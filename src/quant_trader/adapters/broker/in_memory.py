"""In-memory broker adapter for deterministic OMS/execution tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from quant_trader.interfaces.broker import BrokerInterface
from quant_trader.models.common import Order, OrderRequest, OrderStatus, Position, TradeFill


class InMemoryBroker(BrokerInterface):
    """Simple in-memory broker implementing order submit/cancel/replace/fill polling."""

    def __init__(self) -> None:
        """Initialize empty broker state."""

        self._orders: dict[str, Order] = {}
        self._fills: list[TradeFill] = []
        self._positions: dict[str, Position] = {}

    def submit_order(self, order_request: OrderRequest) -> Order:
        """Submit order and acknowledge immediately."""

        order_id = f"ord-{uuid4().hex[:12]}"
        order = Order(order_id=order_id, request=order_request, status=OrderStatus.ACKNOWLEDGED)
        self._orders[order_id] = order
        return order

    def replace_order(self, order_id: str, order_request: OrderRequest) -> Order:
        """Replace order request for an existing order."""

        existing = self._orders[order_id]
        replaced = existing.model_copy(update={"request": order_request, "status": OrderStatus.REPLACED})
        self._orders[order_id] = replaced
        return replaced

    def cancel_order(self, order_id: str) -> Order:
        """Cancel existing order."""

        existing = self._orders[order_id]
        canceled = existing.model_copy(update={"status": OrderStatus.CANCELED})
        self._orders[order_id] = canceled
        return canceled

    def get_order(self, order_id: str) -> Order | None:
        """Return broker order by id."""

        return self._orders.get(order_id)

    def poll_fills(self) -> list[TradeFill]:
        """Return and clear available fill events."""

        fills = list(self._fills)
        self._fills.clear()
        return fills

    def list_positions(self) -> list[Position]:
        """Return broker-maintained position snapshot."""

        return list(self._positions.values())

    def add_fill(self, order_id: str, quantity: int, price: float) -> TradeFill:
        """Inject fill for tests and local workflows."""

        fill = TradeFill(
            fill_id=f"fill-{uuid4().hex[:12]}",
            order_id=order_id,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(timezone.utc),
        )
        self._fills.append(fill)
        return fill
