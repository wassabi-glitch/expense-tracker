# 0027. Debt Ledger Actions, Principal/Charges, and Reversal Rules

Date: 2026-07-10

## Status

Accepted

## Context

ADR 0026 simplified Debt lifecycle and taxonomy: Debt state is derived, archive is separate, `DebtProductKind` should be removed, and Debt should stay decoupled from Payment Plan product language.

After that decision, we reviewed the remaining Debt enums and flows that still felt confusing:

- `DebtLedgerEntryType`
- `DebtLedgerEntrySource`
- `DebtAssetSettlementType`
- `DebtActionKind`
- reversal behavior
- principal vs charges at Debt creation
- payment allocation between principal and charges
- debt charge vs interest semantics

The goal of this ADR is to keep ledger architecture understandable while preserving enough modeling power for real debts.

## Decision

### `DebtLedgerEntryType` is durable ledger history

`DebtLedgerEntryType` answers: what kind of balance-changing entry happened to this Debt?

This enum is not a UI status enum and should not be removed casually. It is part of Debt history.

| Value | Meaning | Decision |
| --- | --- | --- |
| `INITIAL` | Opening Debt balance was created. | Keep. |
| `CHARGE` | Interest, fee, penalty, or other charge increased the Debt. | Keep. |
| `PAYMENT` | Money payment reduced the Debt. | Keep. |
| `FORGIVENESS` | Debt was reduced without wallet money moving. | Keep. |
| `ADJUSTMENT` | Balance was corrected. | Keep, but guard carefully. |
| `REVERSAL` | A later ledger row mathematically cancels an earlier row. | Keep. Required by immutable ledger architecture. |
| `ASSET_SETTLEMENT` | Debt was reduced or settled with an asset rather than cash. | Keep. Future feature. |

### `DebtLedgerEntrySource` is audit provenance

`DebtLedgerEntrySource` answers: who or what created this ledger entry?

| Value | Meaning | Decision |
| --- | --- | --- |
| `USER` | User intentionally created the entry. | Keep. |
| `SYSTEM` | App automation created the entry. | Keep. |
| `IMPORT` | Imported or migrated data created the entry. | Keep. |

This enum is useful for reversal safety. Reversing a user-created entry can be straightforward. Reversing system or imported entries may require stronger confirmation.

### Reversal has two meanings in the product, and they must stay distinct

The UI button labeled "Reverse" is an action request. It maps to:

```text
DebtActionKind.REVERSE_ENTRY
```

If the backend accepts that action, it appends a new ledger entry:

```text
DebtLedgerEntryType.REVERSAL
```

If the original entry touched wallet money, the backend must also create a reversing `FinancialEvent` so wallet history nets to zero without deleting the original event.

`event_subtype` values such as `PRINCIPAL_PAYMENT`, `CHARGE_PAYMENT`, and `ENTRY_REVERSAL` are not core enum states. They are descriptive detail about the ledger entry.

### Reversal is append-only, not deletion

Reversal must never delete or mutate the original ledger entry. It appends the mathematical opposite.

Example:

| id | entry_type | amount_delta | principal_delta | charge_delta | balance_after | reverses_entry_id |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 100 | `INITIAL` | +5,000,000 | +5,000,000 | 0 | 5,000,000 | null |
| 101 | `PAYMENT` | -2,000,000 | -2,000,000 | 0 | 3,000,000 | null |
| 102 | `REVERSAL` | +2,000,000 | +2,000,000 | 0 | 5,000,000 | 101 |

The balance becomes:

```text
+5,000,000
-2,000,000
+2,000,000
= 5,000,000
```

The original payment remains part of history. The reversal explains why its effect no longer counts.

### Reversal order is guarded

Debt reversal must behave like an undo stack.

Only the latest unreversed reversible posted ledger entry may be reversed.

The backend must block:

- reversing `INITIAL` entries
- reversing `REVERSAL` entries
- reversing already-reversed entries
- reversing entries marked `is_reversible = false`
- reversing older entries while newer unreversed reversible entries still exist

Example:

| id | entry_type | amount_delta |
| --- | --- | ---: |
| 1 | `INITIAL` | +1,000,000 |
| 2 | `PAYMENT` | -200,000 |
| 3 | `CHARGE` | +50,000 |
| 4 | `PAYMENT` | -100,000 |

The user may reverse entry `4` first. They may not reverse entry `2` until entries `4` and `3` have been handled.

Reason: reversing from the middle can make the story incoherent. Later actions may have been made based on balances created by earlier actions.

If an old action was real but later circumstances changed, the correct tool is a new business action, not out-of-order reversal. Examples:

- charge waiver
- forgiveness
- balance correction
- refund or new payment
- adjustment

### `DebtAssetSettlementType` stays

Asset settlement is a planned feature and remains part of Debt.

| Value | Meaning | Decision |
| --- | --- | --- |
| `ASSET_RECEIVED` | Someone settles what they owe the user by giving an asset. | Keep. |
| `ASSET_GIVEN` | The user settles what they owe by giving an asset. | Keep. |
| `COLLATERAL_TAKEN` | The user takes pledged collateral as settlement or partial settlement. | Keep for future asset settlement work. |

Future implementation should be explicit about valuation, ownership transfer, and whether the asset settlement fully or partially reduces Debt balance.

### `DebtActionKind` should be simplified to real user actions

`DebtActionKind` is policy/UI action language. It is not ledger history.

Keep these actions:

| Action | Decision |
| --- | --- |
| `RECORD_PAYMENT` | Keep. |
| `ADD_CHARGE` | Keep. |
| `FORGIVE_PARTIAL` / `FORGIVE_FULL` | May be simplified to one `FORGIVE` action with amount/component. |
| `ADJUST_BALANCE` | Keep, guarded. |
| `REVERSE_ENTRY` | Keep. Required for append-only correction. |
| `ARCHIVE` | Keep. User filing action. |
| `RESTORE` | Keep or rename to `UNARCHIVE` for clearer language. |
| `LINK_ASSET` | Keep only if used for asset metadata or future settlement flow. |

Remove or defer these actions:

| Action | Reason |
| --- | --- |
| `SET_COLLATERAL` | Too formal-loan specific for current Debt action surface. Asset settlement can model collateral later. |
| `RESTRUCTURE_TERMS` | Formal loan / Payment Plan shaped. Standalone Debt should not carry this action unless a concrete feature needs it. |

Future asset settlement may introduce a clearer action such as:

```text
SETTLE_WITH_ASSET
```

### Debt creation must separate principal, charges, and wallet movement

Every Debt creation flow should ask the right amount questions:

1. Original debt / principal amount
2. Interest, fees, or charges already included, optional and defaulting to zero
3. Money moved today, if any

The starting Debt balance is:

```text
opening_principal_amount + opening_charge_amount
```

Wallet movement is a separate fact:

```text
actual cash that entered or left wallets today
```

This means wallet movement does not always equal total starting Debt balance.

Example: borrowed money with upfront fee or existing interest:

```text
Principal received: 5,000,000
Opening charges/interest: 500,000
Wallet receives: 5,000,000
Starting Debt balance: 5,500,000
```

Example: receivable with expected interest:

```text
Principal lent: 1,000,000
Opening interest/fees owed to user: 100,000
Wallet paid out: 1,000,000
Starting receivable balance: 1,100,000
```

Example: unpaid service bill:

```text
Principal service amount: 700,000
Opening charges: 0
Wallet movement: none
Starting Debt balance: 700,000
```

Implementation direction:

- Create an `INITIAL` ledger entry for principal.
- Create a `CHARGE` ledger entry only when opening charges are greater than zero.
- Treat `remaining_amount` as a projection/cache from posted Debt ledger entries, not as the source of truth.

### Payment allocation must be explicit

When recording a Debt payment, the user should be able to choose whether the payment reduces principal or charges.

The app should support at least:

- automatic allocation
- pay charges/interest first
- pay original debt/principal first
- custom split

This matches existing forgiveness and balance-correction flows, which already let the user choose principal vs charges.

The default allocation rule must be visible to the user. Hidden principal-first behavior is not acceptable because many real debts clear charges or interest first.

### Debt charge vs interest

Principal is the original debt amount.

Charge is the broad bucket for amounts added on top of principal:

- interest
- late fee
- service fee
- penalty
- collection fee
- manual correction fee

Interest is a type of charge.

Decision:

- Keep the ledger simple: added non-principal amounts are `CHARGE` entries.
- Do not create a competing interest balance system yet.
- Continue supporting manual charge amounts.
- Add clearer charge classification when needed.

Future enhancement:

```text
DebtChargeKind = INTEREST | LATE_FEE | SERVICE_FEE | PENALTY | OTHER
```

Percentage-based interest should start as a helper/calculator that suggests a charge amount. The user confirms it, and the system posts a normal `CHARGE` ledger entry. Do not silently accrue interest in the background until the product has explicit rules for rate, period, compounding, grace, timezone, and partial payments.

## Consequences

### For backend

- Debt creation cannot continue assuming `initial_amount = wallet movement = principal`.
- Creation payloads should distinguish principal amount, opening charge amount, and wallet allocations.
- Debt ledger entries should carry principal and charge deltas from creation onward.
- Reversal must remain append-only and latest-first.
- Wallet-touching reversals must also reverse `FinancialEvent` wallet/entity legs.

### For frontend

- Debt creation UI should show:
  - Original amount
  - Interest, fees, or charges already included
  - Total starting balance
  - Money moved today
- Debt payment UI should expose allocation between principal and charges.
- Reversal buttons should keep explaining why older entries are disabled.
- User-facing copy should avoid making charges and interest sound like separate balances unless the system actually models them separately.

### For future work

- Asset settlement should get its own focused implementation.
- `SET_COLLATERAL` and `RESTRUCTURE_TERMS` should be removed or deferred during Debt cleanup.
- `DebtActionKind` can be simplified after route/UI behavior is aligned.
- A future interest calculator can create confirmed `CHARGE` entries rather than automatic silent accrual.

## References

- ADR 0011: Immutable Ledger Architecture
- ADR 0024: Immutable Ledger Boundary: When It Applies
- ADR 0025: Epicspart2 Obligation Contract
- ADR 0026: Debt Derived State and Taxonomy Simplification
