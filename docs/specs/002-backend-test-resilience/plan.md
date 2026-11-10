# Technical Architecture & Implementation Plan: Backend Test Resilience

**Document**: PLAN-002  
**Feature**: SPEC-002  
**Status**: REFINED FOR APPROVAL  
**Author**: Senior Software Architect  

---

## 1. Technical Boundary & Call-Site Analysis

The external market data boundary is distributed across 4 application services that directly instantiate `yfinance.Ticker`:

```text
                  ┌───────────────────────────────┐
                  │    yfinance.Ticker(symbol)    │
                  └───────────────▲───────────────┘
                                  │ (Direct Imports)
         ┌────────────────┬───────┴────────┬────────────────┐
         │                │                │                │
┌────────┴───────┐┌───────┴──────┐┌────────┴───────┐┌───────┴────────┐
│ MarketService  ││ IndicatorSvc ││  StrategySvc   ││  BacktestSvc   │
└────────▲───────┘└───────▲──────┘└────────▲───────┘└───────▲────────┘
         │                │                │                │
┌────────┴───────┐┌───────┴──────┐┌────────┴───────┐┌───────┴────────┐
│PortfolioService││/indicators/* ││/strategies/run ││ /backtest/run  │
└────────────────┘└──────────────┘└────────────────┘└────────────────┘
```

### Proposed Patch Point:
By patching `yfinance.Ticker` inside `backend/tests/conftest.py`, a single mock interception point covers **all 4 services and all 17 failing tests** simultaneously, with zero changes to application code.

---

## 2. Mock Design & Synthetic Data Invariants

### 2.1 `MockTicker` Class Specification
```python
class MockTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol.strip().upper()
        self.fast_info = MockFastInfo(self.symbol)
    
    def history(self, period="1mo", interval="1d"):
        # If symbol indicates invalid test case, return empty DataFrame
        if self.symbol.startswith("XYZ") or "INVALID" in self.symbol:
            return pd.DataFrame()
        return create_deterministic_bars(self.symbol, period=period, interval=interval)
```

### 2.2 Synthetic Bar Generator (`create_deterministic_bars`)
The generator enforces strict mathematical invariants:
1. **Prices are positive**: Base prices ($150$ for AAPL, $300$ for MSFT, $250$ for TSLA, $120$ for NVDA).
2. **Deterministic wave**: Uses a fixed sinusoidal formula $P_i = P_0 + 5.0 \sin(i / 3.0)$ so indicator math (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP) generates realistic, bounded values without division-by-zero or NaN errors.
3. **Bar Invariants**:
   $$\text{Open} = \text{round}(P_i, 2)$$
   $$\text{Close} = \text{round}(\text{Open} + \delta, 2)$$
   $$\text{High} = \text{round}(\max(\text{Open}, \text{Close}) + 2.0, 2)$$
   $$\text{Low} = \text{round}(\min(\text{Open}, \text{Close}) - 2.0, 2)$$
   $$\text{Volume} = 100,000 + (i \times 1,000)$$
4. **Chronological Index**: UTC `DatetimeIndex` with monotonic daily or intraday increments.

---

## 3. Fixture Lifecycle & Override Strategy

### Why Client-Scoped Fixture is Safest:
Rather than an unconstrained global `autouse=True` fixture that could mask issues in standalone unit tests, we attach `mock_market_data` directly to the `client` fixture:

```python
@pytest.fixture(scope="function")
def mock_market_data():
    with patch("yfinance.Ticker", side_effect=lambda sym: MockTicker(sym)) as mock_patch:
        yield mock_patch

@pytest.fixture(scope="function")
def client(db_session, mock_market_data):
    # Tests using client get database isolation + market data isolation automatically
    ...
```

### Supporting Per-Test Overrides:
Any test needing to simulate a network outage, empty dataset, or specific symbol price can request `mock_market_data` explicitly and reconfigure `mock_market_data.side_effect` or mock methods. The context manager guarantees 100% teardown at the end of the test function.

---

## 4. Expected Files & Changes

| Path | Change Type | Description |
| :--- | :--- | :--- |
| `backend/tests/mock_data.py` | **New File** | `MockTicker`, `MockFastInfo`, `create_deterministic_bars()` helper functions. |
| `backend/tests/conftest.py` | **Modified File** | Add `mock_market_data` fixture; inject into `client` fixture. |
| `docs/project-status.md` | **Documentation** | Update test execution metrics from 39/56 to 56/56 passing. |

**Application source code in `backend/app/` will NOT be modified.**
