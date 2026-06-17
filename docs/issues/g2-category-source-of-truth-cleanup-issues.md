# Issues: G2 - Category and Source-of-Truth Cleanup

Parent PRD: `docs/prd/g2-category-source-of-truth-cleanup.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Deprecate financing-context category for one-time spending**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-6, 13-17

2. **Propagate real purchase categories through debt and payment-plan expense posting**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 2-4, 11-17

3. **Backfill or flag legacy `Installments & Debt` ledger rows**
   - Type: AFK
   - Blocked by: Issue 2
   - User stories covered: 12, 17, 19

4. **Keep parent categories hardcoded and subcategories user-created**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 5-6, 16-17

5. **Project negative wallets into Debts / Obligations without shadow debt rows**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 7-10, 18

6. **Route wallet-backed liability payoff through wallet transfer**
   - Type: AFK
   - Blocked by: Issue 5
   - User stories covered: 7-10, 18

## Issue 1: Deprecate Financing-Context Category For One-Time Spending

## What to build

Stop treating `Installments & Debt` as an active category for ordinary one-time spending. The active category metadata and one-time expense entry path should guide users toward the real purchase category while legacy rows remain readable.

This slice is intentionally narrow: it starts the deprecation at the ordinary expense surface before recurring expenses, session drafts, budget setup, and historical migration are changed.

## Acceptance criteria

- [x] Active category metadata excludes `Installments & Debt`.
- [x] Ordinary one-time expense creation rejects `Installments & Debt` with a clear domain error.
- [x] Expense split lines reject `Installments & Debt` with a clear domain error.
- [x] Existing expenses that already have the legacy category remain readable.
- [x] Existing debt and payment-plan category guardrail tests still pass.
- [x] Frontend one-time expense category selectors no longer offer `Installments & Debt` through the category metadata flow.

## Blocked by

None - can start immediately.

## Suggested verification

- `docker-compose exec api pytest -q tests/test_expenses.py tests/test_debt_action_routes.py::test_deferred_debt_rejects_financing_context_as_expense_category tests/test_installment_routes.py::test_payment_plan_requires_real_category_when_type_has_no_safe_default`
- `npm.cmd run build` if frontend category-selector code is touched.

## Progress

- RED: `tests/test_expenses.py::test_create_expense_rejects_financing_context_category` failed because `/expenses/` accepted `Installments & Debt` with `201`.
- GREEN: active metadata filtering, ordinary expense rejection, and split-line rejection now pass through local venv pytest.
- GREEN: legacy `Installments & Debt` expense rows remain listable and detail-readable while new ordinary writes still fail.
- Completed: remaining cleanup continued through category guardrails, migration/backfill, and wallet-backed obligations.

## Issue 2: Propagate Real Purchase Categories Through Debt And Payment-Plan Expense Posting

## What to build

Make every new debt-backed or payment-plan-backed expense event preserve the real purchase category. Principal portions should use the linked debt or payment-plan real category. Charges, fees, interest, and penalties should use `Debt Charges`. Financing mechanism should be represented by debt/payment-plan links and reference types, not by category.

## Acceptance criteria

- [x] Payment-plan creation requires or derives a real purchase category.
- [x] Payment-plan scheduled principal payments post expense legs under the plan's real category.
- [x] Payment-plan charges post expense legs under `Debt Charges`.
- [x] Regular deferred-expense debt principal payments post under the debt's real category.
- [x] Regular debt charges post under `Debt Charges`.
- [x] Legacy fallback paths do not create new `Installments & Debt` expense legs.
- [x] Public route tests cover payment-plan and debt posting behavior.

## Blocked by

- Issue 1: Deprecate financing-context category for one-time spending

## Suggested verification

- `docker-compose exec api pytest -q tests/test_debt_action_routes.py tests/test_installment_routes.py tests/test_expenses.py`

## Progress

- RED: legacy payment-plan payment paths without real categories surfaced the shared expense category error after resolving to `Installments & Debt`.
- GREEN: payment-plan category resolution now derives safe plan-type defaults or fails with `installments.validation.real_expense_category_required` before debt/payment posting can create deprecated expense legs.
- GREEN: route tests cover payment-plan principal category posting, payment-plan charge posting, deferred-debt principal posting, deferred-debt charge posting, and legacy fallback blocking.

## Issue 3: Backfill Or Flag Legacy `Installments & Debt` Ledger Rows

## What to build

Add a staged migration/backfill path for historical rows that already use `Installments & Debt`. Where a linked debt or payment plan has a trustworthy real category, update the ledger category and budget linkage to that category. Where no safe inference exists, preserve the row and mark or report it for manual review.

## Acceptance criteria

- [x] Linked payment-plan principal rows can be migrated to the plan's real category.
- [x] Linked deferred-expense debt principal rows can be migrated to the debt's real category.
- [x] Charge rows are migrated to or retained as `Debt Charges`, not a purchase category.
- [x] Rows without safe inference are not guessed silently.
- [x] Migration can be rerun safely or has clear idempotency behavior.
- [x] Tests cover migrated and manual-review cases.

## Blocked by

- Issue 2: Propagate real purchase categories through debt and payment-plan expense posting

## Suggested verification

- `docker-compose exec api pytest -q tests/test_expenses.py tests/test_debt_action_routes.py tests/test_installment_routes.py`
- `docker-compose exec api python -m alembic upgrade head` if an Alembic migration is added.

## Progress

- RED: no service existed for a repeatable legacy category backfill/report.
- GREEN: `backfill_deprecated_financing_category_rows` migrates linked payment-plan/debt principal rows to real categories, retags charge rows to `Debt Charges`, rebinds exact-month budgets when present, and returns manual-review rows when no safe inference exists.
- GREEN: rerunning the backfill is idempotent for migrated rows and keeps unresolved legacy rows visible in the manual-review report.

## Issue 4: Keep Parent Categories Hardcoded And Subcategories User-Created

## What to build

Preserve the hardcoded global parent category list while ensuring subcategories remain user-created labels under those parents. This slice should document and test that users can create custom subcategories under real categories and cannot create category structures under the deprecated financing-context category.

## Acceptance criteria

- [x] Parent category choices remain controlled by the backend category vocabulary.
- [x] User-created subcategories remain available under real parent categories.
- [x] Subcategory creation under `Installments & Debt` is blocked for active write paths.
- [x] Existing subcategory behavior under real categories continues to pass.
- [x] The UI copy continues to describe subcategories as user-created lanes or labels, not hardcoded system categories.

## Blocked by

- Issue 1: Deprecate financing-context category for one-time spending

## Suggested verification

- `docker-compose exec api pytest -q tests/test_budget.py tests/test_expenses.py`
- `npm.cmd run build` if frontend category/subcategory copy is touched.

## Progress

- GREEN: active budget creation rejects `Installments & Debt`; legacy budget rows can still exist for backfill/read safety.
- GREEN: budget and project subcategory/category-structure creation under `Installments & Debt` is blocked while real user-created subcategories continue to work.

## Issue 5: Project Negative Wallets Into Debts / Obligations Without Shadow Debt Rows

## What to build

Make the Debts / Obligations area include projected wallet-backed liabilities for credit cards and overdraft-enabled wallets with negative balances. These projected rows should be visibly obligation-like but must not behave like normal debt records or create debt-table duplicates.

## Acceptance criteria

- [x] Negative credit-card wallets appear in the obligations view.
- [x] Negative overdraft wallets appear in the obligations view.
- [x] Positive and zero-balance wallets do not appear as obligations.
- [x] Projected wallet obligations expose wallet-owned actions only.
- [x] Normal debt CRUD/action routes cannot operate on projected wallet obligations.
- [x] Tests prove no debt row is created for a negative wallet projection.

## Blocked by

- Issue 1: Deprecate financing-context category for one-time spending

## Suggested verification

- `docker-compose exec api pytest -q tests/test_wallets.py tests/test_debts.py`
- `npm.cmd run build` if obligations UI is touched.

## Progress

- GREEN: `/debts` now combines formal debt rows with projected negative credit-card and overdraft-wallet obligations marked as `source_type: WALLET`.
- GREEN: projected wallet obligations use wallet-owned action metadata and negative IDs, so normal debt detail/action routes do not operate on them and no debt row is created.

## Issue 6: Route Wallet-Backed Liability Payoff Through Wallet Transfer

## What to build

Add debt-page wording and API/UI wiring so paying a credit card or covering an overdraft uses wallet transfer behavior. The payoff should reduce the negative wallet balance and reduce another wallet by the same amount plus any transfer fee. It must not create a new expense and must not create a normal debt payment.

## Acceptance criteria

- [x] Credit-card payoff from Obligations creates a wallet transfer, not an expense.
- [x] Overdraft cover from Obligations creates a wallet transfer, not an expense.
- [x] Optional transfer fee follows the existing wallet-transfer fee path.
- [x] Wallet balances update exactly like a transfer.
- [x] Wallet ledger/reference labels make credit repayment or overdraft cover understandable.
- [x] Tests prove payoff is liability reduction, not category spending.

## Blocked by

- Issue 5: Project negative wallets into Debts / Obligations without shadow debt rows

## Suggested verification

- `docker-compose exec api pytest -q tests/test_wallets.py tests/test_debts.py`
- `npm.cmd run build` if obligations UI is touched.

## Progress

- GREEN: `/debts/wallet-obligations/{wallet_id}/payoff` validates projected wallet-backed liabilities and records payoff as a wallet transfer with `wallet_obligation_payoff` reference type.
- GREEN: credit-card payoff, overdraft cover, optional transfer fee, transfer balance updates, and no-debt-payment invariants are covered by focused backend tests.
- GREEN: Obligations UI routes projected wallet rows to a payoff dialog instead of normal debt detail/delete actions.
