"""Portfolio position updater based on execution fills."""

from __future__ import annotations

from collections.abc import Iterable

from quant_trader.models.common import Position, Side, TradeFill


class PortfolioPositionUpdater:
    """Maintains positions and updates weighted average cost from fills."""

    def __init__(self) -> None:
        """Initialize empty position book."""

        self._positions: dict[str, Position] = {}

    def positions(self) -> list[Position]:
        """Return all current positions."""

        return list(self._positions.values())

    def get_position(self, instrument_id: str) -> Position:
        """Return one position or a zero position if missing."""

        return self._positions.get(instrument_id, Position(instrument_id=instrument_id, quantity=0, average_price=0.0))

    def apply_fill(self, instrument_id: str, side: Side, fill: TradeFill) -> Position:
        """Apply fill to position and return updated state."""

        current = self.get_position(instrument_id)
        signed_qty = int(fill.quantity if side is Side.BUY else -fill.quantity)
        new_qty = current.quantity + signed_qty

        if new_qty == 0:
            updated = Position(instrument_id=instrument_id, quantity=0, average_price=0.0)
            self._positions[instrument_id] = updated
            return updated

        if current.quantity == 0 or (current.quantity > 0 and signed_qty > 0) or (current.quantity < 0 and signed_qty < 0):
            total_cost = current.average_price * abs(current.quantity) + fill.price * abs(signed_qty)
            average_price = total_cost / abs(new_qty)
        else:
            average_price = current.average_price

        updated = Position(instrument_id=instrument_id, quantity=new_qty, average_price=average_price)
        self._positions[instrument_id] = updated
        return updated

    def seed_positions(self, positions: Iterable[Position]) -> None:
        """Seed book with existing positions, e.g., broker reconciliation results."""

        self._positions = {position.instrument_id: position for position in positions}
