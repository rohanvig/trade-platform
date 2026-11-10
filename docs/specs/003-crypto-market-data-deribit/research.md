# Technical Research: Deribit Public API v2 Integration & Market Data Ingestion

**Feature**: SPEC-003 (Crypto Market Data & Public Deribit Adapter)  
**Status**: REVISED RESEARCH BASELINE  
**Author**: Senior Software Architect  
**Audited Date**: 2026-11-10  

---

## 1. Deribit API v2 Architecture & Endpoints

Deribit provides an institutional-grade JSON-RPC / REST API v2. For Phase 1, all required market data is available through **unauthenticated public REST endpoints**:
* **Base URL (Production)**: `https://www.deribit.com/api/v2/public/`
* **Base URL (Testnet)**: `https://test.deribit.com/api/v2/public/`

---

## 2. Key Endpoint Specifications & Technical Realities

### 2.1 Index Price vs. Instrument Trade Candlesticks
A critical distinction must be maintained between **index-price observations** and **instrument OHLCV candles**:
* **Index Price (`public/get_index_price?index_name=btc_usd`)**:
  * Represents an external spot reference index aggregated by Deribit across multiple major spot exchanges (Coinbase, Bitstamp, Gemini, Kraken, Binance, LMAX).
  * It is a continuous benchmark price, **not an executable orderbook or tradable instrument**. It does not possess trade volume or bid/ask spread history. It must never be represented as genuine tradable OHLCV candles.
* **Tradable Instrument Candles (`public/get_tradingview_chart_data`)**:
  * Traded perpetual contracts—specifically **`BTC-PERPETUAL`** and **`ETH-PERPETUAL`**—represent actual traded derivative volume, market depth, and execution levels.
  * These instruments serve as the definitive high-liquidity source for technical indicator analysis (1D, 4H, 1H) for crypto swing trading.

### 2.2 Resolution Limitations & 4H Candle Aggregation
* **Deribit Native Resolutions**: Deribit supports `"1"`, `"3"`, `"5"`, `"10"`, `"15"`, `"30"`, `"60"` (1H), `"120"`, `"180"`, `"360"`, `"720"`, and `"1D"`.
* **The "240" (4-Hour) Reality**: Deribit does **not** natively support a 240-minute (`4H`) resolution.
* **Architecture Solution**:
  * The adapter fetches 1-Hour (`"60"`) OHLCV bars.
  * An in-memory aggregation engine groups 1H bars into strictly UTC-aligned 4-Hour buckets:
    $$\text{Buckets} \in \{[00:00, 04:00), [04:00, 08:00), [08:00, 12:00), [12:00, 16:00), [16:00, 20:00), [20:00, 24:00)\}$$
  * **Aggregation Formula**:
    $$\text{Open} = \text{Open}_{\text{first bar}}$$
    $$\text{High} = \max(\text{High}_{\text{bars}})$$
    $$\text{Low} = \min(\text{Low}_{\text{bars}})$$
    $$\text{Close} = \text{Close}_{\text{last bar}}$$
    $$\text{Volume} = \sum \text{Volume}_{\text{bars}}$$
  * **Incomplete Bucket Handling**: A 4H bucket containing fewer than 4 completed hourly bars (e.g. the currently forming bucket) is either marked with `is_closed=False` or excluded from closed-bar indicator calculations to prevent look-ahead bias and premature strategy signals.

### 2.3 Options Chain Ingestion & Book Summary
* **Active Instruments (`public/get_instruments?currency=BTC&kind=option&expired=false`)**:
  * Retrieves all contractual definitions.
  * Must be filtered strictly by `is_active=True` / `state="open"`.
  * Extracts: `instrument_name`, `strike`, `expiration_timestamp`, `option_type` (`"call"`/`"put"`), `contract_size` (1.0 for BTC/ETH), `settlement_currency` (`"BTC"`, `"ETH"`, or `"USDC"`), `quote_currency` (`"USD"` or `"USDC"`), and `tick_size`.
* **Book Summary (`public/get_book_summary_by_currency?currency=BTC&kind=option`)**:
  * In a single call, returns live pricing metrics across all active strikes.
  * **Joining Strategy**: Join with instrument metadata using exact `instrument_name`.
  * **Nullable Fields**: On deep out-of-the-money or illiquid strikes, `bid_price`, `ask_price`, or `mark_price` can be `null` or 0. These fields must be modeled as `Decimal | None` and **must never cause the contract to be silently dropped** from the options chain.

### 2.4 Open Interest 8-Hour Refresh Delay
* Deribit updates `open_interest` on `get_book_summary_by_currency` periodically during 8-hour settlement cycles (08:00, 16:00, 24:00 UTC).
* Real-time intraday open interest may lag true contract issuance.
* The domain schema must expose freshness metadata (`open_interest_updated_at` or a staleness warning flag) so analytical engines do not mistake static open interest for zero intraday activity.

### 2.5 Contract Denomination & Currency Conversion
* **Inverse vs. Linear Contracts**:
  * Standard Deribit BTC/ETH options are **coin-margined (inverse)**: premiums and mark prices are denominated directly in the underlying cryptocurrency (`BTC` or `ETH`).
  * Deribit USDC options are **linear**: premiums are denominated in `USDC`.
* **Mandate**:
  * The adapter must preserve the raw exchange denomination (`mark_price_raw` and `quote_currency="BTC"`).
  * Converted USD prices (`mark_price_usd`) must only be calculated when the contract convention is explicitly verified:
    $$\text{mark\_price\_usd} = \text{mark\_price\_raw} \times \text{index\_price} \quad (\text{for coin-margined BTC/ETH})$$
    $$\text{mark\_price\_usd} = \text{mark\_price\_raw} \times 1.0 \quad (\text{for USDC linear})$$

### 2.6 Strict Decimal Conversion Rule
* JavaScript/JSON numbers arriving over HTTP must **never** be parsed using `Decimal(float(x))`, which introduces binary IEEE floating point drift (e.g. `0.045000000000000005`).
* All conversions must pass through string representations: `Decimal(str(x))` or custom JSON decoder hooks.

---

## 3. Rate Limiting, Timeouts & Caching Architecture

### 3.1 Rate Limit Reality
* Deribit enforces IP-based rate limits. However, limits are **endpoint-specific**:
  * `get_instruments` is a heavy query subject to strict limits (bursts can trigger temporary HTTP 429).
  * `get_index_price` and `get_book_summary_by_currency` have higher capacity.
* **Resilience Requirements**:
  * Configurable timeouts: Connect timeout 5.0s, Read timeout 10.0s.
  * Bounded exponential backoff with random jitter on HTTP 429 / HTTP 503 (initial backoff 250ms, multiplier 2.0, max retries 3, max backoff 2.0s).
  * Explicit `DeribitRateLimitError` and `DeribitTimeoutError` exceptions.

### 3.2 Tiered In-Memory Caching & Stampede Protection
To minimize upstream load and guarantee sub-millisecond response times:
1. **Instrument Metadata Cache**: Minimum 60-second TTL (recommended 300s). Refreshed infrequently since new strike listings occur on predictable daily/weekly cycles.
2. **Options Chain Summary Cache**: 15-second TTL.
3. **Index Price Cache**: 10-second TTL.
4. **Historical Candles Cache**: 60-second TTL.
5. **Cache Stampede Protection**: Use an asynchronous locking mechanism (`asyncio.Lock` per cache key) so concurrent incoming requests await the first in-flight upstream fetch rather than hammering the exchange API simultaneously.

### 3.3 Asynchronous Client & Lifespan Management
* The adapter will be built on `httpx.AsyncClient` utilizing standard connection pooling.
* Lifespan management: In FastAPI, instantiate the shared `httpx.AsyncClient` inside the application lifespan context manager (`@asynccontextmanager`) on startup and close it gracefully on shutdown.
