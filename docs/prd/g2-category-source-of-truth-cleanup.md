# PRD: G2 - Category and Source-of-Truth Cleanup

Labels: `ready-for-agent`

## Problem Statement

Sarflog still carries a financing-context category, `Installments & Debt`, inside the global expense category taxonomy. That creates a source-of-truth problem.

When a user buys a phone on installments, the real spending category is Electronics. When a user takes debt for health care, the real spending category is Health. Debt, installment, credit card, and overdraft are financing mechanisms or liability sources, not categories of consumption.

If users or agents keep using financing mechanism as the category, reports cannot support reliable 50/30/20 grouping later, category budgets understate the real life area that was consumed, and the app risks duplicating credit-card liabilities as debt rows even though the wallet balance already owns that truth.

## Solution

Make the category model explicitly separate from financing source of truth.

Global parent expense categories remain hardcoded so reporting, AI categorization, and budget planning have stable anchors. User subcategories remain user-created labels under those parent categories. New spending records, debt-backed purchases, and payment-plan purchases must use the real purchase category, not `Installments & Debt`.

Debt and payment-plan relationships continue to describe why an expense exists and how the obligation is repaid. Credit cards and overdrafts are represented by wallet balances. Negative credit or overdraft wallets can be projected into the Debts / Obligations UI, but repayment is a wallet transfer rather than a new categorized expense or shadow debt row.

Legacy data that already uses `Installments & Debt` should remain readable while new write paths stop creating more of it. Migration/backfill should move old rows to real categories where the linked debt or payment-plan record already knows the correct category, and leave explicit manual review where the app cannot infer a real category safely.

## User Stories

1. As an expense user, I want purchase categories to describe what I bought, so that my spending reports reflect real life.
2. As a payment-plan user, I want a financed phone purchase to count as Electronics, so that installments do not hide electronics spending.
3. As a debt user, I want a deferred medical bill to count as Health, so that debt repayment does not distort my category budget.
4. As a budget user, I want category limits to map to life areas, so that I can plan groceries, transport, housing, and other actual spending.
5. As a reporting user, I want global parent categories to remain stable, so that 50/30/20 reporting can be deterministic later.
6. As a customization user, I want subcategories to remain my own labels, so that Sarflog adapts to my habits without losing reporting structure.
7. As a credit-card user, I want my credit card balance to be the source of truth for what I owe, so that the app does not create duplicate debt rows.
8. As an overdraft user, I want a negative debit wallet to be visible as an obligation, so that I do not forget it while planning.
9. As a wallet user, I want credit-card payoff to be a transfer, so that I do not record the same purchase twice.
10. As a debt user, I want formal debts and wallet-backed liabilities visible together, so that the Debts / Obligations area shows the full obligation picture.
11. As a support/debugging user, I want debt/payment-plan links to explain financing, so that category fields stay clean.
12. As a future analytics user, I want old `Installments & Debt` data migrated where possible, so that reports are not polluted by a deprecated category.
13. As a maintainer, I want new write paths to reject deprecated financing categories, so that legacy cleanup does not become a moving target.
14. As a frontend user, I want category selectors to omit financing mechanism categories, so that I am guided toward the real purchase category.
15. As a debt/payment-plan creator, I want the app to ask for real category when it cannot infer one safely, so that category source of truth stays with the user.
16. As a category user, I want hardcoded parent categories and custom subcategories to stay separate, so that macro reporting and personal detail both work.
17. As a tester, I want public route tests around category acceptance and rejection, so that agents cannot reintroduce financing-as-category later.
18. As a future G3 budget-math implementer, I want credit-card and debt source-of-truth rules settled, so that free-money and backing math does not count fake wealth.
19. As a future G9 reporting implementer, I want the taxonomy cleaned before adding 50/30/20 charts, so that reports do not need workaround buckets.
20. As a future agent, I want G2 to avoid changing core budget capacity math, so that source-of-truth cleanup lands before plan-health formulas.

## Implementation Decisions

- Treat `Installments & Debt` as a deprecated financing-context category, not an active spending category.
- Keep the enum value temporarily for legacy reads, exports, and staged migration safety.
- Hide deprecated financing categories from active category metadata and frontend category selectors.
- Reject new ordinary spending records that try to use `Installments & Debt`.
- Keep debt and payment-plan creation using real purchase categories. If a plan type has a high-confidence default, it may suggest that real category; otherwise the user must choose.
- Payment-plan payments should carry the original real purchase category for principal expense portions and `Debt Charges` for fees, penalties, and interest.
- Regular deferred-expense debt payments should carry the debt's real expense category for principal portions and `Debt Charges` for fees, penalties, and interest.
- A migration/backfill should update legacy linked ledger rows from `Installments & Debt` to the linked debt or payment-plan real category when that inference is safe.
- Legacy rows with no safe inference should remain readable and be flagged for manual review rather than silently guessed.
- Keep global parent categories hardcoded.
- Keep subcategories user-created. Month-specific subcategory limits remain G5 scope, not G2.
- Do not create debt-table rows for credit-card or overdraft liabilities.
- Debts / Obligations UI should combine formal debt/payment-plan records with projected negative wallets.
- Credit-card repayment and overdraft cover reuse wallet transfer behavior and can use clearer reference labels in wallet history.

## Testing Decisions

- Prefer API-level integration tests through existing route fixtures for behavior users can observe.
- Start at the highest existing seams: category metadata, expense creation, split expense, debt creation, payment-plan creation/payment, wallet transfer, and obligations summary/list routes.
- Use service-level tests only where a reusable policy helper would otherwise require too many route permutations.
- Tests should assert observable behavior: allowed/rejected category values, posted financial event category, budget linkage, wallet balance changes, and absence of duplicate debt rows.
- Existing G1 debt/payment-plan tests are prior art for route-level guardrail coverage.
- Existing wallet transfer tests are prior art for credit-card and overdraft repayment as transfer behavior.
- Frontend verification should use build checks when selector/source changes are touched.

## Out of Scope

- Implementing 50/30/20 reporting UI.
- Reworking G3 budget backing math or free-money-now formulas.
- Splitting subcategory tags from month-specific subcategory limits.
- Changing goal funding, planned-purchase, or pay-obligation completion rules beyond preserving category truth.
- Removing the database enum value before legacy data is migrated or explicitly tolerated.
- Full wallet transaction history redesign, except where wallet-backed obligation repayment needs existing transfer evidence.
- Full credit-card statement/reconciliation workflows.

## Further Notes

This PRD implements the G2 direction from the implementation plan and draws from EC-041, EC-116, EC-119, EC-120, and EC-134. EC-042 through EC-046 are dependency context: wallet history, pay-obligation goals, guided goal creation, backend-owned debt goal payment rules, and planned-purchase to payment-plan bridge must not be contradicted by this cleanup.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
