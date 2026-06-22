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

Category floors in this issue are derived, non-binding warning calculations. They are not persisted financial entities, do not reserve wallet money, do not mutate category limits, and never require user acceptance. Issue 3 defines the shared warning contract and supplies debt, deferred-expense, and installment reasons. Issue 4 owns complete recurring-occurrence projection and plugs recurring reasons into that contract. Issue 5 owns all frontend rendering and repair actions.

### Acceptance criteria
- [x] `/budgets/month-summary` exposes explicit plan backing bridge fields: free money now, valid budget spent, cash obligation reserves, expected inflow remaining, available plan backing, monthly budget total, plan backing remaining, and backing shortfall.
- [x] Over-planned responses include cause details instead of only a generic shortfall.
- [x] Category-floor warnings are derived at read time and expose `suggested_minimum`, `current_limit`, `warning_gap`, and structured `reasons`; no category-floor database entity is introduced.
- [x] Issue 3 reasons cover categorized deferred expenses, installment payments, and debts with stable identifiers, titles, due dates, and amounts. The response contract can accept recurring reasons, but full recurring occurrence generation remains Issue 4 scope.
- [x] Cash-only obligations appear as cash reserve pressure, not category floors.
- [x] Current-month category-linked obligations appear as category floors.
- [x] Credit-card positive balances count as owned value up to their unprotected positive amount.
- [x] Credit-card limits and negative credit balances never increase budget backing.
- [x] Goal funding can use only owned positive wallet value and rejects credit limits, negative credit balances, or overdraft capacity.
- [x] Goal protection on a positive credit balance reduces free money the same way cash protection does.
- [x] Normal credit-card purchases still hit monthly category budgets immediately.
- [x] Repaying a credit card remains a wallet transfer and does not create a second category budget hit.
- [x] Borrowed-spending survival exposes an explicit monthly contract: enabled state, cap, borrowed usage, remaining cap, exceeded amount, and the borrowed portion of credit-card or overdraft spending.
- [x] Survival cap availability never makes the normal budget plan healthy or expands budget create/update backing.
- [x] Overdraft-enabled debit/prepaid wallets count only below-zero outflows as survival usage.
- [x] Negative overdraft wallet balances appear as wallet-backed obligations settled by wallet transfer.
- [x] Existing wallet sign convention stays intact: positive means owned value, negative means liability exposure.
- [x] Tests cover positive credit balances, credit limits, protected goal money, mixed positive-to-negative card purchases, overdraft usage, category floors, cash reserves, and normal plan-health honesty.

### Blocked by
- Issue 2: Universal Inflow Wizards & UX Routing

---

## Issue 4: Advanced Recurring Occurrence Architecture & Floors

### What to build
Implement the G30 recurring architecture before completing recurring floor integration. Separate mutable Recurring Templates from durable dated Recurring Occurrences, give templates `Confirm each occurrence` and `Automatically record` modes, preserve occurrence history through edits/archive/pause, and reuse the ordinary multi-wallet expense-posting path for confirmed or automatic financial truth.

Then deepen the already-existing recurring projection feature into one authoritative, read-only occurrence projector used by recurring details and category-floor warnings. A recurring recommendation is scoped to the selected user-local calendar month, not a rolling next-30-days window. It represents the complete month by combining fulfilled actuals, pending/outstanding expectations, and still-projected future expectations without persisting floors or mutating saved category budgets.

Execute this issue in three ordered internal phases. Phase A is the occurrence/lifecycle foundation. Phase B is confirmation and automatic-recording behavior. Phase C is the shared projector and floor integration. Do not begin Phase C against the legacy mutable-template-only model.

### Acceptance criteria

#### Phase A - Occurrence and lifecycle foundation

- [x] A first-class Recurring Occurrence stores template ownership, scheduled due date, expected amount/category snapshots, lifecycle status, optional actual facts, and optional linked financial event.
- [x] `(template_id, scheduled_due_date)` or an equivalent invariant prevents duplicate occurrence materialization.
- [x] Templates support `CONFIRM_EACH` and `AUTO_RECORD`; new-template UI preselects confirmation while existing templates retain automatic behavior after migration.
- [x] Confirmation-mode templates may omit a wallet or keep an optional preferred wallet; automatic templates require one active preferred wallet.
- [x] Templates do not persist multi-wallet split rules; confirmation may choose one or more wallets, while automatic recording uses exactly one configured wallet.
- [x] Updating amount/category affects only the next unresolved and later occurrences; fulfilled occurrences retain event-time truth.
- [x] Delete archives instead of hard-deleting, stops unmaterialized future occurrences, and preserves occurrence/audit history.
- [x] Pause suppresses paused-period occurrences; resume starts at the next future schedule date without catch-up.
- [x] Skip closes one occurrence without posting money; failed automatic occurrences remain actionable.
- [x] Template/occurrence lifecycle commands and scheduler work use compatible row locking and transactional boundaries.
- [x] Debts and payment plans remain outside the recurring architecture and are neither linked nor mirrored as recurring templates.

Phase A verification (2026-06-22): migration upgraded in Docker and `alembic check` reported no schema drift; focused recurring tests passed (`16 passed, 1 skipped`); the existing category-floor contract test passed; and the frontend production image build completed successfully.

#### Phase B - Confirmation and automatic recording

- [x] For `CONFIRM_EACH`, the scheduler materializes one pending occurrence and notification without changing wallets, budgets, or financial ledgers.
- [x] Hourly scheduler runs create at most one initial notification per occurrence; notification read/delete does not resolve the occurrence, explicit snooze controls any later reminder, and backlog discovery uses a grouped notification rather than an alert burst.
- [x] For `AUTO_RECORD`, the scheduler atomically posts the expected expense through the ordinary expense-posting service or leaves an actionable failure.
- [x] Confirmation accepts actual amount, actual date, and one or more wallet allocations whose total exactly equals actual amount.
- [x] Actual amount may be lower or higher than expected within ordinary expense limits; zero uses skip.
- [x] A lower confirmed amount fully closes the occurrence in this release; partial recurring settlement is not introduced.
- [x] Confirmation may explicitly apply the actual amount to future template expectations; default confirmation changes only the occurrence.
- [x] Multi-wallet posting, goal protection, owned/borrowed funding classification, budget effects, and occurrence fulfillment commit atomically.
- [x] Confirmation and scheduler retries are idempotent and cannot duplicate financial events or wallet movements.
- [x] A voided linked financial event cannot remain accepted as fulfilled and surfaces as needing reconciliation.
- [x] Recurring UI exposes recording-mode selection, pending confirmations, expected-versus-actual variance, wallet allocations, skip, and history.
- [x] `Expenses > Recurring` owns the durable `Needs confirmation` queue; notification-bell and Dashboard actions deep-link to the same shared desktop-dialog/mobile-sheet confirmation flow.

#### Phase C - Shared projection and floor integration

- [ ] One pure range-bounded occurrence projector serves recurring projection rows and recurring category-floor warnings.
- [ ] Existing default and custom projection APIs reuse the shared projector; saved custom horizons remain preference metadata.
- [ ] Projection output is read-only and never mutates templates, occurrences, due dates, wallets, budgets, expenses, notifications, or floor records.
- [ ] Current-month defaults use the effective user timezone; explicit selected months use user-local calendar boundaries rather than rolling 30-day windows.
- [ ] Full-month recurring recommendations combine valid fulfilled actual amounts, pending/outstanding expected amounts, and projected future expected amounts without double counting.
- [ ] Paying or confirming an occurrence does not make the full-month recommendation shrink merely because `next_due_date` advanced.
- [ ] Skipped, cancelled, paused-period, and archived future occurrences do not contribute; failed-but-still-outstanding occurrences do contribute.
- [ ] Mid-month amount and category edits preserve fulfilled old values and use current values only for unresolved/future occurrences.
- [ ] Recurring reasons use the Issue 3 floor-warning contract and provide grouped source detail suitable for daily/weekly schedules.
- [ ] Budget month summary, recurring details, and future timeline work can reuse the same occurrence semantics.
- [ ] Public route and scheduler-boundary tests cover lifecycle, confirmation, multi-wallet posting, timezones, projections, floors, idempotency, concurrency, and read-only guarantees.
- [ ] Migrations and backend tests run in Docker; relevant frontend tests and production build pass.

Full product and testing decisions: `docs/prd/g30-advanced-recurring-occurrence-architecture.md`.

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
- [ ] Wallet UI allows goal-funding eligibility to be enabled for overdraft-capable debit/prepaid wallets and credit wallets; only their positive, unprotected balance is presented as available for goals.
- [ ] Goal-funding UI clearly explains that credit limits, overdraft capacity, zero balances, and negative balances cannot fund goals, even when the wallet is eligible to hold goal protection.
- [ ] Supported translations include the new visible budget backing and floor copy.
- [ ] Frontend build passes.

### Blocked by
- Issue 4: Advanced Recurring Occurrence Architecture & Floors

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
