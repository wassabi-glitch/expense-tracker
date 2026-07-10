# 0029. Payment Plan Row Actions, Write-Offs, and Architecture Cleanup

Date: 2026-07-10

## Status

Accepted

## Context

ADR 0028 clarified that Payment Plans need explicit schedule models:

```text
FLAT_TOTAL
AMORTIZED_LOAN
MANUAL_CONTRACT_SCHEDULE
```

After that decision, the remaining confusion is not only schedule generation. The row-level and plan-level action model also needs to become clearer.

The current implementation already has useful foundations:

```text
PaymentPlan
  PaymentPlanPayment rows
  PaymentPlanTransaction records
  PaymentPlanPaymentAllocation records
  PaymentPlanCharge records
  PaymentPlanLedgerEntry records
```

The current row table already tracks:

```text
amount
paid_amount
written_off_amount
component_type: PRINCIPAL / CHARGE
status
```

This is close to the right model, but several meanings are overloaded:

- A row can be fully settled by payment, write-off, or both, but the current terminal row status is named `PAID`.
- `SKIPPED` exists as a status even though skipping is not a mathematically precise settlement state.
- Row write-off currently behaves like an `ADJUSTMENT` ledger entry, but a write-off is a distinct business action.
- Undoing a write-off should append a reversal entry, not delete the original ledger record.
- The current plan creation model still behaves mostly like a flat installment engine.
- Amortized plans will need principal and charge rows that belong to the same installment.

## Decision

### Row write-off is a first-class action

Users must be able to write off a specific scheduled row.

Row write-off means:

```text
This row, or part of this row, no longer needs to be paid.
No wallet money moved.
The remaining plan obligation is reduced.
```

The write-off action must allow both:

```text
Write off remaining amount
Write off custom amount
```

Example:

```text
Oct 6 row
amount: 1,333,333
paid_amount: 1,266,667
written_off_amount: 0
remaining: 66,666

User writes off: 66,666

Result:
paid_amount: 1,266,667
written_off_amount: 66,666
remaining: 0
row is settled
```

This row is settled, but it is not fully paid. UI copy must not imply that wallet money moved for the written-off part.

### Plan-level write-off is also needed

Some real-world settlements apply to the whole plan, not to one row.

Example:

```text
Remaining plan balance: 4,000,000
Provider says: pay 3,500,000 and we forgive the final 500,000
```

This is a plan-level settlement/write-off. The backend should apply the forgiven amount across remaining schedule rows using a predictable rule.

Default rule:

```text
oldest due date first
within the same due date, CHARGE before PRINCIPAL
```

This keeps plan-level forgiveness compatible with the same waterfall mental model used by payments.

### Row status should mean settlement state, not time state

The current row status names should be changed conceptually from:

```text
PENDING
PARTIAL
PAID
SKIPPED
```

to:

```text
UNPAID
PARTIAL
SETTLED
```

Definitions:

```text
remaining = amount - paid_amount - written_off_amount

UNPAID:
  paid_amount == 0
  written_off_amount == 0

PARTIAL:
  remaining > 0
  and paid_amount + written_off_amount > 0

SETTLED:
  remaining == 0
```

The public UI can still display more specific labels derived from the amounts:

```text
paid_amount == amount:
  Paid

written_off_amount == amount:
  Written off

paid_amount > 0 and written_off_amount > 0 and remaining == 0:
  Settled
```

`SKIPPED` should be removed. A missed row is not skipped. It is one of:

```text
overdue
rescheduled
deferred
written off
still unpaid
```

Overdue is derived:

```text
row is UNPAID or PARTIAL
and due_date < today in the user's timezone
```

It is not stored as a row status.

### PaymentPlanPaymentComponentType stays small

The schedule row component type remains:

```text
PRINCIPAL
CHARGE
```

This is enough for payment allocation and balance math.

Interest is not a top-level component. Interest is a kind of charge.

If the app needs more detail later, add a charge kind:

```text
INTEREST
LATE_FEE
SERVICE_FEE
PENALTY
OTHER
```

But the accounting-level component stays:

```text
PRINCIPAL
CHARGE
```

### PaymentPlanLedgerEntryType needs a dedicated write-off type

The ledger entry types should become:

```text
INITIAL or PLAN_CREATED
PAYMENT
CHARGE_ADDED
WRITE_OFF
ADJUSTMENT
REVERSAL
```

Meanings:

| Type | Meaning |
| --- | --- |
| `INITIAL` / `PLAN_CREATED` | The plan obligation was opened. |
| `PAYMENT` | Wallet money or recorded payment reduced the obligation. |
| `CHARGE_ADDED` | A fee, penalty, or interest row was added. |
| `WRITE_OFF` | Some obligation was forgiven, waived, or settled without wallet money. |
| `ADJUSTMENT` | A correction was made because recorded data was wrong. |
| `REVERSAL` | A previous ledger entry was undone without deleting history. |

`ADJUSTMENT` must not be used as a generic bucket for write-offs. A correction and a forgiveness action tell different stories.

Example:

```text
Bank app says Sarflog is 20,000 too high because of rounding:
  ADJUSTMENT

Seller says the last 500,000 no longer needs to be paid:
  WRITE_OFF
```

### Reversals must preserve history

Payment Plan ledger behavior should follow the immutable ledger direction from ADR 0024 and ADR 0027.

Undoing a payment, charge, write-off, or adjustment should append a `REVERSAL` entry.

It should not delete the original ledger entry.

Example:

```text
1. WRITE_OFF
   amount_delta: -66,666
   row: Oct 6

2. REVERSAL
   reverses_entry_id: <write_off_entry_id>
   amount_delta: +66,666
```

This preserves the user's real activity history.

### Row actions and plan actions have different responsibilities

Row actions apply to one scheduled obligation.

Plan actions apply to the contract as a whole.

Row actions:

| Action | Purpose |
| --- | --- |
| Pay row | Pay the remaining amount for one row. |
| Partial pay row | Pay part of one row. |
| Write off row amount | Forgive part or all of one row. |
| Edit due date | Reschedule one row without changing the whole plan. |
| Add row note | Capture context for one scheduled obligation. |
| View row history | Show payments, write-offs, and reversals applied to that row. |

Plan actions:

| Action | Purpose |
| --- | --- |
| Record payment | Pay across the schedule using waterfall allocation. |
| Add fee or penalty | Add a new `CHARGE` row. |
| Write off / settle balance | Forgive part of the remaining plan globally. |
| Edit plan metadata | Change name, provider, category, or non-financial fields. |
| Edit future schedule | Change future schedule rows intentionally. |
| Reverse latest ledger action | Undo the latest reversible financial action. |
| Archive / unarchive | Change visibility without changing financial truth. |
| Delete plan | Only allowed while the plan is pristine. |

Row delete should not be a normal action after real activity exists. Active rows should be paid, written off, rescheduled, or reversed through ledger-backed actions.

## Target Architecture

### Current shape

```text
PaymentPlan
  total_price
  down_payment
  months
  payment_count
  frequency
  remaining_amount
  monthly_payment_amount
  regular_payment_amount
  schedule_rule
  status

  PaymentPlanPayment[]
    amount
    paid_amount
    written_off_amount
    component_type
    status
    due_date
    payment_plan_ledger_entry_id

  PaymentPlanTransaction[]
  PaymentPlanPaymentAllocation[]
  PaymentPlanCharge[]
  PaymentPlanLedgerEntry[]
```

This shape works reasonably for flat installment plans, but it is not expressive enough for ADR 0028's full target.

### Improved shape

```text
PaymentPlan
  plan_type
  schedule_model
  provider
  currency
  start_date
  payment_count
  frequency
  archived_at
  generation_metadata

  derived totals:
    remaining_total
    remaining_principal
    remaining_charges
    lifecycle_status
    time_status

PaymentPlanScheduleRow
  installment_number
  due_date
  component_type: PRINCIPAL / CHARGE
  charge_kind: optional
  amount
  paid_amount
  written_off_amount
  settlement_state: derived or projected

PaymentPlanLedgerEntry
  entry_type
  amount_delta
  principal_delta
  charge_delta
  balance_after
  source
  reverses_entry_id

PaymentPlanPaymentAllocation
  row_id
  transaction_id
  ledger_entry_id
  amount

PaymentPlanWriteOffAllocation
  row_id
  ledger_entry_id
  amount
```

The exact table names can change during implementation. The important model is:

```text
Rows say what is scheduled.
Allocations say how actions touched rows.
Ledger entries say what happened historically.
Derived totals say where the plan stands today.
```

## Architecture Improvements Needed

### Add `schedule_model`

`plan_type` is user/product language.

`schedule_model` is math behavior.

Examples:

```text
STORE_INSTALLMENT -> FLAT_TOTAL
BANK_LOAN -> AMORTIZED_LOAN
OTHER -> user chooses
```

The backend should store the schedule model explicitly.

### Replace `months` as the core term concept

`months` is not enough for weekly, biweekly, quarterly, or manual plans.

The canonical contract term should be:

```text
payment_count + frequency
```

Examples:

```text
12 monthly payments
26 biweekly payments
52 weekly payments
4 quarterly payments
```

### Rename or clarify `remaining_amount`

For flat plans, `remaining_amount` usually means unpaid scheduled total.

For amortized loans, there are multiple useful balances:

```text
remaining principal
remaining charges
remaining scheduled total
```

Example:

```text
Remaining principal: 2,735,583
Future interest rows: 68,234
Remaining scheduled total: 2,803,817
```

The API should expose these explicitly:

```text
remaining_total
remaining_principal
remaining_charges
```

If a stored balance is kept for performance, it should be treated as a projection/cache that can be reconciled from rows and ledger entries.

### Add installment grouping

Amortized plans can have multiple rows for one due date.

Example:

```text
Installment #1, Aug 10
  CHARGE: 75,000 interest
  PRINCIPAL: 1,330,000
```

These two rows should be grouped in the UI as one installment.

Rows need a stable grouping field, such as:

```text
installment_number
schedule_group_id
```

Without grouping, the UI will feel like one loan payment has split into confusing duplicate rows.

### Fix waterfall ordering

Waterfall allocation must follow ADR 0028:

```text
oldest due date first
within same due date, CHARGE before PRINCIPAL
```

This applies to:

```text
plan-level payment
plan-level write-off
bulk settlement
early overpayment
```

### Add write-off allocation history

Current payment allocations can explain how a payment touched rows.

Custom write-offs need the same level of traceability.

If a user writes off 500,000 across three rows, the app should know:

```text
which rows were touched
how much was written off per row
which ledger entry caused it
whether that write-off was later reversed
```

A single `payment_plan_ledger_entry_id` on the row is not enough once rows can receive multiple payments, partial write-offs, and reversals.

### Stop using payment transactions for non-payment actions

A payment transaction should represent an actual payment action.

A write-off is not a payment.

If grouping is needed for write-offs or adjustments, use a neutral action group concept, or rely on the ledger entry plus row allocation records.

This keeps language truthful:

```text
payment -> wallet/payment action
write-off -> forgiven obligation
adjustment -> correction
reversal -> undo history
```

### Keep archive separate from financial state

Archive is visibility.

Financial lifecycle is derived from remaining obligation.

Public plan state should follow the same direction as Debts:

```text
lifecycle_status:
  OPEN
  CLOSED

time_status:
  ON_TRACK
  OVERDUE
  null when closed

archived_at:
  separate visibility flag
```

## Examples

### Flat plan

```text
Phone final price: 15,000,000
Down payment: 3,000,000
Remaining: 12,000,000
Schedule: 12 monthly rows

Each row:
  component_type: PRINCIPAL
  amount: 1,000,000
```

The plan can be paid by:

```text
plan-level payment: 2,500,000
```

Waterfall applies:

```text
Month 1 row: paid 1,000,000
Month 2 row: paid 1,000,000
Month 3 row: paid 500,000
```

### Amortized loan

```text
Principal: 4,070,000
Annual rate: 19.9%
Term: 3 monthly payments
```

Generated rows:

```text
Aug 10 installment #1
  CHARGE interest: 67,492
  PRINCIPAL: 1,334,417

Sep 10 installment #2
  CHARGE interest: 45,362
  PRINCIPAL: 1,356,547

Oct 10 installment #3
  CHARGE interest: 22,872
  PRINCIPAL: 1,379,036
```

The UI should show these as three installments, not six unrelated rows.

### Row write-off

```text
Nov 6 row
amount: 1,333,333
paid: 0
written off: 0

User writes off: 333,333

Result:
paid: 0
written off: 333,333
remaining: 1,000,000
status: PARTIAL
ledger: WRITE_OFF -333,333
```

### Reversing the write-off

```text
Original:
WRITE_OFF -333,333

Undo:
REVERSAL +333,333
reverses_entry_id: <write_off_entry_id>
```

The row returns to:

```text
paid: 0
written off: 0
remaining: 1,333,333
status: UNPAID
```

## Consequences

### Benefits

- Row state becomes mathematically honest.
- Users can handle real-world forgiveness and partial waivers.
- Payment, write-off, correction, and reversal become distinct concepts.
- Payment Plan history becomes compatible with immutable ledger architecture.
- ADR 0028's flat, amortized, and manual schedule models can share the same row/action foundation.
- The UI can show one clean story: what was due, what was paid, what was forgiven, and what remains.

### Costs

- Migrations are needed for enum cleanup.
- Existing code paths that assume `PAID` means paid by wallet money must be corrected.
- Row history needs better allocation records for write-offs.
- Plan creation needs a larger redesign to support schedule models and reviewable schedule drafts.
- The frontend must distinguish paid, written off, and settled rows clearly.

### Implementation direction

Do not start by adding more statuses.

Start by making the domain concepts sharper:

```text
schedule row
component
payment allocation
write-off allocation
ledger entry
derived settlement state
derived overdue state
```

Once those are clean, the UI labels become much easier:

```text
Unpaid
Partial
Paid
Written off
Settled
Overdue
On track
```

## References

- ADR 0005: Payment Plan Engine, Statuses, and Budget Boundary
- ADR 0024: Immutable Ledger Boundary: When It Applies
- ADR 0027: Debt Ledger Actions, Principal/Charges, and Reversal Rules
- ADR 0028: Payment Plan Schedule Models and Contract Review
