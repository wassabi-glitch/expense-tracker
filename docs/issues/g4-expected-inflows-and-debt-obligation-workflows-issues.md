# Issues: G4 - Expected Inflows and Debt Obligation Workflows

Parent PRD: `docs/prd/g4-expected-inflows-and-debt-obligation-workflows.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Require explicit expected payments for receivables**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-6, 15, 17-18

2. **Preserve expected inflow realization history**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 7-11, 15, 17

3. **Warn on dated and overdue debts owed by the user**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 12-13, 15-16

4. **Suggest paydown for open-ended debts owed by the user**
   - Type: AFK
   - Blocked by: Issue 3
   - User stories covered: 14-16

5. **Expose expected inflow lifecycle in month planning**
   - Type: AFK
   - Blocked by: Issues 1-2
   - User stories covered: 3, 7-11, 17

## Issue 1: Require Explicit Expected Payments For Receivables

## What to build

Debt receivables should not become budget backing just because someone owes the user money. When a debt is owed to the user, the debt route should prompt for an explicit expected-payment planning record. `/budgets/expected-incomes` should accept a debt-linked expected payment, and `/budgets/month-summary` should include that amount only after the explicit row exists and remains `EXPECTED`.

## Acceptance criteria

- [x] Creating a debt owed to the user does not change `expected_income_remaining`.
- [x] Debt output includes a workflow warning/prompt that receivable expected payments must be explicit.
- [x] `/budgets/expected-incomes` can create an expected-payment row linked to an active debt owed to the user.
- [x] Debt-linked expected payments are returned by the expected-income list endpoint.
- [x] Debt-linked expected payments contribute to `/budgets/month-summary` only while status is `EXPECTED`.
- [x] Existing salary/source expected income behavior remains green.
- [x] Existing G2 wallet-backed obligation tests remain green.

## Blocked by

None - can start immediately.

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_receivable_debt_requires_explicit_expected_payment_before_budget_backing -q`
- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_expected_income_allows_waiting_on_income_status tests\\test_budget.py::test_expected_income_status_change_can_make_existing_plan_over_planned -q`
- `.\\venv\\Scripts\\pytest -q tests\\test_debts.py::test_debt_list_projects_negative_wallet_obligations_without_debt_rows tests\\test_debts.py::test_credit_wallet_obligation_payoff_uses_transfer_with_fee_not_debt_payment tests\\test_debts.py::test_overdraft_wallet_obligation_payoff_uses_transfer_not_expense -q`

## Progress

- RED: `tests/test_budget.py::test_receivable_debt_requires_explicit_expected_payment_before_budget_backing` failed because receivable debts had no workflow prompt and `/budgets/expected-incomes` only accepted income-source rows.
- GREEN: debt receivables now expose `debts.warning.receivable_expected_payment_requires_explicit_plan`, expected-income rows can link to one active receivable debt, and month summary counts only explicit debt-linked rows while status is `EXPECTED`.
- GREEN: Docker budget suite, debt action routes, and focused G2 wallet-backed obligation tests pass inside the API container.
- GREEN: Alembic sees `1f7c2d9e4a60` as the single head, and Docker `alembic upgrade head` applied the expected-income linkage migration.

## Issue 2: Preserve Expected Inflow Realization History

## What to build

Receiving an expected inflow should mark the expected row `RECEIVED` and preserve the historical expectation. The row should record the actual received amount and link to the wallet/financial event when realization creates or attaches to ledger truth.

## Acceptance criteria

- [x] Realizing an expected income changes status to `RECEIVED`; it does not delete the row.
- [x] Realization stores `received_amount`.
- [x] Realization stores the linked financial event or wallet transaction identifier when available.
- [x] Received rows no longer contribute to `expected_income_remaining`.
- [x] Over-realization and under-realization preserve both expected and received amounts.

## Blocked by

- Issue 1: Require explicit expected payments for receivables

## Suggested verification

- `docker compose exec api pytest -q tests/test_budget.py -q`

## Progress

- RED: `tests/test_budget.py::test_expected_income_mark_received_preserves_expectation_and_links_wallet_event` failed because `POST /budgets/expected-incomes/{id}/mark-received` did not exist.
- GREEN: expected-income realization now creates wallet-backed ledger truth, stores `received_amount`, links `linked_transaction_id`, preserves the expectation as `RECEIVED`, and removes it from expected inflow backing.
- GREEN: debt-linked expected-payment realization records the incoming debt payment, reduces receivable balance, and links the expected row to the generated financial event.

## Issue 3: Warn On Dated And Overdue Debts Owed By The User

## What to build

Debts owed by the user with due dates should produce hard workflow warnings. Current-month dated obligations should remain visible as category floors or cash reserves through G3 math, while overdue obligations should clearly identify missed debt pressure.

## Acceptance criteria

- [x] Active dated debts owed by the user expose hard warning codes before or during the due month.
- [x] Overdue debts owed by the user expose overdue warning codes.
- [x] Category-linked debts continue to appear as category floors.
- [x] Cash-only debts continue to appear as cash obligation reserves.
- [x] Wallet-backed credit/overdraft obligations remain wallet-transfer workflows.

## Blocked by

None - can start immediately.

## Suggested verification

- `docker compose exec api pytest -q tests/test_debt_action_routes.py -q`
- `docker compose exec api pytest -q tests/test_debts.py::test_debt_list_projects_negative_wallet_obligations_without_debt_rows tests/test_debts.py::test_credit_wallet_obligation_payoff_uses_transfer_with_fee_not_debt_payment tests/test_debts.py::test_overdraft_wallet_obligation_payoff_uses_transfer_not_expense -q`

## Progress

- RED: `tests/test_debt_action_routes.py::test_payable_debts_expose_hard_due_and_overdue_warnings` failed because payable debts did not expose due or overdue workflow warning codes.
- GREEN: payable debts with a due date expose `debts.warning.payable_due_hard` or `debts.warning.payable_overdue_hard` through `workflow_warnings`, using the user's effective local date where routes provide timezone context.
- GREEN: existing G3 floors/reserves and G2 wallet-backed obligation invariants stayed green.

## Issue 4: Suggest Paydown For Open-Ended Debts Owed By The User

## What to build

Open-ended debts owed by the user should not be treated as dated obligations, but they should provide soft paydown suggestions so the user can reduce liabilities when free money allows it.

## Acceptance criteria

- [x] Active open-ended debts owed by the user expose soft paydown suggestion codes.
- [x] Suggestions do not reduce plan backing by themselves.
- [x] Suggestions do not block expense save or budget edits.
- [x] Suggestions are distinct from dated/overdue hard warnings.

## Blocked by

- Issue 3: Warn on dated and overdue debts owed by the user

## Suggested verification

- `docker compose exec api pytest -q tests/test_debt_action_routes.py -q`

## Progress

- RED: `tests/test_debt_action_routes.py::test_open_ended_payable_debt_exposes_soft_paydown_suggestion` failed because open-ended payable debts had no suggestion code.
- GREEN: active open-ended payable debts now expose `debts.suggestion.open_ended_paydown` without the due/overdue hard warning codes.
- GREEN: the suggestion is informational only; it does not touch G3 plan backing math.

## Issue 5: Expose Expected Inflow Lifecycle In Month Planning

## What to build

Month planning should explain expected inflow lifecycle state clearly enough for dashboards to distinguish expected, received, missed, and cancelled records without recomputing backing math.

## Acceptance criteria

- [x] Month planning exposes expected inflow totals by lifecycle status.
- [x] Only `EXPECTED` rows contribute to backing.
- [x] Missed expected inflows do not silently roll forward.
- [x] Debt-linked and source-linked expected inflows remain distinguishable in API output.

## Blocked by

- Issue 1: Require explicit expected payments for receivables
- Issue 2: Preserve expected inflow realization history

## Suggested verification

- `docker compose exec api pytest -q tests/test_budget.py -q`

## Progress

- RED: `tests/test_budget.py::test_budget_month_summary_exposes_expected_income_lifecycle_totals_and_items` failed because `/budgets/month-summary` did not expose expected inflow lifecycle fields.
- GREEN: month summary now returns `expected_income_totals` with count, expected amount, and received amount by lifecycle status.
- GREEN: month summary now returns `expected_income_items`, preserving source-linked and debt-linked row identity for dashboards.
- GREEN: only `EXPECTED` rows continue to contribute to `expected_income_remaining` and plan backing.
- GREEN: Docker budget suite passed with 35 tests.
