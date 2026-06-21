# Epic 2 Issues: Budget Intelligence & Backing

## Issue 1: Expected Inflow Lifecycle & Realization

### What to build
Rebuild expected income into an Expected Inflows lifecycle that treats incoming money as a planning promise until real wallet money arrives. Receiving an inflow should ask for the actual amount and one or more destination wallet allocations, atomically create the real ledger movement, update the expectation, and preserve audit history through partial receipts, write-offs, cancellations, splits, and re-open flows.

### Acceptance criteria
- [ ] Frontend wording says "Expected Inflows" instead of "Expected Income" wherever this workspace is user-facing.
- [ ] Receiving an expected inflow opens a realization flow that requires `actual_amount` and `wallet_allocations`, with allocation amounts summing to the actual amount. A legacy single `wallet_id` may be accepted only as a compatibility shortcut.
- [ ] The receive endpoint atomically creates the wallet ledger effect and links it back to the expected inflow.
- [ ] Expected inflow status is math-driven: `EXPECTED`, `PARTIALLY_RECEIVED`, `RESOLVED`, or `CANCELLED`.
- [ ] Remaining expected amount continues to affect budget backing after partial receipt.
- [ ] Partially received inflows cannot have their expected amount edited downward through a normal edit.
- [ ] Delete is hidden/rejected once real money is attached.
- [ ] Force-resolve/write-off and cancel flows close records without deleting history.
- [ ] Re-open removes the terminal close and recalculates status from received-vs-expected math.
- [ ] Moving a partially received inflow to another month splits the record: original month is resolved at received amount, and the remaining amount becomes a new expected inflow in the target month.
- [ ] Overdue inflows show a warning badge without mutating database status.
- [ ] Active and history tabs separate `EXPECTED`/`PARTIALLY_RECEIVED` from `RESOLVED`/`CANCELLED`.

### Blocked by
None - can start immediately.

---

## Issue 2: Universal Inflow Wizards & UX Routing

### What to build
Replace the narrow Money In actions with guided inflow wizards that route users to the right financial domain. The same source-selection model should support recording real cash and creating expected inflows, so earned income, debt paybacks, asset sales, and refunds do not get misclassified as taxable income.

### Acceptance criteria
- [ ] Money In exposes a single "+ Record Inflow" flow with source choices for earned income, debt payback/loan return, asset sale, and refund.
- [ ] "+ Add Expected" uses the same guided source-selection model for planning future inflows.
- [ ] Earned inflows use income source selection and route to the income API.
- [ ] Debt payback/loan inflows select the relevant receivable/debt and route to the debt ledger/payment API without creating a false income entry.
- [ ] Asset sale inflows select an asset and route to the asset liquidation flow.
- [ ] Refund inflows select/search a prior expense or financial event and route to the refund/reversal flow.
- [ ] Expected inflow schema and database support `asset_id` and `refund_event_id`.
- [ ] Expected inflows can be created and queried with earned, debt, asset, and refund source metadata.
- [ ] Tests prove a debt-payback inflow reduces the right debt/receivable and does not inflate earned income totals.
- [ ] UI copy clearly distinguishes earned income from other incoming cash.

### Blocked by
- Issue 1: Expected Inflow Lifecycle & Realization

---

## Issue 3: Budget Explainability & Credit Survival Math

### What to build
Introduce backend budget explainability and survival math so users can understand exactly why a month is covered, waiting on income, tight, or over-planned. The backend should become the source of truth for available plan backing, category floors, cash reserves, credit-card positive-balance treatment, goal availability, and borrowed-spending survival usage.

### Acceptance criteria
- [ ] `/budgets/month-summary` exposes explicit plan backing bridge fields: free money now, valid budget spent, cash obligation reserves, expected inflow remaining, available plan backing, monthly budget total, plan backing remaining, and backing shortfall.
- [ ] Over-planned responses include cause details instead of only a generic shortfall.
- [ ] Category floors include source details for recurring items, deferred expenses, installments, debts, due dates, and amounts.
- [ ] Cash-only obligations appear as cash reserve pressure, not category floors.
- [ ] Current-month category-linked obligations appear as category floors.
- [ ] Credit-card positive balances count as owned value up to their unprotected positive amount.
- [ ] Credit-card limits and negative credit balances never increase budget backing.
- [ ] Goal funding can use only owned positive wallet value and rejects credit limits, negative credit balances, or overdraft capacity.
- [ ] Goal protection on a positive credit balance reduces free money the same way cash protection does.
- [ ] Normal credit-card purchases still hit monthly category budgets immediately.
- [ ] Repaying a credit card remains a wallet transfer and does not create a second category budget hit.
- [ ] Borrowed-spending survival usage counts only the borrowed portion of credit-card or overdraft spending.
- [ ] Survival cap availability never makes the normal budget plan healthy or expands budget create/update backing.
- [ ] Overdraft-enabled debit/prepaid wallets count only below-zero outflows as survival usage.
- [ ] Negative overdraft wallet balances appear as wallet-backed obligations settled by wallet transfer.
- [ ] Existing wallet sign convention stays intact: positive means owned value, negative means liability exposure.
- [ ] Tests cover positive credit balances, credit limits, protected goal money, mixed positive-to-negative card purchases, overdraft usage, category floors, cash reserves, and normal plan-health honesty.

### Blocked by
- Issue 2: Universal Inflow Wizards & UX Routing

---

## Issue 4: Recurring Floors Projection Contract

### What to build
Extract the backend recurring projection and floor-generation contract needed by budget intelligence. Recurring expenses due in the month should generate category floors used by the G9 month-summary math, and recurring detail should expose deterministic cost projection rows. The full month setup wizard UI remains deferred.

### Acceptance criteria
- [ ] Recurring expenses due in a selected month contribute to category floors with source details.
- [ ] Recurring floor data uses the same floor contract returned by budget month summary.
- [ ] Default recurring projection horizons are frequency-appropriate and returned by a backend API.
- [ ] Projection rows count scheduled occurrences over the requested horizon and multiply by recurring amount.
- [ ] Projection output does not mutate due dates, budgets, wallets, debts, expenses, or floor records.
- [ ] Custom projection horizons can be validated and saved as preference metadata if the current recurring API does not already support them.
- [ ] Budget month summary, future timeline work, and recurring detail can reuse the same projection semantics.
- [ ] Route-level tests verify recurring floors and projection rows through public APIs.

### Blocked by
- Issue 3: Budget Explainability & Credit Survival Math

---

## Issue 5: Budget Backing UI Sync

### What to build
Synchronize the Budget Workspace frontend with the backend budget intelligence contract. The UI should render backend plan backing fields and category floors directly instead of deriving plan health from legacy free-money variables or duplicating formulas in React.

### Acceptance criteria
- [ ] Budget summary cards use `plan_backing_remaining` and `backing_shortfall` instead of legacy free-money-only remaining fields.
- [ ] Plan health label, color, and warning logic rely on backend `plan_status` and returned shortfall/cause data.
- [ ] Budget cards show required category floor badges or warnings when their category has floor pressure.
- [ ] Budget details or summary surfaces floor source details for debts, installments, and recurring expenses.
- [ ] A category whose limit is below its required floor is visually distinguished.
- [ ] The UI no longer reverse-engineers backend plan formulas.
- [ ] Existing budget cards still render normal spending, remaining, over-limit, and empty states cleanly on desktop and mobile.
- [ ] Frontend copy avoids envelope language and uses plan backing/category floor/cash reserve terminology.
- [ ] Supported translations include the new visible budget backing and floor copy.
- [ ] Frontend build passes.

### Blocked by
- Issue 4: Recurring Floors Projection Contract

---

## Issue 6: Future Timeline & Budget Cashflow Simulator

### What to build
Add the Commitment Intelligence layer that turns budget planning into a chronological cashflow simulation. The backend should aggregate expected inflows and known obligations into one deterministic future timeline, while the Budgets page gets a 30-day simulator and the Dashboard gets a compact next-5-days pulse.

### Acceptance criteria
- [ ] A future timeline API aggregates expected inflows, debts, installment payments, and recurring expenses into dated timeline events.
- [ ] Timeline events include enough metadata for UI labels, source type, category, amount direction, due date, and resolved/active state.
- [ ] Timeline events are sorted chronologically and can be filtered to 30 days or 5 days.
- [ ] Budgets page renders a 30-day Future Timeline using the shared timeline API.
- [ ] Dashboard renders a Next 5 Days pulse widget from the same data source.
- [ ] Dashboard exposes a deterministic Financial Truth Status such as covered now, waiting on income, or at risk.
- [ ] Budget category cards warn when planned limits threaten upcoming category floors or obligations.
- [ ] Floor warning repair includes a one-click action to set or create a category budget at the required floor.
- [ ] The simulator distinguishes expected inflows from obligations instead of creating a separate "Expected Expenses" tab.
- [ ] Tests cover interleaved inflows and obligations, timeline sorting, 30-day budget view data, 5-day dashboard data, and deterministic status calculation.

### Blocked by
- Issue 5: Budget Backing UI Sync
