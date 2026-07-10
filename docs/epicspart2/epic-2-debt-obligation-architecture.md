# Epic 2: Debt & Obligation Architecture

**Status:** Not Started  
**Depends On:** Epic 1 (Ledger Foundation)

## Goal

Define the current obligation architecture for Sarflog: simplified Debt state, Debt-owned ledger actions, explicit Payment Plan schedule models, and row/plan action rules that preserve truthful money history. This epic now uses ADR 0026-0029 as the active execution sequence.

The older ADR 0003-0005 list is commented out below as historical context only. Those ADRs may still contain useful background, but they are not the live Epic 2 execution set.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0026 - Debt Derived State and Taxonomy Simplification](../adr/0026-debt-derived-state-and-taxonomy-simplification.md)**
   - Makes Debt state derived instead of stored. Debt exposes `lifecycle_status` and `time_status` from balance, due date, and user timezone.
   - Separates archive from lifecycle through `archived_at`.
   - Removes Payment Plan product vocabulary from Debt by eliminating `DebtProductKind`.
   - Keeps Debt focused on origin, counterparty, balance, and due date.

2. [ ] **[ADR 0027 - Debt Ledger Actions, Principal/Charges, and Reversal Rules](../adr/0027-debt-ledger-actions-principal-charges-and-reversals.md)**
   - Defines Debt ledger entries as durable balance history: `INITIAL`, `CHARGE`, `PAYMENT`, `FORGIVENESS`, `ADJUSTMENT`, `REVERSAL`, and future asset settlement.
   - Requires append-only reversals, latest-first reversal guards, and FinancialEvent reversal when wallet money was touched.
   - Splits Debt creation into principal, opening charges, and wallet movement so balance and cash movement are not falsely treated as the same fact.
   - Makes payment allocation between principal and charges explicit.

3. [ ] **[ADR 0028 - Payment Plan Schedule Models and Contract Review](../adr/0028-payment-plan-schedule-models-and-contract-review.md)**
   - Adds explicit Payment Plan schedule models: `FLAT_TOTAL`, `AMORTIZED_LOAN`, and `MANUAL_CONTRACT_SCHEDULE`.
   - Separates product language (`plan_type`) from schedule math (`schedule_model`).
   - Defines flat installment math, amortized loan generation, and manual contract schedules.
   - Requires generated schedules to be reviewable before creation.
   - Refines the Payment Plan waterfall to apply across the whole unpaid schedule: oldest due date first, and within the same due date `CHARGE` before `PRINCIPAL`.

4. [ ] **[ADR 0029 - Payment Plan Row Actions, Write-Offs, and Architecture Cleanup](../adr/0029-payment-plan-row-actions-write-offs-and-architecture-cleanup.md)**
   - Makes row write-off and plan-level write-off first-class actions.
   - Reframes row state as settlement state: `UNPAID`, `PARTIAL`, `SETTLED`; overdue remains derived from user-local date.
   - Adds a dedicated Payment Plan ledger entry type for `WRITE_OFF` instead of treating forgiveness as a generic adjustment.
   - Requires append-only reversals for payments, charges, write-offs, and adjustments.
   - Clarifies the target architecture: schedule rows say what is due, allocations say how actions touched rows, ledger entries say what happened historically, and derived totals say where the plan stands today.

<!--
## Historical ADRs Commented Out

These were the previous live Epic 2 ADRs. They are kept here only as commented historical context while Epic 2 moves to ADR 0026-0029 as the active execution sequence.

1. [ ] **[ADR 0003 - Debt Epoch & The Dual Path Rule](../adr/0003-debt-epoch-and-history.md)**
   - Defines how debts enter the system without corrupting the wallet's opening snapshot. New debts (today's borrowing/lending) flow through wallets and respect the epoch boundary. Pre-existing debts use the `IMPORTED_BALANCE` path - wallet-disconnected, remaining-balance-only, with historical dates as decorative metadata.

2. [ ] **[ADR 0004 - Obligation Mutual Exclusivity: Debt vs Payment Plan](../adr/0004-obligation-mutual-exclusivity.md)**
   - Enforces strict structural decoupling. A financial obligation is either an open-ended Debt (running tab, informal IOU) or a closed-end Payment Plan (car loan, store installment) - never both. Removes the `debt_id` FK from Payment Plans and eliminates the "ghost ledger" synchronization trap where a hidden Debt maintained a parallel balance.

3. [ ] **[ADR 0005 - Payment Plan Engine, Statuses & Budget Boundary](../adr/0005-payment-plan-engine-and-status.md)**
   - The most comprehensive ADR in this group. Defines:
     - **Parent statuses:** `OPEN` / `CLOSED` only (UI visibility, not lifecycle detail).
     - **Schedule row statuses:** `PENDING` / `PARTIAL` / `PAID` (no `SKIPPED`, no stored `OVERDUE`).
     - **Waterfall Spillover Engine:** Payments sweep `CHARGE` rows first, then spill into oldest `PRINCIPAL` rows.
     - **Budget Boundary:** The backend halts with `expenses.budget_required` when a payment hits an unbudgeted category - never auto-materializes a budget.
     - **Row & Parent Actions:** Pay, defer, forgive (row-level write-off), add charge, principal reduction, force-close.
     - **Imported Path:** Mirrors ADR 0003's dual path for historical payment plans with decorative metadata.
-->

## Why This Order

- ADR 0026 cleans the Debt vocabulary first. It removes stored status confusion and keeps Debt separate from Payment Plan product language.
- ADR 0027 then defines Debt-owned money history: principal, charges, payments, forgiveness, adjustments, and reversals.
- ADR 0028 moves to Payment Plans and defines the schedule models that decide how rows are generated.
- ADR 0029 finishes the Payment Plan model by clarifying row settlement, write-offs, reversal history, and the target table responsibilities.

## Execution Rules

- ADR 0026 is the canonical Debt status and taxonomy rule for this epic. Do not reintroduce stored Debt lifecycle statuses or Payment Plan product labels on Debt.
- ADR 0027 is the canonical Debt ledger/action rule. Debt balance is a projection of ledger facts, and wallet-touching reversals must preserve FinancialEvent history.
- ADR 0028 is the canonical Payment Plan schedule rule. `plan_type` is product language; `schedule_model` is math behavior.
- ADR 0029 is the canonical Payment Plan row/action rule. Write-offs are not payments, and write-offs are not generic adjustments.
- Where ADR 0005 conflicts with ADR 0028 or ADR 0029, ADR 0028/0029 win for Epic 2 implementation.
- All implementation must still obey Epic 1 ledger foundation rules and the Epicspart2 money-history definition of done.
