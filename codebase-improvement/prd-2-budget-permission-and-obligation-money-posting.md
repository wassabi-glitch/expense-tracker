# PRD 2: Budget Permission And Obligation Money Posting

Triage: ready-for-agent

## Problem Statement

Sarflog's backend has two architecture problems that now sit directly after the Financial Event Ledger and Expense Posting cleanup.

First, Budget Permission is mixed with Budget reporting. The same broad Budget module currently has to answer several different questions:

1. Is this expense allowed to hit this Budget month?
2. Does this category have spending permission?
3. Does this subcategory or project reservation allow this spend?
4. What is the user's Plan Backing?
5. What should the Budget Month Summary show?
6. What should the Project Budget View show?

Those are related, but they are not the same interface. Callers that only need spending permission should not need to know reporting, project summary, query fragment, or month dashboard behavior. This weakens locality: changing a Budget report can risk money-posting code, and changing Budget permission can risk reporting code.

Second, Debt and Payment Plan flows are intentionally decoupled, but they both touch the same lower-level money posting machinery. Debt and Payment Plan must remain separate domain concepts. A Debt is an open-ended obligation with a running balance. A Payment Plan is a scheduled obligation with strict rows, waterfall behavior, and its own ledger. However, when either one needs to post an expense-shaped charge, wallet settlement, Budget-category impact, or immutable Financial Event, they should delegate the shared money event mechanics to the deeper posting seams instead of rebuilding them in their own route or module code.

The user-facing risk is that Budget discipline and obligation truth can drift. A Payment Plan charge, Debt charge, normal expense, and project-linked expense should all respect the same strict Budget permission rules. Debt and Payment Plan should each keep their own rules, but the Wallet, Budget, and Financial Event mechanics should not be scattered.

## Solution

Create two clearer backend seams:

1. **Budget Permission**: the interface that answers whether a proposed spend can hit Budget permission, subcategory permission, project reservation, and Plan Backing rules.
2. **Obligation Money Posting**: the interface that lets Debt and Payment Plan domain modules delegate wallet-touching and Budget-touching Financial Events without coupling Debt and Payment Plan into one entity.

Budget Permission should sit above reporting and below money-posting flows. Expense Posting, Payment Plan payments, Debt charge payments, recurring expenses, and project-linked expenses should use Budget Permission when they need a yes/no decision or a structured Budget-required failure.

Budget reporting should become separate from permission. Budget Month Summary, Budget dashboard data, Project Budget View, analytics-style totals, and display-only computations can still use shared read models or query helpers, but they should not be the interface that money-posting flows depend on.

Obligation Money Posting should preserve the intentional separation:

```text
Debt domain owns Debt rules.
Payment Plan domain owns Payment Plan rules.
Shared posting seams own Wallet, Budget, and Financial Event mechanics.
```

This PRD must not reintroduce a generic "Obligation" table or merge Debt and Payment Plan behavior.

## User Stories

1. As a Sarflog user, I want every expense-shaped action to respect Budget permission, so that my monthly plan stays mathematically strict.
2. As a Sarflog user, I want missing Budget permission to return a repairable structured error, so that the Budget Interceptor can help me fix it without losing context.
3. As a Sarflog user, I want normal expenses, recurring expenses, Debt charges, and Payment Plan charges to use the same Budget permission rules, so that one flow cannot secretly bypass the plan.
4. As a Sarflog user, I want subcategory limits to behave consistently across expense-shaped flows, so that lanes inside a category remain honest.
5. As a Sarflog user, I want Overlay Project reservations to be checked consistently, so that project spending cannot bypass Budget permission.
6. As a Sarflog user, I want frozen Isolated Project behavior not to leak into unrelated Budget decisions, so that core app logic stays understandable.
7. As a Sarflog user, I want Budget reports to keep showing the same Plan Backing, spending, remaining amount, and red state, so that cleanup does not change financial meaning.
8. As a Sarflog user, I want Project Budget views to keep showing project spending and reservation status, so that project planning remains clear.
9. As a Sarflog user, I want Debt to remain an open-ended obligation, so that informal running balances do not become scheduled contracts.
10. As a Sarflog user, I want Payment Plans to remain scheduled obligations, so that fixed payment rows, charges, and waterfall behavior remain clear.
11. As a Sarflog user, I want Debt charge payments to hit Wallets, Budget categories, and Debt Ledger entries consistently, so that Debt history and Budget history agree.
12. As a Sarflog user, I want Payment Plan charge payments to hit Wallets, Budget categories, and Payment Plan Ledger entries consistently, so that schedule history and Budget history agree.
13. As a Sarflog user, I want Debt principal settlement to preserve Debt-specific rules, so that receivable/payable direction and running balance are correct.
14. As a Sarflog user, I want Payment Plan payments to preserve waterfall rules, so that charges and principal rows are fulfilled in the right order.
15. As a Sarflog user, I want Wallet balances to change exactly once for each obligation payment, so that posting cleanup does not double-count money.
16. As a Sarflog user, I want immutable Financial Events for obligation payments, so that correcting mistakes preserves history.
17. As a Sarflog user, I want Budget-required failures from Debt and Payment Plan flows to look like expense Budget-required failures, so that the frontend repair pattern is universal.
18. As a developer, I want Budget Permission to be a small interface, so that money-posting callers do not depend on Budget reporting internals.
19. As a developer, I want Budget reporting to be isolated from Budget Permission, so that display changes do not risk posting rules.
20. As a developer, I want Debt and Payment Plan code to stay decoupled, so that their domain rules can evolve independently.
21. As a developer, I want Debt and Payment Plan flows to share posting mechanics only at the money-event seam, so that duplicated Wallet/Budget/Financial Event code disappears without merging domains.
22. As a developer, I want tests to cover user-visible behavior at route and domain seams, so that refactors do not encode private helper structure.
23. As a developer, I want naming to avoid "unified obligation model", so that future agents do not accidentally couple Debts and Payment Plans again.
24. As a developer, I want Plan Backing rules to remain testable, so that budget limits cannot exceed honest backing without a structured failure.
25. As a developer, I want project spend permission to be tested through Budget Permission, so that project and Budget behavior stay aligned.

## Implementation Decisions

- Budget Permission is a separate interface from Budget reporting.
- Budget Permission owns spending-time checks: Budget exists or can be materialized, Budget-required failure, Budget limit, subcategory limit, project reservation, Plan Backing impact, and structured repair details.
- Budget reporting owns display-time reads: Budget Month Summary, Budget dashboard totals, Project Budget View, historical spending summaries, and analytics-style breakdowns.
- Money-posting modules should depend on Budget Permission, not on Budget reporting.
- Budget reporting may depend on shared read helpers, but those helpers must not become the write-time permission interface.
- Preserve the Global Budget Interceptor contract. Missing category Budget permission must remain a structured failure that the frontend can catch and repair.
- Preserve strict limit-based budgeting. The backend must not silently auto-create permissive Budget limits when an expense-shaped flow needs explicit Budget permission.
- Preserve Plan Backing meaning: Wallets are reality, Goals are protected real money, expected income is planning support, and Budget Permission is spending permission.
- Preserve Overlay Project behavior as Budget-scoped reservation logic.
- Do not deepen frozen Isolated Project mechanics while working on Budget Permission. If isolated behavior is encountered, quarantine or preserve existing behavior without expanding it.
- Debt remains a standalone domain with its own models, statuses, Debt Ledger, Dual Path rules, receivable/payable direction, principal/charge split, and running balance reconciliation.
- Payment Plan remains a standalone domain with its own models, statuses, schedule rows, charges, waterfall spillover engine, Payment Plan Ledger, and imported path rules.
- Obligation Money Posting must not introduce a generic shared obligation table.
- Obligation Money Posting means Debt and Payment Plan modules call shared money-posting seams for Financial Event, Wallet Ledger, Entity Ledger, Budget Permission, and user-local date mechanics.
- Debt domain modules decide what a Debt action means before calling money posting.
- Payment Plan domain modules decide what a Payment Plan action means before calling money posting.
- Expense Posting and Financial Event Ledger are the preferred lower seams for expense-shaped and low-level money event mechanics.
- Existing route contracts should remain stable.
- Schema changes are not expected for the first version of this PRD.
- Database migrations are not expected unless a later issue reveals a missing index or constraint needed for correctness.
- Existing ledger history must not be rewritten.
- The first implementation slice should introduce Budget Permission through one existing expense-shaped path before migrating broader callers.
- The second implementation slice should separate Budget Month Summary and Project Budget View reads from the write-time permission surface.
- The obligation posting slices should be separate for Debt and Payment Plan so their decoupled domain behavior remains obvious.

## Testing Decisions

- Tests should verify external behavior and domain outcomes, not private helper call order.
- Budget Permission should be tested through real money-posting flows where possible.
- Budget Permission module tests may be added for Plan Backing, limit, subcategory, and project decision behavior when route tests would be too broad.
- Existing expense tests are prior art for Budget-required failures, Budget links, subcategory links, project links, and wallet effects.
- Existing Budget tests are prior art for Plan Backing, Budget Month Summary, Budget limit validation, reallocation, month setup, and category red states.
- Existing Payment Plan tests are prior art for waterfall behavior, charges, schedule row status, structured Budget-required failures, and ledger entries.
- Existing Debt tests are prior art for Debt Ledger entries, running balance reconciliation, charge payment, principal payment, and reversal behavior.
- Add regression coverage proving Budget Permission returns the same structured Budget-required response for normal expenses, Payment Plan charge payments, and Debt charge payments.
- Add regression coverage proving Budget Month Summary output is unchanged after reporting is separated.
- Add regression coverage proving Project Budget View output is unchanged after project reporting is separated.
- Add regression coverage proving Debt charge payments preserve both Debt Ledger impact and Budget category impact after moving through shared posting seams.
- Add regression coverage proving Payment Plan charge payments preserve both Payment Plan Ledger impact and Budget category impact after moving through shared posting seams.
- Add regression coverage proving Debt and Payment Plan models remain decoupled.
- Use Docker-first verification for backend tests unless explicitly running locally.

## Out of Scope

- Merging Debt and Payment Plan into one table, enum, route, or lifecycle.
- Reversing the intentional Debt and Payment Plan database decoupling.
- New Debt product behavior.
- New Payment Plan product behavior.
- New Budget UX.
- New frontend Budget Interceptor behavior.
- New project behavior.
- New Isolated Project mechanics.
- Multicurrency.
- Shared household spaces.
- Premium gating.
- Caching.
- Broad splitting of model and schema modules.
- Rewriting historical ledger data.
- Changing route URLs or frontend API contracts.

## Further Notes

- The phrase "Unify Obligation Posting" is easy to misread. Use "Share Money Posting For Obligation Flows" in implementation issues.
- The distinction is: share the money-event seam, not the domain model.
- This PRD depends conceptually on PRD 1's Financial Event Ledger and Expense Posting seams.
- A good deletion test: if deleting Budget Permission would force every money-posting caller to relearn Budget-required, limit, subcategory, project, and Plan Backing rules, the module has depth.
- Another good deletion test: if deleting Obligation Money Posting would only affect shared Wallet/Budget/Financial Event mechanics but Debt and Payment Plan domain rules remain separate, the seam is correctly scoped.
