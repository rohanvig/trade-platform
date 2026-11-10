# TradePilot — Current Codebase Architecture & System Reality

**Document**: ARCH-CURRENT-001  
**Status**: VERIFIED GROUND TRUTH  
**Audited Date**: 2026-11-10  
**Scope**: As-built implementation in the repository (excluding unmerged plans and future specs)

---

## 1. High-Level Summary

The current repository contains an **equity paper-trading and backtesting prototype** built with **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, and an uncommitted **Next.js 16** frontend. 

The backend follows a traditional **3-tier pattern** (`Endpoints -> Services -> Repositories -> SQLAlchemy ORM`). 

It does **not** currently contain crypto options, Deribit integrations, Black-76 Greeks modeling, or a decoupled pure domain layer.

---

## 2. Capability Classification & Evidence Matrix

Every capability in the repository is classified based on direct code inspection and test execution:

* **VERIFIED**: Code exists, is wired into the runtime, and passes automated tests.
* **PARTIALLY IMPLEMENTED**: Code exists but has known gaps, missing routes, or unmocked external dependencies.
* **NOT IMPLEMENTED**: Referenced in legacy documentation or diagrams but does not exist in code.
* **PLANNED**: Target capability outlined for future milestones.
* **UNVERIFIED**: Code exists but lacks automated tests.

| Subsystem / Capability | Classification | Evidence in Codebase | Notes / Gaps |
| :--- | :--- | :--- | :--- |
| **Authentication & Users** | **VERIFIED** | [`backend/app/models/user.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/user.py)<br>[`backend/app/services/user.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/user.py)<br>[`backend/app/core/security.py`](file:///e:/portfolio/agentic-ai-project/backend/app/core/security.py) | Argon2 password hashing, JWT bearer tokens, `/register`, `/login`, `/me`. Verified by 7 passing tests in `tests/test_auth.py`. |
| **Equities Order Management** | **VERIFIED** | [`backend/app/models/order.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/order.py)<br>[`backend/app/repositories/order.py`](file:///e:/portfolio/agentic-ai-project/backend/app/repositories/order.py)<br>[`backend/app/services/order.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/order.py) | Equities orders (symbol, side: BUY/SELL, type: MARKET/LIMIT/STOP, quantity). Lifecycle states (`PENDING`, `OPEN`, `FILLED`, `CANCELLED`, `REJECTED`). Verified by 9 tests in `tests/test_orders.py`. |
| **Equities Market Data** | **PARTIALLY IMPLEMENTED** | [`backend/app/services/market.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/market.py)<br>[`backend/app/api/v1/endpoints/market.py`](file:///e:/portfolio/agentic-ai-project/backend/app/api/v1/endpoints/market.py) | Ingests equity data via `yfinance`. In-memory dictionary cache with 15s TTL. Database candle persistence is not implemented. Tests fail when run offline due to live network calls. |
| **Redis Caching** | **NOT IMPLEMENTED** | [`docker-compose.yml`](file:///e:/portfolio/agentic-ai-project/docker-compose.yml) | Redis container is defined, but `backend/app/services/market.py` uses an in-memory dictionary. `redis` is not in `backend/requirements.txt`. |
| **Technical Indicators (From Scratch)** | **VERIFIED** | [`backend/app/indicators/`](file:///e:/portfolio/agentic-ai-project/backend/app/indicators/) | SMA, EMA, RSI (Wilder's smoothing), MACD, Bollinger Bands, ATR, VWAP computed from scratch. Mathematical calculations verified by 10 unit tests in `tests/test_indicators.py`. |
| **Equities Strategy Engine** | **VERIFIED** | [`backend/app/strategies/`](file:///e:/portfolio/agentic-ai-project/backend/app/strategies/) | BaseStrategy, Strategy Registry, Dual SMA Crossover, RSI Mean Reversion, MACD Momentum crossover. Mathematical logic verified by 5 unit tests in `tests/test_strategies.py`. |
| **Equities Backtesting Simulator** | **VERIFIED** | [`backend/app/backtester/engine.py`](file:///e:/portfolio/agentic-ai-project/backend/app/backtester/engine.py) | Event-driven bar-by-bar runner, equity curve, Sharpe, Sortino, Max Drawdown, Win Rate, Profit Factor. 2 unit tests passing in `tests/test_backtester.py`. |
| **Equities Paper Portfolio** | **VERIFIED** | [`backend/app/models/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/portfolio.py)<br>[`backend/app/services/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/services/portfolio.py) | Virtual $100k cash portfolio, position tracking, unrealized PnL, live order execution against market price. |
| **Crypto Options Domain & Greeks** | **NOT IMPLEMENTED** | — | No options math, no Black-76, no Implied Volatility solver, no contract metadata, and no options chains exist in the current codebase. |
| **Exchange / Broker Adapters** | **NOT IMPLEMENTED** | — | No external broker adapter (Deribit, Alpaca, Binance) exists in the codebase. Market data is directly coupled to `yfinance`. |
| **Non-Bypassable Risk Engine** | **NOT IMPLEMENTED** | — | Currently only checks whether `cash_balance >= total_cost` in `PortfolioService`. No 1% equity risk sizing, margin ceilings, or Kill Switch exist. |
| **AI Agents & Research** | **NOT IMPLEMENTED** | — | Mentioned in legacy `README.md` and `docs/architecture.md`, but zero AI code, no `ai/` folder, and no LLM libraries exist. |
| **Next.js Web Frontend** | **PARTIALLY IMPLEMENTED** | [`frontend/src/app/`](file:///e:/portfolio/agentic-ai-project/frontend/src/app/) | Next.js 16 app exists (untracked). Implemented: Dashboard, Auth, Market Charts, Indicators, Strategies. Missing: `/backtest`, `/portfolio`, `/orders` (cause 404). Has 2 TypeScript errors (`TS1117`, `TS2339`). |

---

## 3. As-Built Backend Architecture

The backend currently runs as a single FastAPI process structured as follows:

```text
HTTP Clients (Browser / Postman / Tests)
               │
               ▼
FastAPI Routers (backend/app/api/v1/endpoints/)
    ├── health.py        (GET /api/v1/health)
    ├── user.py          (POST /register, POST /login, GET /me)
    ├── order.py         (GET/POST /orders, DELETE /orders/{id}/cancel, POST /orders/{id}/execute)
    ├── market.py        (GET /quote, GET /history, GET /search via yfinance)
    ├── indicator.py     (GET /indicators/sma, ema, rsi, macd, bollinger, atr, vwap)
    ├── strategy.py      (GET /strategies, POST /strategies/run)
    ├── backtest.py      (POST /backtest/run)
    └── portfolio.py     (GET /portfolio, GET /positions, POST /portfolio/reset)
               │
               ▼
Application Services (backend/app/services/)
    ├── user.py          (Password hashing, JWT generation)
    ├── order.py         (Order validation, execution coordination)
    ├── market.py        (yfinance calls, in-memory TTL cache)
    ├── indicator.py     (Calls pure indicator functions)
    ├── strategy.py      (Runs strategy against historical bars)
    ├── backtest.py      (Orchestrates BacktestEngine simulation)
    └── portfolio.py     (Updates cash balance, calculates unrealized PnL)
               │
               ▼
Repositories (backend/app/repositories/)
    ├── user.py          (SQLAlchemy 2.0 select queries for User)
    ├── order.py         (SQLAlchemy 2.0 select/filter/paginate for Order)
    └── portfolio.py     (SQLAlchemy 2.0 queries for Portfolio & Position)
               │
               ▼
Database Persistence
    ├── PostgreSQL 15    (Tables: users, orders, portfolios, positions)
    └── Alembic          (Migration versions in backend/alembic/versions/)
```

---

## 4. Current Database Schema Reality

The actual database consists of four tables defined via SQLAlchemy declarative models:

1. **`users`** ([`app/models/user.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/user.py)):
   * `id` (Integer, PK)
   * `email` (String(255), Unique, Indexed)
   * `hashed_password` (String(255))
   * `full_name` (String(255))
   * `is_active` (Boolean, Default True)
   * `created_at` (DateTime TZ)
2. **`orders`** ([`app/models/order.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/order.py)):
   * `id` (Integer, PK)
   * `user_id` (Integer, FK -> users.id)
   * `symbol` (String(20), Indexed)
   * `side` (Enum: `BUY`, `SELL`)
   * `order_type` (Enum: `MARKET`, `LIMIT`, `STOP`)
   * `status` (Enum: `PENDING`, `OPEN`, `FILLED`, `CANCELLED`, `REJECTED`)
   * `quantity` (Numeric(18, 8))
   * `price` (Numeric(18, 8), Nullable)
   * `created_at`, `updated_at`, `executed_at` (DateTime TZ)
3. **`portfolios`** ([`app/models/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/portfolio.py)):
   * `id` (Integer, PK)
   * `user_id` (Integer, FK -> users.id, Unique)
   * `cash_balance` (Numeric(18, 4), Default 100,000.00)
   * `created_at`, `updated_at` (DateTime TZ)
4. **`positions`** ([`app/models/portfolio.py`](file:///e:/portfolio/agentic-ai-project/backend/app/models/portfolio.py)):
   * `id` (Integer, PK)
   * `portfolio_id` (Integer, FK -> portfolios.id)
   * `symbol` (String(20), Indexed)
   * `quantity` (Numeric(18, 8))
   * `avg_entry_price` (Numeric(18, 8))
   * `created_at`, `updated_at` (DateTime TZ)

---

## 5. Architectural Deficiencies in Current State

1. **No Domain Isolation**: Business math, indicator algorithms, and strategy rules are scattered across `app/indicators/`, `app/strategies/`, and `app/backtester/` without a unified, pure domain layer.
2. **Coupled Data Provider**: `MarketDataService` directly calls `yfinance.Ticker` inside the service method, preventing offline testing and swapping data providers.
3. **No Contract Representation**: The database cannot represent options (no strike price, no expiry date, no option type, no multiplier).
4. **Test Suite Network Dependency**: 17 of 56 tests fail offline because endpoint tests make live network calls to Yahoo Finance instead of using test fixtures.

