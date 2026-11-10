# TradePilot Project Constitution

**Status**: PERMANENT & MANDATORY  
**Authority**: Senior Software Architect & Project Lead  
**Scope**: All architectural decisions, source code, data pipelines, and trading systems in TradePilot.

---

## 1. Core Principles

### Principle 1: Specifications Are the Source of Truth
No functional behavior, trading calculation, risk parameter, or API route may be implemented or altered without an approved feature specification (`spec.md`). If the code contradicts an approved specification, the code is considered defective.

### Principle 2: Financial Precision and Numeric Correctness
Binary floating-point arithmetic (`float`) introduces inexcusable cumulative rounding errors in financial and options accounting.
* All currency amounts, strikes, premiums, margins, cash balances, and position sizes must use Python `Decimal` with explicit rounding contexts (`ROUND_HALF_EVEN`) or database `NUMERIC(18, 8)`.
* Contract quantities and lot sizes must respect the minimum tick and step size of the specific instrument.

### Principle 3: Exchange Contract Specifications Must Be Verified
Never assume contract specifications, settlement mechanisms, or margin models across exchanges.
* For Deribit European crypto options: verify contract multipliers (e.g., 1.0 BTC or 1.0 ETH), coin-margining vs. linear USDC settlement, forward index basis, and expiry settlement times (08:00 UTC).
* Every exchange integration must verify contract metadata against official exchange specifications before placing orders or calculating Greeks.

### Principle 4: Decoupled Domain Architecture
Core domain logic (Black-76 options math, Greeks, payoff calculations, risk sizing, and signal generation) must remain completely independent of:
* Web frameworks (FastAPI, Starlette)
* ORM and persistence frameworks (SQLAlchemy, Alembic)
* External exchange SDKs or HTTP libraries (`httpx`, `curl_cffi`, `requests`)

Domain models must be pure Python objects / dataclasses testable in complete isolation without a running database or network connection.

### Principle 5: Isolated Exchange Adapters
All communication with external trading venues, market data feeds, and broker endpoints must occur through strictly isolated adapter interfaces (`MarketDataAdapter`, `ExecutionAdapter`).
* Adapters translate external schemas into internal domain representations.
* No exchange-specific data structure may leak into services, strategies, or repositories.

### Principle 6: Non-Bypassable Risk Engine
The risk management subsystem acts as an uncompromisable gatekeeper.
* Every executable order—whether initiated by an automated strategy, AI assistant, or human trader—must pass pre-trade validation by the `RiskEngine`.
* Strategies and order services must never have direct write access to order routing without risk approval.
* An emergency **Kill Switch** must be available at all times to instantly halt all order submissions and cancel open paper orders.

### Principle 7: Paper Trading by Default
Safety is non-negotiable.
* The default, unconfigured system execution mode is `PAPER`.
* Live exchange execution must remain strictly disabled and unreachable until explicitly enabled via audited configuration flags (`LIVE_TRADING_ENABLED=True`) and explicit per-session confirmation.

### Principle 8: Auditability and Traceability
All financial operations, order submissions, execution fills, cancellations, and risk rejections must be auditable.
* Order lifecycle state transitions (`PENDING -> OPEN -> FILLED / CANCELLED / REJECTED`) must be recorded with UTC timestamps and state transition reasons.
* Calculations leading to position sizing and risk rejections must be logged.

### Principle 9: Idempotency and Safe Retries
All order submissions and execution calls must support client-generated idempotency keys (`client_order_id`). Duplicate submissions must be detected and rejected gracefully without creating duplicate orders or double fills.

### Principle 10: Preservation of Working Foundations
Existing working authentication (Argon2 password hashing, OAuth2 JWT tokens), database configurations, and core patterns must be preserved. Never introduce rewrite churn or duplicate database sessions, configuration objects, or Base classes.

### Principle 11: Testing Critical Financial Paths
Automated tests are required for:
* Analytical pricing and options Greeks accuracy against verified financial benchmarks.
* Implied Volatility (IV) solver convergence across extreme regimes.
* Spread payoff calculations (Net Debit, Max Loss, Max Profit, Breakevens).
* Risk sizing limits, margin utilization checks, and Kill Switch halts.
* Order lifecycle transitions and idempotency protections.

### Principle 12: Architectural Governance & Decisions
Material changes to the architecture, database schema, or domain interfaces require an Architecture Decision Record (ADR) or an approved `plan.md` before execution.

### Principle 13: Initial Product Defaults vs. Mathematical Truths
* **1% Risk per Trade**: The maximum 1% account equity risk per trade is an initial configurable product safety default, designed for swing trading capital preservation. It is not an immutable mathematical constant and may be adjusted via explicit configuration within safe boundaries.
* **BTC & ETH Asset Universe**: BTC and ETH are initial product focus assets due to their options liquidity on Deribit. The architecture must remain instrument-agnostic to support other assets (e.g., SOL) in future milestones without redesigning the core.

### Principle 14: Prohibition of Unapproved Implementation
No agent or engineer may create or modify application source code without an approved specification, technical plan, and task list.

