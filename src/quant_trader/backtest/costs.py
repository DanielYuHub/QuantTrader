"""Slippage and cost models for backtest execution."""

from __future__ import annotations

from dataclasses import dataclass

from quant_trader.models.common import AssetClass


@dataclass(frozen=True)
class SlippageModel:
    """Linear bps slippage model."""

    bps: float = 1.0

    def apply(self, price: float) -> tuple[float, float]:
        """Return slipped price and absolute slippage value."""

        delta = price * (self.bps / 10_000)
        return price + delta, abs(delta)


@dataclass(frozen=True)
class CommissionModel:
    """Commission and exchange fee model."""

    equity_per_share: float = 0.005
    option_per_contract: float = 0.65
    minimum_ticket: float = 1.0
    sec_fee_rate: float = 0.0

    def cost(self, asset_class: AssetClass, quantity: int, notional: float) -> tuple[float, float]:
        """Return commission and regulatory fee for a trade."""

        if asset_class is AssetClass.OPTION:
            commission = max(self.minimum_ticket, self.option_per_contract * quantity)
        else:
            commission = max(self.minimum_ticket, self.equity_per_share * quantity)
        fees = abs(notional) * self.sec_fee_rate
        return commission, fees
