# PRD: G19 - Universal Inflow Wizards & UX Routing

Labels: `ready-for-agent`

## Problem Statement

Sarflog's "Money In" dashboard currently features a singular "+ Record Income" primary action. Because users naturally navigate to "Money In" whenever cash hits their wallet, they are highly prone to clicking this button to record debt paybacks, asset sales, or loan disbursements. This breaks the user's mental model and causes catastrophic accounting errors: users falsely inflate their taxable "Earned Income," while the actual Debts or Assets in the ledger remain un-updated. Furthermore, creating an "Expected Inflow" that maps to these complex external systems requires a massive, intimidating form with confusing foreign-key dropdowns. 

## Solution

Implement "Universal Inflow Wizards" using progressive disclosure on the "Money In" page. Replace the "+ Record Income" and "+ Add Expected" buttons with wizards that act as smart UI routers. The wizard first asks "Where did this money come from?" (Earned, Debt Payback, Asset Sale, Refund). Based on the selection, it dynamically renders the correct contextual dropdowns (e.g., listing active receivables). Under the hood, the frontend routes the submission to the correct domain API (e.g., `/debts/{id}/payments`). Finally, update the `ExpectedIncome` database model to support `asset_id` and `refund_event_id` to fully back this wizard.

## User Stories

1. As a budget user, I want a single "+ Record Inflow" button on the Money In page, so that I don't have to hunt across 4 different application pages just to log incoming cash.
2. As a budget user, I want the wizard to explicitly ask if the money is Earned, Borrowed/Returned, Sold, or Refunded, so that I don't accidentally bloat my tax reports by logging a loan as income.
3. As a budget user, I want the "+ Add Expected" button to use this exact same guided flow, so that I can easily build budget expectations around pending asset sales or bank loans.
4. As a developer, I want the frontend wizard to act purely as a UI router that fires existing domain APIs (like `/debts/{id}/payments`), so that the backend ledger domains remain safely decoupled.
5. As a backend maintainer, I want the `ExpectedIncome` schema to support `asset_id` and `refund_event_id`, so that expectations can be strictly linked to their actual sources.

## Implementation Decisions

- **UI Wizard Flow (Step 1):** Add a 4-option selector: 💼 Earned Income, 🤝 Debt Payback / Loan, 📱 Asset Sale, 🔙 Refund.
- **UI Wizard Flow (Step 2):** 
  - Earned: Show `IncomeSource` dropdown.
  - Debt/Loan: Show `Debt` dropdown (filtered to active).
  - Asset: Show `Asset` dropdown.
  - Refund: Show a search/dropdown of recent `FinancialEvent` expenses.
- **Frontend Routing:** When logging *real* cash, the wizard submission fires the respective API:
  - Earned -> `POST /income`
  - Debt/Loan -> `POST /debts/{id}/ledger` (Payment)
  - Asset -> `POST /assets/{id}/liquidate`
  - Refund -> `POST /financial-events/{id}/reverse`
- **Backend Schema Update:** Add `asset_id` (ForeignKey to `assets.id`) and `refund_event_id` (ForeignKey to `financial_events.id`) to the `ExpectedIncome` model in `app/models.py`.

## Testing Decisions

- E2E tests verifying the wizard correctly routes a "Debt Payback" submission to the Debt Ledger API, proving that the debt balance is reduced and no false `IncomeEntry` is created.
- Verify `ExpectedIncome` can be successfully created and queried using the new `asset_id` and `refund_event_id` fields.

## Out of Scope

- Merging the actual backend tables (Income, Debts, Assets remain strictly separated in the database; only the UI is unified).
- Complex multi-step refunds (e.g., returning 3 items from a 10-item grocery receipt).

## Further Notes

This PRD resolves the UX accounting trap discovered during the Expected Inflows review. By introducing a Universal Inflow Wizard, Sarflog protects users from categorizing non-taxable cash as earned income, while making complex financial logging incredibly intuitive. Published locally under `docs/prd/` with the `ready-for-agent` label.
