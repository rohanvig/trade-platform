# Technical Research: Backend Test Resilience & External Dependency Mapping

**Feature**: SPEC-002 (Backend Test Resilience & Deterministic Test Harness)  
**Status**: REFINED FOR APPROVAL  
**Author**: Senior Software Architect  
**Audited Date**: 2026-11-10  

---

## 1. Codebase Reality: The Direct `yfinance` Dependency Problem

A common architectural assumption was that all external market data flowed through `MarketDataService`. However, an exhaustive code inspection across `backend/app/` reveals that **four separate services directly import and invoke `yfinance`**:

| Service File | Line | Usage Pattern | Method Called |
| :--- | :---: | :--- | :--- |
| [`backend/app/services/market.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/market.py) | 6, 50, 120 | `ticker = yf.Ticker(sym)` | `ticker.fast_info`, `ticker.history()`, `yf.Search()` |
| [`backend/app/services/indicator.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/indicator.py) | 4, 44 | `ticker = yf.Ticker(sym)` | `ticker.history()` in `_get_history_df()` |
| [`backend/app/services/strategy.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/strategy.py) | 1, 24 | `ticker = yf.Ticker(sym)` | `ticker.history()` in `run_strategy()` |
| [`backend/app/services/backtest.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/backtest.py) | 1, 21 | `ticker = yf.Ticker(sym)` | `ticker.history()` in `run_backtest()` |

In addition, [`backend/app/services/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/portfolio.py) calls `MarketDataService.get_quote(order.symbol)` to determine live market fill prices during paper trading order execution.

### Architectural Implication:
If mocking were applied *only* to `MarketDataService.get_quote` and `MarketDataService.get_history`:
* `test_market.py` and `test_portfolio.py` would pass.
* BUT `test_indicators.py` (7 tests), `test_strategies.py` (2 tests), and `test_backtester.py` (2 tests) — **11 of the 17 failing tests** — would **still fail** because they instantiate `yfinance.Ticker` directly.

Therefore, the only unified boundary that isolates all 17 failing tests without modifying application source code is the **`yfinance.Ticker` interface**.

---

## 2. Application Control-Flow & Validation Defects Exposed by Tests

Inspection of the failing tests reveals that several failures are not merely network timeouts—they expose that application services perform external network calls **before** validating input parameters or checking domain preconditions:

### Defect 1: Backtest Strategy Name Validation
* **Location**: [`backend/app/services/backtest.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/backtest.py#L21-L27)
* **Code Flow**:
  1. `ticker = yf.Ticker(sym); df = ticker.history(...)` (Network request)
  2. `if df.empty: raise ValueError(...)`
  3. `strategy = get_strategy(request.strategy_name, ...)` (Strategy check)
* **Impact on Tests**: In `test_api_run_backtest_invalid_strategy`, the test submits `strategy_name="INVALID_STRATEGY_NAME"`. When network fails, it raises a DNS network error / 400 with "No market data found" rather than the expected `400 Bad Request` with `"Unknown strategy 'INVALID_STRATEGY_NAME'"`.
* **Fix for Testing**: When `yf.Ticker` is mocked to return synthetic bars for valid symbols, execution properly proceeds to line 27, triggering the expected `Unknown strategy` error. (For Phase 1 refactoring, input validation should occur *before* data retrieval).

### Defect 2: Strategy Runner Strategy Name Validation
* **Location**: [`backend/app/services/strategy.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/strategy.py#L24-L30)
* **Code Flow**:
  1. `ticker = yf.Ticker(sym); df = ticker.history(...)` (Network request)
  2. `strategy = get_strategy(request.strategy_name, ...)` (Strategy check)
* **Impact on Tests**: In `test_api_run_strategy_invalid_name`, the test expects `"Unknown strategy" in response.json()["detail"]`. Network failure masked this validation check.

### Defect 3: Paper Sell Order Share Ownership Validation
* **Location**: [`backend/app/services/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/portfolio.py#L93-L133)
* **Code Flow**:
  1. `quote = self.market_service.get_quote(order.symbol)` (Network request)
  2. Check cash balance (for BUY) or check share balance (for SELL)
* **Impact on Tests**: In `test_paper_sell_insufficient_shares_rejected`, the test tries to sell TSLA when 0 shares are owned. Because `get_quote` fails first due to DNS, it returns `"Execution failed: Could not fetch market price"` rather than `"Insufficient shares: Owns 0"`.

---

## 3. Mocking Strategy Recommendation

### Evaluated Options:
1. **Application-Level Refactor (Route everything through `MarketDataService`)**:
   * Clean architecture, but violates Phase 0 constraint: *"Do not modify application source code"*.
2. **Global Monkeypatch on `yfinance.Ticker`**:
   * Patches `yfinance.Ticker` in `conftest.py` attached to the `client` fixture.
   * Intercepts `Ticker.history` and `Ticker.fast_info`.
   * Automatically covers `market.py`, `indicator.py`, `strategy.py`, `backtest.py`, and `portfolio.py`.
   * **Zero application code changes required**.

### Conclusion:
A custom `MockTicker` class in `backend/tests/mock_data.py`, injected via `unittest.mock.patch("yfinance.Ticker")` inside `conftest.py`, is the single most effective, surgical, and reliable solution for Phase 0.
