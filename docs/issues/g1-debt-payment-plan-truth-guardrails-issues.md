# Issues: G1 - Debt and Payment-Plan Truth Guardrails

Parent PRD: `docs/prd/g1-debt-payment-plan-truth-guardrails.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Harden regular debt generic update and delete guardrails**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-7, 15-19, 22

2. **Add payment-plan lifecycle-safe update and delete boundaries**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 7-11, 19, 22

3. **Add payment-plan-owned latest payment undo**
   - Type: AFK
   - Blocked by: Issue 2
   - User stories covered: 12-18, 19, 22

4. **Make debt and payment-plan reversal copy wallet-reality explicit**
   - Type: AFK
   - Blocked by: Issue 3
   - User stories covered: 13, 15-18, 20-22

5. **Unify debt and payment-plan detail activity storylines**
   - Type: AFK
   - Blocked by: Issue 3
   - User stories covered: 20-22

## Issue 1: Harden Regular Debt Generic Update And Delete Guardrails

## What to build

Restrict regular debt generic CRUD so it cannot bypass the debt action model. Generic update should remain useful for safe metadata, but it must not change debt status or financial setup once real activity exists. Opening amount correction and delete are allowed only while a debt is pristine. Payment-plan-managed debts remain protected from regular debt mutation routes.

This slice should preserve existing explicit actions: record payment, add charge, forgive, settle, adjust balance, reverse ledger entry, archive, and restore.

## Acceptance criteria

- [x] Generic debt update cannot set `PAID`, `FORGIVEN`, `SETTLED`, `ARCHIVED`, or `ACTIVE` status directly.
- [x] Generic debt update can still edit safe metadata for a normal active debt.
- [x] Opening amount correction is allowed for a pristine regular debt.
- [x] Opening amount correction is blocked after payment activity exists.
- [x] Opening amount correction is blocked after charge activity exists.
- [x] Opening amount correction is blocked after forgiveness, settlement, adjustment, or reversal history exists.
- [x] Non-pristine regular debt delete is blocked with a domain error.
- [x] Pristine regular debt delete remains available.
- [x] Payment-plan-managed debt update/delete remains blocked through regular debt routes.
- [x] Existing explicit debt action tests continue to pass.

## Blocked by

None - can start immediately.

## Suggested verification

- `docker-compose exec api pytest -q tests/test_debt_policy.py tests/test_debt_action_routes.py tests/test_debts.py`

## Issue 2: Add Payment-Plan Lifecycle-Safe Update And Delete Boundaries

## What to build

Add payment-plan update/delete behavior that respects lifecycle state. Safe details can be edited while the plan is not archived. Financial setup fields and schedule shape can be corrected only before real payment, charge, write-off, linked goal, or correction activity exists. Pristine plans can be deleted; non-pristine plans must use archive or future restructure actions.

## Acceptance criteria

- [x] Pristine payment plan can update safe details.
- [x] Pristine payment plan can correct setup fields that define the schedule.
- [x] Payment plan with payment history cannot update total price, months, frequency, start date, or due dates through generic update.
- [x] Payment plan with charge history cannot update schedule shape through generic update.
- [x] Payment plan with write-off history cannot update schedule shape through generic update.
- [x] Payment plan with linked goal dependency cannot be deleted.
- [x] Pristine payment plan delete removes or reverses linked debt safely.
- [x] Non-pristine payment plan delete is blocked with a domain error.
- [x] Archived payment plan is immutable except restore if a restore action exists.

## Blocked by

- Issue 1: Harden regular debt generic update and delete guardrails

## Suggested verification

- `docker-compose exec api pytest -q tests/test_installment_routes.py tests/test_debt_policy.py`

## Issue 3: Add Payment-Plan-Owned Latest Payment Undo

## What to build

Add a payment-plan-owned undo action for payment operations. The action should reverse the latest payment operation only in v1, restore wallet balance through audit-preserving ledger records, reopen affected schedule rows, update installment allocations, reconcile the linked debt, and keep generic debt ledger reversal blocked for payment-plan-managed debts.

## Acceptance criteria

- [x] Payment-plan latest payment can be undone from a payment-plan route.
- [x] Undo restores wallet balance when wallet money moved.
- [x] Undo creates audit reversal records rather than silently deleting history.
- [x] Undo reopens affected schedule rows and restores paid amounts.
- [x] Undo of a multi-row payment reopens every affected row correctly.
- [x] Undo of a charge-component payment restores charge balance rather than principal balance.
- [x] Older payment undo is blocked until newer payment operations are undone.
- [x] Generic debt ledger reversal remains blocked for payment-plan-managed debts.
- [x] Goal-linked payment undo either updates goal state safely or blocks with a clear reason.

## Blocked by

- Issue 2: Add payment-plan lifecycle-safe update and delete boundaries

## Suggested verification

- `docker-compose exec api pytest -q tests/test_installment_routes.py tests/test_debt_policy.py`

## Issue 4: Make Debt And Payment-Plan Reversal Copy Wallet-Reality Explicit

## What to build

Update reversal/undo user-facing copy and action metadata so wallet-changing undo actions clearly explain that app wallet balances will change and should only be used when the real-world payment failed, was cancelled, refunded, or recorded by mistake.

## Acceptance criteria

- [x] Regular debt reversal confirmation copy warns that app wallet money will be restored.
- [x] Payment-plan undo confirmation copy warns that app wallet money will be restored.
- [x] Copy distinguishes reverse/undo from forgiveness, settlement, charge, correction, and refund paths.
- [x] Blocked older payment-plan reversal explains that newer payments must be undone first.
- [x] English, Russian, and Uzbek locale files include the updated copy.

## Blocked by

- Issue 3: Add payment-plan-owned latest payment undo

## Suggested verification

- `docker-compose exec frontend npm run build`
- Targeted search for the new copy keys in supported locales.

## Issue 5: Unify Debt And Payment-Plan Detail Activity Storylines

## What to build

Make debt and payment-plan detail modals use one audit-storyline mental model. Detail views should show oldest-to-newest activity, business date and recorded timestamp distinctly, and action buttons only where the proper owning domain action exists and is allowed.

## Acceptance criteria

- [x] Debt detail activity remains oldest-to-newest.
- [x] Payment-plan detail activity renders oldest-to-newest.
- [x] Payment-plan details no longer reverse backend debt activity into newest-first order.
- [x] Payment-plan activity shows business date and recorded timestamp.
- [x] Payment-plan activity uses storyline treatment comparable to debt details.
- [x] Undo/Reverse buttons are shown only when the owning domain action exists and is allowed.
- [x] Frontend build passes.

## Blocked by

- Issue 3: Add payment-plan-owned latest payment undo

## Suggested verification

- `docker-compose exec frontend npm run build`
- Manual UI check of debt details and payment-plan details if the frontend is running.
