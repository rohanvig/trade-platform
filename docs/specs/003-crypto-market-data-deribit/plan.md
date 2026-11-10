# Technical Architecture & Implementation Plan: Crypto Market Data & Public Deribit Adapter

**Document**: PLAN-003  
**Feature**: SPEC-003  
**Status**: REVISED ARCHITECTURE PLAN (Pending Review)  
**Author**: Senior Software Architect  
**Updated Date**: 2026-11-10  

---

## 1. System Architecture & Component Interactions

```text
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Controllers Layer                   │
│         (backend/app/api/v1/endpoints/crypto_market.py)     │
│  GET /quote, GET /history, GET /options/expiries, /chain    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               CryptoMarketDataService Layer                 │
│             (backend/app/services/crypto_market.py)         │
│  - Multi-tier TTL Cache (60s metadata, 15s chain, 10s quote)│
│  - Async Stampede Lock (asyncio.Lock per cache key)         │
│  - 4-Hour UTC-Aligned Candle Aggregator                     │
│  - Contract currency conversion (Coin to USD)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               MarketDataAdapter Protocol (Async)            │
│               (backend/app/adapters/base.py)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 DeribitMarketDataAdapter                   │
│              (backend/app/adapters/deribit.py)              │
│  - httpx.AsyncClient with Application Lifespan Management   │
│  - Endpoint-Aware Rate Limiter & Bounded Backoff with Jitter│
│  - String-based Decimal conversion [Decimal(str(x))]        │
│  - Exact instrument_name join & nullable bid/ask handling   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Domain Models & Schemas (`backend/app/schemas/crypto_market.py`)

All models enforce strict `Decimal` parsing and ISO 8601 UTC timestamp serialization.

### 2.1 Index vs. Tradable Instrument Representations
```python
class CryptoQuote(BaseModel):
    """Reference spot index observation (NOT a tradable candle)."""
    underlying: str                   # "BTC" or "ETH"
    index_name: str                   # "btc_usd" or "eth_usd"
    index_price: Decimal              # Reference price in USD
    estimated_delivery_price: Decimal | None = None
    is_index: bool = True
    timestamp: datetime               # UTC timestamp
```

```python
class CryptoCandle(BaseModel):
    """Actual traded instrument OHLCV bar (e.g. BTC-PERPETUAL)."""
    instrument_name: str              # "BTC-PERPETUAL" or "ETH-PERPETUAL"
    timeframe: str                    # "1d", "4h", "1h"
    timestamp: datetime               # UTC bucket start timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal                   # Base asset traded volume
    is_closed: bool = True            # False if bucket is still actively forming
```

### 2.2 Options Chain & Contract Models
```python
class OptionContractSummary(BaseModel):
    """Joined active option contract with market depth metrics."""
    instrument_name: str              # e.g. "BTC-27DEC26-100000-C"
    underlying: str                   # "BTC" or "ETH"
    strike: Decimal                   # Option strike in USD
    option_type: str                  # "CALL" or "PUT"
    expiry_date: date                 # Expiration date
    expiration_timestamp: int         # Milliseconds UTC
    contract_size: Decimal            # Typically 1.0
    settlement_currency: str          # "BTC", "ETH", or "USDC"
    quote_currency: str               # "BTC", "ETH", or "USDC"
    
    # Pricing metrics (Nullable for illiquid / deep OTM strikes)
    mark_price_raw: Decimal | None    # Quoted in exchange denomination
    mark_price_usd: Decimal | None    # Converted to USD
    mark_iv: Decimal | None           # Annualized Implied Volatility %
    bid_price_raw: Decimal | None = None
    ask_price_raw: Decimal | None = None
    bid_price_usd: Decimal | None = None
    ask_price_usd: Decimal | None = None
    
    # Liquidity & Freshness
    open_interest: Decimal = Decimal("0")
    is_oi_delayed: bool = True        # Deribit 8-hour refresh indicator
    volume_usd: Decimal = Decimal("0")
```

```python
class OptionChainResponse(BaseModel):
    """Complete strike ladder response partitioned by contract type."""
    underlying: str
    expiry_date: date
    underlying_index_price: Decimal
    calls: list[OptionContractSummary]
    puts: list[OptionContractSummary]
    total_contracts: int
```

---

## 3. Core Algorithms & Operational Rules

### 3.1 4-Hour UTC Candle Aggregator
Deribit does not support a native 4H (`"240"`) resolution. The aggregation engine implements the following logic:
1. Fetch 1-hour (`"60"`) candles for `BTC-PERPETUAL` or `ETH-PERPETUAL`.
2. Bucket candles by floor timestamp:
   $$\text{bucket\_start} = \text{timestamp} - (\text{timestamp.hour} \pmod 4) \times 1\text{h}$$
3. For each complete 4-hour window ($N=4$ hours):
   $$\text{Open} = \text{bars}[0].\text{open}$$
   $$\text{High} = \max(\text{bar}.\text{high} \text{ for bar in bars})$$
   $$\text{Low} = \min(\text{bar}.\text{low} \text{ for bar in bars})$$
   $$\text{Close} = \text{bars}[-1].\text{close}$$
   $$\text{Volume} = \sum(\text{bar}.\text{volume} \text{ for bar in bars})$$
   $$\text{is\_closed} = \text{True}$$
4. For an in-flight window ($N < 4$ hours):
   * Mark with `is_closed = False`. Exclude from technical indicator calculations by default.

### 3.2 Join Strategy: Metadata + Book Summary
1. Retrieve `public/get_instruments?currency={BTC|ETH}&kind=option&expired=false`.
2. Filter strictly by `is_active=True` and `state="open"`.
3. Store in an in-memory dictionary keyed by `instrument_name`.
4. Retrieve `public/get_book_summary_by_currency?currency={BTC|ETH}&kind=option`.
5. For each book summary record:
   * Look up instrument in the metadata cache by `instrument_name`.
   * If metadata is missing or instrument is expired/inactive, skip.
   * Parse numeric values via string representation (`Decimal(str(val))`).
   * Preserve raw exchange denomination (`mark_price_raw`).
   * Calculate `mark_price_usd = mark_price_raw * index_price` for coin-margined options.
   * If `bid_price` or `ask_price` is missing, assign `None`.
6. Partition into `calls` and `puts` arrays, sorted by `strike` ascending.

### 3.3 Cache Architecture & Stampede Protection
```python
class AsyncTTLMemoryCache:
    """Thread-safe and async-safe in-memory cache with stampede protection."""
    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_set(self, key: str, ttl_seconds: float, fetcher: Callable[[], Awaitable[T]]) -> T:
        now = time.monotonic()
        if key in self._store:
            cached_at, value = self._store[key]
            if now - cached_at < ttl_seconds:
                return value

        # Acquire per-key lock to prevent cache stampede
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double check after lock acquisition
            if key in self._store:
                cached_at, value = self._store[key]
                if time.monotonic() - cached_at < ttl_seconds:
                    return value

            value = await fetcher()
            self._store[key] = (time.monotonic(), value)
            return value
```

### 3.4 Rate Limit, Timeout & Backoff Handling
* Client configuration:
  * `httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))`
* Retry strategy on HTTP 429 (Rate Limit) or HTTP 503 (Overloaded):
  * Attempt up to 3 retries.
  * Backoff interval:
    $$\Delta t = \min(2.0, 0.25 \times 2^{\text{attempt}} + \text{random.uniform}(0, 0.1))$$
  * If retries are exhausted, raise `DeribitRateLimitError("Rate limit exceeded on Deribit API")`.

---

## 4. API Endpoints & Contracts

Mounted under `/api/v1/crypto` in [`backend/app/api/router.py`](file:///e:/portfolio/agentic-ai-project/backend/app/api/router.py):

### 1. `GET /api/v1/crypto/quote?underlying=BTC`
* Returns `CryptoQuote` (HTTP 200).
* Query validation: `underlying` must be `BTC` or `ETH` (case-insensitive).

### 2. `GET /api/v1/crypto/history?underlying=BTC&timeframe=1d&period=30d`
* Returns `list[CryptoCandle]` (HTTP 200).
* `timeframe` allowed values: `"1d"`, `"4h"`, `"1h"`.
* Includes `is_closed` boolean indicator on all bars.

### 3. `GET /api/v1/crypto/options/expiries?underlying=BTC`
* Returns `list[str]` of active expiry dates formatted as `YYYY-MM-DD` (HTTP 200).

### 4. `GET /api/v1/crypto/options/chain?underlying=BTC&expiry=YYYY-MM-DD`
* Returns `OptionChainResponse` (HTTP 200).
* If no contracts exist for the given date, returns empty arrays with `total_contracts=0` (HTTP 200).

### Standard Error Contract
All endpoints adhere to a uniform error schema:
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED | INVALID_ASSET | UPSTREAM_TIMEOUT | NOT_FOUND",
  "message": "Human readable explanation",
  "timestamp": "2026-11-10T18:00:00Z"
}
```

---

## 5. Directory Layout & Module Plan

```text
backend/app/
├── adapters/
│   ├── __init__.py
│   ├── base.py                 # Abstract MarketDataAdapter Protocol (async)
│   ├── deribit.py              # DeribitMarketDataAdapter with httpx.AsyncClient
│   └── exceptions.py           # DeribitRateLimitError, DeribitTimeoutError, etc.
├── schemas/
│   └── crypto_market.py        # Pydantic schemas (CryptoQuote, CryptoCandle, OptionChainResponse)
├── services/
│   └── crypto_market.py        # CryptoMarketDataService (caching, 4H aggregation, USD conversions)
├── api/v1/endpoints/
│   └── crypto_market.py        # FastAPI controllers for /api/v1/crypto/...
└── api/router.py               # Mount crypto_market router
backend/tests/
├── fixtures/
│   └── deribit_samples.py      # Recorded synthetic Deribit JSON responses for offline tests
└── test_crypto_market.py       # Comprehensive offline unit & integration test suite
```

---

## 6. Testing Strategy & Offline Verification

1. **`httpx.MockTransport` Fixture**:
   * Uses recorded responses in `tests/fixtures/deribit_samples.py` to intercept HTTP requests.
   * Simulates successful queries, HTTP 429 rate limits, HTTP 504 timeouts, and malformed JSON.
   * Completely isolated: **zero network sockets opened during tests**.
2. **Acceptance Test Matrix**:
   * Test 4H aggregation math and `is_closed=False` incomplete bucket handling.
   * Test active instrument filtering (`state="open"` only).
   * Test nullable quotes (null bid/ask preserved in strike list).
   * Test open interest freshness flag (`is_oi_delayed=True`).
   * Test `Decimal(str(x))` string parsing without float drift.
   * Test timeout and exponential backoff retry mechanics.
   * Test empty chain response (`HTTP 200` with empty arrays).
   * Test regression invariance: **all 56 existing tests remain passing**.
