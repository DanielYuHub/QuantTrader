"""Provider-agnostic market data interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from quant_trader.market_data.models import Bar, CorporateAction, InstrumentRef, Market, OptionChain, Quote


class MarketDataProviderInterface(ABC):
    """Low-level provider adapter contract for market data sources."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return adapter/provider display name."""

    @abstractmethod
    def list_instruments(self, market: Market, include_options: bool = True) -> list[InstrumentRef]:
        """Return instrument references for a market."""

    @abstractmethod
    def get_realtime_quote(self, symbol: str, market: Market) -> Quote:
        """Return latest available real-time quote for a symbol."""

    @abstractmethod
    def get_historical_bars(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Bar]:
        """Return OHLCV bars in the requested interval and timeframe."""

    @abstractmethod
    def get_option_chain(self, underlying_symbol: str, market: Market, as_of: datetime | None = None) -> OptionChain:
        """Return option chain snapshot for an underlying symbol."""

    @abstractmethod
    def get_corporate_actions(
        self,
        symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        """Return corporate actions in date range if provider supports it."""


class MarketDataServiceInterface(ABC):
    """High-level market data service abstraction consumed by app layers."""

    @abstractmethod
    def quote(self, raw_symbol: str, market: Market) -> Quote:
        """Return normalized real-time quote."""

    @abstractmethod
    def historical_bars(
        self,
        raw_symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Bar]:
        """Return normalized historical bars."""

    @abstractmethod
    def option_chain(self, raw_underlying_symbol: str, market: Market, as_of: datetime | None = None) -> OptionChain:
        """Return normalized option chain for underlying."""

    @abstractmethod
    def corporate_actions(
        self,
        raw_symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        """Return normalized corporate actions."""
