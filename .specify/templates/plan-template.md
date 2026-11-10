# Technical Architecture & Implementation Plan: [Feature Name]

**Document**: PLAN-[XXX]  
**Feature**: SPEC-[XXX]  
**Status**: [DRAFT | PENDING APPROVAL | APPROVED | IMPLEMENTED]  
**Author**: [Author Name / Role]  

---

## 1. Existing Architecture Analysis
*Analyze the existing code, database models, services, and endpoints related to this feature. Identify reusable components and potential breaking changes.*

---

## 2. Proposed Technical Design & System Architecture
*Describe the high-level design, layer interactions, and sequence flow.*

```text
[API Controller] ──> [Application Service] ──> [Domain Model/Engine] ──> [Repository / Adapter]
```

---

## 3. Module Boundaries & Directory Structure

```text
backend/app/
├── api/v1/endpoints/
│   └── [new or modified endpoints]
├── services/
│   └── [service orchestration]
├── domain/
│   └── [pure domain logic and financial math]
├── adapters/
│   └── [external exchange integration]
├── repositories/
│   └── [data access queries]
├── models/
│   └── [SQLAlchemy ORM models]
└── schemas/
    └── [Pydantic v2 schemas]
```

---

## 4. Database Schema Changes & Migrations
*Detail all new tables, column modifications, indexes, foreign keys, and constraints.*
- **New Tables**: [Table definitions and columns]
- **Modified Tables**: [Columns added, modified, or foreign keys]
- **Alembic Migration Plan**: [Migration script name and execution strategy]

---

## 5. API Contracts & Endpoint Definitions
*Specify HTTP methods, paths, request payloads, and response structures.*

### Endpoint: `[METHOD] /api/v1/[path]`
- **Description**: [Summary]
- **Request Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {}
  ```
- **Response `200 OK`**:
  ```json
  {}
  ```
- **Error Responses**: `400 Bad Request`, `422 Unprocessable Entity`

---

## 6. Security & Safety Considerations
- **Authentication & Authorization**: How access is controlled.
- **Financial Validation**: Non-bypassable risk engine gates, max loss verification.
- **Idempotency**: Client order ID handling and duplicate detection.
- **Kill Switch**: How this feature behaves when trading is halted.

---

## 7. Testing Strategy
- **Unit Tests**: Pure domain logic, mathematical correctness, edge cases.
- **Integration Tests**: Repository queries, database transactions, service orchestration.
- **API Tests**: Endpoint status codes, schema validation, auth enforcement.
- **Mocking**: External exchange feeds and third-party APIs.

---

## 8. Risks, Trade-offs & Alternative Approaches
| Option / Approach | Pros | Cons | Selected? | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Approach A** | ... | ... | [Yes/No] | ... |
| **Approach B** | ... | ... | [Yes/No] | ... |

---

## 9. Architecture Decisions (ADRs)
- **ADR-01**: [Decision summary, context, and consequences]
- **ADR-02**: [Decision summary, context, and consequences]

