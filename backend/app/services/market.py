from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any

import yfinance as yf

from app.schemas.market import (
    Candle,
    HistoricalDataResponse,
    QuoteResponse,
    SymbolSearchResult,
)


class MarketDataService:
    """
    Market Data Service providing real-time quotes, historical OHLCV bars,
    and symbol search with an in-memory TTL cache to reduce latency and respect rate limits.
    """

    _quote_cache: dict[str, tuple[float, QuoteResponse]] = {}
    CACHE_TTL_SECONDS = 15

    # Popular curated symbols for instant search & autocomplete fallback
    POPULAR_SYMBOLS = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ", "quote_type": "EQUITY"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE Arca", "quote_type": "ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ", "quote_type": "ETF"},
        {"symbol": "BTC-USD", "name": "Bitcoin USD", "exchange": "CCC", "quote_type": "CRYPTOCURRENCY"},
        {"symbol": "ETH-USD", "name": "Ethereum USD", "exchange": "CCC", "quote_type": "CRYPTOCURRENCY"},
    ]

    def get_quote(self, symbol: str) -> QuoteResponse:
        sym = symbol.strip().upper()
        now = time.time()

        # Check in-memory cache
        if sym in self._quote_cache:
            timestamp, cached_quote = self._quote_cache[sym]
            if now - timestamp < self.CACHE_TTL_SECONDS:
                return cached_quote

        ticker = yf.Ticker(sym)

        # Retrieve fast_info or info
        try:
            fast_info = getattr(ticker, "fast_info", None)
            price = None
            open_price = None
            high = None
            low = None
            prev_close = None
            volume = None
            currency = "USD"

            if fast_info:
                price = getattr(fast_info, "last_price", None)
                open_price = getattr(fast_info, "open", None)
                high = getattr(fast_info, "day_high", None)
                low = getattr(fast_info, "day_low", None)
                prev_close = getattr(fast_info, "previous_close", None)
                currency = getattr(fast_info, "currency", "USD") or "USD"

            # If fast_info was insufficient, fallback to history(period="1d")
            if price is None:
                hist = ticker.history(period="1d")
                if hist.empty:
                    raise ValueError(f"No price data available for symbol '{sym}'")
                latest = hist.iloc[-1]
                price = float(latest["Close"])
                open_price = float(latest["Open"])
                high = float(latest["High"])
                low = float(latest["Low"])
                volume = int(latest["Volume"])

            # Calculate change and percent
            change = None
            change_percent = None
            if price is not None and prev_close:
                change = Decimal(str(round(price - prev_close, 4)))
                change_percent = Decimal(
                    str(round(((price - prev_close) / prev_close) * 100, 2))
                )

            quote = QuoteResponse(
                symbol=sym,
                price=Decimal(str(round(price, 4))),
                currency=currency,
                open=Decimal(str(round(open_price, 4))) if open_price is not None else None,
                high=Decimal(str(round(high, 4))) if high is not None else None,
                low=Decimal(str(round(low, 4))) if low is not None else None,
                previous_close=Decimal(str(round(prev_close, 4))) if prev_close is not None else None,
                change=change,
                change_percent=change_percent,
                volume=volume,
                timestamp=datetime.now(timezone.utc),
            )

            # Store in cache
            self._quote_cache[sym] = (now, quote)
            return quote

        except Exception as exc:
            raise ValueError(f"Failed to fetch quote for '{sym}': {str(exc)}") from exc

    def get_history(
        self,
        symbol: str,
        timeframe: str = "1d",
        period: str = "1mo",
    ) -> HistoricalDataResponse:
        sym = symbol.strip().upper()
        ticker = yf.Ticker(sym)

        # Supported intervals in yfinance: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        # Supported periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        try:
            hist = ticker.history(period=period, interval=timeframe)
        except Exception as exc:
            raise ValueError(f"Error requesting history for '{sym}': {str(exc)}") from exc

        if hist.empty:
            raise ValueError(
                f"No historical data found for '{sym}' with period='{period}' and timeframe='{timeframe}'"
            )

        candles: list[Candle] = []
        for index, row in hist.iterrows():
            ts = index.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            candles.append(
                Candle(
                    timestamp=ts,
                    open=Decimal(str(round(float(row["Open"]), 4))),
                    high=Decimal(str(round(float(row["High"]), 4))),
                    low=Decimal(str(round(float(row["Low"]), 4))),
                    close=Decimal(str(round(float(row["Close"]), 4))),
                    volume=int(row["Volume"]),
                )
            )

        return HistoricalDataResponse(
            symbol=sym,
            timeframe=timeframe,
            count=len(candles),
            candles=candles,
        )

    def search_symbols(self, query: str) -> list[SymbolSearchResult]:
        q = query.strip().upper()
        results: list[SymbolSearchResult] = []

        # First check popular symbols
        for item in self.POPULAR_SYMBOLS:
            if q in item["symbol"] or q in item["name"].upper():
                results.append(SymbolSearchResult(**item))

        # Try yfinance Search if available
        try:
            search_obj = yf.Search(query, max_results=8)
            quotes = getattr(search_obj, "quotes", [])
            for item in quotes:
                sym = item.get("symbol")
                if sym and not any(r.symbol == sym for r in results):
                    results.append(
                        SymbolSearchResult(
                            symbol=sym,
                            name=item.get("shortname") or item.get("longname") or sym,
                            exchange=item.get("exchange"),
                            quote_type=item.get("quoteType"),
                        )
                    )
        except Exception:
            pass

        return results
