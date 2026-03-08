"""Tests for educational strategy examples."""

from __future__ import annotations

from datetime import datetime, timezone

from quant_trader.market_data.models import (
    Market,
    OptionChain,
    OptionChainEntry,
    OptionContract,
    OptionRight,
)
from quant_trader.models.common import Side
from quant_trader.strategy.examples import (
    CoveredCallStrategy,
    HKMeanReversionStrategy,
    OptionsVolatilityBreakoutStrategy,
    USEquityMomentumStrategy,
)
from quant_trader.strategy.models import StrategyContext, StrategyEvent, StrategyMode, StrategyScheduleEvent



def _event(price: float, instrument: str = "AAPL") -> StrategyEvent:
    return StrategyEvent(timestamp=datetime.now(timezone.utc), instrument_id=instrument, price=price)



def test_us_momentum_strategy_generates_buy_signal() -> None:
    """Momentum strategy should emit BUY when price trend rises."""

    strategy = USEquityMomentumStrategy(lookback=3)
    context = StrategyContext(mode=StrategyMode.BACKTEST)

    assert strategy.on_event(_event(100.0), context) == []
    assert strategy.on_event(_event(101.0), context) == []
    signals = strategy.on_event(_event(103.0), context)

    assert len(signals) == 1
    assert signals[0].side is Side.BUY



def test_hk_mean_reversion_generates_buy_signal_on_drop() -> None:
    """Mean reversion strategy should buy after sufficiently deep pullback."""

    strategy = HKMeanReversionStrategy(lookback=3, threshold_bps=50)
    context = StrategyContext(mode=StrategyMode.PAPER)

    strategy.on_event(_event(100.0, "00700.HK"), context)
    strategy.on_event(_event(100.0, "00700.HK"), context)
    signals = strategy.on_event(_event(99.0, "00700.HK"), context)

    assert len(signals) == 1
    assert signals[0].side is Side.BUY



def _sample_chain() -> OptionChain:
    return OptionChain(
        underlying_symbol="AAPL",
        market=Market.US,
        timestamp=datetime.now(timezone.utc),
        entries=[
            OptionChainEntry(
                contract=OptionContract(
                    contract_symbol="AAPL250117C00110000",
                    underlying_symbol="AAPL",
                    market=Market.US,
                    expiry=datetime(2025, 1, 17, tzinfo=timezone.utc),
                    strike=110.0,
                    right=OptionRight.CALL,
                ),
                implied_volatility=0.2,
            )
        ],
    )



def test_covered_call_strategy_emits_sell_signal_when_covered() -> None:
    """Covered call should emit SELL option signal when owning >=100 shares."""

    strategy = CoveredCallStrategy(underlying_symbol="AAPL")
    context = StrategyContext(
        mode=StrategyMode.LIVE,
        positions={"AAPL": 200},
        option_chains={"AAPL": _sample_chain()},
    )
    schedule = StrategyScheduleEvent(timestamp=datetime.now(timezone.utc), trigger_name="weekly")

    signals = strategy.on_schedule(schedule, context)

    assert len(signals) == 1
    assert signals[0].side is Side.SELL
    assert signals[0].instrument_id == "AAPL250117C00110000"



def test_vol_breakout_strategy_emits_signal_after_iv_jump() -> None:
    """Vol breakout should emit BUY after baseline is formed and IV spikes."""

    strategy = OptionsVolatilityBreakoutStrategy("AAPL", lookback=2, breakout_multiplier=1.1)
    schedule = StrategyScheduleEvent(timestamp=datetime.now(timezone.utc), trigger_name="intraday")

    base_chain = _sample_chain()
    high_iv_chain = _sample_chain().model_copy(
        update={
            "entries": [
                base_chain.entries[0].model_copy(update={"implied_volatility": 0.4}),
            ]
        }
    )

    context_base = StrategyContext(mode=StrategyMode.BACKTEST, option_chains={"AAPL": base_chain})
    context_spike = StrategyContext(mode=StrategyMode.BACKTEST, option_chains={"AAPL": high_iv_chain})

    assert strategy.on_schedule(schedule, context_base) == []
    assert strategy.on_schedule(schedule, context_base) == []
    signals = strategy.on_schedule(schedule, context_spike)

    assert len(signals) == 1
    assert signals[0].side is Side.BUY
