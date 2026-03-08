"""Tests for options handling in backtest engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quant_trader.backtest.costs import CommissionModel, SlippageModel
from quant_trader.backtest.engine import BacktestEngine, BacktestInputs
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Bar, Market, OptionContract, OptionRight
from quant_trader.models.common import AssetClass, Side
from quant_trader.strategy.base import BaseStrategy
from quant_trader.strategy.engine import StrategyEngine
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategySignal
from quant_trader.strategy.portfolio import PortfolioConstructionConfig, PortfolioConstructor


class BuyOptionStrategy(BaseStrategy):
    """Buys one option contract on every event for test purposes."""

    strategy_id = "buy_option"

    def __init__(self, contract_symbol: str) -> None:
        self._contract_symbol = contract_symbol

    def on_event(self, event: StrategyEvent, context: StrategyContext) -> list[StrategySignal]:
        _ = event, context
        return [
            StrategySignal(
                strategy_id=self.strategy_id,
                timestamp=event.timestamp,
                instrument_id=self._contract_symbol,
                asset_class=AssetClass.OPTION,
                side=Side.BUY,
                strength=1.0,
                reason="option entry",
            )
        ]



def _bar(ts: datetime, symbol: str, open_price: float, close_price: float) -> Bar:
    return Bar(
        symbol=symbol,
        market=Market.US,
        timestamp=ts,
        open=open_price,
        high=max(open_price, close_price),
        low=min(open_price, close_price),
        close=close_price,
        volume=100,
    )



def test_option_expiration_closes_position() -> None:
    """Expired option contracts should be closed by expiration handling."""

    t0 = datetime(2025, 1, 2, 15, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=1)
    contract_symbol = "AAPL250103C00100000"

    option_bars = [_bar(t0, contract_symbol, 2.0, 2.1), _bar(t1, contract_symbol, 2.2, 0.0)]
    underlying_bars = [_bar(t0, "AAPL", 100.0, 101.0), _bar(t1, "AAPL", 105.0, 106.0)]
    benchmark = [_bar(t0, "SPY", 500.0, 501.0), _bar(t1, "SPY", 502.0, 503.0)]

    option_contract = OptionContract(
        contract_symbol=contract_symbol,
        underlying_symbol="AAPL",
        market=Market.US,
        expiry=t1,
        strike=100.0,
        right=OptionRight.CALL,
    )

    strategy_engine = StrategyEngine(
        strategies=[BuyOptionStrategy(contract_symbol)],
        portfolio_constructor=PortfolioConstructor(PortfolioConstructionConfig(base_lot_size=1, min_strength_threshold=0.0)),
    )
    backtest = BacktestEngine(
        strategy_engine=strategy_engine,
        calendar=TradingCalendar(),
        slippage_model=SlippageModel(bps=0),
        commission_model=CommissionModel(option_per_contract=0.0, minimum_ticket=0.0),
    )

    result = backtest.run(
        BacktestInputs(
            bars_by_instrument={contract_symbol: option_bars, "AAPL": underlying_bars},
            benchmark_bars=benchmark,
            option_contracts={contract_symbol: option_contract},
        )
    )

    assert len(result.fills) >= 1
    assert result.equity_curve[-1].equity > 0
