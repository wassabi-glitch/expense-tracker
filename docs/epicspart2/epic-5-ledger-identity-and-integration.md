# Epic 5: Ledger Identity & Cross-Domain Integration

**Status:** Not Started  
**Depends On:** Epic 4 (Expected Inflow Architecture) & Epic 2 (Debt & Obligation Architecture)

## Goal
The core engines — ledger, debts, budgets, and expected inflows — are now architecturally defined. This epic makes them communicate correctly across domain boundaries. It establishes consistent naming rules so the ledger reads like a human journal (not a robot log), bridges debts and inflows for receivable tracking, and fixes the frontend schema consumption bugs caused by earlier architectural shifts.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0015 — Income Sources & Ledger Naming](../adr/0015-income-sources-and-ledger-naming.md)**
   - Adopts the industry-standard Entity+Memo accounting pattern for Expected Inflows. The Source (e.g., "Client X", "Upwork") is retained as a strict FK for analytics and tax reporting. The Title (e.g., "July Salary") is the human-readable memo. Backend must never generate robot titles — `FinancialEvent.title` inherits `Promise.title` exactly. Also requires a Creatable Select component for frictionless source creation and a dedicated Income Sources Hub page for lifetime analytics.

2. [ ] **[ADR 0016 — Global Ledger Naming & Refund Duality](../adr/0016-global-ledger-naming-and-refund-duality.md)**
   - Extends 0015's strict title inheritance rule globally across all "Money In" transaction types:
     - **Refunds:** Inherit original expense title exactly. No "Refund for:" prefix.
     - **Debt Receipts:** Use user's custom `note` as title. Counterparty name goes in metadata subtitle.
     - **Asset Sales:** Use exact asset/promise title. No "Asset Sale:" prefix.
     - **Corrections:** Only exception — system-generated "Balance Adjustment" permitted if user gave no note.
   - Also formalizes the **Refund Duality** rule: refunds are contra-expenses and must appear in both Wallet Inflow (physical cash entered) and Category Expenses (reduces true category spend). Hiding either breaks the math.

3. [ ] **[ADR 0017 — Debt Receivables & Deadline Decoupling](../adr/0017-debt-receivables-and-deadline-decoupling.md)**
   - The cross-domain bridge between Debts (Epic 2) and Expected Inflows (Epic 4):
     - **No Auto-Trust:** Receivable debts never auto-project to the timeline. Users must explicitly create an Expected Inflow to declare "I expect this cash on this date."
     - **Splits via Two-Layer:** Complex repayments (e.g., 1M debt in three installments) use one Promise + multiple Schedules from ADR 0012. No pollution of the Debt model.
     - **Deadline Decoupling:** Debt `expected_return_date` (contractual deadline) and Inflow `due_date` (tactical reality) are strictly independent. Adjusting one never mutates the other. The debt stays "Overdue" while the inflow safely projects the actual cash arrival date.

4. [ ] **[ADR 0018 — Frontend API Schema Unwrapping & Status Matching](../adr/0018-frontend-api-schema-unwrapping.md)**
   - Fixes frontend schema consumption bugs caused by earlier architectural changes:
     - **Debt Dropdown Bug:** Frontend filtered debts by `"ACTIVE"` instead of `"OPEN"` (ADR 0005 changed statuses).
     - **Refund Dropdown Bug:** Frontend didn't unwrap the polymorphic `ExpenseFeedItemOut` wrapper, reading `item.event_type` instead of `item.expense.transaction_type`.
   - Formalizes two rules: (1) always unwrap polymorphic feed payloads before filtering, and (2) aggressively deprecate hardcoded status strings that violate recent ADRs.

## Why This Order
- ADR 0015 sets the naming contract for inflows specifically. Must come first because 0016 extends it globally.
- ADR 0016 takes that contract and applies it everywhere — refunds, debts, assets. Also adds the contra-expense accounting rule.
- ADR 0017 bridges the debt and inflow domains. It depends on both Epic 2's debt model and Epic 4's two-layer architecture.
- ADR 0018 is the cleanup pass — fixes the frontend bugs that naturally arise when backend architectures change underneath existing UI code.

## Execution Rules
- ADR 0015 and 0016 require refactoring `expected_inflow_service.py`, `debt_payment_service.py`, and `wallet_service.py` to strip all hardcoded robot strings and route user notes to the `title` field.
- ADR 0017 does not require schema changes — it's a behavioral/UX rule. But the UI must proactively prompt users to link open Receivables to Expected Inflows at the start of each month.
- ADR 0018's fixes are surgical — targeted to `ExpectedInflowDialogs.jsx`. But the *rules* it establishes (strict unwrapping, status deprecation) must be enforced as a team-wide frontend standard going forward.
