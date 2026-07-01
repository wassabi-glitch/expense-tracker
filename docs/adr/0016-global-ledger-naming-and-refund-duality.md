# 0016. Global Ledger Naming and Refund Duality

## Context

Following the naming rules established for Expected Inflows in ADR-0015, we audited the rest of the application's "Money In" ledgers (Returned, Borrowed, Sold, and Corrections tabs). We discovered that the "Robot Naming" anti-pattern had infected the entire application:
- Refunds were prepending redundant strings like `"Partial Refund"` or `"Refund for:"` to titles.
- Debt payments (Borrowed) were overwriting user memos with counterparty names and ugly system tags (`[debt_txn:123]`).
- Asset sales were forcing `"Asset Sale: {Title}"`.

Furthermore, there was a UX concern regarding the apparent redundancy of displaying Refunds in *both* the "Money In" page and the "Expenses" page.

## Decision

We are expanding the strict Title Inheritance rule globally across all transaction types and officially documenting the double-entry accounting logic for Contra-Expenses.

### 1. Global Strict Title Inheritance
The General Ledger is a human-readable journal. The `title` column belongs to the user, not the system.
- **Refunds (Returned):** Must exactly inherit the original expense title (or the Promise title). We strictly forbid prepending redundant strings like "Refund for:". The fact that it is a refund is handled entirely by UI badges (Reference Type) and positive green amounts.
- **Debt Receipts (Borrowed):** Must use the user's custom `note` as the primary title. The Counterparty Name (the Entity) must not overwrite the title; it belongs in the metadata subtitle.
- **Asset Sales (Sold):** Must use the exact `{Asset Name}` or the Promise Title. Prepending "Asset Sale:" is forbidden, as the UI `Sold` tab and badges already provide that context.
- **Corrections:** This is the only exception where a system-generated title (`"Balance Adjustment"`) is permitted, but *only* if the user did not provide a custom note during reconciliation.

### 2. The Refund Duality (Contra-Expense Ledgering)
We are explicitly affirming the decision to display Refunds in both the Wallet Inflow ("Money In") ledgers and the Category Outflow ("Expenses") ledgers.
- **The Accounting Rule:** A refund is a **Contra-Expense** (a negative expense). It is not true income.
- **Wallet Math (Money In):** It must appear here because physical cash entered the wallet. The wallet balance cannot be reconciled without it.
- **Category Math (Expenses):** It must appear here to reduce the true category spend. If a user spends $100 on groceries and returns $20, the Expenses ledger must show the +$20 so the user's budget accurately reflects an $80 net spend. Hiding it from the Expenses page would break the user's mental model of their category budgets.

## Consequences

- **UX Consistency:** Users can trust that the memos they write will always be preserved in the General Ledger without robotic pollution.
- **Mathematical Clarity:** The dual-display of refunds ensures both Wallet reconciliations and Budget tracking remain perfectly accurate.
- **Development Effort:** We must refactor `debt_payment_service.py`, `wallet_service.py`, and the refund logic in `expected_inflow_service.py` to strip out all hardcoded strings and properly route user notes to the `title` field.
