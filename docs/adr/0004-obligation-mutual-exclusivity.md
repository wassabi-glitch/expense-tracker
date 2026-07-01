# Obligation Mutual Exclusivity: Debt vs Payment Plan

In the original schema, a `PaymentPlan` could optionally be linked to a `Debt` via a `debt_id` foreign key. This resulted in backend logic that attempted to "hide" the linked Debt from the UI to prevent double-counting in user views. However, this created a dangerous "ghost ledger" trap: the hidden Debt still maintained its own parallel ledger and `remaining_amount` in the database, risking silent data corruption and desynchronization when payments were made to the Payment Plan.

**Decision:**
We are enforcing strict **Mutual Exclusivity** between Debts and Payment Plans. They are 100% decoupled with zero structural links to each other.

An obligation is either:
1. **A Debt:** An open-ended running balance with no strict schedule (e.g., an informal IOU, a running tab).
2. **A Payment Plan:** A closed-end, strictly scheduled obligation (e.g., a 36-month Car Loan, a store installment).

It can never be both.

**Action Required for Implementation:**
- The `debt_id` foreign key must be removed from the `PaymentPlan` model.
- The `payment_plan` relationship must be removed from the `Debt` model.
- All backend filtering logic (e.g., in `obligation_source_service.py`) that hides Debts based on Payment Plan linkage must be removed.
- **Migration Strategy:** For any existing Payment Plan that currently links to a Debt, the Payment Plan will permanently assume full ownership of the obligation, and the corresponding shadow Debt record must be completely deleted from the database.

**Why:**
True decoupling eliminates the dual-ledger synchronization risk. It forces the user (and the system) to treat open-ended tabs and closed-ended loans as fundamentally different financial tools with separate lifecycles, ensuring the database mathematically reflects exactly what the user sees in the UI.
