# Issue Breakdown For PRD 2: Budget Permission And Obligation Money Posting

Parent PRD: `prd-2-budget-permission-and-obligation-money-posting.md`

Triage: ready-for-agent

## Proposed Breakdown For Approval

1. **Introduce Budget Permission through normal expense posting**
   - Type: AFK
   - Blocked by: PRD 1 Issue 1
   - User stories covered: 1, 2, 3, 4, 5, 18, 22, 24, 25

2. **Move subcategory and project spend checks behind Budget Permission**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 4, 5, 6, 18, 22, 25

3. **Separate Budget Month Summary from Budget Permission**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 7, 18, 19, 22, 24

4. **Separate Project Budget View from Budget Permission**
   - Type: AFK
   - Blocked by: 2, 3
   - User stories covered: 5, 6, 8, 18, 19, 22, 25

5. **Define the Obligation Money Posting seam without merging domains**
   - Type: AFK
   - Blocked by: PRD 1 Issue 1
   - User stories covered: 9, 10, 20, 21, 22, 23

6. **Route Debt charge money events through shared posting seams**
   - Type: AFK
   - Blocked by: 1, 5
   - User stories covered: 3, 11, 13, 15, 16, 17, 20, 21, 22, 23

7. **Route Payment Plan charge and payment money events through shared posting seams**
   - Type: AFK
   - Blocked by: 1, 5
   - User stories covered: 3, 12, 14, 15, 16, 17, 20, 21, 22, 23

8. **Add cross-flow Budget Interceptor and decoupling regression coverage**
   - Type: AFK
   - Blocked by: 6, 7
   - User stories covered: 2, 3, 9, 10, 17, 20, 21, 22, 23

Review questions before implementation:

- Does issue 5 feel clear enough that no agent will merge Debt and Payment Plan concepts?
- Should Budget Month Summary and Project Budget View be separate issues, or merged into one reporting cleanup?
- Should Debt charge and Payment Plan charge migration stay separate, as written?
- Are all slices correctly marked AFK?

---

## Issue 1: Introduce Budget Permission Through Normal Expense Posting

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Introduce a Budget Permission seam through the normal expense posting path. A normal expense should still validate category Budget permission, Budget limits, Plan Backing, subcategory constraints, project constraints, and structured Budget-required failures exactly as before. The difference is that money-posting callers should depend on a small Budget Permission interface instead of broad Budget reporting behavior.

This issue should prove the seam with the safest and most common expense-shaped flow before migrating Debt or Payment Plan flows.

## Acceptance criteria

- [x] Normal expense creation still succeeds when the category Budget has valid permission.
- [x] Normal expense creation still fails with the existing structured Budget-required response when the category has no Budget permission.
- [x] Budget limit failures still return the existing error behavior.
- [x] Plan Backing validation remains unchanged.
- [x] Subcategory and project behavior remains unchanged for normal expense posting.
- [x] Expense Posting calls a Budget Permission interface rather than broad Budget reporting behavior.
- [x] Existing normal expense and Budget limit tests pass.
- [x] New focused regression coverage proves Budget Permission preserves normal expense behavior.

## Blocked by

- PRD 1 Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 2: Move Subcategory And Project Spend Checks Behind Budget Permission

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Move spend-time subcategory checks and project spend checks behind Budget Permission. Expense-shaped flows should ask one spending permission seam whether the category, subcategory, Overlay Project reservation, and current frozen Isolated Project behavior allow the spend.

This issue should not expand Isolated Project mechanics. It should preserve or quarantine existing behavior while keeping core Budget Permission understandable.

## Acceptance criteria

- [x] Subcategory limit validation still behaves the same for normal expenses.
- [x] Overlay Project reservation validation still behaves the same for project-linked expenses.
- [x] Frozen Isolated Project behavior is preserved without introducing new isolated project mechanics.
- [x] Budget-required and project-category-not-part-of-project failures remain unchanged.
- [x] Expense Posting no longer has to know separate subcategory/project permission internals beyond the Budget Permission result.
- [x] Existing project-linked expense and subcategory tests pass.
- [x] New regression coverage proves project-linked spending still respects Budget Permission.

## Blocked by

- Issue 1: Introduce Budget Permission Through Normal Expense Posting

---

## Issue 3: Separate Budget Month Summary From Budget Permission

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Separate display-time Budget Month Summary behavior from write-time Budget Permission. Budget Month Summary should still show the same Plan Backing, free money, expected income, valid Budget spend, category floors, red states, and monthly totals, but money-posting callers should not depend on the summary-building interface.

This slice is a behavior-preserving separation of read/reporting behavior from spend permission behavior.

## Acceptance criteria

- [x] Budget Month Summary output remains unchanged for existing covered scenarios.
- [x] Plan Backing, free money now, expected income remaining, valid Budget spend, and backing shortfall values remain unchanged.
- [x] Category floor and borrowing pressure values remain unchanged.
- [x] Budget Permission does not depend on Budget Month Summary output.
- [x] Existing Budget Month Summary and Budget tests pass.
- [x] New regression coverage proves the summary output is stable across representative covered, waiting-on-income, and over-planned months.

## Blocked by

- Issue 1: Introduce Budget Permission Through Normal Expense Posting

---

## Issue 4: Separate Project Budget View From Budget Permission

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Separate Project Budget View reporting from write-time Budget Permission. Project Budget View should continue showing project spending, category reservations, subcategory reservations, selected month values, overlay financials, and deferred isolated project data as before. Spending permission should remain a small Budget Permission decision, not a dependency on project reporting output.

This issue preserves current project behavior and does not unfreeze Isolated Projects.

## Acceptance criteria

- [x] Project Budget View output remains unchanged for Overlay Projects.
- [x] Selected month reservation and spend calculations remain unchanged.
- [x] Project category and subcategory breakdowns remain unchanged.
- [x] Frozen Isolated Project data remains preserved without adding new mechanics.
- [x] Budget Permission does not depend on Project Budget View output.
- [x] Existing project budget and project deletion/resolution tests pass where relevant.
- [x] New regression coverage proves project reporting remains stable after separation.

## Blocked by

- Issue 2: Move Subcategory And Project Spend Checks Behind Budget Permission
- Issue 3: Separate Budget Month Summary From Budget Permission

---

## Issue 5: Define The Obligation Money Posting Seam Without Merging Domains

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Define the Obligation Money Posting seam as a narrow delegation point for Debt and Payment Plan money events. This seam must explicitly preserve domain separation: Debt remains an open-ended running-balance obligation, and Payment Plan remains a scheduled obligation with rows and waterfall behavior.

The seam should only cover shared money mechanics such as Financial Event creation, Wallet Ledger entries, Entity Ledger links, Budget Permission checks, and user-local date propagation. It must not introduce a generic shared obligation entity.

## Acceptance criteria

- [x] The new seam name and documentation avoid implying a merged Debt/Payment Plan model.
- [x] Debt-specific rules remain in Debt modules.
- [x] Payment Plan-specific rules remain in Payment Plan modules.
- [x] The seam delegates to Expense Posting and Financial Event Ledger where appropriate.
- [x] No schema or database migration merges Debt and Payment Plan concepts.
- [x] Existing Debt and Payment Plan tests still pass before any flow migration.
- [x] A small test or documentation assertion makes the intended separation clear for future agents.

## Blocked by

- PRD 1 Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 6: Route Debt Charge Money Events Through Shared Posting Seams

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Route Debt charge money events through the shared posting seams while keeping Debt domain rules separate. Debt should still decide whether an action is principal, charge, forgiveness, adjustment, receivable, payable, or imported. Once Debt decides a charge is expense-shaped and wallet-touching, Budget Permission, Expense Posting, and Financial Event Ledger should handle the shared money mechanics.

This issue should focus on Debt charge flows, not Payment Plans.

## Acceptance criteria

- [x] Paying a Debt charge still creates the correct Debt Ledger entry.
- [x] Paying a Debt charge still updates Debt remaining amount and charge balance correctly.
- [x] Expense-shaped Debt charges still hit the correct Budget category.
- [x] Missing Budget permission for a Debt charge still returns the structured Budget-required failure.
- [x] Wallet balances change exactly once.
- [x] Financial Event, Wallet Ledger, and Entity Ledger links remain correct.
- [x] Existing Debt charge and Debt payment tests pass.
- [x] New regression coverage proves Debt domain rules remain separate from Payment Plan rules.

## Blocked by

- Issue 1: Introduce Budget Permission Through Normal Expense Posting
- Issue 5: Define The Obligation Money Posting Seam Without Merging Domains

---

## Issue 7: Route Payment Plan Charge And Payment Money Events Through Shared Posting Seams

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Route Payment Plan charge and payment money events through the shared posting seams while keeping Payment Plan domain rules separate. Payment Plan should still own schedule rows, row statuses, charges, write-offs, parent status, imported path behavior, and waterfall spillover. Once Payment Plan decides what money event must be posted, Budget Permission, Expense Posting, and Financial Event Ledger should handle the shared mechanics.

This issue should focus on Payment Plan flows, not Debt flows.

## Acceptance criteria

- [x] Payment Plan payments still apply waterfall behavior correctly.
- [x] Charge rows still get paid before principal rows according to current rules.
- [x] Payment Plan Ledger entries remain correct.
- [x] Expense-shaped Payment Plan charges still hit the correct Budget category.
- [x] Missing Budget permission for Payment Plan charges still returns the structured Budget-required failure.
- [x] Wallet balances change exactly once.
- [x] Financial Event, Wallet Ledger, Entity Ledger, Payment Plan, and payment-row links remain correct.
- [x] Existing Payment Plan payment, charge, write-off, and reversal tests pass where relevant.
- [x] New regression coverage proves Payment Plan domain rules remain separate from Debt rules.

## Blocked by

- Issue 1: Introduce Budget Permission Through Normal Expense Posting
- Issue 5: Define The Obligation Money Posting Seam Without Merging Domains

---

## Issue 8: Add Cross-Flow Budget Interceptor And Decoupling Regression Coverage

## Parent

PRD 2: Budget Permission And Obligation Money Posting

## What to build

Add cross-flow regression coverage proving the architecture cleanup preserved the product contract. The same structured Budget-required failure should appear for normal expenses, Debt charge payments, and Payment Plan charge payments. Debt and Payment Plan should remain decoupled while sharing only money-posting mechanics.

This is a verification slice after the migrations, not a new product behavior slice.

## Acceptance criteria

- [x] A normal expense without Budget permission returns the expected structured Budget-required failure.
- [x] A Debt charge without Budget permission returns the expected structured Budget-required failure.
- [x] A Payment Plan charge without Budget permission returns the expected structured Budget-required failure.
- [x] Debt tests prove Debt remains an open-ended running-balance obligation.
- [x] Payment Plan tests prove Payment Plan remains a scheduled obligation with row and waterfall rules.
- [x] Tests prove shared posting mechanics do not merge Debt and Payment Plan persistence or lifecycle.
- [x] Relevant Budget, Debt, Payment Plan, and Expense test suites pass.
- [x] Any remaining direct broad Budget reporting dependencies from money-posting code are documented for follow-up.

## Blocked by

- Issue 6: Route Debt Charge Money Events Through Shared Posting Seams
- Issue 7: Route Payment Plan Charge And Payment Money Events Through Shared Posting Seams
