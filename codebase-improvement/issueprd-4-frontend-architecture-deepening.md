# Issue Breakdown For PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

Parent PRD: `prd-4-frontend-architecture-deepening.md`

Triage: ready-for-agent

## Proposed Breakdown For Approval

1. **Deepen the Expected Inflow source picker read model**
   - Type: AFK
   - Blocked by: None - can start immediately
   - User stories covered: 1, 2, 3, 4, 5, 25, 26, 35, 36, 38, 39

2. **Introduce the Project details seam and route from Budgets**
   - Type: AFK
   - Blocked by: None - can start immediately
   - User stories covered: 6, 7, 8, 27, 28, 35, 36, 38, 39

3. **Move Project structure editing behind the Project details seam**
   - Type: AFK
   - Blocked by: 2
   - User stories covered: 6, 7, 8, 27, 28, 35, 36, 39

4. **Move Project lifecycle and deletion resolution behind the Project details seam**
   - Type: AFK
   - Blocked by: 2
   - User stories covered: 6,
     7, 9, 10, 11, 12, 27, 28, 35, 36, 38, 39

5. **Establish canonical query keys and ledger cache invalidation through Expense and Wallet flows**
   - Type: AFK
   - Blocked by: None - can start immediately
   - User stories covered: 13, 14, 29, 30, 35, 36, 39

6. **Migrate remaining ledger-adjacent mutation side effects to the cache module**
   - Type: AFK
   - Blocked by: 5
   - User stories covered: 13, 14, 29, 30, 35, 36, 39

7. **Implement the Budget Interceptor through normal expense creation**
   - Type: AFK
   - Blocked by: 5
   - User stories covered: 15, 16, 17, 18, 31, 32, 35, 36, 38, 39

8. **Extend the Budget Interceptor across recurring, session draft, Debt, and Payment Plan flows**
   - Type: AFK
   - Blocked by: 7
   - User stories covered: 15, 16, 17, 18, 19, 31, 32, 35, 36, 38, 39

9. **Deepen the user-local calendar module through Payment Plan schedule preview**
   - Type: AFK
   - Blocked by: None - can start immediately
   - User stories covered: 20, 21, 24, 33, 34, 35, 36, 38, 39

10. **Migrate Dashboard, Analytics, and form date-only behavior to the calendar module**
    - Type: AFK
    - Blocked by: 9
    - User stories covered: 20, 22, 23, 24, 33, 34, 35, 36, 38, 39

11. **Add frontend deepening guardrails and cross-flow verification**
    - Type: AFK
    - Blocked by: 1, 3, 4, 6, 8, 10
    - User stories covered: 35, 36, 38, 39, 40

Review questions before implementation:

- Does the Project details seam need a design review before agents move heavy Project flows, or is ADR-0020 enough?
- Should Budget Interceptor coverage include CSV/import flows in this PRD, or stay limited to currently visible money flows?
- Should the ledger cache module migrate all query keys in one pass after Issue 5, or leave compatibility aliases longer?
- Should the calendar module include all display formatting, or only date-only parsing, comparison, and arithmetic in this PRD?

---

## Issue 1: Deepen The Expected Inflow Source Picker Read Model

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Create a deeper Expected Inflow source picker read model that gives the Expected Inflow editor normalized source options for Earned income, Receivable Debt repayment, Refund, and Asset Sale. The read model should hide backend payload unwrapping, source-kind filtering, and Debt lifecycle status rules from the editor.

This issue should directly enforce ADR-0018 and fix the source picker leakage identified in the architecture review.

## Acceptance criteria

- [x] Earned income choices include active income sources and preserve current Expected Inflow creation behavior.
- [x] Receivable choices include open Debts owed to the user and exclude closed or irrelevant Debts.
- [x] Receivable choices do not depend on legacy `ACTIVE` Debt status when the current lifecycle status is the intended rule.
- [x] Refund choices unwrap feed-oriented expense payloads before filtering or displaying labels.
- [x] Refund choices show stable user-facing labels using the original expense identity, title, and date where available.
- [x] Refund choices exclude refund rows or otherwise prevent linking a refund to another refund.
- [x] Asset Sale choices include owned assets and preserve current Asset Sale behavior.
- [x] The Expected Inflow editor consumes normalized source options rather than raw backend payloads where practical.
- [x] Existing Expected Inflow create and edit flows remain functional.
- [x] Targeted tests cover all four source kinds and the ADR-0018 regression cases.
- [x] Frontend build or targeted frontend tests pass.

## Blocked by

None - can start immediately

---

## Issue 2: Introduce The Project Details Seam And Route From Budgets

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Introduce the Project details seam as the destination for Project depth while keeping Budgets as the monthly attention surface. Budgets should show concise Project summary cards and route users to a dedicated Project details view when they need lifecycle, structure, or deletion context.

This issue creates the seam and navigation path without moving every heavy flow yet.

## Acceptance criteria

- [x] A dedicated Project details view is reachable from Project cards on the Budgets screen.
- [x] The Project details view loads the selected Project's summary, type, status, month context, and high-level financial state.
- [x] The Project details view has clear loading, empty, missing-project, and error states.
- [x] The Budgets screen remains usable as a monthly Budget permission overview after the route is added.
- [x] Existing Budget details behavior remains unchanged.
- [x] Overlay Project behavior remains active and visible.
- [x] Frozen Isolated Project behavior is not expanded.
- [x] If a minimal backend read contract is needed for Project details, it is added narrowly and covered by tests.
- [x] Frontend navigation and build verification pass.

## Blocked by

None - can start immediately

---

## Issue 3: Move Project Structure Editing Behind The Project Details Seam

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Move Project structure editing behind the Project details seam. Project category reservations, subcategory reservations, Project-specific limits, and structure management should happen in Project details rather than inside the Budgets monthly attention surface.

The Budgets screen should route to the Project details seam for structure work and keep only summary-level status and calls to action.

## Acceptance criteria

- [x] Project structure editing is available from Project details for the same Project cases currently supported.
- [x] Budgets no longer owns the primary structure editing workflow for Projects.
- [x] Budgets still shows monthly Project reservation summaries needed for Budget permission awareness.
- [x] Overlay Project category and subcategory reservation behavior remains unchanged.
- [x] State reset and error handling for structure editing remain stable after the move.
- [x] Existing Project structure tests or equivalent coverage pass.
- [x] New tests cover opening Project details from Budgets and editing a supported Project structure path.
- [x] Frontend build passes.

## Blocked by

- Issue 2: Introduce The Project Details Seam And Route From Budgets

---

## Issue 4: Move Project Lifecycle And Deletion Resolution Behind The Project Details Seam

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Move Project lifecycle actions and deletion resolution behind the Project details seam. Pause, resume, complete, restore, archive, detach expenses, and delete linked expenses should be presented with Project context and user-facing language.

This issue should respect ADR-0019 and ADR-0020: deletion decisions need affected expense context, and heavy Project flows belong on Project details rather than Budgets.

## Acceptance criteria

- [x] Project details exposes state-aware lifecycle actions for supported Project states.
- [x] Archived Projects are not offered meaningless repeat archive actions.
- [x] Project deletion resolution is available from Project details.
- [x] Deletion resolution shows affected expense context when the backend contract provides it.
- [x] If affected expense context is missing, the backend contract is expanded narrowly and covered by tests.
- [x] User-facing copy avoids primary ledger implementation language such as void, cascade void, reversal, and ledger entries.
- [x] Budgets keeps summary status and routes to Project details for heavy lifecycle decisions.
- [x] Existing Project deletion payload behavior remains compatible.
- [x] Tests cover state-aware actions, deletion resolution choices, and user-facing labels.
- [x] Frontend build passes.

## Blocked by

- Issue 2: Introduce The Project Details Seam And Route From Budgets

---

## Issue 5: Establish Canonical Query Keys And Ledger Cache Invalidation Through Expense And Wallet Flows

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Create the ledger side-effect cache module through the most common money flows: Expenses and Wallets. The module should own canonical query-key naming and named invalidation behavior for views affected by ledger truth and plan health.

This issue should migrate enough real mutations to prove the module earns its depth without attempting to migrate the entire frontend in one pass.

## Acceptance criteria

- [x] Canonical query-key naming exists for the main ledger-adjacent frontend data sets.
- [x] Expense create, update, delete, refund, split, merge, asset marking, and recurring marking use shared cache side-effect behavior where practical.
- [x] Wallet create, update, delete, transfer, fee, interest, default wallet, and reconciliation use shared cache side-effect behavior where practical.
- [x] Existing query-key spellings remain compatible while callers migrate.
- [x] The cache module avoids duplicating broad invalidation arrays in each mutation hook.
- [x] Dashboard, Wallets, Expenses, Budgets, Analytics, Debts, and Notifications refresh behavior remains at least as complete as before for migrated flows.
- [x] Targeted tests cover canonical keys and at least one Expense and one Wallet invalidation path.
- [x] Existing frontend tests for Expense and Wallet behavior pass where present.
- [x] Frontend build passes.

## Blocked by

None - can start immediately

---

## Issue 6: Migrate Remaining Ledger-Adjacent Mutation Side Effects To The Cache Module

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Migrate the remaining ledger-adjacent mutation hooks to the shared cache module. Income, Expected Inflows, Debts, Payment Plans, Goals, Assets, Recurring, session drafts, Budget Permission, and Project mutation flows should stop hand-writing broad invalidation lists where the shared module can express the consequence.

This issue finishes the cache locality work after the module has been proven through Expense and Wallet flows.

## Acceptance criteria

- [x] Income and Expected Inflow mutations use shared cache side-effect behavior where practical.
- [x] Debt mutations use shared cache side-effect behavior while preserving Debt domain rules.
- [x] Payment Plan mutations use shared cache side-effect behavior while preserving Payment Plan domain rules.
- [x] Goal mutations use shared cache side-effect behavior without regressing protected real money behavior.
- [x] Asset mutations use shared cache side-effect behavior.
- [x] Recurring and session draft money movements use shared cache side-effect behavior where practical.
- [x] Budget Permission and Project mutations use canonical keys where practical.
- [x] Legacy key aliases or compatibility invalidations remain where needed during migration.
- [x] Tests cover representative migrated flows and query-key compatibility.
- [x] Frontend build passes.

## Blocked by

- Issue 5: Establish Canonical Query Keys And Ledger Cache Invalidation Through Expense And Wallet Flows

---

## Issue 7: Implement The Budget Interceptor Through Normal Expense Creation

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Implement the Global Budget Interceptor through normal one-time expense creation. When the backend rejects an expense because Budget permission is missing, the frontend should keep the user's draft, show an in-context repair flow, create or update the missing Budget permission, then replay the original expense.

This issue proves ADR-0009 on the safest single money flow before extending it across the app.

## Acceptance criteria

- [x] Normal expense creation detects structured Budget-required errors.
- [x] Budget-required detection does not depend on fragile localized message text.
- [x] The user's original expense draft is preserved while the repair flow is open.
- [x] The repair flow identifies the missing category and Budget month.
- [x] The repair flow suggests a useful Budget permission amount based on the attempted expense.
- [x] Successful repair creates or updates Budget permission and replays the original expense.
- [x] Cancellation leaves the original expense unposted and does not create partial state.
- [x] Repair failure and replay failure show clear recoverable errors.
- [x] Cache invalidation after repair and replay uses the shared cache module.
- [x] Tests cover success, cancellation, repair failure, and replay failure.
- [x] Frontend build passes.

## Blocked by

- Issue 5: Establish Canonical Query Keys And Ledger Cache Invalidation Through Expense And Wallet Flows

---

## Issue 8: Extend The Budget Interceptor Across Recurring, Session Draft, Debt, And Payment Plan Flows

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Extend the Budget Interceptor to other flows that can hit strict Budget permission: recurring template creation or confirmation, session draft finalization, Debt settlement or charge posting, and Payment Plan charge or payment posting.

Each migrated flow should preserve its draft or intent, route Budget-required repair through the shared module, and replay the original action after repair.

## Acceptance criteria

- [x] Recurring template or recurring confirmation Budget-required errors route through the Budget Interceptor.
- [x] Session draft finalization Budget-required errors route through the Budget Interceptor.
- [x] Debt-related money movement Budget-required errors route through the Budget Interceptor where applicable.
- [x] Payment Plan money movement Budget-required errors route through the Budget Interceptor where applicable.
- [x] Each flow preserves its original draft or intent while the repair flow is open.
- [x] Each flow replays the original action after successful repair.
- [x] Flow-specific errors remain understandable after replay failure.
- [x] The shared cache module handles refresh after successful repair and replay.
- [x] Tests cover one success and one cancellation or failure case for each migrated flow.
- [x] Frontend build passes.

## Blocked by

- Issue 7: Implement The Budget Interceptor Through Normal Expense Creation

---

## Issue 9: Deepen The User-Local Calendar Module Through Payment Plan Schedule Preview

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Deepen the user-local calendar module through Payment Plan schedule preview. Payment Plan schedule calculations should use date-only operations that do not shift the intended due date when local time and UTC differ.

This issue proves the frontend calendar seam on a high-risk obligation flow without attempting to migrate every date usage at once.

## Acceptance criteria

- [x] The calendar module owns date-only parsing for user-facing frontend dates.
- [x] The calendar module owns adding weeks, months, quarters, and years for date-only schedule previews.
- [x] The calendar module avoids `toISOString` day shifts for date-only Payment Plan due dates.
- [x] Payment Plan schedule preview keeps the intended dates in a timezone where local midnight and UTC differ.
- [x] Existing Payment Plan creation behavior remains unchanged except for corrected date safety.
- [x] Tests cover monthly, weekly, biweekly, quarterly, and yearly schedule preview behavior.
- [x] Tests include at least one timezone boundary case.
- [x] Frontend build or targeted frontend tests pass.

## Blocked by

None - can start immediately

---

## Issue 10: Migrate Dashboard, Analytics, And Form Date-Only Behavior To The Calendar Module

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Migrate Dashboard, Analytics, and high-value form date-only behavior to the user-local calendar module after the Payment Plan seam is proven. This should cover date-only sort, range validation, relative due labels, max date behavior, and display labels where raw JavaScript dates can shift the user's intended day.

This issue should not rewrite every display helper. It should focus on user-facing date-only behavior where calendar correctness matters.

## Acceptance criteria

- [x] Dashboard due labels use the calendar module for date-only comparison.
- [x] Dashboard date sorting avoids date-only timezone shifts.
- [x] Analytics custom range validation uses the calendar module for inclusive day counts and comparisons.
- [x] Analytics chart sorting and long date labels avoid date-only timezone shifts.
- [x] High-value Budget, Expense, Income, Debt, Payment Plan, Savings, and Wallet form defaults or max dates use existing timezone-safe helpers or the deeper calendar module.
- [x] Technical timestamps continue using technical datetime formatting.
- [x] Tests cover Dashboard relative labels, Analytics custom ranges, and at least one form date validation case.
- [x] Frontend build passes.

## Blocked by

- Issue 9: Deepen The User-Local Calendar Module Through Payment Plan Schedule Preview

---

## Issue 11: Add Frontend Deepening Guardrails And Cross-Flow Verification

## Parent

PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

## What to build

Add guardrails and cross-flow verification for the frontend deepening program. The goal is to make regressions visible: source picker callers should not re-learn backend wrapper shapes, Budgets should not absorb Project details again, mutation hooks should not reintroduce broad hand-written cache lists, Budget-required repair should remain shared, and date-only logic should not bypass the calendar seam.

This is a final hardening slice after the main migrations.

## Acceptance criteria

- [x] A source picker regression test proves Expected Inflow source options still unwrap payloads and use current Debt eligibility rules.
- [x] A Project seam regression proves Budgets routes to Project details for heavy Project work.
- [x] Cache guardrails or tests catch accidental reintroduction of broad duplicated query invalidation lists where practical.
- [x] Budget Interceptor regression coverage proves repair-and-replay still works through at least one migrated non-expense flow.
- [x] Calendar guardrails or tests catch high-risk date-only operations bypassing the calendar module where practical.
- [x] ADR-0009, ADR-0018, ADR-0020, and frontend timezone rules are referenced in test names, documentation, or nearby guidance where useful.
- [x] Existing frontend build passes.
- [x] Any remaining shallow modules that could not be safely migrated are documented with reasons and follow-up candidates.

## Blocked by

- Issue 1: Deepen The Expected Inflow Source Picker Read Model
- Issue 3: Move Project Structure Editing Behind The Project Details Seam
- Issue 4: Move Project Lifecycle And Deletion Resolution Behind The Project Details Seam
- Issue 6: Migrate Remaining Ledger-Adjacent Mutation Side Effects To The Cache Module
- Issue 8: Extend The Budget Interceptor Across Recurring, Session Draft, Debt, And Payment Plan Flows
- Issue 10: Migrate Dashboard, Analytics, And Form Date-Only Behavior To The Calendar Module
