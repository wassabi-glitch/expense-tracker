# Session Draft Decisions

Date: 2026-07-14

## Purpose

Session Drafts are the review workspace for complex expense capture. They should let the user build a receipt, basket, OCR import, voice import, or other grouped spending moment before anything becomes posted ledger truth.

The mission is:

```text
Draft first.
Review and edit.
Finalize into one truthful posted expense event.
```

## Decisions

### Keep Source Types

Keep the current source-type idea, such as `MANUAL` and `OCR`.

Reason:

- The feature is expected to support receipt scanning and other intelligent capture flows later.
- OCR and manual entry should share the same review-and-finalize path.
- Intelligent inputs should create drafts, not direct posted expenses.

### Demote Discount From Ledger Truth

Discount should not drive posted ledger math.

The ledger should care about actual paid item amounts, wallet outflow, category impact, project links, and reimbursements. A discount may be useful as receipt/OCR evidence, but it should not be the core mechanism for deriving category amounts.

Preferred direction:

```text
Item amounts = actual spending truth.
Optional receipt metadata may remember detected discounts.
Final posted ledger uses actual item amounts.
```

### Derive Session Total From Items

The user should not normally type `amount_paid` as a separate competing truth.

Preferred direction:

```text
session_total = sum(session item amounts)
wallet allocation total must equal session_total
finalized expense amount equals session_total
```

For OCR or receipt imports, a scanned receipt total can exist as source metadata or a reconciliation check, but it should not silently override item rows.

Example:

```text
OCR item sum: 268,000
Receipt total: 270,000

Status: needs review
Action: adjust item rows, add a fee/rounding row, or accept a clearly modeled correction
```

### Keep Friend Splits As Reimbursements

Friend splits are useful when they mean:

```text
I paid money from my wallet, and someone now owes me back.
```

The bridge to the Debts module is useful because it preserves both facts:

```text
Wallet outflow happened now.
Receivable repayment is expected later.
```

Preferred language:

```text
reimbursement split
```

rather than vague generic split math.

### Friend Splits Do Not Reduce Budget Enforcement

Monthly category budget limits should be checked against the full session item amounts.

Example:

```text
Dinner session: 300,000
Ali owes back: 180,000

Dining Out budget impact: 300,000
Receivable Debt: 180,000
Net personal burden report: 120,000
```

Reason:

- The user really fronted the full cash outflow.
- Budget limits should not be bypassed by adding reimbursement rows.
- Later repayment should settle the Debt, not rewrite the original expense fact.

Future reporting can distinguish:

```text
Gross category spend
Expected reimbursement
Net personal burden
```

## Frontend Rework Needed

The current Session Draft UI needs serious rework.

Observed direction:

- The feature has a strong product mission, but the current UI feels broken and conceptually heavy.
- The user should not have to manually balance unclear fields like item total, amount paid, discount, and wallet allocations.
- The composer should guide the user through a cleaner flow:

```text
1. Add or review item rows.
2. Confirm derived session total.
3. Allocate payment wallets to match the derived total.
4. Optionally add reimbursement splits.
5. Finalize.
```

The frontend should make the model obvious:

```text
Items define the spend.
Wallets explain how it was paid.
Reimbursements explain who owes back.
Finalize posts the truth.
```

Until this is redesigned, the backend feature may be logically useful while still feeling unreliable or confusing to users.


# Explore possible useful links with all 4 Goal types.