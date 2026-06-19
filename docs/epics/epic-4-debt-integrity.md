# Epic 4: Debt & Payment Plan Integrity

**Status:** Not Started  
**Depends On:** Can be executed independently, but ideally after Epic 1.

## Goal
Restore absolute mathematical truth and user recovery to the Debt/Payment Plan domain. This epic fixes critical aggregation bugs (Phantom Payments) that lie to the user about their real cash balances, and it provides the necessary UI controls for users to correct setup mistakes in their long-term payment schedules. It also aligns the technical domain language with the product philosophy by renaming "Installments" to "Payment Plans".

## PRDs Included

1. [ ] **Domain Language Refactor: Installments -> Payment Plans**
   - *Technical Debt:* Rename the database tables, SQLAlchemy models, schemas, and API routes from "Installments" to "Payment Plans" to ensure ubiquitous language across the stack.
2. [ ] **[G18 - Debt Ledger Reconciliation Math](../prd/g18-debt-ledger-reconciliation-math.md)**
   - *Backend Math:* Fix the `charge_delta > 0` reversal blindspot and move the `total_paid` calculation into the backend to eliminate naive and dangerous frontend math.
3. [ ] **[G15 - Payment Plan Edit/Delete UI](../prd/g15-installment-plan-edit-delete-ui.md)**
   - *User Recovery:* Wire up the frontend "Edit" and "Delete" buttons for payment plans, respecting the pristine vs. non-pristine guardrails.

## Execution Rules
- **Strict Due Dates Enforcement:** Make `due_date` strictly REQUIRED for all Debts and Payment Plans at the database layer. Null dates break the chronological Timeline Simulator (G20) and silently bypass Category Floor warnings (G6/G9). Forcing a date guarantees architectural integrity and teaches users financial agency.
- Execute the Domain Language Refactor first to set the correct naming convention.
- G18 is a critical bug fix that requires careful testing of ledger aggregations.
- G15 is a straightforward frontend connection task using existing backend endpoints.
