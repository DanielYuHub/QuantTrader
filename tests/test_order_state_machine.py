"""Tests for OMS state machine transitions."""

from __future__ import annotations

import pytest

from quant_trader.models.common import OrderStatus
from quant_trader.oms.state_machine import InvalidOrderTransitionError, validate_transition



def test_valid_transition_ack_to_partial_fill() -> None:
    """ACKNOWLEDGED -> PARTIALLY_FILLED should be allowed."""

    validate_transition(OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED)



def test_invalid_transition_filled_to_acknowledged_raises() -> None:
    """FILLED should not transition back to ACKNOWLEDGED."""

    with pytest.raises(InvalidOrderTransitionError):
        validate_transition(OrderStatus.FILLED, OrderStatus.ACKNOWLEDGED)
