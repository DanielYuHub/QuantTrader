"""Tests for symbol normalization."""

from __future__ import annotations

import pytest

from quant_trader.market_data.models import Market
from quant_trader.market_data.symbols import SymbolNormalizationError, SymbolNormalizer



def test_normalize_us_symbol_uppercases_and_keeps_dot() -> None:
    """US symbols should normalize to uppercase canonical format."""

    normalizer = SymbolNormalizer()
    assert normalizer.normalize("brk/b", Market.US) == "BRK.B"



def test_normalize_hk_symbol_zero_pads_and_suffixes() -> None:
    """HK symbols should normalize to five digits plus .HK suffix."""

    normalizer = SymbolNormalizer()
    assert normalizer.normalize("700", Market.HK) == "00700.HK"



def test_invalid_hk_symbol_raises() -> None:
    """Invalid HK symbols should raise normalization error."""

    normalizer = SymbolNormalizer()
    with pytest.raises(SymbolNormalizationError):
        normalizer.normalize("HK.700", Market.HK)
