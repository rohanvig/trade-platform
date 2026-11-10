# Feature Specification: Backend Test Resilience & External Isolation

**Feature ID**: SPEC-002  
**Status**: REFINED FOR APPROVAL  
**Author**: Senior Software Architect  
**Scope**: Phase 0 — Deterministic Mock Test Harness, Network Isolation, and Test Suite Stabilization  
**Audited Date**: 2026-11-10  

---

## 1. Problem Statement
The TradePilot backend test suite consists of 56 tests across 8 test modules. 17 endpoint integration tests make direct external network calls to Yahoo Finance. Because `MarketDataService`, `IndicatorService`, `StrategyService`, and `BacktestService` all directly instantiate `yfinance.Ticker`, these tests fail in offline sandboxes or CI environments with DNS resolution errors.

Furthermore, several services fetch market data *before* validating domain preconditions (e.g. strategy registration or position ownership), causing network crashes to mask application validation logic.

To comply with the Project Constitution, the backend test harness must be isolated from external network dependencies, execute 100% deterministically offline, and enable complete verification of application control-flow logic.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- [ ] Stabilize all 56 backend tests to pass deterministically offline without internet or DNS access.
- [ ] Provide synthetic OHLCV bar and quote generators satisfying strict financial invariants:
  - Positive prices ($P > 0$).
  - $Low \le \min(Open, Close)$.
  - $High \ge \max(Open, Close)$.
  - Non-negative volume ($V \ge 0$).
  - Chronological, timezone-aware UTC timestamps.
- [ ] Provide a unified `MockTicker` intercepting `yfinance.Ticker` across all 4 consuming services (`market.py`, `indicator.py`, `strategy.py`, `backtest.py`).
- [ ] Ensure the mock can be customized per-test to simulate empty data, provider errors, and specific symbol scenarios.
- [ ] Achieve full test suite execution time under 3 seconds (down from 25.21s).
- [ ] Zero modifications to application source code in `backend/app/`.

### 2.2 Non-Goals
- Refactoring `yfinance` callers into a unified interface (reserved for Phase 1 Deribit migration).
- Re-architecting database schemas or FastAPI dependency injection.

---

## 3. Functional Requirements

| Requirement ID | Summary | Description | Priority |
| :--- | :--- | :--- | :--- |
| **FR-001** | Unified `MockTicker` Implementation | Test harness must implement a `MockTicker` simulating `yfinance.Ticker`, providing `history(period, interval)` and `fast_info` attributes (`last_price`, `open`, `day_high`, `day_low`, `previous_close`, `currency`). | P0 |
| **FR-002** | Mathematically Correct Synthetic Bars | Synthetic bar generator must produce Pandas DataFrames with strictly valid OHLCV relationships ($Low \le \min(O,C)$, $High \ge \max(O,C)$), positive prices, non-negative volume, and strictly increasing UTC timestamps. | P0 |
| **FR-003** | Symbol-Specific Routing & Error Simulation | `MockTicker` must return valid bars for standard tickers (`AAPL`, `MSFT`, `TSLA`, `NVDA`, `BTC-USD`), empty DataFrames for invalid tickers (`XYZQWERTY*`), and allow tests to simulate exceptions (e.g. timeout or connection drop). | P0 |
| **FR-004** | Client-Scoped Mock Integration | The `client` fixture in `conftest.py` must automatically activate the `MockTicker` patch, ensuring all endpoint tests execute offline without requiring boilerplates in individual test functions. | P0 |
| **FR-005** | Per-Test Override Capability | Allow individual tests to explicitly inject custom price behavior or simulated provider failures via a configurable `mock_market` fixture handle. | P1 |

---

## 4. Non-Functional Requirements

| Requirement ID | Category | Description | Target Metric |
| :--- | :--- | :--- | :--- |
| **NFR-001** | Test Execution Speed | Entire 56-test suite must execute in under 3.0 seconds. | < 3.0s |
| **NFR-002** | Offline Independence | Zero network socket connections or DNS resolution attempts during test execution. | 100% Offline |
| **NFR-003** | Code Preservation | 100% of changes confined to `backend/tests/`. Zero application diff. | 0 app files modified |
| **NFR-004** | Test State Isolation | Each test must execute independently with automatic fixture teardown and clean in-memory SQLite tables. | 100% Isolated |

---

## 5. Acceptance Criteria (Testable Verification)

- [ ] **AC-001**: Running `cd backend; pytest tests -v` in standard offline sandbox passes with **56 passed, 0 failed, 0 errors**.
- [ ] **AC-002**: `test_backtester.py` verifies both valid backtest execution (`HTTP 200`) and invalid strategy rejection (`HTTP 400` with `"Unknown strategy"`).
- [ ] **AC-003**: `test_strategies.py` verifies strategy signal generation and invalid strategy rejection (`HTTP 400` with `"Unknown strategy"`).
- [ ] **AC-004**: `test_portfolio.py` verifies paper buy, paper sell, manual execution, and insufficient shares rejection (`HTTP 400` with `"Insufficient shares"`).
- [ ] **AC-005**: `test_indicators.py` verifies all 7 indicator endpoints return valid data points and invalid symbol returns `HTTP 400`.
- [ ] **AC-006**: Total test execution time is under 3.0 seconds.

---

## 6. Traceability Matrix

| Requirement | Design Element (Plan) | Implementation Task | Verification Test |
| :--- | :--- | :--- | :--- |
| **FR-001** | `MockTicker` in `mock_data.py` | TSK-020 | `test_market.py::test_market_quote_success` |
| **FR-002** | `create_deterministic_bars()` | TSK-020 | `test_indicators.py::test_api_get_sma` |
| **FR-003** | `MockTicker` symbol dispatcher | TSK-020 | `test_indicators.py::test_api_indicator_invalid_symbol` |
| **FR-004** | `conftest.py` client fixture hook | TSK-021 | All 17 failing tests |
| **FR-005** | Configurable fixture handle | TSK-021 | Individual override test verification |
| **NFR-001** | In-memory synthetic generation | TSK-022 | `pytest` terminal execution timing |
