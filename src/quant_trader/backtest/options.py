"""Option expiration and assignment/exercise modeling hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from quant_trader.backtest.models import BacktestPosition


class OptionLifecycleHook(ABC):
    """Interface for assignment/exercise and expiration behavior customization."""

    @abstractmethod
    def on_expiration(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """Return cash adjustment applied when option expires."""

    @abstractmethod
    def on_assignment(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """Return cash adjustment if assignment occurs."""

    @abstractmethod
    def on_exercise(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """Return cash adjustment if exercise occurs."""


class DefaultOptionLifecycleHook(OptionLifecycleHook):
    """Default conservative option lifecycle behavior."""

    def on_expiration(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """Settle intrinsic value in cash if spot price is available."""

        _ = timestamp
        if position.contract is None or spot_price is None or position.quantity == 0:
            return 0.0

        strike = position.contract.strike
        if position.contract.right.value == "CALL":
            intrinsic = max(spot_price - strike, 0.0)
        else:
            intrinsic = max(strike - spot_price, 0.0)
        return intrinsic * position.quantity * position.contract.multiplier

    def on_assignment(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """No assignment by default."""

        _ = position, spot_price, timestamp
        return 0.0

    def on_exercise(self, position: BacktestPosition, spot_price: float | None, timestamp: datetime) -> float:
        """No discretionary exercise by default."""

        _ = position, spot_price, timestamp
        return 0.0
