"""Portfolio accounting and mark-to-market logic for backtesting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from quant_trader.backtest.models import BacktestFill, BacktestPosition, EquitySnapshot, PnLAttribution
from quant_trader.models.common import AssetClass, Side


@dataclass
class PortfolioAccounting:
    """Stateful portfolio accounting for fills, positions, and PnL."""

    initial_cash: float
    cash: float = field(init=False)
    realized_pnl: float = field(default=0.0, init=False)
    peak_equity: float = field(default=0.0, init=False)
    positions: dict[str, BacktestPosition] = field(default_factory=dict, init=False)
    attribution: PnLAttribution = field(default_factory=PnLAttribution, init=False)

    def __post_init__(self) -> None:
        """Initialize mutable accounting state."""

        self.cash = self.initial_cash
        self.peak_equity = self.initial_cash

    def apply_fill(self, fill: BacktestFill) -> None:
        """Apply one fill to cash, position state, and realized attribution."""

        sign = 1 if fill.side is Side.BUY else -1
        delta_qty = sign * fill.quantity
        trade_notional = fill.price * fill.quantity

        if fill.side is Side.BUY:
            self.cash -= trade_notional
        else:
            self.cash += trade_notional
        self.cash -= (fill.commission + fill.fees)

        pos = self.positions.get(
            fill.instrument_id,
            BacktestPosition(
                instrument_id=fill.instrument_id,
                quantity=0,
                average_price=0.0,
                asset_class=fill.asset_class,
            ),
        )

        new_qty = pos.quantity + delta_qty
        if pos.quantity == 0 or (pos.quantity > 0 and delta_qty > 0) or (pos.quantity < 0 and delta_qty < 0):
            total_cost = pos.average_price * abs(pos.quantity) + fill.price * abs(delta_qty)
            avg = total_cost / max(abs(new_qty), 1)
            pos = pos.model_copy(update={"quantity": new_qty, "average_price": avg})
        else:
            closed_qty = min(abs(delta_qty), abs(pos.quantity))
            pnl_per_unit = (fill.price - pos.average_price) * (1 if pos.quantity > 0 else -1)
            realized = pnl_per_unit * closed_qty
            self.realized_pnl += realized
            self._add_attribution(fill.instrument_id, fill.asset_class, realized)

            pos = pos.model_copy(update={"quantity": new_qty, "average_price": pos.average_price if new_qty != 0 else 0.0})

        self.positions[fill.instrument_id] = pos

    def snapshot(self, timestamp: datetime, marks: dict[str, float]) -> EquitySnapshot:
        """Build current equity snapshot from mark prices."""

        market_value = 0.0
        unrealized = 0.0
        for instrument_id, position in self.positions.items():
            if position.quantity == 0:
                continue
            mark = marks.get(instrument_id)
            if mark is None:
                continue
            market_value += position.quantity * mark
            unrealized += (mark - position.average_price) * position.quantity

        equity = self.cash + market_value
        self.peak_equity = max(self.peak_equity, equity)
        drawdown = 0.0 if self.peak_equity <= 0 else (self.peak_equity - equity) / self.peak_equity

        return EquitySnapshot(
            timestamp=timestamp,
            cash=self.cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
            drawdown=drawdown,
        )

    def _add_attribution(self, instrument_id: str, asset_class: AssetClass, pnl: float) -> None:
        """Accumulate realized PnL attribution buckets."""

        self.attribution.by_instrument[instrument_id] = self.attribution.by_instrument.get(instrument_id, 0.0) + pnl
        key = asset_class.value
        self.attribution.by_asset_class[key] = self.attribution.by_asset_class.get(key, 0.0) + pnl
