# Task Breakdown: Crypto Market Data & Public Deribit Adapter

**Document**: TASKS-003  
**Feature**: SPEC-003  
**Status**: REVISED TASKS BASELINE (Pending Review)  
**Author**: Senior Software Architect  
**Updated Date**: 2026-11-10  

---

## 1. Task Matrix & Traceability

| Task ID | Batch | Summary | Traceability (FR / NFR) | Expected Files | Acceptance Criteria | Status |
| :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **TSK-030** | Batch 1 | Define Pydantic domain schemas with string-based `Decimal` parsing, nullable quotes, `is_index`, and `is_closed` flags | FR-001, FR-003, FR-008, FR-010, FR-014, NFR-001 | `backend/app/schemas/crypto_market.py` | AC-001, AC-005, AC-006, AC-007 | Complete |
| **TSK-031** | Batch 1 | Define async `MarketDataAdapter` protocol and Deribit domain exceptions | FR-001, FR-013, NFR-002, NFR-005 | `backend/app/adapters/base.py`, `backend/app/adapters/exceptions.py` | AC-008, AC-009 | Complete |
| **TSK-032** | Batch 1 | Implement `DeribitMarketDataAdapter` with `httpx.AsyncClient`, rate limiting, bounded exponential backoff, and metadata join | FR-002, FR-004, FR-006, FR-007, FR-009, FR-013, NFR-003 | `backend/app/adapters/deribit.py` | AC-001, AC-004, AC-005, AC-008 | Complete |
| **TSK-033** | Batch 2 | Implement `CryptoMarketDataService` with tiered TTL caching, stampede lock, 4H UTC candle aggregator, and coin-to-USD conversion | FR-004, FR-005, FR-009, FR-011, FR-012, NFR-003 | `backend/app/services/crypto_market.py` | AC-002, AC-003 | Complete |
| **TSK-034** | Batch 2 | Implement FastAPI endpoints under `/api/v1/crypto/...`, application lifespan management, and mount to API router | FR-002, FR-003, FR-004, FR-006, NFR-005 | `backend/app/api/v1/endpoints/crypto_market.py`, `backend/app/api/router.py`, `backend/app/main.py` | AC-001..AC-006 | Complete |
| **TSK-035** | Batch 2 | Build offline synthetic fixtures (`deribit_samples.py`) and test suite verifying all 10 acceptance criteria | NFR-004, AC-001..AC-010 | `backend/tests/fixtures/deribit_samples.py`, `backend/tests/test_crypto_market.py` | AC-001..AC-010 | Complete |

---

## 2. Cohesive Implementation Batches

### Batch 1: Domain Schemas, Protocol & Deribit Async Adapter
- [x] **TSK-030**: Create `backend/app/schemas/crypto_market.py`:
  - `CryptoQuote`: `underlying`, `index_name`, `index_price` (`Decimal`), `is_index=True`, `timestamp`.
  - `CryptoCandle`: `instrument_name`, `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, `is_closed`.
  - `OptionContractSummary`: `instrument_name`, `strike`, `option_type`, `expiry_date`, `expiration_timestamp`, `contract_size`, `settlement_currency`, `quote_currency`, nullable `mark_price_raw`, `mark_price_usd`, `mark_iv`, `bid_price_raw`, `ask_price_raw`, `bid_price_usd`, `ask_price_usd`, `open_interest`, `is_oi_delayed=True`.
  - `OptionChainResponse`: `underlying`, `expiry_date`, `underlying_index_price`, `calls`, `puts`, `total_contracts`.
  - Use custom field validators ensuring string-based `Decimal` conversion without float artifacts.
- [x] **TSK-031**: Create `backend/app/adapters/base.py` and `backend/app/adapters/exceptions.py`:
  - Define `MarketDataAdapter(Protocol)` with async signatures:
    - `async def get_index_price(underlying: str) -> CryptoQuote`
    - `async def get_instrument_candles(instrument_name: str, resolution: str, start_ts: int, end_ts: int) -> list[CryptoCandle]`
    - `async def get_active_instruments(currency: str) -> list[dict]`
    - `async def get_book_summary(currency: str) -> list[dict]`
  - Define domain exceptions: `DeribitRateLimitError`, `DeribitTimeoutError`, `DeribitDataError`, `UnsupportedAssetError`.
- [x] **TSK-032**: Create `backend/app/adapters/deribit.py`:
  - Implement `DeribitMarketDataAdapter` accepting an `httpx.AsyncClient`.
  - Connects to `https://www.deribit.com/api/v2/public/`.
  - Enforce timeouts: 5s connect, 10s read.
  - Rate limiting & retry: On HTTP 429 or 503, apply bounded exponential backoff with jitter (initial 250ms, multiplier 2.0, max 3 retries, ceiling 2.0s). Raise `DeribitRateLimitError` on exhaustion.
  - Join logic: match instruments and book summaries using exact `instrument_name`. Filter `state="open"`. Maintain nullable bid/ask/mark prices.

### Batch 2: Application Service, API Controllers & Offline Test Harness
- [x] **TSK-033**: Create `backend/app/services/crypto_market.py`:
  - Tiered in-memory TTL cache with per-key `asyncio.Lock` stampede protection:
    - 60s minimum TTL on instrument metadata.
    - 15s TTL on options chains.
    - 10s TTL on index quotes.
    - 60s TTL on historical candles.
  - 4-Hour UTC candle aggregation engine:
    - Ingest 1H bars for `BTC-PERPETUAL` and `ETH-PERPETUAL`.
    - Group into UTC-aligned 4H buckets (`00:00`, `04:00`, `08:00`, `12:00`, `16:00`, `20:00`).
    - Open = first bar Open, High = max(High), Low = min(Low), Close = last bar Close, Volume = sum(Volume).
    - Incomplete bucket handling: assign `is_closed=False` to in-progress windows.
  - Coin-to-USD conversion: compute `mark_price_usd = mark_price_raw * index_price` for coin-margined options.
- [x] **TSK-034**: Create `backend/app/api/v1/endpoints/crypto_market.py` and router wiring:
  - Mount endpoints:
    - `GET /api/v1/crypto/quote?underlying=BTC`
    - `GET /api/v1/crypto/history?underlying=BTC&timeframe=1d&period=30d` (Supports `1d`, `4h`, `1h`)
    - `GET /api/v1/crypto/options/expiries?underlying=BTC`
    - `GET /api/v1/crypto/options/chain?underlying=BTC&expiry=YYYY-MM-DD`
  - Lifespan management in `backend/app/main.py`: manage `httpx.AsyncClient` lifecycle gracefully.
  - Standardized error schemas (`{"error_code": str, "message": str, "timestamp": str}`).
- [x] **TSK-035**: Create `backend/tests/fixtures/deribit_samples.py` and `backend/tests/test_crypto_market.py`:
  - Synthetic offline fixtures using `httpx.MockTransport`.
  - Automated tests verifying AC-001 through AC-010:
    - Index observation pricing and UTC timestamps.
    - 4H candle aggregation math and incomplete bucket `is_closed=False` flag.
    - Active instrument filtering (`state="open"` only).
    - Nullable bid/ask retention in strike ladder.
    - Open interest freshness flag (`is_oi_delayed=True`).
    - Decimal string parsing invariance.
    - Timeout and HTTP 429 exponential backoff retry behavior.
    - Malformed response error handling.
    - Complete suite regression verification (56 existing + new tests passing 100% offline).
