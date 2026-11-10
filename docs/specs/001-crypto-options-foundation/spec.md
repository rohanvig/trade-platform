# Feature Specification: Crypto Options Swing-Trading Workstation (Core Architecture)

**Feature ID**: SPEC-001  
**Status**: DRAFT FOR APPROVAL  
**Author**: Senior Software Architect & Lead Engineer  
**Scope**: Milestone 1 — Crypto Options Foundation, Deribit Data Ingestion, Greeks Engine, Options Contract Selection, Risk Management (1% Equity Rule), and Paper Trading.

---

## 1. Functional Requirements

### 1.1 Market & Options Chain Data Ingestion
- **FR-001**: System shall retrieve live index quotes and multi-timeframe OHLCV candles (1D, 4H, 1H) for primary crypto underlyings: **BTC** and **ETH**.
- **FR-002**: System shall retrieve the full active options chain from Deribit (or equivalent crypto derivatives venue) for BTC and ETH without requiring authenticated exchange credentials for public market data.
- **FR-003**: System shall parse options contract metadata: underlying asset, expiration timestamp, strike price, contract type (`CALL` / `PUT`), contract multiplier (1.0 for BTC/ETH), settlement style (European), and minimum tick size.
- **FR-004**: System shall compute and cache real-time bid, ask, mark price, mark implied volatility (IV), and open interest for every active strike across all active expiration cycles.

### 1.2 Quantitative & Options Greeks Engine
- **FR-005**: System shall implement the **Black-76** European options pricing model from scratch using high-precision calculations.
- **FR-006**: System shall calculate analytical first and second-order Greeks:
  - **Delta ($\Delta$)**: Price sensitivity with respect to underlying forward.
  - **Gamma ($\Gamma$)**: Delta sensitivity with respect to underlying forward.
  - **Theta ($\Theta$)**: Daily time decay.
  - **Vega ($\nu$)**: Sensitivity with respect to a 1% change in implied volatility.
  - **Rho ($\rho$)**: Sensitivity with respect to interest rate.
- **FR-007**: System shall calculate implied volatility (IV) from option market prices using Newton-Raphson with bounded Brent solver fallback.

### 1.3 Technical Analysis & Multi-Timeframe Bias
- **FR-008**: System shall compute swing-trading technical indicators across 1D, 4H, and 1H candles:
  - Exponential Moving Averages (EMA 20, 50, 200)
  - Relative Strength Index (RSI 14)
  - Average True Range (ATR 14)
  - Volume moving average and volume profile
- **FR-009**: System shall derive directional market bias (`BULLISH`, `BEARISH`, `NEUTRAL`) combining higher timeframe (1D/4H) trend alignment and 1H trigger conditions.

### 1.4 Options Strategy Selection & Trade Construction
- **FR-010**: System shall construct three defined-risk swing trading strategy structures:
  1. **Long Call**: Outright long call for strong bullish continuation/breakouts.
  2. **Long Put**: Outright long put for strong bearish breakdowns/hedging.
  3. **Bull Call Debit Spread**: Long lower strike call + Short higher strike call (same expiry) to reduce IV crush and theta decay.
  4. **Bear Put Debit Spread**: Long higher strike put + Short lower strike put (same expiry).
- **FR-011**: System shall evaluate options contract suitability based on:
  - Days to Expiry (DTE): Target 14 to 45 DTE for swing trading to minimize immediate gamma volatility while retaining theta efficiency.
  - Delta target: 0.30 to 0.50 Delta for outright directional calls/puts; 0.40/0.20 Delta for debit spread legs.
  - Bid-Ask Spread sanity check: Reject illiquid strikes where spread exceeds 5% of mid-price.

### 1.5 Risk Management & Position Sizing Engine
- **FR-012**: System shall strictly enforce a **Maximum 1% Account Equity Risk Limit per trade**.
- **FR-013**: System shall compute position size (number of contracts) such that:
  $$\text{Contracts} = \left\lfloor \frac{\text{Account Equity} \times 0.01}{\text{Max Loss per Contract}} \right\rfloor$$
  where for outright long options, $\text{Max Loss} = \text{Premium Paid} \times \text{Multiplier}$, and for debit spreads, $\text{Max Loss} = (\text{Net Debit Paid}) \times \text{Multiplier}$.
- **FR-014**: System shall enforce pre-trade validation gates that **cannot be bypassed**:
  - Rejection if total portfolio margin utilization exceeds 50% of equity.
  - Rejection if calculated position size is 0 contracts (insufficient risk budget).
  - Rejection if market data is stale (>60 seconds old).
- **FR-015**: System shall provide an emergency **Global Kill Switch** (`POST /api/v1/risk/kill-switch`) that immediately cancels all pending orders, blocks any new order submissions, and logs the administrative action.

### 1.6 Paper Trading & Order Management
- **FR-016**: System execution mode shall default to `PAPER` execution. Real live trading shall be disabled by default.
- **FR-017**: System shall support single-leg and multi-leg (spread) paper order submission, execution against live exchange mark/ask quotes, order cancellation, and lifecycle tracking (`PENDING`, `SUBMITTED`, `FILLED`, `CANCELLED`, `REJECTED`).
- **FR-018**: System shall track paper portfolio balances, active option positions, aggregate portfolio Greeks ($\sum \Delta, \sum \Gamma, \sum \Theta, \sum \text{Vega}$), cash, and unrealized/realized PnL.

---

## 2. Non-Functional Requirements

- **NFR-001 (Financial Precision)**: All monetary amounts, strike prices, option premiums, and position quantities must use Python `Decimal` or PostgreSQL `NUMERIC(18, 8)` to prevent floating point drift.
- **NFR-002 (Auditing & Idempotency)**: All order requests must support client-generated idempotency keys (`client_order_id`). Every order state transition and risk rejection must generate an audit log record with timestamps in UTC.
- **NFR-003 (Layered Architecture)**: API routes must not contain business or options math. Math belongs in `domain/` and `services/`, and database queries belong in `repositories/`.
- **NFR-004 (Performance & Latency)**: Options chain parsing and Greek computation for an entire expiration cycle (<100 strikes) must complete in under 150ms.
- **NFR-005 (Safety by Default)**: Live exchange API keys, if ever configured in `.env`, must require explicit system flag `LIVE_TRADING_ENABLED=True` and per-order confirmation; otherwise, all order routing falls back to simulated paper execution.

---

## 3. Acceptance Criteria (Testable Verification)

- **AC-001 (Deribit Ingestion)**: Given BTC or ETH, when `DeribitClient.get_options_chain()` is called, it returns all active expiries and strikes with valid bid, ask, and mark prices without authentication.
- **AC-002 (Greeks Accuracy)**: Black-76 pricing and Greeks for known benchmark options match verified theoretical reference values within $10^{-4}$ tolerance.
- **AC-003 (Spread Payoff Calculation)**: Bull Call and Bear Put debit spreads correctly calculate Net Debit, Max Profit, Max Loss, and Breakeven prices.
- **AC-004 (1% Risk Enforcement)**: An order requesting position size that risks 1.01% of account equity is rejected with HTTP 422 / `RiskLimitExceededError`.
- **AC-005 (Kill Switch)**: When the kill switch is triggered, subsequent order submissions return HTTP 403 Forbidden with `TRADING_HALTED` code.
- **AC-006 (Multi-Timeframe Technical Bias)**: Indicator engine correctly calculates 1D, 4H, and 1H indicators on crypto candle series and outputs structured trend bias.
- **AC-007 (Paper Order Lifecycle)**: Single-leg and multi-leg spread orders can be created, executed at live mark price, tracked in positions, and closed with proper PnL accounting.

