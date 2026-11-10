# TradePilot — Architecture Principles & Target Boundaries

**Document**: ARCH-PRINCIPLES-001  
**Status**: APPROVED TARGET ARCHITECTURE  
**Scope**: Backend System Design, Domain Boundaries, and Data Flow

---

## 1. Target Layered Architecture

To achieve long-term maintainability, complete unit testability, and financial safety, TradePilot establishes a strict 5-layer separation of concerns.

> **Note on Implementation Status**: The current codebase implements a 3-tier structure (`FastAPI -> Services -> Repositories -> SQLAlchemy`). The pure `Domain` layer and isolated `Adapters` layer defined below represent the **target architecture** to be introduced in Milestone 1 and adhered to in all subsequent milestones.

```text
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Controllers)                  │
│   FastAPI Routers, HTTP Validation, Request/Response DTOs   │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Calls Services)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Application Services (Orchestration)            │
│   Workflow coordination, transactional boundaries, auth     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌───────────────────────────────┐ ┌───────────────────────────┐
│         Domain Layer          │ │      Adapters Layer       │
│  Pure financial math, Greeks, │ │  Exchange API clients,    │
│  payoffs, risk sizing, bias   │ │  external market feeds    │
│  (Zero framework dependencies)│ │  (Deribit, Binance, etc.) │
└──────────────┬────────────────┘ └───────────────────────────┘
               │ (Persistence Models)
               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Repositories (Data Access)                  │
│       SQLAlchemy 2.0 select / execute queries & filters     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database & Persistence                    │
│             PostgreSQL 15 (Relational Storage)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities & Rules

### 2.1 API Layer (`app/api/`)
* **Responsibilities**: Handles HTTP requests, parameter validation via Pydantic schemas, dependency injection (authentication, db sessions), and HTTP status codes.
* **Constraints**: Must **never** execute financial calculations, run database queries directly, or interact with external exchange APIs.

### 2.2 Application Services (`app/services/`)
* **Responsibilities**: Orchestrates business workflows across domain engines and repositories. Handles transactions, coordinates event logging, and translates between DTOs and domain models.
* **Constraints**: Does not perform raw mathematical modeling; delegates mathematical computations to the Domain layer.

### 2.3 Domain Layer (`app/domain/`) — Pure Core
* **Responsibilities**: The heart of the platform. Encapsulates:
  * Black-76 pricing and analytical Greeks calculations.
  * Numerical Implied Volatility (IV) solvers.
  * Options payoff diagrams and spread metrics.
  * Strike and expiration selection algorithms.
  * Risk sizing calculations (1% equity risk rule) and pre-trade validation gates.
  * Technical indicator math and multi-timeframe trend alignment.
* **Strict Constraints**: Must be **100% pure Python**. Zero imports of FastAPI, Starlette, SQLAlchemy, Alembic, or external exchange SDKs. All models are pure Python dataclasses or Pydantic domain models. Must be testable without network or database access.

### 2.4 External Adapters (`app/adapters/`)
* **Responsibilities**: Encapsulates all external network communication with exchanges, market data feeds, or third-party APIs (e.g., Deribit public REST API).
* **Constraints**: Converts third-party JSON schemas into standardized domain objects. No exchange-specific field names or quirks may leak past the adapter boundary into application services.

### 2.5 Repository Layer (`app/repositories/`)
* **Responsibilities**: Manages database persistence using SQLAlchemy 2.0. Implements explicit queries, filtering, pagination, and transactional commits.
* **Constraints**: Encapsulates all ORM details so the rest of the application remains decoupled from database schema specifics.

---

## 3. Cross-Cutting Architectural Requirements

### 3.1 Financial Precision
* Binary floating-point representation (`float`) is prohibited for currency values, strike prices, option premiums, cash balances, and position lot sizes.
* Calculations must use Python `Decimal` with explicit rounding modes (`ROUND_HALF_EVEN`).
* Database columns must use `NUMERIC(18, 8)` or `NUMERIC(18, 4)`.

### 3.2 Security & Authentication
* Passwords must be hashed using Argon2 (`pwdlib`) with memory and computation hardness.
* Authentication uses OAuth2 Password Bearer flow with HMAC-SHA256 (`HS256`) JWTs.
* Exchange API keys (when added for live trading in future phases) must be encrypted at rest and never returned in API responses or written to logs.

### 3.3 Auditability & Idempotency
* All state transitions (`PENDING -> OPEN -> FILLED / CANCELLED / REJECTED`) must be stamped with UTC timestamps and audit reasons.
* Every order creation endpoint must accept an optional or required `client_order_id` to guarantee idempotent execution and protect against network retries.

### 3.4 Testability
* Every domain component must have unit test coverage verifying accuracy against analytical references.
* External adapters must have mock fixtures for offline testing.
* Application services and endpoints must be verified with integration tests using an isolated test database.

### 3.5 Future Multi-User & Commercial Isolation
* Even in the V1 personal workstation, every database query and operation must filter by `user_id`.
* Global state is prohibited in application services; all state must reside in the database or be passed explicitly per request.
* This ensures that evolving from a single-user personal workstation to a multi-tenant commercial SaaS product requires no foundational schema redesign.

