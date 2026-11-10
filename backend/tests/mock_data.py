import math
from typing import Any
import pandas as pd


class MockFastInfo:
    """Simulates the fast_info property of a yfinance Ticker."""

    def __init__(
        self,
        symbol: str,
        last_price: float | None = None,
        open_price: float | None = None,
        day_high: float | None = None,
        day_low: float | None = None,
        previous_close: float | None = None,
        currency: str = "USD",
    ):
        self.symbol = symbol
        self.last_price = last_price
        self.open = open_price
        self.day_high = day_high
        self.day_low = day_low
        self.previous_close = previous_close
        self.currency = currency


def create_deterministic_bars(
    symbol: str,
    period: str = "1mo",
    interval: str = "1d",
    base_price: float | None = None,
) -> pd.DataFrame:
    """
    Generates a deterministic OHLCV pandas DataFrame with strictly valid financial invariants:
    - Positive prices (P > 0)
    - Low <= min(Open, Close)
    - High >= max(Open, Close)
    - Non-negative volume (Volume >= 0)
    - Chronological, timezone-aware UTC DatetimeIndex
    """
    period_lower = period.lower() if period else "1mo"
    if "1d" in period_lower:
        count = 5
    elif "5d" in period_lower:
        count = 5
    elif "1mo" in period_lower:
        count = 30
    elif "3mo" in period_lower:
        count = 60
    elif "6mo" in period_lower:
        count = 120
    elif "1y" in period_lower or "2y" in period_lower:
        count = 250
    else:
        count = 60

    if base_price is None:
        sym_upper = symbol.upper()
        if "AAPL" in sym_upper:
            base_price = 150.0
        elif "MSFT" in sym_upper:
            base_price = 300.0
        elif "TSLA" in sym_upper:
            base_price = 250.0
        elif "NVDA" in sym_upper:
            base_price = 120.0
        elif "BTC" in sym_upper:
            base_price = 65000.0
        else:
            base_price = 100.0

    end_date = pd.Timestamp("2026-11-01 00:00:00", tz="UTC")
    freq = "h" if ("h" in interval or "m" in interval) else "D"
    dates = pd.date_range(end=end_date, periods=count, freq=freq, tz="UTC")

    data = []
    for i in range(count):
        # A smooth deterministic sine wave permitting SMA crossover and RSI signals
        wave = 8.0 * math.sin(i / 6.0)
        open_val = round(base_price + wave, 2)
        close_delta = 1.5 if i % 2 == 0 else -1.2
        close_val = round(open_val + close_delta, 2)
        high_val = round(max(open_val, close_val) + 2.0, 2)
        low_val = round(min(open_val, close_val) - 2.0, 2)
        volume_val = 100000 + (i * 500)

        data.append(
            {
                "Open": open_val,
                "High": high_val,
                "Low": low_val,
                "Close": close_val,
                "Volume": volume_val,
            }
        )

    return pd.DataFrame(data, index=dates)


class MockMarketController:
    """Allows individual tests to override quotes, candles, search results, or inject provider errors."""

    def __init__(self):
        self.custom_quotes: dict[str, float] = {}
        self.custom_bars: dict[str, pd.DataFrame] = {}
        self.custom_fast_info: dict[str, MockFastInfo | None] = {}
        self.custom_search_results: dict[str, list[dict[str, Any]]] = {}
        self.errors: dict[str, Exception] = {}
        self.search_calls: list[dict[str, Any]] = []
        self.ticker_calls: list[str] = []

    def set_price(self, symbol: str, price: float) -> None:
        self.custom_quotes[symbol.strip().upper()] = price

    def set_empty_history(self, symbol: str) -> None:
        self.custom_bars[symbol.strip().upper()] = pd.DataFrame()

    def set_search_results(self, query: str, results: list[dict[str, Any]]) -> None:
        self.custom_search_results[query.strip()] = results

    def set_error(self, symbol: str, exc: Exception) -> None:
        self.errors[symbol.strip().upper()] = exc

    def reset(self) -> None:
        self.custom_quotes.clear()
        self.custom_bars.clear()
        self.custom_fast_info.clear()
        self.custom_search_results.clear()
        self.errors.clear()
        self.search_calls.clear()
        self.ticker_calls.clear()


class MockSearch:
    """Mock replacement for yfinance.Search to isolate symbol search from network calls."""

    def __init__(
        self,
        query: str,
        max_results: int = 8,
        controller: MockMarketController | None = None,
    ):
        self.query = query
        self.max_results = max_results
        self.controller = controller
        self.quotes: list[dict[str, Any]] = self._generate_quotes(query)

    def _generate_quotes(self, query: str) -> list[dict[str, Any]]:
        q_clean = query.strip()
        if self.controller:
            if q_clean in self.controller.errors:
                raise self.controller.errors[q_clean]
            if q_clean.upper() in self.controller.errors:
                raise self.controller.errors[q_clean.upper()]
            if q_clean in self.controller.custom_search_results:
                return self.controller.custom_search_results[q_clean][: self.max_results]
            if q_clean.upper() in self.controller.custom_search_results:
                return self.controller.custom_search_results[q_clean.upper()][: self.max_results]

        q = q_clean.lower()
        results: list[dict[str, Any]] = []
        if "apple" in q or "aapl" in q:
            results.append(
                {
                    "symbol": "AAPL",
                    "shortname": "Apple Inc.",
                    "longname": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            )
        elif "msft" in q or "micro" in q:
            results.append(
                {
                    "symbol": "MSFT",
                    "shortname": "Microsoft Corporation",
                    "longname": "Microsoft Corporation",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            )
        elif "tsla" in q or "tesla" in q:
            results.append(
                {
                    "symbol": "TSLA",
                    "shortname": "Tesla, Inc.",
                    "longname": "Tesla, Inc.",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            )
        elif "nvda" in q or "nvidia" in q:
            results.append(
                {
                    "symbol": "NVDA",
                    "shortname": "NVIDIA Corporation",
                    "longname": "NVIDIA Corporation",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            )
        elif "btc" in q or "bitcoin" in q:
            results.append(
                {
                    "symbol": "BTC-USD",
                    "shortname": "Bitcoin USD",
                    "longname": "Bitcoin USD",
                    "exchange": "CCC",
                    "quoteType": "CRYPTOCURRENCY",
                }
            )
        else:
            results.append(
                {
                    "symbol": q_clean.upper(),
                    "shortname": f"{q_clean.title()} Corp",
                    "longname": f"{q_clean.title()} Corporation",
                    "exchange": "NASDAQ",
                    "quoteType": "EQUITY",
                }
            )
        return results[: self.max_results]


class MockTicker:
    """Mock replacement for yfinance.Ticker satisfying all call patterns across the codebase."""

    def __init__(self, symbol: str, controller: MockMarketController):
        self.symbol = symbol.strip().upper()
        self.controller = controller

    @property
    def fast_info(self) -> MockFastInfo | None:
        if self.symbol in self.controller.errors:
            raise self.controller.errors[self.symbol]

        if self.symbol in self.controller.custom_fast_info:
            return self.controller.custom_fast_info[self.symbol]

        if self.symbol.startswith("XYZ") or "INVALID" in self.symbol:
            return None

        price = self.controller.custom_quotes.get(self.symbol)
        if price is None:
            if "AAPL" in self.symbol:
                price = 150.0
            elif "MSFT" in self.symbol:
                price = 300.0
            elif "TSLA" in self.symbol:
                price = 250.0
            elif "NVDA" in self.symbol:
                price = 120.0
            elif "BTC" in self.symbol:
                price = 65000.0
            else:
                price = 100.0

        return MockFastInfo(
            symbol=self.symbol,
            last_price=price,
            open_price=round(price - 1.0, 2),
            day_high=round(price + 2.0, 2),
            day_low=round(price - 2.0, 2),
            previous_close=round(price - 0.5, 2),
            currency="USD",
        )

    def history(self, period: str = "1mo", interval: str = "1d", **kwargs: Any) -> pd.DataFrame:
        if self.symbol in self.controller.errors:
            raise self.controller.errors[self.symbol]

        if self.symbol in self.controller.custom_bars:
            return self.controller.custom_bars[self.symbol]

        if self.symbol.startswith("XYZ") or "INVALID" in self.symbol:
            return pd.DataFrame()

        base_price = self.controller.custom_quotes.get(self.symbol)
        return create_deterministic_bars(
            symbol=self.symbol,
            period=period,
            interval=interval,
            base_price=base_price,
        )

