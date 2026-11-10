# Feature Specification: Crypto Market Data & Public Deribit Adapter

**Feature ID**: SPEC-003  
**Status**: REVISED SPECIFICATION (Pending Review)  
**Author**: Senior Software Architect  
**Scope**: Phase 1 — Public Deribit Async REST Adapter, Multi-Timeframe BTC/ETH Candles, and Options Chain Ingestion  
**Updated Date**: 2026-11-10  

---

## 1. Problem Statement
TradePilot is transitioning from an equities prototype into a dedicated personal crypto-options swing-trading workstation focused on **BTC** and **ETH**. The legacy market data layer is coupled to equities via `yfinance`, lacking any capability to fetch crypto options chains, contract specifications, or multi-timeframe candle aggregations.

To establish the data foundation for quantitative options analytics (Phase 2), strategy selection (Phase 4), and paper trading (Phase 6), TradePilot requires a decoupled, resilient, unauthenticated market data adapter that interfaces with Deribit API v2 asynchronously while guaranteeing strict financial precision, rate-limit resilience, and zero interference with existing equities endpoints.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- [ ] Define an asynchronous, exchange-agnostic `MarketDataAdapter` protocol in `app/adapters/base.py`.
- [ ] Implement `DeribitMarketDataAdapter` in `app/adapters/deribit.py` using an async `httpx.AsyncClient` with application lifespan management.
- [ ] Ingest real-time underlying index prices for `BTC` (`btc_usd`) and `ETH` (`eth_usd`) as distinct benchmark price observations.
- [ ] Ingest traded instrument OHLCV candles (`BTC-PERPETUAL` and `ETH-PERPETUAL`) for 1D and 1H, and construct strictly UTC-aligned 4H candles through deterministic internal aggregation.
- [ ] Retrieve and cache active contract metadata (`state="open"`, `expired=false`), preserving `contract_size`, `settlement_currency`, `quote_currency`, and `expiration_timestamp`.
- [ ] Retrieve and join live book summaries to produce the complete options chain, treating missing bids/asks/marks as nullable rather than dropping contracts.
- [ ] Preserve raw exchange premium denominations (`BTC`/`ETH`/`USDC`) and calculate converted USD values only after contract convention verification.
- [ ] Convert all JSON numeric amounts to `Decimal` using string representations (`Decimal(str(x))`), avoiding binary float drift.
- [ ] Implement tiered in-memory caching with cache stampede protection (`asyncio.Lock`):
  - Instrument Metadata: 60s TTL minimum (default 300s)
  - Options Chain Summary: 15s TTL
  - Index Quotes: 10s TTL
  - Historical Candles: 60s TTL
- [ ] Implement endpoint-aware rate-limiting, timeouts (5s connect / 10s read), bounded exponential backoff with jitter on HTTP 429/503, and explicit domain exceptions (`DeribitRateLimitError`, `DeribitTimeoutError`).
- [ ] Expose clean REST endpoints under `/api/v1/crypto/...` with standardized error schemas and empty-data handling.
- [ ] Ensure 100% offline test suite execution using `httpx.MockTransport` fixtures, preserving all 56 existing tests.

### 2.2 Non-Goals
- Authenticated account management or private order execution (paper trading uses simulated fills).
- Persistent historical tick or candle database storage in PostgreSQL (in-memory caching satisfies Milestone 1).
- Universal altcoin coverage (strictly scoped to BTC and ETH).
- Modifying or breaking existing equities endpoints or models.

---

## 3. User Stories
- **US-01**: As a crypto swing trader, I want to view live reference index prices for BTC and ETH so that I can gauge underlying spot valuations.
- **US-02**: As a quantitative swing trader, I want to access 1D, 4H, and 1H candles for BTC and ETH with verified financial invariants and proper 4H bucket aggregation so that I can compute multi-timeframe indicators without look-ahead bias.
- **US-03**: As an options trader, I want to view active options chains by expiry with complete strike ladders, mark prices, IV, and open interest freshness flags, even when certain out-of-the-money strikes lack active bids or asks.

---

## 4. Functional Requirements

### 4.1 Architecture & Protocols
* **FR-001 (Async Protocol)**: Define an asynchronous `MarketDataAdapter` protocol in `app/adapters/base.py` declaring async methods for index quotes, candles, contract metadata, and options chains.
* **FR-002 (HTTP Client Lifespan)**: Implement `DeribitMarketDataAdapter` using `httpx.AsyncClient` whose connection pool is managed within FastAPI's application lifespan context.

### 4.2 Market Observations & Traded Candles
* **FR-003 (Index Observations)**: Retrieve real-time index prices for `BTC` (`btc_usd`) and `ETH` (`eth_usd`). Explicitly tag these as benchmark index observations (`is_index=True`) and never represent them as tradable OHLCV candles.
* **FR-004 (Instrument Candles)**: Ingest 1D and 1H OHLCV candles from perpetual instruments (`BTC-PERPETUAL` and `ETH-PERPETUAL`).
* **FR-005 (4H Candle Aggregation)**:
  * Ingest 1H candles and aggregate them into complete, UTC-aligned 4-Hour buckets: `[00:00, 04:00)`, `[04:00, 08:00)`, `[08:00, 12:00)`, `[12:00, 16:00)`, `[16:00, 20:00)`, `[20:00, 24:00)`.
  * Aggregation rules: $\text{Open} = \text{Open}_{\text{first}}$, $\text{High} = \max(\text{High})$, $\text{Low} = \min(\text{Low})$, $\text{Close} = \text{Close}_{\text{last}}$, $\text{Volume} = \sum \text{Volume}$.
  * Incomplete bucket handling: The currently forming 4H bucket with $<4$ completed 1H bars must be flagged with `is_closed=False` and excluded from closed-candle technical indicator calculations.

### 4.3 Options Chain & Contract Ingestion
* **FR-006 (Instrument Metadata)**: Ingest active contract definitions from `public/get_instruments`, filtering strictly by `is_active=True` / `state="open"`. Preserve `instrument_name`, `strike`, `expiration_timestamp`, `contract_size`, `settlement_currency`, `quote_currency`, and `instrument_type`.
* **FR-007 (Book Summary Joining)**: Join live book summaries (`public/get_book_summary_by_currency`) to active instrument definitions using exact `instrument_name`.
* **FR-008 (Nullable Bids/Asks/Marks)**: Model `bid_price`, `ask_price`, `mark_price`, and `mark_iv` as nullable (`Decimal | None`). Never drop an active contract from the chain due to absent quotes.
* **FR-009 (Currency Denomination & Conversion)**: Preserve raw exchange quote denomination (`mark_price_raw` in BTC/ETH/USDC). Calculate `mark_price_usd` only when contract convention is validated against the live index price.
* **FR-010 (Open Interest Freshness)**: Expose open interest along with a freshness metadata flag (`is_oi_delayed=True`) acknowledging Deribit's 8-hour settlement reporting cycle.

### 4.4 Resilience, Caching & Performance
* **FR-011 (Tiered In-Memory Caching)**: Maintain separate in-memory caches:
  * Instrument metadata: $\ge 60$s TTL (default 300s).
  * Options chain book summaries: 15s TTL.
  * Index prices: 10s TTL.
  * Historical candles: 60s TTL.
* **FR-012 (Stampede Protection)**: Protect all cache miss lookups with key-specific async locks (`asyncio.Lock`) to prevent thundering herd requests to the exchange.
* **FR-013 (Rate-Limit & Timeout Handling)**: Enforce 5s connect / 10s read timeouts. On HTTP 429 or HTTP 503, apply bounded exponential backoff with jitter (initial 250ms, multiplier 2.0, max 3 retries, max backoff 2.0s). Raise `DeribitRateLimitError` if retries are exhausted.
* **FR-014 (String-Based Decimal Conversion)**: All numeric conversions from JSON payloads to Python `Decimal` must strictly utilize string parsing (`Decimal(str(val))`), never `Decimal(float)`.

---

## 5. Non-Functional Requirements

| Requirement ID | Category | Description | Target Metric |
| :--- | :--- | :--- | :--- |
| **NFR-001** | Financial Precision | All financial prices, strikes, and volumes must be represented using Python `Decimal` with explicit string conversion. | 0 float drift |
| **NFR-002** | Layer Isolation | External Deribit JSON-RPC structures must terminate at the adapter boundary. Application services only receive clean Pydantic domain models. | 100% decoupled |
| **NFR-003** | Performance & Latency | Cached requests must resolve in $<5$ms; uncached full chain parsing must complete in $<150$ms. | $<150$ms |
| **NFR-004** | Offline Determinism | All adapter and service tests must execute offline using `httpx.MockTransport` without internet access. | 100% Offline |
| **NFR-005** | API Error Contracts | Standardized error response JSON schema (`{"error_code": str, "message": str, "timestamp": str}`) with proper HTTP status codes (400, 404, 429, 503). | Uniform Error DTO |

---

## 6. Acceptance Criteria (Testable Verification)

- [ ] **AC-001 (Index Observation)**: Calling `adapter.get_index_price("BTC")` returns a valid `CryptoQuote` where `is_index=True`, price is a positive `Decimal`, and timestamp is UTC.
- [ ] **AC-002 (4H Aggregation Correctness)**: Given twelve 1-hour candles starting at 00:00 UTC, the aggregation engine produces exactly three 4-hour candles with correct Open (first bar), High (max), Low (min), Close (last bar), and Volume (sum).
- [ ] **AC-003 (Incomplete Bucket Handling)**: Given an ongoing 4-hour cycle with only two 1-hour candles, the aggregated 4H bar is returned with `is_closed=False` and properly segregated.
- [ ] **AC-004 (Active Instrument Filtering)**: Inactive or expired instruments (`state != "open"` or `expired=True`) are excluded from the options chain.
- [ ] **AC-005 (Nullable Quote Resilience)**: Deep out-of-the-money contracts with `bid=null` and `ask=null` are retained in the options chain with `bid_price=None` and `ask_price=None`.
- [ ] **AC-006 (Open Interest Freshness Flag)**: The options chain summary includes `is_oi_delayed=True` and records the reporting cycle status.
- [ ] **AC-007 (Strict Decimal Invariance)**: Ingesting floating point JSON numbers (e.g. `0.045`) converts to exact `Decimal("0.045")` without binary representation artifacts.
- [ ] **AC-008 (Timeout & Rate-Limit Backoff)**: When Deribit returns HTTP 429, the client retries with exponential backoff; if retries are exhausted, it raises `DeribitRateLimitError`.
- [ ] **AC-009 (Malformed Response Handling)**: Malformed JSON or missing required fields raises `DeribitDataError` rather than unhandled key errors or raw tracebacks.
- [ ] **AC-010 (Regression Invariance)**: The existing equities API and all 56 existing tests continue to pass 100% offline.

---

## 7. Edge Cases & Boundary Conditions
1. **Weekend Trading**: Unlike equities, crypto markets trade 24/7/365. Candles and timestamps have no market-closure gaps.
2. **Contract Expiry at 08:00 UTC**: Deribit options expire strictly at 08:00 UTC on Fridays. The expiration parser must accurately treat 08:00 UTC as the termination timestamp.
3. **Empty Options Chain**: If querying an expiry date with no active contracts, the API returns a valid `OptionChainResponse` with `calls=[]`, `puts=[]`, and `total_contracts=0` (HTTP 200), not an HTTP 500 error.
4. **Unsupported Asset**: Querying symbols other than `BTC` and `ETH` immediately raises `UnsupportedAssetError` returning HTTP 400.
