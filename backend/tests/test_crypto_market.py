import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient
import httpx
import pytest

from app.adapters.deribit import DeribitMarketDataAdapter
from app.adapters.exceptions import (
    DeribitDataError,
    DeribitRateLimitError,
    DeribitTimeoutError,
    UnsupportedAssetError,
)
from app.api.dependencies import get_crypto_service
from app.main import app
from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoQuote,
    OptionChainResponse,
)
from app.services.crypto_market import (
    AsyncTTLMemoryCache,
    CryptoMarketDataService,
    aggregate_1h_to_4h_candles,
)
from tests.fixtures.deribit_samples import (
    BTC_BOOK_SUMMARY_PAYLOAD,
    BTC_INDEX_PAYLOAD,
    BTC_INSTRUMENTS_PAYLOAD,
    CHART_DATA_1D_PAYLOAD,
    CHART_DATA_1H_PAYLOAD,
    ETH_BOOK_SUMMARY_PAYLOAD,
    ETH_INDEX_PAYLOAD,
    ETH_INSTRUMENTS_PAYLOAD,
)


def create_mock_transport_handler():
    """Returns a handler routing requests to deterministic sample payloads."""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)

        if "get_index_price" in url:
            if "index_name=btc_usd" in url:
                return httpx.Response(200, json=BTC_INDEX_PAYLOAD)
            elif "index_name=eth_usd" in url:
                return httpx.Response(200, json=ETH_INDEX_PAYLOAD)
            return httpx.Response(400, json={"error": "invalid index"})

        elif "get_tradingview_chart_data" in url:
            if "resolution=1D" in url:
                return httpx.Response(200, json=CHART_DATA_1D_PAYLOAD)
            return httpx.Response(200, json=CHART_DATA_1H_PAYLOAD)

        elif "get_instruments" in url:
            if "currency=BTC" in url:
                return httpx.Response(200, json=BTC_INSTRUMENTS_PAYLOAD)
            elif "currency=ETH" in url:
                return httpx.Response(200, json=ETH_INSTRUMENTS_PAYLOAD)
            return httpx.Response(400, json={"error": "unsupported currency"})

        elif "get_book_summary_by_currency" in url:
            if "currency=BTC" in url:
                return httpx.Response(200, json=BTC_BOOK_SUMMARY_PAYLOAD)
            elif "currency=ETH" in url:
                return httpx.Response(200, json=ETH_BOOK_SUMMARY_PAYLOAD)
            return httpx.Response(400, json={"error": "unsupported currency"})

        return httpx.Response(404, json={"error": "not found"})

    return handler


@pytest.fixture
def mock_crypto_service():
    """Provides a CryptoMarketDataService wired to a deterministic MockTransport and fixed clock."""
    transport = httpx.MockTransport(create_mock_transport_handler())
    client = httpx.AsyncClient(transport=transport)
    adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
    fixed_now = datetime(2026, 11, 2, 0, 0, 0, tzinfo=timezone.utc)
    service = CryptoMarketDataService(
        adapter=adapter,
        clock=lambda: fixed_now,
    )
    yield service
    asyncio.run(client.aclose())


# ==============================================================================
# 1. UNIT TESTS: CryptoMarketDataService & Cache Correctness Audit
# ==============================================================================

@pytest.mark.anyio
async def test_service_quote_retrieval_and_cache_ttl(mock_crypto_service: CryptoMarketDataService):
    """Verify quote retrieval and that subsequent call within TTL returns cached instance."""
    quote1 = await mock_crypto_service.get_index_quote("BTC")
    assert quote1.underlying == "BTC"
    assert quote1.index_price == Decimal("68435.12")
    assert quote1.is_index is True

    # Call again - cache should return same instance
    quote2 = await mock_crypto_service.get_index_quote("BTC")
    assert quote1 is quote2


@pytest.mark.anyio
async def test_cache_monotonic_expiration():
    """Verify cache uses monotonic time and expires after TTL."""
    cache = AsyncTTLMemoryCache()
    cache.set("key1", "val1", ttl=0.05)
    assert cache.get("key1") == "val1"
    await asyncio.sleep(0.06)
    assert cache.get("key1") is None


@pytest.mark.anyio
async def test_cache_failed_fetches_not_cached():
    """Verify failed upstream fetches are NEVER cached as valid responses."""
    cache = AsyncTTLMemoryCache()
    attempts = 0

    async def flaky_fetcher():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise DeribitRateLimitError("Temporary upstream 429")
        return "success_val"

    # First attempt fails
    with pytest.raises(DeribitRateLimitError):
        await cache.get_or_set("flaky_key", ttl_seconds=10.0, fetcher=flaky_fetcher)

    # Failed result must NOT be cached
    assert cache.get("flaky_key") is None

    # Subsequent attempt retries and succeeds
    val = await cache.get_or_set("flaky_key", ttl_seconds=10.0, fetcher=flaky_fetcher)
    assert val == "success_val"
    assert cache.get("flaky_key") == "success_val"


@pytest.mark.anyio
async def test_cache_concurrent_same_key_single_fetch():
    """Verify concurrent callers for the same key trigger exactly ONE fetch."""
    call_count = 0

    class CountingAdapter:
        async def get_index_price(self, underlying: str):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate network latency
            return CryptoQuote(
                underlying=underlying,
                index_name="btc_usd",
                index_price=Decimal("68435.12"),
                is_index=True,
                timestamp=datetime.now(timezone.utc),
            )

    service = CryptoMarketDataService(adapter=CountingAdapter())

    # Launch 5 concurrent calls on cold cache
    quotes = await asyncio.gather(*[service.get_index_quote("BTC") for _ in range(5)])
    assert len(quotes) == 5
    assert all(q.index_price == Decimal("68435.12") for q in quotes)
    # The adapter was invoked exactly ONCE thanks to stampede lock
    assert call_count == 1


@pytest.mark.anyio
async def test_cache_concurrent_different_keys_parallel_fetch():
    """Verify different keys fetch concurrently without mutual blocking."""
    order: list[str] = []

    async def fetch_a():
        await asyncio.sleep(0.02)
        order.append("A")
        return "valA"

    async def fetch_b():
        await asyncio.sleep(0.01)
        order.append("B")
        return "valB"

    cache = AsyncTTLMemoryCache()
    res = await asyncio.gather(
        cache.get_or_set("keyA", ttl_seconds=10.0, fetcher=fetch_a),
        cache.get_or_set("keyB", ttl_seconds=10.0, fetcher=fetch_b),
    )
    assert res == ["valA", "valB"]
    # B finished before A because they executed in parallel without lock contention
    assert order == ["B", "A"]


def test_cache_lock_lifecycle_bounded_growth():
    """Verify lock collection is pruned when exceeding capacity, preventing unbounded growth."""
    cache = AsyncTTLMemoryCache()
    # Populate with 300 unique keys
    for i in range(300):
        cache.set(f"key_{i}", f"val_{i}", ttl=60.0)
        cache._locks[f"key_{i}"] = asyncio.Lock()

    assert len(cache._locks) == 300
    cache._prune_locks()
    # Unlocked locks pruned to within MAX_LOCKS
    assert len(cache._locks) <= cache.MAX_LOCKS


# ==============================================================================
# 2. 4-HOUR CANDLE AGGREGATION & CLOSURE SEMANTICS AUDIT
# ==============================================================================

def test_4h_aggregation_perfect_continuous_buckets():
    """
    Audit 1: Four continuous, closed hourly candles in a completed bucket (b_end <= now_utc) -> is_closed=True.
    """
    base_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=base_dt + timedelta(hours=i),
            open=Decimal(str(68000 + (i * 10))),
            high=Decimal(str(68000 + (i * 10) + 20)),
            low=Decimal(str(68000 + (i * 10) - 10)),
            close=Decimal(str(68000 + (i * 10) + 5)),
            volume=Decimal("100.0"),
            is_closed=True,
        )
        for i in range(12)
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=now_utc)
    assert len(candles_4h) == 3

    # Bucket 1: 00:00 to 04:00 (Hours 0, 1, 2, 3)
    b1 = candles_4h[0]
    assert b1.timestamp == datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert b1.open == bars_1h[0].open
    assert b1.close == bars_1h[3].close
    assert b1.high == max(b.high for b in bars_1h[0:4])
    assert b1.low == min(b.low for b in bars_1h[0:4])
    assert b1.volume == Decimal("400.0")
    assert b1.is_closed is True

    # Bucket 2: 04:00 to 08:00 (Hours 4, 5, 6, 7)
    b2 = candles_4h[1]
    assert b2.timestamp == datetime(2026, 11, 1, 4, 0, 0, tzinfo=timezone.utc)
    assert b2.is_closed is True

    # Bucket 3: 08:00 to 12:00 (Hours 8, 9, 10, 11)
    b3 = candles_4h[2]
    assert b3.timestamp == datetime(2026, 11, 1, 8, 0, 0, tzinfo=timezone.utc)
    assert b3.is_closed is True


def test_4h_aggregation_source_candle_still_open():
    """
    Audit 2: Four continuous candles where one source hourly candle is still open (is_closed=False) -> is_closed=False.
    """
    base_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 11, 1, 5, 0, 0, tzinfo=timezone.utc)
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=base_dt + timedelta(hours=i),
            open=Decimal("68000"),
            high=Decimal("68100"),
            low=Decimal("67900"),
            close=Decimal("68050"),
            volume=Decimal("100"),
            is_closed=(i != 3),  # The 4th hour is still actively forming
        )
        for i in range(4)
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=now_utc)
    assert len(candles_4h) == 1
    # Even though bucket ended and 4 bars exist, one source bar was open -> 4H bar is NOT closed
    assert candles_4h[0].is_closed is False


def test_4h_aggregation_currently_forming_bucket():
    """
    Audit 3: Four continuous candles in currently forming bucket (bucket end > now_utc) -> is_closed=False.
    """
    base_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    # Current time is 03:45 UTC, while bucket ends at 04:00 UTC
    now_utc = datetime(2026, 11, 1, 3, 45, 0, tzinfo=timezone.utc)
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=base_dt + timedelta(hours=i),
            open=Decimal("68000"),
            high=Decimal("68100"),
            low=Decimal("67900"),
            close=Decimal("68050"),
            volume=Decimal("100"),
            is_closed=True,
        )
        for i in range(4)
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=now_utc)
    assert len(candles_4h) == 1
    # Bucket end (04:00) is in the future relative to now_utc (03:45) -> is_closed=False
    assert candles_4h[0].is_closed is False


def test_4h_aggregation_missing_hourly_interval():
    """
    Audit 4: 4H bucket with missing intermediate hour (e.g. hours 0, 1, 3 with hour 2 missing) -> is_closed=False.
    """
    base_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 11, 1, 5, 0, 0, tzinfo=timezone.utc)
    # Intentionally omit hour 2
    hours = [0, 1, 3]
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=base_dt + timedelta(hours=h),
            open=Decimal("68000"),
            high=Decimal("68100"),
            low=Decimal("67900"),
            close=Decimal("68050"),
            volume=Decimal("100"),
            is_closed=True,
        )
        for h in hours
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=now_utc)
    assert len(candles_4h) == 1
    assert candles_4h[0].is_closed is False


def test_4h_aggregation_completed_historical_bucket():
    """
    Audit 5: Completed historical bucket from previous day -> is_closed=True.
    """
    yesterday_dt = datetime(2026, 10, 31, 8, 0, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=yesterday_dt + timedelta(hours=i),
            open=Decimal("67000"),
            high=Decimal("67500"),
            low=Decimal("66800"),
            close=Decimal("67200"),
            volume=Decimal("200"),
            is_closed=True,
        )
        for i in range(4)
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=now_utc)
    assert len(candles_4h) == 1
    assert candles_4h[0].timestamp == yesterday_dt
    assert candles_4h[0].is_closed is True


def test_4h_aggregation_utc_boundary_transition():
    """
    Audit 6: UTC boundary transitions across midnight (20:00 to 00:00 of next day).
    Bucket: 20:00, 21:00, 22:00, 23:00 UTC.
    Bucket end is 00:00:00 of next day.
    """
    start_dt = datetime(2026, 11, 1, 20, 0, 0, tzinfo=timezone.utc)
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=start_dt + timedelta(hours=i),
            open=Decimal("68000"),
            high=Decimal("68500"),
            low=Decimal("67800"),
            close=Decimal("68200"),
            volume=Decimal("150"),
            is_closed=True,
        )
        for i in range(4)
    ]

    # Subcase A: Current time is 23:55 UTC (before midnight) -> is_closed=False
    before_midnight = datetime(2026, 11, 1, 23, 55, 0, tzinfo=timezone.utc)
    res_before = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=before_midnight)
    assert len(res_before) == 1
    assert res_before[0].is_closed is False

    # Subcase B: Current time is 00:05 UTC next day -> is_closed=True
    after_midnight = datetime(2026, 11, 2, 0, 5, 0, tzinfo=timezone.utc)
    res_after = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h, now_utc=after_midnight)
    assert len(res_after) == 1
    assert res_after[0].is_closed is True
    assert res_after[0].timestamp == start_dt


def test_4h_aggregation_partial_in_flight_bucket():
    """
    AC-003: An actively forming 4H bucket with only 2 completed hours is flagged is_closed=False.
    """
    base_dt = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    # Only hours 0 and 1
    bars_1h = [
        CryptoCandle(
            instrument_name="BTC-PERPETUAL",
            timeframe="1h",
            timestamp=base_dt + timedelta(hours=h),
            open=Decimal("68000"),
            high=Decimal("68100"),
            low=Decimal("67900"),
            close=Decimal("68050"),
            volume=Decimal("100"),
            is_closed=True,
        )
        for h in [0, 1]
    ]

    candles_4h = aggregate_1h_to_4h_candles("BTC-PERPETUAL", bars_1h)
    assert len(candles_4h) == 1
    assert candles_4h[0].is_closed is False


# ==============================================================================
# 3. FASTAPI ENDPOINT INTEGRATION TESTS (TSK-034)
# ==============================================================================

@pytest.fixture
def crypto_client(mock_crypto_service: CryptoMarketDataService, db_session, mock_market):
    """Overrides crypto service dependency and yields TestClient."""
    app.dependency_overrides[get_crypto_service] = lambda: mock_crypto_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_crypto_service, None)


def test_api_crypto_quote_btc(crypto_client: TestClient):
    """Verify GET /api/v1/crypto/quote?underlying=BTC returns valid CryptoQuote."""
    response = crypto_client.get("/api/v1/crypto/quote?underlying=BTC")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["underlying"] == "BTC"
    assert data["index_name"] == "btc_usd"
    assert data["is_index"] is True
    assert float(data["index_price"]) == 68435.12


def test_api_crypto_quote_eth(crypto_client: TestClient):
    """Verify GET /api/v1/crypto/quote?underlying=ETH returns valid CryptoQuote."""
    response = crypto_client.get("/api/v1/crypto/quote?underlying=ETH")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["underlying"] == "ETH"
    assert data["index_name"] == "eth_usd"
    assert float(data["index_price"]) == 3520.75


def test_api_crypto_quote_unsupported_asset(crypto_client: TestClient):
    """Verify querying an unsupported asset returns HTTP 400 with standardized error schema."""
    response = crypto_client.get("/api/v1/crypto/quote?underlying=SOL")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    err = response.json()
    assert "detail" in err
    detail = err["detail"]
    assert detail["error_code"] == "UNSUPPORTED_ASSET"
    assert "Unsupported asset 'SOL'" in detail["message"]


def test_api_crypto_history_4h_aggregated(crypto_client: TestClient):
    """Verify GET /api/v1/crypto/history?underlying=BTC&timeframe=4h returns 4H candles."""
    response = crypto_client.get("/api/v1/crypto/history?underlying=BTC&timeframe=4h&period=7d")
    assert response.status_code == status.HTTP_200_OK
    candles = response.json()
    assert isinstance(candles, list)
    assert len(candles) > 0
    c0 = candles[0]
    assert c0["instrument_name"] == "BTC-PERPETUAL"
    assert c0["timeframe"] == "4h"
    assert "open" in c0
    assert "close" in c0
    assert "is_closed" in c0


def test_api_crypto_history_invalid_timeframe(crypto_client: TestClient):
    """Verify unsupported timeframe returns HTTP 400."""
    response = crypto_client.get("/api/v1/crypto/history?underlying=BTC&timeframe=5m")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    err = response.json()["detail"]
    assert err["error_code"] == "INVALID_PARAMETER"


def test_api_crypto_options_expiries(crypto_client: TestClient):
    """Verify GET /api/v1/crypto/options/expiries?underlying=BTC returns sorted date strings."""
    response = crypto_client.get("/api/v1/crypto/options/expiries?underlying=BTC")
    assert response.status_code == status.HTTP_200_OK
    expiries = response.json()
    assert isinstance(expiries, list)
    assert "2026-12-25" in expiries
    assert "2027-01-29" in expiries
    assert expiries == sorted(expiries)


def test_api_crypto_options_chain_success(crypto_client: TestClient):
    """Verify GET /api/v1/crypto/options/chain?underlying=BTC&expiry=2026-12-25 returns complete chain."""
    response = crypto_client.get("/api/v1/crypto/options/chain?underlying=BTC&expiry=2026-12-25")
    assert response.status_code == status.HTTP_200_OK
    chain = response.json()
    assert chain["underlying"] == "BTC"
    assert chain["expiry_date"] == "2026-12-25"
    assert float(chain["underlying_index_price"]) == 68435.12
    assert "calls" in chain
    assert "puts" in chain
    assert chain["total_contracts"] == len(chain["calls"]) + len(chain["puts"])

    # Verify call contracts
    call = next(c for c in chain["calls"] if c["strike"] == "100000.0")
    assert call["option_type"] == "CALL"
    assert call["settlement_currency"] == "BTC"
    assert call["is_oi_delayed"] is True

    # Verify illiquid strike retains None
    illiquid_call = next(c for c in chain["calls"] if c["strike"] == "120000.0")
    assert illiquid_call["bid_price_raw"] is None
    assert illiquid_call["ask_price_raw"] is None


def test_api_crypto_options_chain_invalid_date_format(crypto_client: TestClient):
    """Verify malformed date query returns HTTP 400."""
    response = crypto_client.get("/api/v1/crypto/options/chain?underlying=BTC&expiry=not-a-date")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    err = response.json()["detail"]
    assert err["error_code"] == "INVALID_PARAMETER"


def test_api_crypto_options_chain_empty_expiry(crypto_client: TestClient):
    """Verify querying an expiry date with no contracts returns 200 with empty arrays."""
    response = crypto_client.get("/api/v1/crypto/options/chain?underlying=BTC&expiry=2030-01-01")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_contracts"] == 0
    assert data["calls"] == []
    assert data["puts"] == []


# ==============================================================================
# 4. ERROR MAPPING & LIFESPAN CLEANUP TESTS
# ==============================================================================

def test_api_crypto_rate_limit_error_mapping(crypto_client: TestClient, mock_crypto_service: CryptoMarketDataService):
    """Verify upstream DeribitRateLimitError maps to HTTP 429."""
    with patch.object(mock_crypto_service.adapter, "get_index_price", side_effect=DeribitRateLimitError("Rate limit")):
        response = crypto_client.get("/api/v1/crypto/quote?underlying=BTC")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.json()["detail"]["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_api_crypto_timeout_error_mapping(crypto_client: TestClient, mock_crypto_service: CryptoMarketDataService):
    """Verify upstream DeribitTimeoutError maps to HTTP 504."""
    with patch.object(mock_crypto_service.adapter, "get_index_price", side_effect=DeribitTimeoutError("Timed out")):
        response = crypto_client.get("/api/v1/crypto/quote?underlying=BTC")
        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert response.json()["detail"]["error_code"] == "UPSTREAM_TIMEOUT"


def test_api_crypto_data_error_mapping(crypto_client: TestClient, mock_crypto_service: CryptoMarketDataService):
    """Verify upstream DeribitDataError maps to HTTP 502."""
    with patch.object(mock_crypto_service.adapter, "get_index_price", side_effect=DeribitDataError("Bad JSON")):
        response = crypto_client.get("/api/v1/crypto/quote?underlying=BTC")
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json()["detail"]["error_code"] == "UPSTREAM_PROVIDER_ERROR"


def test_app_lifespan_manages_single_client():
    """Verify that FastAPI lifespan creates a single httpx.AsyncClient and closes it on shutdown."""
    with TestClient(app) as test_client:
        assert hasattr(app.state, "http_client")
        client = app.state.http_client
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

    # On shutdown, the client is closed
    assert client.is_closed

