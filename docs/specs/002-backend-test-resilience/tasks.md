# Task Breakdown: Backend Test Resilience

**Document**: TASKS-002  
**Feature**: SPEC-002  
**Status**: COMPLETED  
**Author**: Senior Software Architect  

---

## 1. Task Matrix & Traceability

| Task ID | Phase / Batch | Summary | Traceability (FR / NFR) | Expected Files | Tests Required | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TSK-020** | Batch 1 | Implement `MockTicker` and `create_deterministic_bars` satisfying financial invariants | FR-001, FR-002, FR-003 | `backend/tests/mock_data.py` | Unit checks on generated bars | **Completed** |
| **TSK-021** | Batch 1 | Implement `mock_market_data` fixture and wire into `client` fixture in `conftest.py` | FR-004, FR-005, NFR-002 | `backend/tests/conftest.py` | Test harness isolation | **Completed** |
| **TSK-022** | Batch 1 | Execute full backend test suite (`pytest tests -v`) and verify 56/56 tests passing | AC-001..AC-006, NFR-001 | Terminal run | All 56 backend tests (PASS) | **Completed** |
| **TSK-023** | Batch 1 | Synchronize `docs/project-status.md` with verified 100% passing test baseline | NFR-003 | `docs/project-status.md` | Verification report | **Completed** |

---

## 2. Cohesive Implementation Batches

### Batch 1: Test Resilience Harness & Verification (Single Focused Batch)
- [x] **TSK-020**: Create `backend/tests/mock_data.py`:
  - `MockFastInfo`: provides `last_price`, `open`, `day_high`, `day_low`, `previous_close`, `currency`.
  - `create_deterministic_bars(symbol, period, interval)`: produces deterministic Pandas DataFrame with valid OHLCV invariants ($L \le \min(O,C)$, $H \ge \max(O,C)$, $V \ge 0$, strictly positive prices, chronological UTC `DatetimeIndex`).
  - `MockTicker`: implements `history(period, interval)` and `fast_info`. Returns empty DataFrame for `XYZ*` or `INVALID*` symbols.
- [x] **TSK-021**: Update `backend/tests/conftest.py`:
  - Add `mock_market_data` fixture using `unittest.mock.patch("yfinance.Ticker")`.
  - Inject `mock_market_data` into `client` fixture so all API tests receive deterministic offline mock automatically.
- [x] **TSK-022**: Run full test suite:
  - Command: `cd backend; .\venv\Scripts\python -m pytest tests -v`
  - Target: **56 passed, 0 failed** in 4.44 seconds.
- [x] **TSK-023**: Update `docs/project-status.md` to document verified 56/56 passing tests and offline resilience.
