# Edge Case Implementation Plan

Date: 2026-06-12

Source scope: `docs/EDGE_CASES_AND_BUGS.md` EC-047 to EC-051, EC-054, and EC-108 to EC-136.

## Status Template

Use these values when updating any group:

- `Not Executed`: no code started.
- `In Process`: code is actively being changed.
- `Partially Completed`: some code shipped, but invariants/tests/UI are incomplete.
- `Blocked`: cannot continue without a product or technical decision.
- `Completed`: backend, frontend, tests, migration/backfill, and docs are done where relevant.
- `Deferred`: intentionally postponed after review.

Each group should keep this shape:

```text
Status:
Source ECs:
Depends on:
Next code step:
Done when:
```

## Global Priority Rules

1. Newer ECs win when ideas conflict. Treat higher EC numbers as newer product truth.
2. Wallet reality beats plan metadata. Expense/payment entry must record real life even when budgets become red.
3. Budgets are monthly spending permissions, not cash envelopes.
4. Goals are protected real money. Funding goals reduces free money available for budgets.
5. Credit cards are negative-balance wallets, not shadow debt rows.
6. Debt and payment-plan history must evolve through explicit actions, not silent row mutation.
7. Use `Over-Planned`, `Exceeds Free Cash`, or `Unbacked` for over-committed budget planning; avoid envelope-funding wording.

## Verification Environment

- Treat this project as Docker-first for integrated verification.
- Frontend, backend/API, database, and Redis all run in Docker.
- Run Redis-dependent backend suites inside the API container with `docker compose exec api pytest ...`.
- Do not use local venv pytest for suites that depend on Redis, Docker DB state, or the running API container environment.
- Local venv pytest is acceptable only for narrow non-Redis checks that are known to be independent of Docker services.

## Execution Groups

### G0 - Budget Language Cleanup

Status: `Completed`

Source ECs: EC-111

Depends on: none

Next code step: none for G0; backend, frontend, tests, translations, and current planning docs use `Over-Planned` / `over_planned`.

Done when: no budget plan-health surface implies envelope funding; tests/snapshots expect the new language.

### G1 - Debt and Payment-Plan Truth Guardrails

Status: `Completed`

Source ECs: EC-047, EC-048, EC-049, EC-050, EC-051

Depends on: none

Next code step: harden debt/payment-plan policies before adding richer UI:

- Debt generic update edits only safe metadata.
- Debt status changes use explicit actions.
- Opening amount/delete are allowed only while pristine.
- Payment-plan setup fields are editable only before real activity.
- Payment-plan payments get a plan-owned latest-operation `Undo payment` path.
- Reversal copy warns that wallet balance changes only match reality if the real payment failed, was cancelled, refunded, or recorded by mistake.
- Debt and payment-plan detail modals render audit storylines oldest-to-newest.

Done when: generic CRUD cannot bypass explicit debt/payment-plan actions; payment-plan reversal reconciles schedule, debt, financial event, wallet effect, and goal dependencies or blocks clearly; tests cover pristine and non-pristine paths.

### G2 - Category and Source-of-Truth Cleanup

Status: `Completed`

Source ECs: EC-116, EC-119, EC-120, EC-134

Depends on: G1 for payment-plan/debt safety if existing data must be migrated.

Completed work:

- Deprecated/migrated `INSTALLMENTS_DEBT` for active write paths while preserving legacy reads and backfill/manual-review safety.
- Kept global parent categories hardcoded and subcategories user-created.
- Treated credit-card liabilities and overdrafts as negative wallet balances, not debt-table duplicates.
- Made Debts / Obligations combine formal debts plus projected negative wallets.
- Routed credit-card payoff and overdraft cover through wallet transfers, including the existing transfer-fee path.

Done when: financing mechanism is not used as an expense category; credit-card payoff is a wallet transfer; category taxonomy can support 50/30/20 reporting later.

### G3 - Core Budget Backing Math

Status: `Completed`

Source ECs: EC-109, EC-115, EC-127, EC-128, EC-131, EC-135

Depends on: G0 for copy; G2 for category and credit-card source of truth.

Completed work:

- Centralized the first plan-capacity slice in budget service.
- Added `valid_budget_spent` to month summary.
- Effective backing now counts only cash-backed valid budget spent, capped by each category's effective monthly limit.
- Budget create/update validation uses the same effective backing calculation.
- Credit-card spending remains borrowing pressure and does not add fake backing.
- Category overspending leaks out of valid spent and can make the global plan `Over-Planned`.
- Protected goal money remains excluded from planning capacity after valid budget spending is added back.
- Mixed cash/credit spending is prorated so only the cash-backed share contributes to valid spent.
- Category-linked debts, installment/payment-plan dues, and recurring expenses are exposed as category floors rather than blind global subtraction.
- Cash-only dated debts are exposed through `cash_obligation_reserve_total` and reduce plan backing.
- Ordinary over-budget expense save records ledger truth first and leaves the affected plan red instead of returning `budgets.limit_exceeded`.

Next code step: none for G3; continue to G4 expected inflow and debt obligation workflows.

```text
valid_budget_spent = min(category_spent, category_limit)
effective_backing = free_money_now + expected_inflows + total_valid_budget_spent - applicable_cash_obligation_reserves
plan_status = Covered unless total_limits > effective_backing
```

Important refinements:

- `free_money_now` sums only positive wallet cash after protected goal money/reserves; ignore negative credit-card balances and available credit limits.
- Expected inflows include salary, receivables, and liquidity loans, with debt-funded plans flagged.
- Category-linked debts and recurring expenses become category minimums/floors, not blind global subtraction.
- Cash-only debts use pre-flight warning/reserve flows.
- Budget create/update may be blocked when the plan is impossible; expense save must not be blocked by over-budget status.

Done when: normal in-limit spending keeps plan status stable; overspending/unbudgeted spending makes the plan `Over-Planned`; goal funding consumes unallocated free money only; credit-card float does not create fake wealth.

### G4 - Expected Inflows and Debt Obligation Workflows

Status: `Completed`

Source ECs: EC-129, EC-130, EC-131, EC-132

Depends on: G3

Completed work:

- Added G4 PRD and local issue breakdown.
- Added explicit receivable expected-payment support through `/budgets/expected-incomes`.
- Debt receivables now expose a workflow prompt instead of auto-contributing to plan backing.
- `/budgets/month-summary` includes debt-linked expected payments only when an explicit expected-income row exists and remains `EXPECTED`.
- Expected-income rows now have debt/linkage fields for later realization history: `debt_id`, `received_amount`, and `linked_transaction_id`.
- Added `POST /budgets/expected-incomes/{id}/mark-received` to preserve expected inflow rows as `RECEIVED`, store actual received amount, create/link wallet-backed ledger truth, and keep received rows out of expected inflow backing.
- Debt-linked expected-payment realization records the incoming debt payment, reduces the receivable balance, and links the expected row to the generated financial event.
- Active dated payable debts now expose hard due/overdue workflow warnings.
- Active open-ended payable debts now expose a soft paydown suggestion without changing plan backing.
- Month summary now exposes expected inflow lifecycle totals and item rows, so dashboards can distinguish `EXPECTED`, `RECEIVED`, `MISSED`, and `CANCELLED` records without recomputing backing math.
- Docker verification rule documented: frontend, backend/API, DB, and Redis are Docker-first; Redis-dependent backend tests run with `docker compose exec api pytest ...`.

Next code step: none for G4; continue to G5 month-scoped subcategory architecture.

Done when: expected inflows are honest planning records with lifecycle state, missed expectations do not silently roll forward, and owing-debt warnings match the two-bucket model.

### G5 - Month-Scoped Subcategory Architecture

Status: `Completed`

Source ECs: EC-120, EC-121, EC-122, EC-123, EC-124, EC-125

Depends on: G3

Completed work:

- Added G5 PRD and local issue breakdown.
- Split `UserSubcategory` tag identity from budget-month limit rows.
- Added `BudgetSubcategoryLimit(budget_id, subcategory_id, monthly_limit)`.
- Budget detail and subcategory routes now expose the selected budget month's limit without mutating historical months.
- Lazy budget materialization copies prior-month subcategory limit rows into the new budget month.
- Lazy budget materialization preserves unbounded subcategories as unbounded.
- Enforced `sum(subcategory_limits) <= parent_category_limit` within the selected parent budget month.
- Parent-category spending without a subcategory remains allowed.
- Subcategory overspending records the real expense and budget detail reports negative remaining / red state.
- Parent-category overspending still leaks to global plan backing through G3 math.
- Added same-parent subcategory reallocation from parent buffer or sibling subcategory only.
- Budget UI now shows month-scoped subcategory limits, parent buffer, unspecified parent spending, red subcategory states, and same-parent repair actions.
- Docker verification passed for the full budget suite and narrow expense subcategory regressions.
- Frontend production build passed.

Next code step:

- none for G5; continue to G6 new month planner and recurring floors.

Verification note:

- The in-app browser was unavailable for a UI smoke check, but Docker-backed backend verification and frontend production build passed.

Done when: historical subcategory limits no longer mutate retroactively; subcategory overspend is visual/actionable but never blocks expense save; parent-category overspend leaks to global backing through G3 math.

### G6 - New Month Planner and Recurring Floors

Status: `Completed`

Source ECs: EC-126, EC-131, EC-133, EC-136

Depends on: G3, G4, G5

Completed work:

- Added G6 PRD and local issue breakdown.
- Disabled automatic budget rollover effects for v1; recomputation clears legacy budget ledger effects and does not create new rollover/cap-trim/sweep entries.
- Added explicit month setup preview modes: plan from scratch, copy previous month, and smart auto-fill.
- Preview uses timezone-validated target months and existing G3/G4/G5 pre-flight math.
- Added explicit month setup apply for copy previous month and smart auto-fill.
- Copy previous month creates missing selected-month parent budgets and copies month-scoped subcategory limits.
- Smart auto-fill raises parent category limits to satisfy computed category floors.
- Docker-backed budget verification passed.
- Payable-debt category floors now classify by repayment accounting route: any active payable debt with an expense category becomes a category floor unless it is explicitly cash-only debt.
- Recurring default projection API added with frequency-specific horizons.
- Saved custom recurring projection horizons added as recurring preference metadata, with ad hoc preview support.
- Recurring UI now renders backend default/custom/preview projection rows and can save custom horizons.
- Docker-backed budget and recurring verification passed; frontend production build passed.

Next code step:

- none for G6; continue to G7 projects and goal deployment.

Done when: a new month can be initialized without stale rollover assumptions, and required category floors are visible before the user overspends by accident.

### G7 - Projects and Goal Deployment

Status: `Complete`

Source ECs: EC-112, EC-113, EC-114, EC-117, EC-118, EC-127

Depends on: G3 for unfunded project overspending; G5 if project subcategories share budget-lane concepts.

Completed work:

- Added G7 PRD and local issue breakdown.
- Added API-level tests for project expense tagging by `expense_date`.
- Added API-level tests for project date expansion/shrink validation.
- Project expense validation now enforces `project.start_date <= expense_date <= project.target_end_date` when an end date exists.
- Project update validation now allows date expansion and blocks end-date shrinking that would orphan tagged expenses.
- Added API-level tests for completed project locks and explicit reopen.
- Completed projects now reject project metadata, category-limit, subcategory, and new expense-tagging mutations until reopened.
- Added API-level tests for early Fund Project graduation into an isolated project stash.
- Fund Project graduation now releases currently funded/unreleased money as the initial project stash by default.
- Project summaries now expose tick-up/tick-down reporting direction and isolated project funding shortfall.
- Isolated goal-funded project spending beyond released funding is reported as a shortfall instead of being hidden by a hard cap; wallet/free-money pressure remains visible through G3 budget summary math.

Next code step:

- none for G7 backend; frontend can consume `progress_direction`, `released_funding`, `remaining_funding`, and `funding_shortfall` for project visuals.

Verification note:

- Docker-backed verification passed for the G7 narrow slice, `tests/test_expenses.py`, and `tests/test_goals.py`.

Done when: completed reports are protected, late backdated receipts can be tagged correctly, early graduation works, and isolated-project shortfalls reduce free money through G3 math.

### G8 - Expense Entry and Post-Save UX

Status: `Completed`

Source ECs: EC-109, EC-110, EC-123

Depends on: G3 for over-budget math; G5 for subcategory actions.

Completed work:

- Completed first half: Quick Add shows inline parent-category/subcategory over-budget warnings without disabling save.
- Completed first half: after a saved parent-category overage, Quick Add opens repair actions to reallocate, increase limit, or leave red.
- Completed second half: after a saved subcategory overage, Quick Add opens repair actions for parent-buffer reallocation, sibling-subcategory reallocation, parent limit increase, or leave-red.
- Verification completed with Docker-backed budget and expense test suites plus Docker frontend build. Browser smoke was attempted, but the in-app browser target was unavailable in this environment.

Done when: users can record real transactions in one save even if category or subcategory plans break, then immediately see the right repair options.

### G9 - Reporting, Timeline, and Opportunity Cost

Status: `Not Executed`

Source ECs: EC-054, EC-116, EC-136

Depends on: G2, G3, G4, G6

Next code step:

- Add deterministic future timeline items only after source data is reliable: expected inflows, recurring expenses, installments, debts, and goal target dates.
- Add 50/30/20 reporting after category taxonomy is stable.
- Show opportunity-cost warnings only for large, over-budget, unsafe, obligation-threatening, or goal-threatening spending.
- Do not show exact goal-delay claims until projection math is reliable.

Done when: dashboard intelligence is useful without fake precision or warning fatigue.

## Recommended Coding Order

1. G0 - Copy cleanup.
2. G1 - Debt/payment-plan data safety.
3. G2 - Category and source-of-truth cleanup.
4. G3 - Core budget backing math.
5. G4 - Expected inflow and debt obligation workflows.
6. G5 - Month-scoped subcategories.
7. G6 - New month planner and recurring floors.
8. G7 - Project/goal lifecycle.
9. G8 - Expense entry UX.
10. G9 - Reporting/timeline/opportunity cost.

This order protects financial history first, then fixes the math foundation, then builds user-facing planning and intelligence on top.
