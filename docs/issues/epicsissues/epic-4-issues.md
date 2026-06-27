# Epic 4 Issues: Debt & Payment Plan Integrity

Parent: [Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Can start independently; Epic 1 completion is preferred.

## Issue 1: Rename Installments to Payment Plans Canonically

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md)

### What to build

Make "Payment Plan" the canonical domain language end-to-end. The backend schema, SQLAlchemy models, Pydantic schemas, API routes, frontend API client, React hooks, query keys, UI component names, tests, and user-facing copy should stop treating "Installment" as the primary concept.

The migration must preserve existing user data while moving the app to canonical payment-plan names. Any temporary compatibility alias must be explicit, tested, and isolated from the active app paths.

### Acceptance criteria

- [x] Database tables are renamed from `installment_plans`, `installment_payments`, and `installment_payment_allocations` to canonical payment-plan table names while preserving existing rows, foreign keys, indexes, constraints, and ownership isolation.
- [x] SQLAlchemy model classes, relationships, enum names, and foreign-key field names use `PaymentPlan` / `payment_plan` language.
- [x] Pydantic schemas and response fields use `PaymentPlan*` names, including nested debt details and goal/savings bridge outputs.
- [x] The canonical backend route is payment-plan named, and active frontend code no longer calls `/installments`.
- [x] Frontend API modules, React Query hooks, query keys, component names, and local state use payment-plan language.
- [x] User-facing UI copy says "Payment Plan(s)" instead of "Installment(s)" except where a product subtype intentionally describes a store installment.
- [x] Tests, fixtures, and helper names are updated to the canonical vocabulary.
- [x] Alembic upgrade and downgrade preserve existing linked debts, payments, allocations, goals, entity-ledger links, assets, and project links.
- [x] Backend tests and frontend build pass after the rename.

### Blocked by

None - can start immediately.

---

## Issue 2: Enforce Debt and Payment Plan Due-Date Integrity

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md)

### What to build

Make obligation dates non-optional so debts and payment plans cannot disappear from future timelines, category-floor warnings, or planning simulations. A user should always provide a concrete due date for debts, and every payment-plan schedule must remain fully dated at the database and API boundary.

### Acceptance criteria

- [x] Debt creation requires a concrete due date for the obligation; the backend no longer accepts an undated debt.
- [x] Debt update cannot clear the obligation due date or move it before the debt's creation/start date.
- [x] The debt table enforces the canonical due-date field as non-null after an Alembic backfill for existing rows.
- [x] Existing debt date ambiguity is resolved so timelines and floors read one canonical due-date field instead of silently falling back across optional fields.
- [x] Payment-plan creation and update guarantee a non-null plan start date and non-null due date for every generated schedule payment.
- [x] Payment-plan schedule regeneration for pristine plans cannot produce undated payment rows.
- [x] Frontend debt and payment-plan forms require the relevant date fields and surface validation errors without relying on backend-only failures.
- [x] Future timeline, category-floor, and obligation tests prove undated debts or payment-plan rows cannot bypass warnings.
- [x] Alembic migration, backend tests, and frontend build pass.

### Blocked by

- Issue 1: Rename Installments to Payment Plans Canonically

---

## Issue 3: Reconcile Debt Ledger Charges and Paid Totals

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G18 - Debt Ledger Reconciliation Math](../../prd/g18-debt-ledger-reconciliation-math.md)

### What to build

Fix the Phantom Payments bug by making the backend the only source of truth for debt ledger aggregation. Reversed charges must reduce total charges, and the API must return real cash paid from posted payment ledger entries instead of forcing the frontend to infer paid cash from remaining balance math.

### Acceptance criteria

- [x] Debt total charges include negative reversal ledger entries; a charge followed by its reversal returns `total_charges == 0`.
- [x] The backend exposes a `total_paid` debt aggregate that counts real cash payments only.
- [x] Forgiveness, asset settlement discounts, and downward balance corrections reduce `remaining_amount` without increasing `total_paid`.
- [x] A real debt payment increases `total_paid` by the paid amount.
- [x] `DebtOut` includes `total_paid`, and every debt response builder maps it consistently for list, detail, payment, charge, forgiveness, settlement, adjustment, reversal, goal, and payment-plan-linked flows.
- [x] Frontend debt cards/details display the backend `total_paid` field and no longer calculate paid cash as `(initial + charges) - remaining`.
- [x] Debt ledger tests cover charge reversal, forgiveness with zero paid, and real payment totals.
- [x] Frontend tests or focused assertions cover display of backend-provided paid totals. (Gap documented: No frontend test harness exists; verified via manual review that `total_paid` is purely read from the backend DTO.)
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 1: Rename Installments to Payment Plans Canonically

---

## Issue 4: Wire Payment Plan Edit and Delete UI

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G15 - Payment Plan Edit/Delete UI](../../prd/g15-installment-plan-edit-delete-ui.md)

### What to build

Connect the existing payment-plan backend guardrails to the frontend so users can correct setup mistakes, edit safe metadata, and delete erroneous pristine plans. The UI must respect pristine versus non-pristine rules: pristine plans can edit setup fields and be deleted, while active plans with real activity can only edit safe metadata and must explain why destructive changes are locked.

### Acceptance criteria

- [ ] React Query mutations exist for updating and deleting payment plans, reuse the shared API client, and invalidate payment-plan, debt, budget, wallet, goal, dashboard, and analytics side effects after success.
- [ ] Payment-plan cards or details expose clear Edit and Delete actions on desktop and mobile.
- [ ] Edit opens a payment-plan modal that allows safe metadata edits at any time.
- [ ] Financial setup fields such as total price, down payment, payment count/months, frequency, and start date are editable only for pristine plans.
- [ ] Non-pristine plans show locked setup fields with localized copy explaining that recorded activity prevents changing financial history.
- [ ] Pristine plans can be deleted only after an explicit confirmation dialog.
- [ ] Delete is disabled for non-pristine plans with a tooltip or inline reason explaining that recorded activity prevents deletion.
- [ ] Successful edits and deletes refresh the plan list, plan details, linked debt state, budget warnings, future timeline, wallets, goals, and dashboard summaries.
- [ ] API failures leave local state unchanged and show localized actionable errors.
- [ ] Frontend tests cover pristine edit/delete, non-pristine locked setup fields, disabled delete reason, mutation payloads, cache invalidation, and error handling.
- [ ] Frontend build passes.

### Blocked by

- Issue 1: Rename Installments to Payment Plans Canonically
- Issue 2: Enforce Debt and Payment Plan Due-Date Integrity

---

## Issue 5: Simplify Debt State and Archive Workflow

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Replace the overloaded debt status model with simple derived debt state and a separate archive workflow. Debts should expose derived lifecycle status, derived time status, and archive visibility without treating active, overdue, paid, forgiven, settled, written off, defaulted, in collection, or archived as competing lifecycle statuses.

Archive must be a user filing action, not a money state. Users can archive open or closed debts, restore archived debts, and the backend recomputes open/closed and overdue/on-track from balance, due date, and the user's effective current date.

### Acceptance criteria

- [x] Debt API responses expose derived `lifecycle_status` as `OPEN` when reconciled remaining balance is positive and `CLOSED` when it is zero.
- [x] Debt API responses expose derived `time_status` as `ON_TRACK` or `OVERDUE` only for open debts.
- [x] Closed debts return no time status even when their due date is in the past.
- [x] Debt archive state is stored separately from lifecycle and time status, preferably as nullable archive metadata.
- [x] `is_archived` is derived from archive metadata in debt API responses.
- [x] Open debts can be archived without changing balance, due date, ledger entries, or lifecycle calculation.
- [x] Closed debts can be archived without changing balance, due date, ledger entries, or lifecycle calculation.
- [x] Archived debts are hidden from ordinary debt lists by default.
- [x] Debt list APIs support filtering for archived debts and including archived debts when requested.
- [x] Restore or unarchive clears archive metadata and recomputes lifecycle and time status from current reality.
- [x] Generic debt update cannot set lifecycle, time, or archive state directly.
- [x] Dedicated archive and restore actions exist for debts.
- [x] Frontend debt filters and badges stop using the old overloaded status vocabulary.
- [x] Frontend debt views support clear filters for open, closed, overdue, archived, owed by me, and owed to me.
- [x] Tests cover open/on-track, open/overdue, closed/no-time-status, archive, restore, default list hiding, archived list visibility, and blocked generic status mutation.
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 2: Enforce Debt and Payment Plan Due-Date Integrity
- Issue 3: Reconcile Debt Ledger Charges and Paid Totals

---

## Issue 6: Make Debt Forgiveness, Correction, and Reversal Component-Aware

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Make debt forgiveness, balance correction, and reversal record what changed in real life instead of silently pushing all reductions into principal, using a hidden principal-first split, or letting users time-travel old ledger entries into impossible balances. Users should choose plain-language intent such as forgiving original debt, waiving charges/fees, correcting original debt amount, correcting remaining principal, correcting charges/fees, or reversing the latest mistaken debt action.

The UI should preview before and after principal/original debt, charges/fees, and total remaining balance before saving. The backend should record honest principal and charge deltas, reconcile cached remaining amount from the debt ledger, and keep cash paid totals separate from forgiveness and corrections.

Reverse means a recorded action was a mistake. It should be latest-action-first within the same debt ledger. Older real-world changes should use waiver/forgiveness, correction, or refund instead of arbitrary old reversal.

### Acceptance criteria

- [x] Forgiveness supports forgiving remaining original debt/principal without reducing charge balance.
- [x] Forgiveness supports waiving remaining charges/fees without reducing principal balance.
- [x] Full remaining forgiveness clears both remaining principal and remaining charges.
- [x] Partial forgiveness no longer relies on a hidden principal-first split without user intent.
- [x] Forgiveness creates debt ledger entries and does not mutate opening amount directly.
- [x] Forgiveness never increases cash paid totals.
- [x] Pristine opening amount correction remains available for setup mistakes before real activity exists.
- [x] Non-pristine principal correction creates a ledger adjustment against principal.
- [x] Charge or fee correction creates a ledger adjustment against charges.
- [x] Any fallback total-only correction is explicit, previewed, and records metadata explaining the allocation decision.
- [x] Balance correction no longer silently treats every adjustment as principal.
- [x] Debt detail/activity views show component-aware forgiveness and correction entries clearly.
- [x] Frontend forms use plain real-life labels rather than forcing users to understand accounting jargon.
- [x] Frontend forms preview before and after original debt, charges/fees, and total remaining balance.
- [x] Regular debt reversal allows reversing the latest unreversed action on a debt.
- [x] Regular debt reversal blocks reversing an older debt action while newer unreversed actions exist on the same debt.
- [x] Regular debt reversal does not enforce global LIFO across unrelated debts.
- [x] Blocked older reversal copy explains that the user can undo newer debt actions first if the older action was recorded by mistake.
- [x] Blocked older reversal copy guides users toward charge waiver, correction, or refund when the older action was real but later changed.
- [x] Reversal tests prove reversing an older charge after a newer payment on the same debt is blocked.
- [x] Reversal tests prove activity on a different debt does not block reversal for this debt.
- [x] Tests assert principal and charge deltas for forgiveness and correction, not only final total balance.
- [x] Tests assert forgiven and corrected amounts do not inflate cash paid totals.
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 3: Reconcile Debt Ledger Charges and Paid Totals
- Issue 5: Simplify Debt State and Archive Workflow

---

## Issue 7: Give Payment Plans Their Own Accounting Path

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Decouple new payment-plan behavior from regular debts. Creating a payment plan should no longer create a hidden debt row, and payment-plan payments, charges, write-offs, undo, and summaries should operate through payment-plan-owned records while still creating real wallet and financial events when money moves.

This slice should make the new payment-plan path self-contained while preserving existing payment-plan user workflows: create plan, view plan, record payment, add charge, write off, undo supported actions, and see accurate plan balance and schedule state.

### Acceptance criteria

- [x] Creating a new payment plan does not create a regular debt row.
- [x] New payment plans do not store a regular debt foreign key.
- [x] Payment-plan list and detail responses no longer require linked debt data for new plans.
- [x] Payment-plan payments update plan-owned balance and schedule rows without creating regular debt transactions.
- [x] Payment-plan payments still create wallet and financial events when real money moves.
- [x] Payment-plan charges are plan-owned and do not create regular debt charge records for new plans.
- [x] Payment-plan write-offs are plan-owned and do not create regular debt forgiveness entries for new plans.
- [x] Payment-plan undo paths restore plan-owned payment/write-off state without regular debt ledger reversal.
- [x] Payment-plan summaries use plan-owned amounts rather than linked debt remaining amount.
- [x] Payment-plan detail activity remains an oldest-to-newest storyline using plan-owned records.
- [x] Payment-plan UI removes linked debt identifiers and linked debt copy for new plans.
- [x] New tests prove create, payment, charge, write-off, undo, list, detail, and summary work for payment plans with no debt row.
- [x] Existing wallet, budget, timeline, and activity behavior remains correct for payment-plan money movement.
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 1: Rename Installments to Payment Plans Canonically
- Issue 2: Enforce Debt and Payment Plan Due-Date Integrity

---

## Issue 8: Migrate Existing Payment-Plan Debt Coupling

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Migrate existing payment plans away from hidden debt rows without losing user history. Existing plan balances, schedule payments, charges, write-offs, allocations, wallet events, financial events, assets, projects, and audit activity must survive the decoupling.

Synthetic debt rows that exist only because payment plans previously needed regular debt backing should be converted into payment-plan-owned history and retired or detached safely. Real user-created debts must remain regular debts.

### Acceptance criteria

- [x] Migration distinguishes payment-plan backing debts from real user-created debts.
- [x] Existing payment-plan principal balances are migrated into payment-plan-owned accounting.
- [x] Existing payment-plan charge history is migrated into payment-plan-owned charge history.
- [x] Existing payment-plan write-off history is migrated into payment-plan-owned write-off history.
- [x] Existing payment-plan payment allocations preserve wallet and financial event links.
- [x] Existing payment-plan activity remains available in plan details after migration.
- [x] Existing payment-plan summaries match pre-migration balances after migration.
- [x] Existing wallet balances are not changed by the migration.
- [x] Existing financial events are preserved and remain traceable to payment-plan history.
- [x] Existing assets, projects, subcategories, and category links remain attached to the payment plan where applicable.
- [x] Goals that targeted a payment-plan-linked debt are migrated to target the payment plan where the plan is the real obligation.
- [x] Synthetic payment-plan backing debts no longer appear in regular debt lists after migration.
- [x] Real debts are not silently converted, archived, deleted, or detached by the migration.
- [x] Migration has upgrade and downgrade coverage where practical.
- [x] Migration tests cover pristine plans, paid plans, charged plans, written-off plans, partially paid plans, goal-linked plans, and bank-loan disbursement-style plans.
- [x] Backend tests pass after migration.

### Blocked by

- Issue 7: Give Payment Plans Their Own Accounting Path

---

## Issue 9: Wire Payment Plan Edit and Delete for the Decoupled Model

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Implement the G32-safe version of payment-plan edit and delete UX. This keeps the useful pristine/non-pristine rules from Issue 4, but removes linked-debt assumptions. Users can correct mistaken pristine plans, edit safe metadata after activity, and understand why financial setup and deletion are locked once real plan activity exists.

This issue supersedes the linked-debt parts of Issue 4. It should not refresh, display, delete, or depend on linked debt state.

### Acceptance criteria

- [ ] React Query mutations exist for updating and deleting payment plans through the decoupled payment-plan API.
- [ ] Payment-plan cards or details expose clear Edit and Delete actions on desktop and mobile.
- [ ] Edit opens a payment-plan modal that allows safe metadata edits at any time while the plan is not archived.
- [ ] Financial setup fields such as total price, down payment, payment count/months, frequency, and start date are editable only for pristine plans.
- [ ] Editing pristine setup fields safely regenerates plan-owned schedule rows and plan-owned balances.
- [ ] Non-pristine plans show locked setup fields with localized copy explaining that recorded activity prevents changing financial history.
- [ ] Pristine plans can be deleted only after an explicit confirmation dialog.
- [ ] Deleting a pristine payment plan removes plan-owned schedule and setup records without touching regular debts.
- [ ] Delete is disabled for non-pristine plans with a tooltip or inline reason explaining that recorded activity prevents deletion.
- [ ] Successful edits and deletes refresh payment-plan list, payment-plan detail, budget warnings, future timeline, wallets, goals, dashboard, and analytics data as applicable.
- [ ] Successful edits and deletes do not invalidate or refresh linked debt state because payment plans are decoupled from debts.
- [ ] API failures leave local state unchanged and show localized actionable errors.
- [ ] Frontend tests cover pristine edit/delete, non-pristine locked setup fields, disabled delete reason, mutation payloads, cache invalidation, and error handling.
- [ ] Frontend build passes.

### Blocked by

- Issue 7: Give Payment Plans Their Own Accounting Path
- Issue 8: Migrate Existing Payment-Plan Debt Coupling

---

## Issue 10: Reconnect Goals, Timeline, Budgets, and Dashboards After Payment-Plan Decoupling

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Update cross-feature surfaces so debts and payment plans remain visible in planning without relying on hidden linked debt rows. Goals, future timeline, budget warnings, category floors, dashboard summaries, analytics, and details should explicitly understand regular debts and payment plans as separate obligation sources.

### Acceptance criteria

- [x] Goals can target regular debts directly.
- [x] Goals can target payment plans directly without requiring a linked debt.
- [x] Existing goal payment flows still work for regular debt targets.
- [x] Existing goal payment-plan flows work through plan-owned records after decoupling.
- [x] Future timeline shows regular debt obligations from debt due dates.
- [x] Future timeline shows payment-plan obligations from plan-owned schedule rows.
- [x] Budget warnings and category floors continue to account for regular debt obligations where applicable.
- [x] Budget warnings and category floors continue to account for payment-plan schedule obligations where applicable.
- [x] Dashboard and analytics summaries do not double-count payment plans as both plans and debts.
- [x] Debt receivable expected-payment behavior remains explicit and does not auto-trust open receivables.
- [x] Payment-plan expected outflows are sourced from payment-plan schedule rows, not debt rows.
- [x] API response contracts make source type explicit enough for the frontend to render debt and payment-plan items separately.
- [x] Tests cover goals, timeline, budget summary, category floors, dashboard totals, and no double counting.
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 7: Give Payment Plans Their Own Accounting Path
- Issue 8: Migrate Existing Payment-Plan Debt Coupling

---

## Issue 11: Remove Debt Policy and Old Coupling Contracts

**Type:** AFK

### Parent

[Epic 4 - Debt & Payment Plan Integrity](../../epics/epic-4-debt-integrity.md), [G32 - Debt and Payment Plan Architecture Reset](../../prd/g32-debt-payment-plan-architecture-reset.md)

### What to build

Remove the generalized debt policy/action restriction machinery and old public contracts that only existed to manage overloaded debt statuses and payment-plan-managed debts. Debt rules should live in debt-owned actions, and payment-plan rules should live in payment-plan-owned actions.

The final state should have no public "managed by payment plan" debt concept, no generic debt status mutation, no old overloaded debt status filters, and no payment-plan route that calls regular debt policy for core plan behavior.

### Acceptance criteria

- [x] Regular debt action rules are enforced inside debt-owned route or service handlers.
- [x] Payment-plan action rules are enforced inside payment-plan-owned route or service handlers.
- [x] The generalized debt policy service is removed or reduced to only genuinely shared helpers that are not policy orchestration.
- [x] Debt action restriction persistence is removed unless a concrete user-facing lock feature is intentionally kept.
- [x] Formal settlement is removed as a separate debt action from the backend action model, debt routes, frontend buttons, forms, policy copy, and tests.
- [x] Formal and informal debts both use the same component-aware forgiveness/waiver action for reducing debt without wallet money movement.
- [x] Backend debt policy no longer blocks forgiveness only because a debt is formal, and no longer routes formal debt reductions through a separate settlement-only path.
- [x] Payment-plan routes no longer call regular debt policy for payment, charge, write-off, or undo behavior.
- [x] Goal flows no longer call regular debt policy for payment-plan-owned behavior.
- [x] Debt API responses no longer expose managed-by-payment-plan fields.
- [x] Debt details no longer embed payment-plan details as a debt subresource.
- [x] Frontend code no longer branches on payment-plan-managed debt behavior.
- [x] Old debt status filters and copy are removed from active frontend paths.
- [x] The legacy `DebtStatus` enum and `debts.status` database column are removed or replaced by a minimal non-public transitional field only if migration safety requires it.
- [x] Any migration away from old debt statuses preserves real balances, ledger history, archive metadata, due dates, and user ownership without converting user meaning silently.
- [x] Backend services for budgets, timelines, goals, expected inflows, savings, and debt summaries stop querying old status enum values and use derived lifecycle/archive reality instead.
- [x] Tests that existed only to prove payment-plan-managed debt blocking are deleted or replaced with decoupled behavior tests.
- [x] Tests prove archived debt immutability/restore behavior through the new archive model rather than the old status model.
- [x] Backend tests and frontend build pass.

### Blocked by

- Issue 5: Simplify Debt State and Archive Workflow
- Issue 6: Make Debt Forgiveness, Correction, and Reversal Component-Aware
- Issue 8: Migrate Existing Payment-Plan Debt Coupling
- Issue 10: Reconnect Goals, Timeline, Budgets, and Dashboards After Payment-Plan Decoupling
