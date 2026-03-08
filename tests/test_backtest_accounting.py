"""Regression tests for backtest position basis and realized PnL accounting."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant_trader.backtest.accounting import PortfolioAccounting
from quant_trader.backtest.models import BacktestFill
from quant_trader.models.common import AssetClass, Side


def _fill(side: Side, quantity: int, price: float) -> BacktestFill:
    return BacktestFill(
        timestamp=datetime(2025, 1, 2, 14, 30, tzinfo=ZoneInfo("UTC")),
        instrument_id="AAPL",
        side=side,
        quantity=quantity,
        price=price,
        slippage=0.0,
        commission=0.0,
        fees=0.0,
        asset_class=AssetClass.EQUITY,
    )


def test_partial_reduce_without_crossing_flat_preserves_basis_and_realized_pnl() -> None:
    """Reducing an open position should keep basis for residual quantity and realize close PnL only."""

    accounting = PortfolioAccounting(initial_cash=100_000.0)
    accounting.apply_fill(_fill(Side.BUY, quantity=10, price=100.0))
    accounting.apply_fill(_fill(Side.SELL, quantity=4, price=110.0))

    position = accounting.positions["AAPL"]
    assert position.quantity == 6
    assert position.average_price == pytest.approx(100.0)
    assert accounting.realized_pnl == pytest.approx(40.0)


def test_exact_flatten_to_zero_clears_basis_and_realized_pnl_is_correct() -> None:
    """A fill that exactly flattens position should reset basis and realize full close PnL."""

    accounting = PortfolioAccounting(initial_cash=100_000.0)
    accounting.apply_fill(_fill(Side.BUY, quantity=10, price=100.0))
    accounting.apply_fill(_fill(Side.SELL, quantity=10, price=110.0))

    position = accounting.positions["AAPL"]
    assert position.quantity == 0
    assert position.average_price == pytest.approx(0.0)
    assert accounting.realized_pnl == pytest.approx(100.0)


def test_long_to_short_flip_resets_basis_to_flip_fill_price() -> None:
    """Crossing from long through flat to short should reset residual basis to flip fill price."""

    accounting = PortfolioAccounting(initial_cash=100_000.0)
    accounting.apply_fill(_fill(Side.BUY, quantity=10, price=100.0))
    accounting.apply_fill(_fill(Side.SELL, quantity=15, price=90.0))

    position = accounting.positions["AAPL"]
    assert position.quantity == -5
    assert position.average_price == pytest.approx(90.0)
    assert accounting.realized_pnl == pytest.approx(-100.0)


def test_short_to_long_flip_resets_basis_to_flip_fill_price() -> None:
    """Crossing from short through flat to long should reset residual basis to flip fill price."""

    accounting = PortfolioAccounting(initial_cash=100_000.0)
    accounting.apply_fill(_fill(Side.SELL, quantity=10, price=100.0))
    accounting.apply_fill(_fill(Side.BUY, quantity=15, price=110.0))

    position = accounting.positions["AAPL"]
    assert position.quantity == 5
    assert position.average_price == pytest.approx(110.0)
    assert accounting.realized_pnl == pytest.approx(-100.0)
