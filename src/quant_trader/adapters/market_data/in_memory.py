"""In-memory market data provider adapter for tests and local development."""

from __future__ import annotations

from datetime import datetime

from quant_trader.interfaces.market_data import MarketDataProviderInterface
from quant_trader.market_data.models import Bar, CorporateAction, InstrumentRef, Market, OptionChain, Quote


class InMemoryMarketDataProvider(MarketDataProviderInterface):
    """Simple in-memory provider implementing the market data contract."""

    def __init__(
        self,
        instruments: list[InstrumentRef],
        quotes: dict[tuple[Market, str], Quote],
        bars: dict[tuple[Market, str, str], list[Bar]],
        chains: dict[tuple[Market, str], OptionChain],
        actions: dict[tuple[Market, str], list[CorporateAction]] | None = None,
    ) -> None:
        """Store in-memory market data payloads."""

        self._instruments = instruments
        self._quotes = quotes
        self._bars = bars
        self._chains = chains
        self._actions = actions or {}

    @property
    def provider_name(self) -> str:
        """Return adapter name."""

        return "in-memory"

    def list_instruments(self, market: Market, include_options: bool = True) -> list[InstrumentRef]:
        """Return instruments by market."""

        return [inst for inst in self._instruments if inst.market is market]

    def get_realtime_quote(self, symbol: str, market: Market) -> Quote:
        """Return quote for symbol."""

        return self._quotes[(market, symbol)]

    def get_historical_bars(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Bar]:
        """Return historical bars filtered by timestamp range."""

        all_bars = self._bars[(market, symbol, timeframe)]
        return [bar for bar in all_bars if start <= bar.timestamp <= end]

    def get_option_chain(self, underlying_symbol: str, market: Market, as_of: datetime | None = None) -> OptionChain:
        """Return option chain for underlying symbol."""

        return self._chains[(market, underlying_symbol)]

    def get_corporate_actions(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        """Return corporate actions within range."""

        actions = self._actions.get((market, symbol), [])
        return [action for action in actions if start <= action.ex_date <= end]
