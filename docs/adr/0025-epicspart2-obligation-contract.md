# 0025. Epicspart2 Obligation Contract — Immutable-Ledger Rules for Debt and Payment-Plan Work

Date: 2026-07-10

## Status

Accepted

## Context

ADR 0011 established the append-only immutable ledger architecture across Sarflog: posted financial events must never be hard-deleted or mutated in place. ADR 0024 bounded that rule with a one-line test: **the immutable-ledger pattern applies if and only if an operation produces wallet legs with non-zero amounts.**

Tickets 1–6 of Epicspart2 built the shared seams (`post_financial_event`, `void_financial_event`, correction reposts, closed-period guardrails) and converted standalone income as the proof slice. ADR 0024 explicitly called out that Tickets 7 and 8 exist because debt, payment-plan, asset, and expected-inflow paths have not yet been fully converted to the shared seams.

Ticket 7 establishes the contract for new Epicspart2 obligation work. It does **not** fix every existing violation — those are conversion work for future tickets. It ensures that new debt and payment-plan work does not introduce *more* mutable money history.

## Decision

### The wallet-legs test (from ADR 0024)

> **Did this operation produce wallet legs with non-zero amounts?** If yes → immutable. If no → mutable.

Every new Epicspart2 PR touching Debt or Payment Plan money flows must apply this test before choosing how to handle create, update, delete, and undo/reversal operations.

### Concrete examples for obligation work

| Action | Wallet legs? | Immutable ledger? | Correct pattern |
|--------|-------------|-------------------|-----------------|
| Record debt payment (money transferred) | ✅ Wallet outflow | ✅ Use `post_financial_event` | `void_financial_event` for undo |
| Record payment plan payment | ✅ Wallet outflow | ✅ Use `post_expense_event` seam | Create reversal FinancialEvent for undo |
| Undo payment plan payment | ✅ Wallet was touched | ✅ Create reversal FinancialEvent; keep original | `_create_financial_event_reversal` |
| Reverse debt ledger entry | ✅ Wallet was touched | ✅ Void FinancialEvent; create DebtLedgerEntry REVERSAL | Route `POST /debts/{id}/ledger/{entry_id}/reverse` |
| Delete pristine debt (no payments, no money) | ❌ No money moved | ❌ Delete Debt row directly | `DELETE /debts/{id}` with pristine check |
| Delete pristine payment plan (no payments) | ❌ No payments made | ❌ Delete plan directly | `DELETE /plans/{id}` with pristine check |
| Update debt counterparty name | ❌ Metadata only | ❌ Direct `setattr` on Debt row | `PATCH /debts/{id}` with metadata fields |
| Update payment plan note | ❌ Metadata only | ❌ Direct `setattr` on plan row | `PATCH /plans/{id}` with metadata fields |
| Create/delete budget | ❌ Spending permission | ❌ Delete directly | No FinancialEvent created |
| Create/delete recurring template | ❌ Intent only | ❌ Archive/delete directly | No FinancialEvent created |
| Goal creation/deletion (no contributions) | ❌ Reservation | ❌ Delete directly | No FinancialEvent created |
| Add debt charge (interest/fee) | ❌ No wallet movement (yet) | ❌ DebtLedgerEntry only | FinancialEvent created only when paid |
| Write off payment plan payment | ❌ No wallet movement | ❌ PaymentPlanLedgerEntry ADJUSTMENT only | Status change, no wallet effect |

### Rules for new obligation code

1. **If an operation produces FinancialEvent wallet legs**, it must use `post_financial_event` (or `post_expense_event` for expense-shaped flows) for creation and `void_financial_event` for undo/reversal. Never hard-delete a `FinancialEvent` row, and never mutate `amount`, `wallet_id`, or `category` of a POSTED event.

2. **If an operation does not produce wallet legs**, direct mutation (UPDATE or DELETE) is acceptable. This includes metadata fields (counterparty_name, description, note, expected_return_date), planning intent (budgets, recurring templates, goals without contributions), and draft state.

3. **Correction flows must append, not rewrite.** A correction to a posted obligation event must void the original (creating a reversal) and post a corrected event. The original FinancialEvent, WalletLedger rows, and EntityLedger rows remain available for audit.

4. **`remaining_amount` on Debt and PaymentPlan is a projection**, computed from the sum of ledger entries (`DebtLedgerEntry.amount_delta` or `PaymentPlanLedgerEntry.amount_delta`) filtered by `status = POSTED`. It must never be set directly without a corresponding ledger entry recording the fact.

### Shared seams to use

| Seam | Location | When to use |
|------|----------|-------------|
| `post_financial_event` | `app.domains.ledger._ledger_service` | Create any money event with wallet legs |
| `void_financial_event` | `app.domains.ledger._ledger_service` | Void a posted FinancialEvent (shared reversal) |
| `post_expense_event` | `app.domains.posting._posting_service` | Create expense-shaped events with budget/goal/epoch validation |
| `post_obligation_event` | `app.services.obligation_money_posting_service` | Delegate non-expense obligation events through the shared seam |
| `_create_financial_event_reversal` | `app.routers.debts` | Create a reversal FinancialEvent for debt/payment-plan undo flows |
| `create_debt_ledger_entry` | `app.domains.debt._debt_service` | Append a row to the debt-specific ledger |
| `reverse_debt_transaction_ledger` | `app.domains.debt._debt_service` | Create REVERSAL entries in the debt ledger |

### Forbidden patterns

The following patterns exist in the current codebase and are acknowledged as conversion work. New Epicspart2 code must not introduce more of them:

1. **`db.delete(event)` on a FinancialEvent row** — found in `delete_debt` and `delete_transaction` in `app/routers/debts.py`. Instead use `void_financial_event`.

2. **Manual `FinancialEvent` / `WalletLedger` / `EntityLedger` row construction** — found in `_record_initial_transfer_event` and the non-expense path of `_record_wallet_allocated_debt_event` in `app/routers/debts.py`. Instead use `post_financial_event`.

3. **`db.delete(ledger_entry)` on a DebtLedgerEntry or PaymentPlanLedgerEntry** — found in `undo_write_off_payment` in `app/routers/payment_plans.py`. Instead mark the entry REVERSED and append a counter-balancing entry.

4. **`db.delete(transaction)` on a PaymentPlanTransaction or DebtTransaction** — found in `undo_latest_payment_plan_payment` in `app/routers/payment_plans.py`. Instead mark the transaction voided.

5. **Direct `WalletService.adjust_balance()` call to reverse wallet effects** — the `reverse_wallet_effect` function in `app/domains/debt/_debt_service.py` adjusts balances directly without creating a FinancialEvent reversal. All wallet balance adjustments must go through `post_financial_event`.

### PR review checklist

Every new Epicspart2 PR touching debt or payment-plan money flows must pass this checklist:

- [ ] **Wallet-legs test**: Does the operation produce FinancialEvent wallet legs with non-zero amounts? If yes, immutable treatment is required. If no, proceed to the next item.
- [ ] **No hard-delete of FinancialEvent**: No `db.delete(event)` on any FinancialEvent row. Use `void_financial_event` instead.
- [ ] **No in-place mutation of POSTED events**: Amount, wallet, category, and date of a POSTED FinancialEvent must not be mutated. Use correction repost instead.
- [ ] **Seam usage**: All money events are created through `post_financial_event` (or `post_expense_event` for expense-shaped flows). No manual `FinancialEvent` / `WalletLedger` / `EntityLedger` construction.
- [ ] **Reversals are append-only**: Undo/reversal flows create REVERSAL FinancialEvents or REVERSAL ledger entries. No hard-delete of events, ledger entries, or transactions.
- [ ] **Projections are projections**: `remaining_amount` on Debt and PaymentPlan is computed from ledger entries, never set directly without a corresponding ledger entry.
- [ ] **Metadata stays mutable**: Counterparty name, description, note, expected_return_date, and other non-money fields may be updated in place without creating reversals.
- [ ] **Non-money entities excluded**: Budgets, recurring templates, session drafts, and goals without contributions do not create FinancialEvents on create/delete.
- [ ] **Regression test**: The PR includes or updates a test in `tests/test_immutable_ledger_guardrails.py` that proves posted FinancialEvents remain available after any new undo/reversal action.

## Consequences

### For developers
- Every new Epicspart2 PR touching debt or payment-plan money flows has a clear, one-question test: "Did this operation produce wallet legs?"
- The contract checklist in this ADR serves as a PR review gate.
- The shared seams are already built and tested — no new infrastructure is needed.

### For reviewers
- Regression tests in `tests/test_immutable_ledger_guardrails.py` encode the contract in executable form. If a PR introduces a new hard-delete or bypass pattern, the tests will catch it.
- The forbidden patterns list provides concrete examples of what to reject.

### For the roadmap
- Existing violations (listed under "Forbidden patterns") remain as conversion work for future Epicspart2 tickets.
- Ticket 8 (wallet projection verification) and Ticket 9 (definition of done) build on this contract.

## References

- [[0011-immutable-ledger-architecture]] — Core decision establishing the append-only ledger
- [[0024-immutable-ledger-boundary-when-it-applies]] — The wallet-legs boundary test
- `tests/test_immutable_ledger_guardrails.py` — Executable regression guardrails for this contract
- `docs/epicspart2-tickets/tickets1-ledger-foundation.md` — Ticket 7 specification
