# 0028. Payment Plan Schedule Models and Contract Review

Date: 2026-07-10

## Status

Accepted

## Context

Payment Plans have been difficult to reason about because one creation flow currently tries to cover very different real-world products.

The existing backend mostly behaves like a flat installment engine:

```text
remaining_amount = total_price - down_payment
payment_amount = remaining_amount / payment_count
```

That is correct for store installment and buy-now-pay-later plans, but it is not enough for true bank-style loans where each payment contains both interest and principal.

Payment Plans need an explicit schedule model so the app does not infer financial math from vague product labels alone.

## Decision

### Payment Plans have schedule models

Payment Plan type and schedule math are related, but they are not the same concept.

We will model the schedule behavior explicitly.

Initial schedule models:

```text
FLAT_TOTAL
AMORTIZED_LOAN
MANUAL_CONTRACT_SCHEDULE
```

### Model 1: `FLAT_TOTAL`

This is the "Nasiya" / buy-now-pay-later / flat installment model.

Examples:

- Uzum Nasiya
- Zoodpay
- store installment
- marketplace installment
- product financing where the final price is already known
- service contract with fixed total amount

User-facing idea:

```text
The seller gives one final total price. The app divides the unpaid total across scheduled rows.
```

Data to ask:

```text
What did you buy or contract for?
Provider / seller
Final total price
Down payment paid today
Number of payments
Frequency
First due date
```

Math:

```text
remaining = final_total_price - down_payment
row_amount = remaining / payment_count
```

All generated rows are `PRINCIPAL` rows because the seller's markup is already baked into the final total price.

Example:

```text
Phone cash price: not needed by this model
Nasiya final price: 15,000,000
Down payment: 3,000,000
Payments: 12 monthly

Remaining scheduled amount: 12,000,000
Each row: 1,000,000 principal
```

### Model 2: `AMORTIZED_LOAN`

This is the bank loan / mortgage / auto loan model.

Examples:

- bank loan
- microloan
- mortgage
- auto loan
- education loan when it behaves like a bank loan

User-facing idea:

```text
The user borrowed principal. Interest is charged over time on the remaining principal.
```

Data to ask:

```text
What is the loan for?
Provider / lender
Principal loan amount
Annual interest rate
Term / number of payments
Payment frequency
First due date
Whether money entered a wallet today
```

Definitions:

| Term | Meaning |
| --- | --- |
| Principal | The amount borrowed or financed before interest. |
| Interest | Cost charged over time for using the borrowed principal. |
| Term | How long the contract lasts, represented as payment count plus frequency. |
| Frequency | How often payments are due: monthly, weekly, biweekly, quarterly, etc. |
| Periodic rate | Interest rate converted into the payment frequency period. |

The UI should ask for annual interest rate first because that is the common lending language. The backend converts it to a periodic rate.

Examples:

```text
Annual rate: 24%
Monthly periodic rate: 24% / 12 = 2%
Weekly periodic rate: 24% / 52
Biweekly periodic rate: 24% / 26
Quarterly periodic rate: 24% / 4
```

The app can generate a standard fixed-payment amortized schedule with the PMT formula:

```text
payment_amount = PMT(principal, periodic_rate, payment_count)
interest_for_period = remaining_principal * periodic_rate
principal_for_period = payment_amount - interest_for_period
remaining_principal = remaining_principal - principal_for_period
```

For each due date, the schedule should represent both components:

```text
CHARGE row: interest portion
PRINCIPAL row: principal portion
```

Example:

```text
Principal: 4,070,000
Annual rate: 19.9%
Frequency: monthly
Term: 3 payments
First due date: Aug 10, 2026
```

Generated preview:

| Due date | Total payment | Interest / charge | Principal | Remaining principal |
| --- | ---: | ---: | ---: | ---: |
| Aug 10, 2026 | 1,401,909 | 67,492 | 1,334,417 | 2,735,583 |
| Sep 10, 2026 | 1,401,909 | 45,362 | 1,356,547 | 1,379,036 |
| Oct 10, 2026 | 1,401,908 | 22,872 | 1,379,036 | 0 |

Final rows may be adjusted for rounding so remaining principal reaches zero.

### Model 3: `MANUAL_CONTRACT_SCHEDULE`

Manual schedule mode is the escape hatch for exact bank-contract matching.

Use this when:

- the bank app already shows exact rows
- the contract uses a formula Sarflog does not model
- each row has unusual amounts
- fees, insurance, holidays, grace periods, or custom rounding make generated rows differ

The user enters scheduled rows:

| Due date | Principal | Interest / fees | Total |
| --- | ---: | ---: | ---: |
| Aug 10, 2026 | 1,330,000 | 75,000 | 1,405,000 |
| Sep 10, 2026 | 1,360,000 | 45,000 | 1,405,000 |
| Oct 10, 2026 | 1,380,000 | 17,000 | 1,397,000 |

In this mode, the bank contract is the source of truth and Sarflog records the plan-owned schedule from the user-provided rows.

This should not be the default experience. It should be available when exactness matters.

Future ergonomics:

- paste rows
- CSV import
- copy previous row
- auto-fill due dates
- bulk edit totals
- import from a bank statement later

### Waterfall applies to the whole unpaid schedule

The Payment Plan waterfall is not limited to one month.

When a user records a payment, the system applies it across the whole unpaid schedule in this order:

```text
oldest due date first
within the same due date: CHARGE rows before PRINCIPAL rows
then next due date
```

Example:

| Due date | Component | Unpaid |
| --- | --- | ---: |
| Aug 1 | `CHARGE` | 100,000 |
| Aug 1 | `PRINCIPAL` | 900,000 |
| Sep 1 | `CHARGE` | 80,000 |
| Sep 1 | `PRINCIPAL` | 920,000 |

If the user pays 1,100,000:

```text
Aug charge: 100,000 paid
Aug principal: 900,000 paid
Sep charge: 80,000 paid
Sep principal: 20,000 paid
```

This preserves the plan-owned payment story while allowing early or over-sized payments.

### Generated schedules must be reviewable

For generated flat and amortized schedules, the final creation step should show a schedule preview before the user presses Create.

Preview should include:

```text
total principal
total interest / charges
total to pay
final due date
scheduled rows
```

The user should be able to:

- edit a row
- add a fee row
- change a due date
- switch to manual schedule mode
- proceed when the generated schedule matches their contract closely enough

The preview must be useful but not intimidating. Most users should be able to glance and create the plan.

### Sarflog generates helpful schedules, not legal guarantees

Sarflog can generate a mathematically correct standard amortized schedule when it has:

```text
principal amount
annual interest rate
payment frequency
payment count / term
first due date
rounding rule
```

But real lenders may differ. Banks can use:

- daily interest instead of simple period interest
- 365-day or 360-day year basis
- uneven first or final periods
- holidays or weekend due-date shifting
- insurance or service fees
- grace periods
- lender-specific rounding rules
- annuity or declining-balance variations

Therefore:

```text
Sarflog's generated schedule is a planning tool.
The bank contract or bank app is the source of truth.
```

If the generated schedule differs row-by-row, the user should switch to manual contract schedule mode rather than fighting the formula.

### Payment Plan types should map to schedule models by default

Default mapping:

| Plan type | Default schedule model |
| --- | --- |
| `STORE_INSTALLMENT` | `FLAT_TOTAL` |
| `PRODUCT_FINANCING` | `FLAT_TOTAL` |
| `SERVICE_CONTRACT` | `FLAT_TOTAL` by default |
| `BANK_LOAN` | `AMORTIZED_LOAN` |
| `MORTGAGE` | `AMORTIZED_LOAN` |
| `AUTO_LOAN` | `AMORTIZED_LOAN` |
| `EDUCATION_LOAN` | Depends on provider; allow user choice |
| `OTHER` | Allow user choice |

Plan type is product language. Schedule model is math behavior. The backend should store the schedule model explicitly instead of relying only on plan type.

## Consequences

### For backend

- Add explicit schedule model behavior for Payment Plans.
- Keep flat division for `FLAT_TOTAL`.
- Add amortization schedule generation for `AMORTIZED_LOAN`.
- Support manual schedule row creation for `MANUAL_CONTRACT_SCHEDULE`.
- Store enough metadata to explain how a schedule was generated.
- Keep `PaymentPlanPayment.component_type` because it supports principal and charge rows.
- Waterfall allocation remains plan-wide and due-date ordered, with charges before principal at the same due date.

### For frontend

- Payment Plan creation should branch by schedule model.
- Flat plans should ask for final price, down payment, count, frequency, and first due date.
- Amortized plans should ask for principal, annual interest rate, term/payment count, frequency, first due date, and optional wallet disbursement.
- Manual mode should let the user enter exact rows from the bank contract.
- The final step should show a reviewable schedule preview before creation.

### For product language

- "Term" means how long the contract lasts: payment count plus frequency.
- "Interest rate" should default to annual rate in the UI.
- "Frequency" determines how annual rate converts to periodic rate.
- "Interest" is represented as scheduled `CHARGE` rows.
- "Principal" is represented as scheduled `PRINCIPAL` rows.

## References

- ADR 0005: Payment Plan Engine, Statuses, and Budget Boundary
- ADR 0024: Immutable Ledger Boundary: When It Applies
- ADR 0025: Epicspart2 Obligation Contract
- ADR 0027: Debt Ledger Actions, Principal/Charges, and Reversal Rules
