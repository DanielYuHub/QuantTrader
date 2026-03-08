"""Example educational strategies."""

from quant_trader.strategy.examples.covered_call import CoveredCallStrategy
from quant_trader.strategy.examples.hk_mean_reversion import HKMeanReversionStrategy
from quant_trader.strategy.examples.us_momentum import USEquityMomentumStrategy
from quant_trader.strategy.examples.vol_breakout import OptionsVolatilityBreakoutStrategy

__all__ = [
    "CoveredCallStrategy",
    "HKMeanReversionStrategy",
    "OptionsVolatilityBreakoutStrategy",
    "USEquityMomentumStrategy",
]
