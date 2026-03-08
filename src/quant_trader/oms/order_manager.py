"""Order manager implementation with risk checks and duplicate protections."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_trader.execution.service import ExecutionService
from quant_trader.interfaces.order_manager import OrderManagerInterface
from quant_trader.interfaces.risk import RiskManagerInterface
from quant_trader.models.common import MarketQuote, Order, OrderRequest, OrderStatus, Position, TradeFill
from quant_trader.oms.state_machine import validate_transition
from quant_trader.portfolio.updater import PortfolioPositionUpdater


class DuplicateEventError(ValueError):
    """Raised when duplicate idempotency keys or fill events are observed."""


class OrderManager(OrderManagerInterface):
    """Stateful OMS implementation for order lifecycle and fill processing."""

    def __init__(
        self,
        execution_service: ExecutionService,
        risk_manager: RiskManagerInterface,
        position_updater: PortfolioPositionUpdater,
    ) -> None:
        """Initialize order manager dependencies."""

        self._execution_service = execution_service
        self._risk_manager = risk_manager
        self._position_updater = position_updater
        self._orders: dict[str, Order] = {}
        self._order_keys: set[str] = set()
        self._fill_ids_seen: set[str] = set()

    def create_order(self, order_request: OrderRequest, latest_quote: MarketQuote | None = None) -> Order:
        """Create and route a new order after pre-trade risk checks."""

        if order_request.idempotency_key in self._order_keys:
            msg = f"Duplicate order idempotency key: {order_request.idempotency_key}"
            raise DuplicateEventError(msg)

        now = datetime.now(timezone.utc)
        positions = self._position_updater.positions()
        decision = self._risk_manager.evaluate_order(order_request, positions, latest_quote, now)

        if not decision.allowed:
            rejected = Order(
                order_id=f"rejected-{order_request.idempotency_key}",
                request=order_request,
                status=OrderStatus.REJECTED,
                reject_reason=decision.reason,
            )
            self._orders[rejected.order_id] = rejected
            self._order_keys.add(order_request.idempotency_key)
            return rejected

        broker_order = self._execution_service.submit(order_request)
        self._orders[broker_order.order_id] = broker_order
        self._order_keys.add(order_request.idempotency_key)
        return broker_order

    def replace_order(self, order_id: str, order_request: OrderRequest, latest_quote: MarketQuote | None = None) -> Order:
        """Replace an existing order via broker and validate transition."""

        if order_request.idempotency_key in self._order_keys:
            msg = f"Duplicate order idempotency key: {order_request.idempotency_key}"
            raise DuplicateEventError(msg)

        existing = self._require_order(order_id)
        validate_transition(existing.status, OrderStatus.REPLACED)
        now = datetime.now(timezone.utc)
        positions = self._position_updater.positions()
        decision = self._risk_manager.evaluate_order(order_request, positions, latest_quote, now)

        if not decision.allowed:
            rejected = Order(
                order_id=f"rejected-{order_request.idempotency_key}",
                request=order_request,
                status=OrderStatus.REJECTED,
                reject_reason=decision.reason,
            )
            self._orders[rejected.order_id] = rejected
            self._order_keys.add(order_request.idempotency_key)
            return rejected

        replaced = self._execution_service.replace(order_id, order_request)
        updated = replaced.model_copy(update={"status": OrderStatus.REPLACED, "request": order_request})
        if replaced.order_id != order_id:
            del self._orders[order_id]
        self._orders[replaced.order_id] = updated
        self._order_keys.add(order_request.idempotency_key)
        return updated

    def cancel_order(self, order_id: str) -> Order:
        """Cancel an existing order and validate transition."""

        existing = self._require_order(order_id)
        validate_transition(existing.status, OrderStatus.CANCELED)
        canceled = self._execution_service.cancel(order_id)
        self._orders[order_id] = canceled.model_copy(update={"status": OrderStatus.CANCELED})
        return self._orders[order_id]

    def process_fill(self, fill: TradeFill) -> Order:
        """Process fill, update order status, and update portfolio positions."""

        if fill.fill_id in self._fill_ids_seen:
            msg = f"Duplicate fill event received: {fill.fill_id}"
            raise DuplicateEventError(msg)
        self._fill_ids_seen.add(fill.fill_id)

        order = self._require_order(fill.order_id)
        if order.status in {OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.FILLED}:
            msg = f"Fill received for non-open order {order.order_id} in status {order.status}"
            raise ValueError(msg)

        new_filled = order.filled_quantity + int(fill.quantity)
        requested_qty = int(order.request.quantity)

        if new_filled > requested_qty:
            msg = (
                f"Overfill detected for order {order.order_id}: "
                f"requested={requested_qty} attempted_fill_total={new_filled}"
            )
            raise ValueError(msg)

        if new_filled < requested_qty:
            target_status = OrderStatus.PARTIALLY_FILLED
        else:
            target_status = OrderStatus.FILLED

        validate_transition(order.status, target_status)

        prev_notional = (order.average_fill_price or 0.0) * order.filled_quantity
        new_notional = prev_notional + fill.price * int(fill.quantity)
        avg_fill = new_notional / new_filled

        updated_order = order.model_copy(
            update={
                "filled_quantity": new_filled,
                "average_fill_price": avg_fill,
                "status": target_status,
            }
        )
        self._orders[order.order_id] = updated_order

        self._position_updater.apply_fill(order.request.instrument_id, order.request.side, fill)
        return updated_order

    def get_order(self, order_id: str) -> Order | None:
        """Return one local OMS order."""

        return self._orders.get(order_id)

    def refresh_fills(self) -> list[Order]:
        """Poll broker fills and process resulting order updates."""

        updates: list[Order] = []
        for fill in self._execution_service.poll_fills():
            updates.append(self.process_fill(fill))
        return updates

    def _require_order(self, order_id: str) -> Order:
        """Return order or raise when missing."""

        order = self._orders.get(order_id)
        if order is None:
            msg = f"Unknown order: {order_id}"
            raise KeyError(msg)
        return order
