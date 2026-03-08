"""Order state machine utilities."""

from __future__ import annotations

from quant_trader.models.common import OrderStatus


class InvalidOrderTransitionError(ValueError):
    """Raised when order transitions violate state machine rules."""


_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_NEW: {OrderStatus.ACKNOWLEDGED, OrderStatus.REJECTED, OrderStatus.CANCELED},
    OrderStatus.ACKNOWLEDGED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
        OrderStatus.REPLACED,
        OrderStatus.REJECTED,
    },
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REPLACED},
    OrderStatus.REPLACED: {OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELED},
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELED: set(),
    OrderStatus.REJECTED: set(),
}


def validate_transition(current: OrderStatus, target: OrderStatus) -> None:
    """Validate state transition and raise when invalid."""

    allowed = _ALLOWED_TRANSITIONS[current]
    if target not in allowed:
        msg = f"Invalid order transition: {current} -> {target}"
        raise InvalidOrderTransitionError(msg)
