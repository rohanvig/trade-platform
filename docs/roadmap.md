# TradePilot — Development Roadmap

This document outlines the phased development plan for the TradePilot platform, detailing completed milestones and immediate upcoming targets.

---

## Milestone Overview

| Phase | Milestone | Status | Key Deliverables |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Foundation & Core Backend | 🟢 Complete (100%) | Auth, JWT, Orders API, Repository Pattern, Docker, CORS, Pytest |
| **Phase 2** | Market Data Service | 🟢 In Progress (85%) | Historical Bars (OHLCV), Live Quotes, Symbol Search, TTL Caching |
| **Phase 3** | Technical Indicators (From Scratch) | 🟢 Complete (100%) | SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP |
| **Phase 4** | Strategy Engine | 🟢 Complete (100%) | BaseStrategy, Registry, SMA Crossover, RSI Reversion, MACD |
| **Phase 5** | Backtesting Engine | 🟢 Complete (100%) | Historical Simulator, Equity Curve, Drawdown, Sharpe, Sortino |
| **Phase 6** | Paper Trading | 🟢 Complete (100%) | Virtual Portfolio, Live Quote Execution, Position Tracking |
| **Phase 7** | Broker Integration | ⚪ Planned | Live Broker API Adapter, Webhooks, Order Routing |
| **Phase 8** | AI-Assisted Trading Research | ⚪ Planned | Market News Summarizer, LLM Agent Analysts, Journal Copilot |
| **Phase 9** | Web Dashboard (Frontend) | ⚪ Planned | Next.js App, TradingView Lightweight Charts, Order Book |
| **Phase 10** | Cloud Deployment & CI/CD | ⚪ Planned | Docker Production Images, GitHub Actions, AWS / ECS Deployment |

---

## Detailed Checklists

### Phase 1 — Foundation & Core Backend
- [x] Repository setup and clean directory structure
- [x] FastAPI application initialization and Pydantic Settings
- [x] PostgreSQL & Redis via Docker Compose
- [x] SQLAlchemy 2.0 ORM with Alembic migration pipeline
- [x] User registration with Argon2 password hashing
- [x] OAuth2 JWT authentication (`/login`, `/me`)
- [x] Order model, schema validation, and database tables
- [x] Order creation and user-specific order queries
- [x] System Architecture Documentation (`docs/architecture.md`)
- [x] CORS middleware configuration
- [x] Order cancellation endpoint (`POST /orders/{id}/cancel`)
- [x] Order filtering (by status, symbol) and pagination
- [x] Pytest testing suite for auth and order endpoints

### Phase 2 — Market Data Ingestion & Storage
- [x] Historical market data download adapter (`yfinance` provider)
- [x] Real-time quote endpoint (`GET /api/v1/market/quote?symbol=...`)
- [x] In-memory TTL caching for frequent quote requests (15s TTL)
- [x] Historical bars endpoint (`GET /api/v1/market/history?symbol=...&timeframe=...`)
- [x] Symbol search and metadata autocomplete endpoint
- [ ] OHLCV Candle persistent database model & migration

### Phase 3 — Technical Indicators (From Scratch)
- [x] Simple Moving Average (SMA)
- [x] Exponential Moving Average (EMA)
- [x] Relative Strength Index (RSI - Wilder's Smoothing)
- [x] Moving Average Convergence Divergence (MACD)
- [x] Average True Range (ATR)
- [x] Bollinger Bands
- [x] Volume-Weighted Average Price (VWAP)
- [x] Indicator endpoints (`GET /api/v1/indicators/*`)
- [x] Automated test suite verifying indicator mathematical correctness (17 tests)

### Phase 4 — Strategy Engine
- [x] Base Strategy abstract class and interface (`BaseStrategy`)
- [x] Dual SMA Crossover strategy (`SMACrossoverStrategy`)
- [x] RSI Mean-Reversion strategy (`RSIMeanReversionStrategy`)
- [x] MACD momentum crossover strategy (`MACDCrossoverStrategy`)
- [x] Dynamic Strategy Registry (`list_strategies`, `get_strategy`)
- [x] Signal generation (`BUY`, `SELL`, `HOLD`) with timestamps & reasons
- [x] Automated Stop Loss and Take Profit risk calculations
- [x] Strategy endpoints (`GET /api/v1/strategies`, `POST /api/v1/strategies/run`)
- [x] Automated test suite for strategies (7 tests)

### Phase 5 — Backtesting Engine
- [x] Event-driven bar-by-bar backtest runner (`BacktestEngine`)
- [x] Intra-bar Stop Loss and Take Profit execution checks
- [x] Configurable commissions and slippage simulation
- [x] Full performance metrics: Net Profit, CAGR, Max Drawdown, Win Rate, Profit Factor
- [x] Risk-adjusted ratios: Sharpe Ratio & Sortino Ratio
- [x] Timestamped Equity Curve timeseries output for charting
- [x] Backtesting API endpoint (`POST /api/v1/backtest/run`)
- [x] Automated test suite for Backtesting Engine (5 tests)

### Phase 6 — Paper Trading & Virtual Portfolio
- [x] SQLAlchemy models for `Portfolio` ($100k virtual cash) and `Position`
- [x] PortfolioRepository managing cash, positions, and average buy price updates
- [x] PortfolioService calculating live unrealized PnL and total portfolio value
- [x] Simulated order execution against live market quotes (`POST /orders/{id}/execute`)
- [x] Immediate paper execution support on order creation (`POST /orders?execute=true`)
- [x] Insufficient funds and insufficient shares validation
- [x] Portfolio endpoints (`GET /api/v1/portfolio`, `GET /api/v1/portfolio/positions`)
- [x] Automated test suite for Paper Trading (5 tests)

---

*Updated: October 2026*
