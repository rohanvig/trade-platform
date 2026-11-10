# TradePilot — Master Development Roadmap

**Document**: ROADMAP-001  
**Status**: APPROVED BASELINE  
**Focus**: Personal Crypto Options Swing-Trading Workstation (BTC & ETH)

---

## 1. Roadmap Architecture: Foundation First

Per TradePilot's project constitution, all architecture and testing foundations must be stabilized before introducing complex trading and derivative features.

```text
[Phase 0: Governance & Test Stability]
                │
                ▼
[Phase 1: Crypto Market Data & Exchange Adapter]
                │
                ▼
[Phase 2: Pure Domain Greeks & Quantitative Core]
                │
                ▼
[Phase 3: Risk Management Engine & Trading Safety]
                │
                ▼
[Phase 4: Options Strategy Construction & Selection]
                │
                ▼
[Phase 5: Database Schema Evolution & Order Idempotency]
                │
                ▼
[Phase 6: Options Paper Trading & Portfolio Greeks]
                │
                ▼
[Phase 7: Frontend Workstation & Visual Options Desk]
                │
                ▼
[Phase 8: Multi-Timeframe Trend Intelligence]
                │
                ▼
[Phase 9: Controlled Live Execution & Multi-User Evolution]
```

---

## 2. Detailed Milestone Breakdown

### Phase 0: SDD Governance & Test Resilience (Immediate Priority)
- [x] Establish SDD governance baseline (`AGENTS.md`, `.specify/memory/constitution.md`, `.specify/memory/product-context.md`, `.specify/memory/architecture-principles.md`).
- [x] Create reusable SDD templates (`spec-template.md`, `plan-template.md`, `tasks-template.md`).
- [ ] Add offline test fixtures in `backend/tests/conftest.py` so all existing 56 backend tests pass 100% offline and in CI.
- [ ] Reconcile and formalize Feature Specification `SPEC-001` for the Crypto Options Workstation.

### Phase 1: Crypto Market Data & Public Deribit Adapter
- [ ] Define abstract `MarketDataAdapter` interface in `app/adapters/`.
- [ ] Implement `DeribitMarketDataAdapter` using Deribit public REST endpoints (no authentication required).
- [ ] Retrieve live BTC and ETH spot/forward index quotes.
- [ ] Fetch complete options chain (expiries, strikes, bids, asks, mark price, open interest) with 15s TTL caching.
- [ ] Retrieve multi-timeframe historical candle series (1D, 4H, 1H).

### Phase 2: Pure Domain Greeks & Quantitative Core
- [ ] Create `app/domain/greeks/` with zero framework dependencies.
- [ ] Implement Black-76 European options pricing for Calls and Puts using Python `Decimal` precision.
- [ ] Calculate first- and second-order analytical Greeks: Delta ($\Delta$), Gamma ($\Gamma$), Theta ($\Theta$), Vega ($\nu$), Rho ($\rho$).
- [ ] Implement Newton-Raphson numerical Implied Volatility (IV) solver with bounded Brent fallback.
- [ ] Benchmark Greeks against verified academic and market reference tables in automated unit tests.

### Phase 3: Risk Management Engine & Trading Safety
- [ ] Implement `app/domain/risk/sizer.py` enforcing the 1% maximum account equity risk rule per trade.
- [ ] Implement pre-trade validation gates:
  - Total portfolio margin utilization ceiling ($\le 50\%$).
  - Minimum lot size and zero-size contract rejection.
  - Stale quote detection ($>60$ seconds).
  - Bid-ask spread sanity check (reject strikes where spread $> 5\%$ of mid).
- [ ] Implement the **Emergency Kill Switch** (`app/domain/risk/kill_switch.py`) with administrative halt capabilities.

### Phase 4: Options Strategy Construction & Selection
- [ ] Implement defined-risk payoff calculations in `app/domain/options/payoff.py`:
  - Long Call & Long Put outright payoffs.
  - Bull Call Debit Spread (Long lower strike + Short higher strike).
  - Bear Put Debit Spread (Long higher strike + Short lower strike).
  - Calculate Net Debit, Max Profit, Max Loss, Breakeven points, and Risk/Reward ratios.
- [ ] Implement contract candidate selector (`app/domain/options/selector.py`):
  - Filter for swing horizon: 14 to 45 Days to Expiration (DTE).
  - Filter for target Delta: 0.30 to 0.50 Delta for outrights, 0.40/0.20 for spread legs.

### Phase 5: Database Schema Evolution & Order Idempotency
- [ ] Create `instruments` table via Alembic migration (`symbol`, `underlying`, `instrument_type`, `option_type`, `strike_price`, `expiry_date`, `contract_multiplier`).
- [ ] Update `orders` table: add `client_order_id` (unique index for idempotency), `instrument_id`, `parent_order_id` (multi-leg spreads), and execution prices.
- [ ] Update `portfolios` and `positions` tables to support option contract positions and Greeks.
- [ ] Preserve existing User and Auth tables.

### Phase 6: Options Paper Trading & Portfolio Greeks
- [ ] Support paper execution of single-leg and multi-leg spread orders against live mark quotes.
- [ ] Calculate aggregate portfolio Greeks exposure ($\sum \Delta, \sum \Gamma, \sum \Theta, \sum \text{Vega}$).
- [ ] Track cash balance, margin used, unrealized PnL, and realized PnL.
- [ ] Add portfolio reset and position close endpoints.

### Phase 7: Frontend Workstation & Visual Options Desk
- [ ] Fix TypeScript errors in existing Next.js frontend (`page.tsx` style bug, `market/page.tsx` series bug).
- [ ] Build `/options-chain` page with visual strike selection, IV smile, and Greeks display.
- [ ] Build `/backtest` and `/orders` pages.
- [ ] Build `/portfolio` page with aggregate Greeks risk gauges and active positions table.
- [ ] Track `frontend/` directory in Git.

### Phase 8: Multi-Timeframe Trend Intelligence & Market Structure
- [ ] Implement multi-timeframe technical indicator analysis (1D, 4H, 1H) using EMA 20/50/200, RSI 14, ATR 14.
- [ ] Derive structured directional bias (`BULLISH`, `BEARISH`, `NEUTRAL`).
- [ ] Integrate Fair Value Gap (FVG), order blocks, and key support/resistance zones.

### Phase 9: Controlled Live Execution & Multi-User Evolution
- [ ] Live exchange execution adapter with encrypted API key management.
- [ ] Strict confirmation workflows and multi-signature authorization for live trades.
- [ ] Multi-tenant organization isolation and cloud infrastructure (Docker, AWS, ECS).

