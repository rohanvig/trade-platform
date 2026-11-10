# Task Breakdown: Crypto Options Workstation Core

**Document**: TASKS-001  
**Feature**: SPEC-001  
**Status**: PENDING APPROVAL  

---

## Task Matrix & Traceability

| Task ID | Phase | Summary | Traceability | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TSK-001** | Prep | Setup `domain/`, `adapters/`, and module structures | NFR-003 | Pending |
| **TSK-002** | Domain | Implement Black-76 pricing & analytical Greeks engine with `Decimal` precision | FR-005, FR-006, NFR-001 | Pending |
| **TSK-003** | Domain | Implement Newton-Raphson + Brent Implied Volatility (IV) numerical solver | FR-007 | Pending |
| **TSK-004** | Tests | Unit test suite for Black-76 Greeks & IV solver against verified market benchmarks | AC-002 | Pending |
| **TSK-005** | Domain | Options Payoff calculator (Long Call, Long Put, Bull/Bear Debit Spreads) | FR-010, AC-003 | Pending |
| **TSK-006** | Domain | Contract Candidate Selector (DTE 14-45, Delta 0.30-0.50, spread check) | FR-011 | Pending |
| **TSK-007** | Domain | Risk Engine: 1% account risk sizer, pre-trade validator, and Kill Switch | FR-012, FR-013, FR-014, FR-015 | Pending |
| **TSK-008** | Tests | Unit tests for Risk Engine (1% enforcement, zero size rejection, kill switch) | AC-004, AC-005 | Pending |
| **TSK-009** | Adapters | Deribit Public API client (BTC & ETH index quotes, multi-timeframe candles, options chain) | FR-001, FR-002, FR-003, AC-001 | Pending |
| **TSK-010** | Database | Alembic migration & models for `instruments`, multi-leg orders, and portfolio Greeks | NFR-001, NFR-002 | Pending |
| **TSK-011** | Services | Application Services: `CryptoMarketService`, `OptionsService`, `RiskService` | NFR-003 | Pending |
| **TSK-012** | API | FastAPI endpoints for crypto quotes, chains, greeks, payoff, risk, and kill switch | FR-004, FR-006, FR-015 | Pending |
| **TSK-013** | Integration| End-to-end integration tests: quote → strike selection → risk sizing → paper order | AC-007 | Pending |
| **TSK-014** | Docs | Update API contracts, database schemas, and documentation artifacts | Section 10 | Pending |

---

## Execution Stages (Batched Workflows)

### Batch 1: Quantitative Core (Pure Domain Logic & Mathematical Verification)
- [ ] TSK-001: Directory scaffolding.
- [ ] TSK-002: Black-76 analytical pricing and Greeks in `app/domain/greeks/black76.py`.
- [ ] TSK-003: Implied Volatility solver in `app/domain/greeks/iv_solver.py`.
- [ ] TSK-004: Comprehensive unit tests in `tests/test_greeks.py`.
- [ ] TSK-005: Payoff models for single-leg and debit spreads in `app/domain/options/payoff.py`.
- [ ] TSK-006: Contract selector in `app/domain/options/selector.py`.

### Batch 2: Risk Management & Trading Safety
- [ ] TSK-007: Risk sizing (1% rule), order validation gates, and Kill Switch in `app/domain/risk/`.
- [ ] TSK-008: Automated risk unit tests in `tests/test_risk_engine.py`.

### Batch 3: Market Data & Exchange Ingestion
- [ ] TSK-009: Deribit public REST adapter in `app/adapters/deribit/client.py` and chain parser.
- [ ] TSK-010: Database migrations and instrument ORM models.

### Batch 4: Application Services & API Exposure
- [ ] TSK-011: Service orchestration in `app/services/`.
- [ ] TSK-012: FastAPI REST routers under `/api/v1/crypto`, `/api/v1/options`, `/api/v1/risk`.
- [ ] TSK-013: Integration and acceptance tests verifying all ACs.
- [ ] TSK-014: Synchronization of documentation artifacts (`docs/api.md`, `docs/database.md`, `docs/roadmap.md`).

