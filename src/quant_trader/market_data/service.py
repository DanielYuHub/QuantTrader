"""High-level market data service with normalization, caching, retry, timeout, and calendars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeVar

from quant_trader.interfaces.market_data import MarketDataProviderInterface, MarketDataServiceInterface
from quant_trader.market_data.cache import TTLCache
from quant_trader.market_data.calendar import TradingCalendar
from quant_trader.market_data.models import Bar, CorporateAction, Market, OptionChain, Quote
from quant_trader.market_data.symbols import SymbolNormalizer
from quant_trader.utils.resilience import RetryPolicy, run_with_retry, run_with_timeout


@dataclass(frozen=True)
class MarketDataServiceConfig:
    """Configuration for market data service behavior."""

    timeout_seconds: float = 2.0
    retry_policy: RetryPolicy = RetryPolicy(attempts=3, delay_seconds=0.05)
    quote_ttl_seconds: int = 2
    chain_ttl_seconds: int = 10


R = TypeVar("R")


class MarketDataService(MarketDataServiceInterface):
    """Provider-agnostic service used by strategies and research layers."""

    def __init__(
        self,
        provider: MarketDataProviderInterface,
        calendar: TradingCalendar,
        symbol_normalizer: SymbolNormalizer,
        cache: TTLCache[object],
        config: MarketDataServiceConfig | None = None,
    ) -> None:
        """Initialize service dependencies."""

        self._provider = provider
        self._calendar = calendar
        self._normalizer = symbol_normalizer
        self._cache = cache
        self._config = config or MarketDataServiceConfig()

    def quote(self, raw_symbol: str, market: Market) -> Quote:
        """Return normalized quote with caching, timeout, and retries."""

        symbol = self._normalizer.normalize(raw_symbol, market)
        cache_key = f"quote:{market}:{symbol}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Quote):
            return cached

        quote = self._execute_with_resilience(self._provider.get_realtime_quote, symbol, market)
        quote_local = quote.model_copy(update={"timestamp": self._calendar.convert_timestamp(quote.timestamp, market)})
        self._cache.set(cache_key, quote_local, self._config.quote_ttl_seconds)
        return quote_local

    def historical_bars(
        self,
        raw_symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Bar]:
        """Return historical bars normalized to market timezone."""

        symbol = self._normalizer.normalize(raw_symbol, market)
        bars = self._execute_with_resilience(self._provider.get_historical_bars, symbol, market, start, end, timeframe)
        return [bar.model_copy(update={"timestamp": self._calendar.convert_timestamp(bar.timestamp, market)}) for bar in bars]

    def option_chain(self, raw_underlying_symbol: str, market: Market, as_of: datetime | None = None) -> OptionChain:
        """Return option chain with resilience and short-lived caching."""

        symbol = self._normalizer.normalize(raw_underlying_symbol, market)
        as_of_key = as_of.isoformat() if as_of else "latest"
        cache_key = f"chain:{market}:{symbol}:{as_of_key}"

        cached = self._cache.get(cache_key)
        if isinstance(cached, OptionChain):
            return cached

        chain = self._execute_with_resilience(self._provider.get_option_chain, symbol, market, as_of)
        chain_local = chain.model_copy(update={"timestamp": self._calendar.convert_timestamp(chain.timestamp, market)})
        self._cache.set(cache_key, chain_local, self._config.chain_ttl_seconds)
        return chain_local

    def corporate_actions(
        self,
        raw_symbol: str,
        market: Market,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        """Return normalized corporate actions (empty list if provider has none)."""

        symbol = self._normalizer.normalize(raw_symbol, market)
        actions = self._execute_with_resilience(self._provider.get_corporate_actions, symbol, market, start, end)
        return [
            action.model_copy(update={"ex_date": self._calendar.convert_timestamp(action.ex_date, market)})
            for action in actions
        ]

    def _execute_with_resilience(self, func: Callable[..., R], *args: object) -> R:
        """Run provider operation with retry and timeout behavior."""

        return run_with_retry(
            lambda: run_with_timeout(func, *args, timeout_seconds=self._config.timeout_seconds),
            policy=self._config.retry_policy,
        )
