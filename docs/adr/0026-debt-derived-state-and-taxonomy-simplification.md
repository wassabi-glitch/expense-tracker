# 0026. Debt Derived State and Taxonomy Simplification

Date: 2026-07-10

## Status

Accepted

## Context

The Debt domain still carries legacy enum concepts that came from an older architecture where Debts and Payment Plans were coupled. That coupling caused Debt to absorb Payment Plan vocabulary such as mortgages, car loans, store installments, service pay-later products, and bank loan product labels.

Debt status also became overloaded. One stored enum attempted to describe lifecycle, urgency, archive state, collection severity, payment outcome, and forgiveness outcome. The product direction is now simpler: Debts and Payment Plans are separate domains, and Debt should expose only clear derived states.

The project is still in development. Preserving legacy Debt rows is not required for this cleanup. We may drop stale columns, stale enum values, and existing development data if that is the cleanest path.

## Decision

### Debt status is derived, not stored

Debt has two public state concepts:

1. `lifecycle_status`
2. `time_status`

`lifecycle_status` is derived from the Debt balance:

| Derived value | Rule |
| --- | --- |
| `OPEN` | `remaining_amount > 0` |
| `CLOSED` | `remaining_amount <= 0` |

`time_status` is derived from lifecycle status, the Debt due date, and the user's local business date:

| Derived value | Rule |
| --- | --- |
| `ON_TRACK` | Debt is `OPEN` and `expected_return_date >= today_in_user_timezone` |
| `OVERDUE` | Debt is `OPEN` and `expected_return_date < today_in_user_timezone` |
| `null` | Debt is `CLOSED` |

Valid combinations:

| Lifecycle | Time status | Valid? | Meaning |
| --- | --- | --- | --- |
| `OPEN` | `ON_TRACK` | Yes | The Debt still has balance and the due date has not passed. |
| `OPEN` | `OVERDUE` | Yes | The Debt still has balance and the due date has passed. |
| `CLOSED` | `null` | Yes | The Debt has no remaining balance. |
| `CLOSED` | `ON_TRACK` | No | Closed Debts do not need time urgency. |
| `CLOSED` | `OVERDUE` | No | Closed Debts must never look overdue. |

`OPEN`, `CLOSED`, `ON_TRACK`, and `OVERDUE` may exist as backend/API schema enums, but they must not be stored as Debt table columns. They are API language, not persistence truth.

### Archive is separate from Debt status

Archive is a user filing action, not a lifecycle status.

The stored archive source of truth is `archived_at`.

A Debt may be open and archived, or closed and archived. Restoring a Debt clears archive metadata and does not invent a lifecycle transition. The backend recomputes lifecycle and time status from balance, due date, and user timezone.

The legacy `DebtStatus` enum and `debts.status` column should be removed, not replaced with `OPEN` or `CLOSED`.

### Debt and Payment Plan taxonomy must stay separate

Debt answers:

1. Who owes whom?
2. Why does the obligation exist?
3. Who is the counterparty?
4. What is the balance and due date?

Payment Plan answers:

1. What scheduled repayment structure exists?
2. What type of plan is it?
3. What rows are due, paid, partial, or pending?
4. What schedule-specific charges, deferrals, or write-offs exist?

Debt must not keep Payment Plan product vocabulary.

### `DebtProductKind` should be removed from Debt

`DebtProductKind` is the main confusing enum and should be eliminated from the Debt model, schemas, API payloads, and UI.

The following values are Payment Plan vocabulary and do not belong to standalone Debt:

| Value | Reason |
| --- | --- |
| `MORTGAGE` | Scheduled loan product. Belongs to Payment Plan type. |
| `CAR_LOAN` | Scheduled vehicle loan. Belongs to Payment Plan type. |
| `STORE_INSTALLMENT` | Installment-plan language. Belongs to Payment Plan type. |
| `SERVICE_PAY_LATER` | Scheduled service/pay-later product. Belongs to Payment Plan type. |
| `BANK_LOAN` | If scheduled, it belongs to Payment Plan. If simple Debt, `counterparty_kind = BANK` and `origin_kind = CASH_BORROWED` are enough. |

The remaining values are also not worth keeping as a separate Debt enum:

| Value | Reason |
| --- | --- |
| `INFORMAL_DEBT` | The default Debt case does not need a product label. |
| `PERSONAL_REIMBURSEMENT` | Duplicates `origin_kind`. |
| `CLIENT_RECEIVABLE` | Duplicates `origin_kind = RECEIVABLE_INCOME`. |
| `OTHER` | Escape hatch caused by an unclear enum. |

Future Debt UI should not show raw product labels such as `CLIENT_RECEIVABLE` or `PERSONAL_REIMBURSEMENT`.

### Keep `DebtOriginKind`

`DebtOriginKind` answers: why did this Debt come into existence?

Current meaning:

| Value | Meaning | Example |
| --- | --- | --- |
| `CASH_BORROWED` | The user received money and owes it back. | I borrowed cash from Akmal. |
| `CASH_LENT` | The user gave money and someone owes it back. | I lent money to my brother. |
| `DEFERRED_EXPENSE` | The user received goods, work, or service and will pay later. | A mechanic repaired my car and I need to pay next week. |
| `SPLIT_REIMBURSEMENT` | Someone owes the user because the user paid a shared expense. | I paid a group restaurant bill and friends owe their shares. |
| `PERSONAL_REIMBURSEMENT` | Someone owes the user for a personal repayment case. | I bought medicine for a relative and they will repay me. |
| `RECEIVABLE_INCOME` | Someone owes the user earned income that has not arrived yet. | A client owes me for completed work. |
| `FINANCED_ASSET_PURCHASE` | The user got an asset now and owes money for it. | I took a laptop now and owe the seller. If scheduled, this should become Payment Plan territory. |
| `DAMAGE_COMPENSATION` | Someone owes compensation for damage or loss, or the user owes compensation. | Someone damaged my phone and owes repair cost. |
| `IMPORTED_BALANCE` | Starting or imported Debt where detailed origin is unknown. | I already owed this balance before using Sarflog. |

`RECEIVABLE_INCOME` has no direct enum named `PAYABLE_INCOME` because income is not payable from the user's perspective. The opposite user flow is an unpaid expense, service, work, or bill. That is currently covered by `DEFERRED_EXPENSE`.

Decision: keep `DEFERRED_EXPENSE` as the backend enum value for now, but improve the UI wording.

Preferred UI wording for the `OWING` flow:

> I received work, service, or goods and need to pay later

Supporting copy:

> No wallet changed now. This is an unpaid bill or payable obligation.

This covers:

- A freelancer did work for the user.
- A mechanic repaired the user's car.
- A plumber, doctor, tutor, shop, or service provider expects payment later.
- A friend paid for the user and the user needs to repay them.

No new Debt origin enum is needed for this case unless future backend behavior truly differs from `DEFERRED_EXPENSE`.

### Keep `DebtCounterpartyKind`

`DebtCounterpartyKind` answers: what kind of party is on the other side?

Current meaning:

| Value | Meaning | Example |
| --- | --- | --- |
| `PERSON` | Individual person. | Friend, sibling, coworker, neighbor. |
| `BANK` | Bank or lender. | Bank, microloan provider, credit institution. |
| `COMPANY` | Business or organization. | Employer, client company, repair shop, service provider. |
| `STORE` | Seller, store, or marketplace. | Phone shop, furniture store, online marketplace seller. |
| `GOVERNMENT` | Government, tax, fine, or legal body. | Tax debt, government fine, official obligation. |
| `OTHER` | Unknown or uncategorized counterparty. | Imported or unclear record. |

This enum is still useful and should remain unless a future UI simplification proves it unnecessary.

## Consequences

### For backend

- Debt state must be computed from facts, not stored as lifecycle columns.
- Time status must use the user's timezone-aware business date.
- `DebtStatus` and `debts.status` should be deleted rather than simplified into another stored status.
- Archive filtering should use `archived_at`.
- Payment Plan type must not be mapped into Debt product fields.
- Debt route filters should continue to expose `lifecycle_status`, `time_status`, and archive filters, not legacy status filters.

### For frontend

- Debt UI should show `Open`, `Closed`, `On track`, and `Overdue` only from derived API fields.
- Closed Debts should not show `On track` or `Overdue`.
- Debt creation reason cards should use plain user language rather than raw enum names.
- The `OWING` reason currently worded as "Someone paid for me" should be broadened to cover unpaid work, services, goods, and bills.
- Product-kind badges and labels such as `CLIENT_RECEIVABLE`, `PERSONAL_REIMBURSEMENT`, `STORE_INSTALLMENT`, or `BANK_LOAN` should disappear from Debt UI.

### For migrations

- Because the project is still in development, destructive cleanup is acceptable.
- Existing development data that depends on legacy Debt statuses or product kinds may be dropped.
- The migration goal is clarity, not historical compatibility.

## References

- ADR 0003: Debt Epoch and History
- ADR 0005: Payment Plan Engine, Statuses, and Budget Boundary
- ADR 0017: Debt Receivables and Deadline Decoupling
- ADR 0025: Epicspart2 Obligation Contract
