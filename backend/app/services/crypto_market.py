import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import time
from typing import Any, Awaitable, Callable, TypeVar

from app.adapters.base import MarketDataAdapter
from app.adapters.exceptions import UnsupportedAssetError
from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoQuote,
    OptionChainResponse,
    OptionContractSummary,
)

T = TypeVar("T")


class CacheItem:
    """Represents a cached value with a monotonic expiration timestamp."""

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class AsyncTTLMemoryCache:
    """
    Thread-safe and async-safe in-memory cache with per-key stampede protection
    using asyncio.Lock, bounded lock lifecycle, and monotonic expiration.
    """

    MAX_LOCKS = 256
    MAX_ITEMS = 1024

    def __init__(self):
        self._store: dict[str, CacheItem] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _prune_locks(self) -> None:
        """Prunes unlocked locks when the lock dictionary exceeds capacity."""
        if len(self._locks) > self.MAX_LOCKS:
            unused = [k for k, l in self._locks.items() if not l.locked()]
            for k in unused:
                self._locks.pop(k, None)

    def _prune_expired_items(self) -> None:
        """Prunes expired cache items when storage exceeds capacity."""
        if len(self._store) > self.MAX_ITEMS:
            now = time.monotonic()
            expired = [k for k, item in self._store.items() if now >= item.expires_at]
            for k in expired:
                self._store.pop(k, None)

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item and not item.is_expired():
            return item.value
        return None

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._prune_expired_items()
        self._store[key] = CacheItem(value, ttl)

    def clear(self) -> None:
        self._store.clear()
        self._locks.clear()

    async def get_or_set(
        self,
        key: str,
        ttl_seconds: float,
        fetcher: Callable[[], Awaitable[T]],
    ) -> T:
        # First check without locking (fast path)
        val = self.get(key)
        if val is not None:
            return val

        # Acquire per-key lock to prevent cache stampede
        if key not in self._locks:
            self._prune_locks()
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double check after acquiring lock
            val = self.get(key)
            if val is not None:
                return val

            # Execute fetcher; failed fetches raise and are NEVER cached
            fresh_val = await fetcher()
            self.set(key, fresh_val, ttl_seconds)
            return fresh_val


def _parse_period_to_timedelta(period: str) -> timedelta:
    p = period.strip().lower()
    if p.endswith("d"):
        days = int(p[:-1])
        return timedelta(days=days)
    elif p.endswith("w"):
        weeks = int(p[:-1])
        return timedelta(weeks=weeks)
    elif p.endswith("mo"):
        months = int(p[:-2])
        return timedelta(days=months * 30)
    elif p.endswith("m") and not p.endswith("mo"):
        months = int(p[:-1])
        return timedelta(days=months * 30)
    elif p.endswith("y"):
        years = int(p[:-1])
        return timedelta(days=years * 365)
    return timedelta(days=30)


def _get_4h_bucket_start(dt: datetime) -> datetime:
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    bucket_hour = utc_dt.hour - (utc_dt.hour % 4)
    return utc_dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)


def aggregate_1h_to_4h_candles(
    instrument_name: str,
    hourly_candles: list[CryptoCandle],
    now_utc: datetime | None = None,
) -> list[CryptoCandle]:
    """
    Aggregates 1-hour candles into UTC-aligned 4-Hour candles.
    
    Bucket boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
    
    Closure Semantics:
    A 4H candle is marked closed (is_closed=True) ONLY when:
    1. Exactly four expected hourly candles exist.
    2. Their timestamps match the UTC bucket offsets 0, 1, 2, and 3 hours.
    3. Every source hourly candle is marked closed (bar.is_closed is True).
    4. The 4H bucket end timestamp (bucket_start + 4h) is less than or equal to current UTC time.
    Otherwise, is_closed is set to False.
    """
    if not hourly_candles:
        return []

    ref_now = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if ref_now.tzinfo is None:
        ref_now = ref_now.replace(tzinfo=timezone.utc)
    else:
        ref_now = ref_now.astimezone(timezone.utc)

    sorted_bars = sorted(hourly_candles, key=lambda b: b.timestamp)
    buckets: dict[datetime, list[CryptoCandle]] = {}

    for bar in sorted_bars:
        b_start = _get_4h_bucket_start(bar.timestamp)
        buckets.setdefault(b_start, []).append(bar)

    aggregated: list[CryptoCandle] = []

    for b_start in sorted(buckets.keys()):
        b_bars = sorted(buckets[b_start], key=lambda b: b.timestamp)
        b_end = b_start + timedelta(hours=4)

        # 1. Bucket end timestamp <= now_utc
        # 2. Exactly four expected hourly candles exist
        # 3. Timestamps match UTC offsets 0, 1, 2, 3 hours
        # 4. Every source hourly candle is marked closed
        has_four_bars = len(b_bars) == 4
        offsets_match = (
            has_four_bars
            and all(
                b_bars[idx].timestamp == b_start + timedelta(hours=idx)
                for idx in range(4)
            )
        )
        all_bars_closed = all(bar.is_closed for bar in b_bars)
        bucket_ended = b_end <= ref_now

        is_closed = (
            bucket_ended
            and has_four_bars
            and offsets_match
            and all_bars_closed
        )

        open_val = b_bars[0].open
        high_val = max(b.high for b in b_bars)
        low_val = min(b.low for b in b_bars)
        close_val = b_bars[-1].close
        volume_val = sum(b.volume for b in b_bars)

        aggregated.append(
            CryptoCandle(
                instrument_name=instrument_name,
                timeframe="4h",
                timestamp=b_start,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val,
                is_closed=is_closed,
            )
        )

    return aggregated


class CryptoMarketDataService:
    """
    High-level crypto market data service providing tiered in-memory TTL caching,
    cache stampede protection, 4H UTC candle aggregation, and options chain organization.
    """

    QUOTE_TTL = 10.0
    CHAIN_TTL = 15.0
    CANDLE_TTL = 60.0
    METADATA_TTL = 60.0

    SUPPORTED_ASSETS = ("BTC", "ETH")
    SUPPORTED_TIMEFRAMES = ("1h", "4h", "1d")

    def __init__(
        self,
        adapter: MarketDataAdapter,
        cache: AsyncTTLMemoryCache | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self.adapter = adapter
        self.cache = cache or AsyncTTLMemoryCache()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def clear_cache(self) -> None:
        """Purge all in-memory cache entries."""
        self.cache.clear()

    def _validate_underlying(self, underlying: str) -> str:
        asset = underlying.strip().upper()
        if asset not in self.SUPPORTED_ASSETS:
            raise UnsupportedAssetError(
                f"Unsupported asset '{underlying}'. TradePilot only supports {list(self.SUPPORTED_ASSETS)}."
            )
        return asset

    def _validate_timeframe(self, timeframe: str) -> str:
        tf = timeframe.strip().lower()
        if tf not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. Allowed timeframes: {list(self.SUPPORTED_TIMEFRAMES)}."
            )
        return tf

    async def get_index_quote(self, underlying: str) -> CryptoQuote:
        """
        Retrieves real-time index reference quote with 10s TTL caching.
        """
        asset = self._validate_underlying(underlying)
        cache_key = f"quote:{asset}"

        return await self.cache.get_or_set(
            cache_key,
            self.QUOTE_TTL,
            lambda: self.adapter.get_index_price(asset),
        )

    async def get_candles(
        self,
        underlying: str,
        timeframe: str = "1d",
        period: str = "30d",
    ) -> list[CryptoCandle]:
        """
        Retrieves traded perpetual candles (BTC-PERPETUAL / ETH-PERPETUAL) with 60s TTL caching.
        For 4H timeframe, retrieves 1H candles and aggregates them into UTC-aligned 4H buckets.
        """
        asset = self._validate_underlying(underlying)
        tf = self._validate_timeframe(timeframe)
        instrument = f"{asset}-PERPETUAL"

        delta = _parse_period_to_timedelta(period)
        now = self.clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)

        start_dt = now - delta
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(now.timestamp() * 1000)

        cache_key = f"candles:{instrument}:{tf}:{period}"

        async def _fetch() -> list[CryptoCandle]:
            if tf == "4h":
                # Deribit does not support 4h natively: fetch 1h and aggregate internally
                hourly_candles = await self.adapter.get_instrument_candles(
                    instrument_name=instrument,
                    resolution="60",
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                return aggregate_1h_to_4h_candles(instrument, hourly_candles, now_utc=now)
            elif tf == "1h":
                return await self.adapter.get_instrument_candles(
                    instrument_name=instrument,
                    resolution="60",
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
            else:  # "1d"
                return await self.adapter.get_instrument_candles(
                    instrument_name=instrument,
                    resolution="1D",
                    start_ts=start_ts,
                    end_ts=end_ts,
                )

        return await self.cache.get_or_set(cache_key, self.CANDLE_TTL, _fetch)

    async def get_option_expiries(self, underlying: str) -> list[str]:
        """
        Retrieves sorted list of active options expiration dates formatted as YYYY-MM-DD.
        Cached with 60s minimum TTL.
        """
        asset = self._validate_underlying(underlying)
        cache_key = f"expiries:{asset}"

        async def _fetch() -> list[str]:
            active_instruments = await self.adapter.get_active_instruments(asset)
            expiry_set: set[str] = set()

            for inst in active_instruments:
                exp_ts = inst.get("expiration_timestamp")
                if exp_ts:
                    exp_date = datetime.fromtimestamp(
                        exp_ts / 1000.0, tz=timezone.utc
                    ).date()
                    expiry_set.add(exp_date.isoformat())

            return sorted(expiry_set)

        return await self.cache.get_or_set(cache_key, self.METADATA_TTL, _fetch)

    async def get_options_chain(
        self,
        underlying: str,
        expiry: date | str | None = None,
    ) -> OptionChainResponse:
        """
        Retrieves joined active options chain partitioned into calls and puts.
        Cached with 15s TTL.
        """
        asset = self._validate_underlying(underlying)

        target_date: date | None = None
        if isinstance(expiry, str) and expiry.strip():
            try:
                target_date = date.fromisoformat(expiry.strip())
            except ValueError as exc:
                raise ValueError(
                    f"Invalid expiry date format '{expiry}'. Expected YYYY-MM-DD."
                ) from exc
        elif isinstance(expiry, date):
            target_date = expiry

        expiry_key = target_date.isoformat() if target_date else "all"
        cache_key = f"chain:{asset}:{expiry_key}"

        async def _fetch() -> OptionChainResponse:
            # Concurrently fetch contracts and index quote
            contracts, quote = await asyncio.gather(
                self.adapter.get_options_chain(asset, expiry_date=target_date),
                self.get_index_quote(asset),
            )

            calls = [c for c in contracts if c.option_type == "CALL"]
            puts = [c for c in contracts if c.option_type == "PUT"]

            calls.sort(key=lambda c: c.strike)
            puts.sort(key=lambda c: c.strike)

            effective_date = target_date or (contracts[0].expiry_date if contracts else date.today())

            return OptionChainResponse(
                underlying=asset,
                expiry_date=effective_date,
                underlying_index_price=quote.index_price,
                calls=calls,
                puts=puts,
                total_contracts=len(contracts),
            )

        return await self.cache.get_or_set(cache_key, self.CHAIN_TTL, _fetch)

