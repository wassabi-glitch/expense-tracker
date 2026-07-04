# Epic 2: Debt & Obligation Architecture

**Status:** Not Started  
**Depends On:** Epic 1 (Ledger Foundation)

## Goal
Define the complete domain model for financial obligations — how debts enter the system, the strict boundary between open-ended debts and scheduled payment plans, and the full lifecycle engine for payment plans including statuses, the waterfall spillover, forgiveness, and the imported-balance path. These three ADRs establish the obligation domain on top of Epic 1's ledger integrity rules.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0003 — Debt Epoch & The Dual Path Rule](../adr/0003-debt-epoch-and-history.md)**
   - Defines how debts enter the system without corrupting the wallet's opening snapshot. New debts (today's borrowing/lending) flow through wallets and respect the epoch boundary. Pre-existing debts use the `IMPORTED_BALANCE` path — wallet-disconnected, remaining-balance-only, with historical dates as decorative metadata.

2. [ ] **[ADR 0004 — Obligation Mutual Exclusivity: Debt vs Payment Plan](../adr/0004-obligation-mutual-exclusivity.md)**
   - Enforces strict structural decoupling. A financial obligation is either an open-ended Debt (running tab, informal IOU) or a closed-end Payment Plan (car loan, store installment) — never both. Removes the `debt_id` FK from Payment Plans and eliminates the "ghost ledger" synchronization trap where a hidden Debt maintained a parallel balance.

3. [ ] **[ADR 0005 — Payment Plan Engine, Statuses & Budget Boundary](../adr/0005-payment-plan-engine-and-status.md)**
   - The most comprehensive ADR in this group. Defines:
     - **Parent statuses:** `OPEN` / `CLOSED` only (UI visibility, not lifecycle detail).
     - **Schedule row statuses:** `PENDING` / `PARTIAL` / `PAID` (no `SKIPPED`, no stored `OVERDUE`).
     - **Waterfall Spillover Engine:** Payments sweep `CHARGE` rows first, then spill into oldest `PRINCIPAL` rows.
     - **Budget Boundary:** The backend halts with `expenses.budget_required` when a payment hits an unbudgeted category — never auto-materializes a budget.
     - **Row & Parent Actions:** Pay, defer, forgive (row-level write-off), add charge, principal reduction, force-close.
     - **Imported Path:** Mirrors ADR 0003's dual path for historical payment plans with decorative metadata.

## Why This Order
- ADR 0003 establishes the entry rules: how obligations get born without breaking the wallet epoch (Epic 1).
- ADR 0004 cleans the structural foundation: no more tangled debt↔plan FKs. This must happen before the engine can be trusted.
- ADR 0005 builds the full engine on that clean foundation: statuses, waterfall, actions, budget boundary.

## Execution Rules
- ADR 0004's migration (removing `debt_id` FK, deleting shadow Debt records for linked Payment Plans) is a high-risk database operation. Must be executed with a reversible migration and tested against production-shaped data.
- ADR 0005's budget boundary rule (`expenses.budget_required` error) defines the *backend contract*. The corresponding frontend interceptor UX is governed by ADR 0009 in a later epic.
- The waterfall engine (ADR 0005 §3) is already architecturally correct per the ADR — preserve and validate, do not rewrite.
