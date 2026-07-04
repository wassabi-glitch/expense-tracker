# Epic 3: Budget Enforcement & Intercept Pattern

**Status:** Not Started  
**Depends On:** Epic 2 (Debt & Obligation Architecture)

## Goal
Define the budget system's enforcement philosophy and the universal UX pattern for resolving budget conflicts. Epic 2's payment plan engine already throws `expenses.budget_required` errors when charges hit unbudgeted categories. This epic establishes the two rules that govern the budget side of that interaction: (1) you cannot budget money you don't possess, and (2) when a transaction is blocked, the system resolves it in-context without destroying the user's workflow.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0006 — Strict Limit Balancing & The Cancellation of Permissive UX](../adr/0006-strict-limit-balancing-no-permissive-ux.md)**
   - The philosophy. Explicitly cancels the "Permissive UX" model that allowed saving overplanned budgets. Institutes strict limit balancing for all Month Setup modes (Plan from Scratch, Copy Last Month, Smart Auto-Fill). If the plan exceeds available Plan Backing, the system blocks the save and forces manual trimming. Friction is a feature — it guarantees mathematical truth.

2. [ ] **[ADR 0009 — Global Budget Interceptor Pattern (In-Context Resolution)](../adr/0009-global-budget-interceptor.md)**
   - The pattern. When any transaction (expense, debt settlement, payment plan charge) attempts to hit an unbudgeted category, the backend halts with a structured `400 Bad Request`. The frontend catches it with a universal interceptor modal — freezes the draft, shows the missing category, pre-fills a recommended limit, displays Plan Backing, and chains two API calls (create budget → re-submit transaction) on confirm. Built once, mounted globally across Quick Add, Debt Settlement, Payment Plans, and CSV Import.

## Why These Two Together
- **0006 is the constraint.** It says: "The system will never let you budget money you don't have."
- **0009 is the escape hatch.** It says: "When you hit that constraint mid-workflow, here's how we guide you through it without losing your context."
- Together they form Sarflog's complete budget enforcement contract. The backend is mathematically strict (0006), but the frontend is forgiving and helpful (0009). Strict rules, smooth resolution.

## Dependency Chain
Epic 2's ADR 0005 (Payment Plan Engine §4) defines the *backend contract* — the `expenses.budget_required` error that fires when a payment plan charge hits an unbudgeted category. This epic defines the *budget-side response* to that contract. The chain is: Epic 1 (ledger rules) → Epic 2 (obligations throw budget errors) → Epic 3 (budget system catches and resolves them).

## Execution Rules
- ADR 0006's intercept rule must be enforced at the API layer for all Month Setup endpoints (`POST /budgets/setup`), not just in the frontend.
- ADR 0009's interceptor modal is a single universal React component. It must be tested against all transaction flows that can trigger the `expenses.budget_required` error: Quick Add, Debt Settlement, Payment Plan charges, and future CSV Import.
- The real-time "Amount Remaining to Balance" indicator (0006) and the "Plan Backing" display (0009) must consume the same backend math to avoid divergence.
