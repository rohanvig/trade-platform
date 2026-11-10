# TradePilot — Product Context & Vision

**Document**: PRODUCT-CONTEXT-001  
**Status**: APPROVED BASELINE  
**Product**: TradePilot (Crypto Options Swing-Trading Workstation)

---

## 1. Product Vision & Evolution

TradePilot is conceived as a **high-precision personal crypto options swing-trading workstation**, engineered initially around the most liquid crypto derivatives markets: **BTC** and **ETH**.

### Evolution Strategy:
1. **Phase 1 (Current Target — Personal Workstation)**:
   A single-trader or personal workstation offering deep market intelligence, multi-timeframe trend analysis (1D, 4H, 1H), automated Deribit options chain ingestion, Black-76 Greeks analytics, defined-risk strategy construction (Long Calls/Puts, Debit Spreads), automated 1% equity risk sizing, paper trading, and trade journaling.
2. **Phase 2 (Future Target — Commercial Multi-User Platform)**:
   Evolve the architecture into a secure, scalable, multi-tenant commercial trading platform supporting multi-user portfolio isolation, organization-level risk controls, multi-broker routing, automated webhooks, and cloud-scale backtesting.

---

## 2. Core Functional Pillars

### 2.1 Market Intelligence & Data Feeds
* Ingest real-time underlying index and perpetual quotes for BTC and ETH.
* Multi-timeframe OHLCV bar aggregation (1D for macro trend, 4H for swing momentum, 1H for precise entry/exit timing).
* Full options chain ingestion from Deribit (expirations, strikes, bids, asks, mark prices, IV, and open interest).

### 2.2 Technical Analysis Engine
* Trend, momentum, and volatility indicators computed from scratch:
  * Exponential Moving Averages (EMA 20, 50, 200)
  * Relative Strength Index (RSI 14)
  * Average True Range (ATR 14)
  * Volume Profile and Volume Moving Averages
* Multi-timeframe directional bias derivation (`BULLISH`, `BEARISH`, `NEUTRAL`).

### 2.3 Options Analytics & Greeks Engine
* **Black-76 Pricing Model**: European option valuation on forward prices.
* **Analytical Greeks**: First- and second-order Greeks ($\Delta, \Gamma, \Theta, \nu, \rho$) computed continuously across active chains.
* **Implied Volatility (IV) Extraction**: Newton-Raphson solver with Brent fallback for reliable IV calibration across strikes.
* **Option Chain Surface**: Visualizing IV smile, skew, and term structure.

### 2.4 Strategy Research & Selection
* Construction of defined-risk option structures suited for swing trading:
  * **Long Call**: Bullish breakout/continuation.
  * **Long Put**: Bearish breakdown/downside hedge.
  * **Bull Call Debit Spread**: Lower strike long call + higher strike short call (same expiry) to mitigate theta decay and volatility crush.
  * **Bear Put Debit Spread**: Higher strike long put + lower strike short put (same expiry).
* Automated strike and expiration filtering: targeting 14 to 45 Days to Expiration (DTE), 0.30 to 0.50 Delta, and liquid bid-ask spreads ($<5\%$).

### 2.5 Risk Management & Trading Safety
* **1% Account Risk Sizing Default**: Automated calculation of contract lots based on maximum trade loss $\le 1\%$ of current account equity.
* **Pre-Trade Validation Gates**: Checks for margin utilization ($<50\%$), spread sanity, and quote freshness.
* **Emergency Kill Switch**: Immediate cessation of new orders and cancellation of pending orders.

### 2.6 Paper Trading & Order Management
* Default paper trading simulator executing orders against live Deribit mark prices.
* Support for single-leg and multi-leg spread execution with deterministic state transitions (`PENDING -> OPEN -> FILLED / CANCELLED / REJECTED`).
* Tracking portfolio cash balance, active positions, unrealized/realized PnL, and aggregate portfolio Greeks ($\sum \Delta, \sum \Gamma, \sum \Theta, \sum \text{Vega}$).

### 2.7 Backtesting & Strategy Evaluation
* Historical simulation of options strategies on historical price and volatility datasets.
* Comprehensive performance analytics: CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate, and Equity Curves.

### 2.8 Trading Journal & Audit Log
* Continuous logging of order rationales, market conditions at execution, and trade lifecycle events.
* Performance attribution by strategy type, underlying asset, and market regime.

---

## 3. Current Implementation Reality vs. Target Vision

To maintain complete intellectual honesty, the table below clearly demarcates what is currently implemented in the codebase versus what is planned:

| Capability | Current Status in Codebase | Target Vision |
| :--- | :--- | :--- |
| **Asset Universe** | Equities (`AAPL`, `MSFT`) via `yfinance`. | Crypto (`BTC`, `ETH`) via public Deribit REST API. |
| **Market Data** | Quotes & historical bars via `yfinance` with in-memory TTL caching. | Multi-timeframe (1D, 4H, 1H) crypto candles + full options chain from Deribit. |
| **Technical Indicators** | SMA, EMA, RSI, MACD, ATR, Bollinger, VWAP written from scratch on equity bars. | Multi-timeframe trend alignment and market structure on BTC/ETH. |
| **Options Analytics / Greeks** | **Not Implemented (0%)**. | Black-76 analytical Greeks, numerical IV solver, payoff diagrams, strike selection. |
| **Strategy Engine** | Simple equity SMA and RSI crossover strategies. | Defined-risk options strategies (Long Calls/Puts, Bull/Bear Debit Spreads). |
| **Risk Engine** | Rudimentary cash check in `PortfolioService`. | Rigorous pre-trade validation, 1% equity sizing, margin ceiling, emergency Kill Switch. |
| **Order Management** | Implemented for equities (Market, Limit, Stop orders) with repository pattern. | Extended for options contract metadata, multi-leg spreads, and `client_order_id` idempotency. |
| **Paper Trading** | $100k equity paper portfolio tracking stock positions and cash. | Virtual portfolio tracking options contracts, Greeks sensitivities, and multi-leg positions. |
| **Backtesting Engine** | Bar-by-bar stock simulator with commissions and slippage. | Options backtester supporting time decay, delta changes, and spread expirations. |
| **Frontend UI** | Next.js 16 dashboard with Market, Indicators, Strategies (untracked, 2 type errors). | Comprehensive trading desk with options chain, payoff graphs, backtest UI, and portfolio monitor. |
| **Multi-User Commercial** | Basic JWT auth and User table present. | Multi-tenant tenant isolation, API key vault, enterprise RBAC, cloud deployment. |

