"""Symbol normalization utilities for US and HK markets."""

from __future__ import annotations

import re

from quant_trader.market_data.models import Market


class SymbolNormalizationError(ValueError):
    """Raised when a symbol cannot be normalized."""


class SymbolNormalizer:
    """Normalize market symbols into canonical internal format."""

    _hk_pattern = re.compile(r"^(\d{1,5})(?:\.HK)?$")

    def normalize(self, raw_symbol: str, market: Market) -> str:
        """Return canonical symbol for the given market."""

        if market is Market.US:
            symbol = raw_symbol.strip().upper().replace("/", ".")
            if not symbol:
                msg = "US symbol is empty"
                raise SymbolNormalizationError(msg)
            return symbol

        if market is Market.HK:
            match = self._hk_pattern.match(raw_symbol.strip().upper())
            if not match:
                msg = f"Invalid HK symbol: {raw_symbol}"
                raise SymbolNormalizationError(msg)
            code = match.group(1).zfill(5)
            return f"{code}.HK"

        msg = f"Unsupported market for symbol normalization: {market}"
        raise SymbolNormalizationError(msg)
