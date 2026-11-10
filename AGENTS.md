# AGENTS.md — Spec-Driven Development (SDD) Operating Instructions for TradePilot

Welcome to **TradePilot**. All AI coding agents, autonomous subagents, and human contributors operating in this repository must adhere strictly to these Spec-Driven Development (SDD) instructions.

TradePilot is a financial trading workstation where **correctness, risk management, and auditable safety take absolute priority over implementation speed**.

---

## 1. Golden Rules for Agents

Every agent working on this codebase must follow these mandatory operating rules:

1. **Inspect Existing Code First**: Always inspect relevant existing modules, directory structures, schemas, database models, and dependencies before proposing or implementing changes. Never guess architecture or interfaces.
2. **Never Implement Without an Approved Specification**: No functional change, new feature, or architectural refactor may be implemented without an approved specification (`spec.md`), implementation plan (`plan.md`), and task breakdown (`tasks.md`).
3. **Traceability is Mandatory**: Maintain strict traceability:
   $$\text{Requirement (FR/NFR)} \longrightarrow \text{Design (Plan)} \longrightarrow \text{Task (TSK)} \longrightarrow \text{Implementation (Code)} \longrightarrow \text{Verification (Test)}$$
4. **Preserve Working Functionality**: Do not break, rewrite, or delete existing working authentication, database migrations, or utility modules without documented justification and explicit approval.
5. **Enforce Financial Precision**: Never use floating-point types (`float`) for monetary amounts, option strikes, premiums, or account balances. Use Python `Decimal` with explicit rounding contexts or PostgreSQL `NUMERIC(18, 8)`.
6. **Protect the Risk Engine**: The risk engine is sovereign. Strategies, order routers, and execution adapters must never bypass pre-trade risk validation gates or the emergency Kill Switch.
7. **Paper Trading by Default**: The default execution mode is always `PAPER`. Live trading execution must remain disabled and unreachable unless explicitly authorized with safety controls.
8. **Work in Cohesive Batches**: After a specification, technical plan, and task list have been approved by the user, implement in complete, cohesive milestones rather than asking permission for every individual line of code.
9. **Never Claim Tests Passed Without Execution**: Execute unit and integration tests and report exact terminal results. Never fabricate test outcomes.
10. **Report Transparently**: Following every implementation batch, report:
    * Files created or modified
    * Actual implementation completed
    * Tests executed and exact results
    * Known limitations or edge cases
    * Remaining tasks and any approved deviations

---

## 2. Standard 10-Step SDD Workflow

Every feature lifecycle must proceed through these ordered steps:

```text
[Step 1: Inspect Code]
       ↓
[Step 2: Requirement Discovery & spec.md]
       ↓
[Step 3: Technical Research & research.md (if needed)]
       ↓
[Step 4: Architecture Design & plan.md]
       ↓
[Step 5: Actionable Task Breakdown & tasks.md]
       ↓
[Step 6: Human Review & Explicit Approval]  <--- STOP HERE UNTIL APPROVED
       ↓
[Step 7: Batched Implementation]
       ↓
[Step 8: Automated Testing & Verification]
       ↓
[Step 9: Documentation Synchronization]
       ↓
[Step 10: Completion Reporting & Status Update]
```

---

## 3. Governance Reference Files

Agents must consult the following governing documents located in `.specify/memory/` and `.specify/templates/`:

* **Constitution**: [`.specify/memory/constitution.md`](file:///e:/portfolio/agentic-ai-project/.specify/memory/constitution.md) — The permanent project constitution, non-negotiable principles, and trading safety requirements.
* **Product Context**: [`.specify/memory/product-context.md`](file:///e:/portfolio/agentic-ai-project/.specify/memory/product-context.md) — Product vision, target personas, asset universe (BTC/ETH), and feature roadmap.
* **Architecture Principles**: [`.specify/memory/architecture-principles.md`](file:///e:/portfolio/agentic-ai-project/.specify/memory/architecture-principles.md) — Decoupled layered architecture (`API -> Service -> Domain -> Repo -> DB`), adapter boundaries, and security rules.
* **Specification Template**: [`.specify/templates/spec-template.md`](file:///e:/portfolio/agentic-ai-project/.specify/templates/spec-template.md)
* **Plan Template**: [`.specify/templates/plan-template.md`](file:///e:/portfolio/agentic-ai-project/.specify/templates/plan-template.md)
* **Tasks Template**: [`.specify/templates/tasks-template.md`](file:///e:/portfolio/agentic-ai-project/.specify/templates/tasks-template.md)
* **Current System Reality**: [`docs/architecture/current-architecture.md`](file:///e:/portfolio/agentic-ai-project/docs/architecture/current-architecture.md) & [`docs/project-status.md`](file:///e:/portfolio/agentic-ai-project/docs/project-status.md) — The verified ground truth of the current codebase.

---

## 4. Response Format for Feature Proposals

Before implementing any feature, agents must respond in the following structured format:

1. **Objective**
2. **Existing Implementation Findings**
3. **Requirements (FRs & NFRs)**
4. **Proposed Technical Design**
5. **Files and Modules Affected**
6. **Database / API Changes**
7. **Implementation Plan & Task Breakdown**
8. **Testing Strategy**
9. **Risks and Unresolved Decisions**
10. **Acceptance Criteria**

**Stop and await explicit human approval** before creating or modifying application source code.

