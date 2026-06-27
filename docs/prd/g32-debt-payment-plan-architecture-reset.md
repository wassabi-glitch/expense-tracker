# PRD: G32 - Debt and Payment Plan Architecture Reset

Labels: `ready-for-agent`

## Problem Statement

Sarflog's debt and payment-plan architecture currently mixes separate real-world concepts in ways that create confusing user psychology and fragile backend rules.

Debts and payment plans are visually separate in the product, but the backend still links payment plans to hidden debt rows and debt ledger records. This means payment-plan behavior leaks into debt policy, debt action availability, goal links, ledger reversal rules, and UI copy. Users experience payment plans as a separate workflow, while the database treats them as a special kind of debt. That mismatch makes the system harder to reason about and harder to safely evolve.

Debt statuses are also overloaded. One enum currently tries to represent lifecycle, time urgency, legal severity, closure reason, and archive state. Users do not need to see many badges such as active, overdue, defaulted, in collection, paid, settled, forgiven, written off, and archived. Most users need to know whether a debt is still open, whether it needs attention, and whether it is hidden from the main working view.

Debt correction and forgiveness also need clearer semantics. The ledger already has separate principal and charge deltas, but current balance correction always adjusts principal, and forgiveness uses a fixed principal-first split. That can produce the correct total balance while misrepresenting which real-world component changed.

The result is a debt module that is mathematically capable but conceptually too tangled. The next architecture slice should simplify the domain aggressively while preserving ledger truth and repairability.

## Solution

Reset debts and payment plans into separate backend domains.

Debts remain simple obligations between the user and a counterparty. Payment plans become their own obligation workflow with their own schedule, payments, charges, write-offs, archive state, and accounting records. Payment plans must no longer create, own, or depend on hidden debt rows.

Debt state becomes reality-derived and psychologically simple:

- `lifecycle_status`: `OPEN` or `CLOSED`, derived from the current debt balance.
- `time_status`: `ON_TRACK` or `OVERDUE`, derived from due date and current date, and only meaningful while the debt is open.
- `is_archived`: derived from stored archive metadata and used only for visibility/focus.

Archive is not a debt lifecycle status. It is a user filing action. A user may archive either an open or closed debt, and may restore it later. Restoring does not invent a new state; it simply reveals the debt again, and the backend recomputes lifecycle and time status from reality.

Debt amounts continue to use the ledger as the authority. The debt header may keep useful projection fields such as opening amount and remaining amount, but remaining amount is a cached current balance, not independent truth. Money-changing actions must write ledger entries and reconcile the cached balance from ledger totals.

Forgiveness and correction become component-aware. The product should ask what changed in real life using plain language, such as correcting the original debt amount or correcting charges/fees. The backend should record principal and charge deltas honestly instead of silently pushing all corrections into principal.

Debt reversal must also become reality-aware. Reverse means "this recorded action was a mistake," not "the real-world situation changed later." Regular debt reversal should therefore follow a latest-action-first rule within each individual debt ledger. If a user wants to remove an old charge after newer debt activity exists, the normal path should be charge waiver/forgiveness, correction, or refund depending on what happened in real life.

## User Stories

1. As a debt user, I want debts and payment plans to be separate concepts, so that I do not see hidden payment-plan debts in regular debt workflows.
2. As a payment-plan user, I want payment plans to manage their own schedule and balance, so that plan payments do not depend on regular debt actions.
3. As a debt user, I want to see simple debt status language, so that I understand whether a debt is open, closed, overdue, or archived without confusing badges.
4. As a debt user, I want overdue to be an attention signal, not a lifecycle status, so that a closed debt never looks overdue.
5. As a debt user, I want closed debts to stop showing time urgency, so that paid or cleared obligations do not keep nagging me.
6. As a debt user, I want archive to hide a debt from my main view, so that old or temporarily ignored records do not clutter my workspace.
7. As a debt user, I want to archive open debts, so that I can file away items I do not want in my working list while preserving the truth.
8. As a debt user, I want to restore archived debts, so that I can bring them back without losing their original balance, due date, or history.
9. As a debt user, I want restoring an archived debt to recompute whether it is overdue, so that the app reflects the current real-world situation.
10. As a debt user, I want forgiveness to reduce the obligation without changing wallet money, so that non-cash forgiveness is recorded honestly.
11. As a debt user, I want to choose whether forgiveness applies to the original debt amount or charges/fees, so that the ledger story matches the real agreement.
12. As a debt user, I want full forgiveness to clear both remaining original debt and remaining charges, so that the debt closes cleanly.
13. As a debt user, I want charge waivers to reduce charges rather than principal, so that future charge totals are not misleading.
14. As a debt user, I want correction to ask what was wrong, so that I do not accidentally corrupt the principal/charge breakdown.
15. As a debt user, I want to correct an original setup amount before real activity exists, so that mistaken debt creation can be fixed safely.
16. As a debt user, I want to correct remaining principal after history exists through a ledger entry, so that the audit trail remains explainable.
17. As a debt user, I want to correct remaining charges after history exists through a charge-aware ledger entry, so that charge history remains explainable.
18. As a debt user, I want the UI to preview before and after balances, so that I understand the effect before saving a forgiveness or correction.
19. As a debt user, I want remaining balance to stay accurate after every payment, charge, forgiveness, correction, archive, and restore action, so that I can trust the debt list.
20. As a debt user, I want cash paid to stay separate from forgiven or corrected amounts, so that my payment history does not lie.
21. As a debt user, I want open debts with future due dates to show as on track, so that not every open debt feels urgent.
22. As a debt user, I want open debts with past due dates to show as overdue, so that missed obligations stand out.
23. As a debt user, I want closed debts to show as closed regardless of due date, so that finished obligations stay finished.
24. As a payment-plan user, I want plan payments to update payment-plan balance and schedule rows directly, so that plans do not depend on debt reconciliation.
25. As a payment-plan user, I want plan charges and fees to be plan-owned, so that payment-plan charges do not appear as regular debt charges.
26. As a payment-plan user, I want plan write-offs to be plan-owned, so that write-off behavior does not depend on debt forgiveness or settlement.
27. As a payment-plan user, I want payment-plan details to stop showing linked debt identifiers, so that the UI matches the domain boundary.
28. As a budget user, I want debt payments and payment-plan payments to still create real wallet and financial events when money moves, so that wallet reality remains intact.
29. As a goal user, I want goal links to target debts or payment plans explicitly, so that goal funding does not depend on hidden linked records.
30. As a developer, I want debt rules to live in the debt actions that enforce them, so that an abstract policy layer is not needed for a simplified model.
31. As a developer, I want payment-plan rules to live in payment-plan actions, so that plan behavior can evolve independently from debt behavior.
32. As a developer, I want debt balances to be rebuildable from ledger entries, so that cached balances can be repaired if they drift.
33. As a developer, I want remaining amount treated as a projection, so that no route treats it as an independent source of truth.
34. As a developer, I want old overloaded debt status values removed from public contracts, so that future UI and API work cannot reintroduce confusing badges.
35. As a tester, I want route-level tests for the new debt lifecycle and time status rules, so that status simplification cannot regress.
36. As a tester, I want migration tests for payment-plan decoupling, so that existing plan history is preserved while hidden debt coupling is removed.
37. As a debt user, I want reversal to undo only the latest relevant debt action, so that the ledger cannot be time-traveled into an impossible balance.
38. As a debt user, I want old charge mistakes to guide me toward waiver, correction, or refund actions, so that I do not misuse reverse for real-world changes.
39. As a debt user, I want unrelated debts to stay independent, so that undoing a debt action is not blocked by activity on another debt.
40. As a developer, I want reversal ordering enforced inside each debt ledger rather than globally, so that accounting dependencies are protected without creating arbitrary cross-debt blockers.

## Implementation Decisions

- Payment plans must be fully decoupled from debts at the database, backend, API, and frontend levels.
- New payment plans must not create debt rows.
- Payment plans must not store a foreign key to a debt row.
- Debts must not expose a payment-plan relationship or "managed by payment plan" field.
- Payment-plan payments must not create regular debt transactions.
- Payment-plan charges must not create regular debt charges.
- Payment-plan write-offs must not create regular debt forgiveness entries.
- Payment plans may still create financial events and wallet ledger entries when real money moves.
- Payment plans need their own owned accounting mechanism for plan balance, schedule payments, charges, write-offs, reversals, and corrections.
- Existing data migration must preserve wallet events, financial events, plan payments, plan charges, write-offs, and audit history.
- Existing synthetic debt rows created only to back payment plans should be migrated into payment-plan-owned records and detached or retired without losing real financial history.
- Real user-created debts must remain debts and must not be silently converted into payment plans.
- Goal links that currently depend on payment-plan-linked debt rows must be migrated so that goals can explicitly reference the payment plan where the plan is the real target.
- Debt lifecycle must be simplified to `OPEN` and `CLOSED` for public API and UI behavior.
- Debt lifecycle should be derived from reconciled current balance: positive balance means open, zero balance means closed.
- Debt lifecycle must not be changed through generic status updates.
- Time status must be derived by the backend and not stored in the database.
- Time status is meaningful only for open debts.
- Open debts with due dates before the user's effective current date are `OVERDUE`.
- Open debts with due dates today or later are `ON_TRACK`.
- Closed debts return no time status.
- Archive state must be separate from lifecycle and time status.
- Archive state should be stored with nullable archive metadata, preferably an archive timestamp.
- `is_archived` should be derived from archive metadata for API responses.
- Archive must be allowed for both open and closed debts.
- Restore or unarchive must clear archive metadata without changing the debt balance, due date, ledger, or lifecycle rules.
- Archived debts should be hidden from ordinary working lists by default.
- APIs should support archived filtering or inclusion for archive views.
- Archived debts should mainly expose restore/unarchive in the UI; ordinary money-changing actions should require restoring first unless a later product decision explicitly allows archived mutation.
- The old debt status vocabulary must be removed from public user-facing behavior: active, overdue, defaulted, in collection, paid, settled, forgiven, written off, and archived must no longer be competing lifecycle statuses.
- Closure reason must not become another badge or status. The ledger history is enough to explain whether a debt reached zero through payment, forgiveness, correction, or another action.
- Opening amount should remain stored as a debt header fact because it is part of the debt's setup identity and is useful for lists, summaries, and user understanding.
- Remaining amount may remain stored as a cached projection for performance and ergonomics, but the debt ledger is the authority.
- Any money-changing debt action must create ledger entries and then reconcile the cached remaining amount from posted ledger totals.
- Generic routes must not directly set remaining amount as independent truth.
- Debt list and summary APIs may use cached remaining amount if reconciliation invariants are maintained.
- The debt ledger must preserve the invariant that amount delta equals the sum of principal and charge movement for component-aware entries.
- Forgiveness must not mutate opening amount.
- Forgiveness must not count as cash paid.
- Forgiveness should create forgiveness ledger entries and reduce cached remaining amount through reconciliation.
- Forgiveness must support forgiving original debt balance, waiving charges/fees, and forgiving the full remaining balance.
- Full remaining forgiveness must clear both remaining principal and remaining charges.
- Partial forgiveness must no longer silently use a hard-coded principal-first split without user intent.
- Balance correction must not silently treat every correction as principal.
- Correction must ask what was wrong in real-world language: original debt amount, charges/fees, or remaining original debt balance.
- Pristine opening amount correction may update the stored opening amount and initial ledger entry because no later history depends on the old setup.
- Non-pristine principal correction must create an adjustment ledger entry against principal.
- Charge correction must create an adjustment ledger entry against charges.
- Any fallback "known total only" correction must show a clear preview and record explicit metadata explaining the allocation decision; it must not be the default path.
- The debt UI should show before and after balances for principal/original debt, charges/fees, and total remaining when recording forgiveness or correction.
- Regular debt reversal must follow a latest-unreversed-action-first rule within the same debt ledger.
- Regular debt reversal must not require global LIFO across unrelated debts.
- Reversing an older debt ledger entry should be blocked when newer unreversed entries exist on the same debt.
- Blocked older reversal should explain the real alternatives: undo newer actions first if the older entry was recorded by mistake, or use waiver/forgiveness, correction, or refund if the real-world situation changed later.
- If one financial event touches multiple obligations, reversal should target the event-level dependency rather than pretending unrelated debt ledgers are globally ordered.
- Debt action availability can be computed inside debt-owned route or service handlers.
- The existing generalized debt policy and action restriction model should be removed unless a concrete user-facing lock feature is reintroduced.
- Payment-plan action availability must be computed inside payment-plan-owned route or service handlers.
- Backend response contracts should expose simple derived fields such as lifecycle status, time status, and archive state instead of requiring the frontend to infer them.
- The frontend should remove status filters and badges based on the old overloaded status values.
- The frontend should provide simple filters such as open, closed, overdue, archived, owed by me, and owed to me.
- Payment-plan UI should remove linked debt language and identifiers.
- This PRD supersedes earlier debt/payment-plan coupling assumptions where they conflict with this architecture reset.

## Testing Decisions

- Tests should prioritize public API behavior over implementation details.
- Debt route tests should prove that lifecycle status is derived from balance and cannot be set directly.
- Debt route tests should prove that time status is derived from due date and current user date, and is absent for closed debts.
- Debt archive tests should prove open and closed debts can be archived, hidden from default lists, restored, and recomputed correctly after restore.
- Debt action tests should prove payments, charges, forgiveness, and corrections update ledger entries and reconciled remaining amount.
- Forgiveness tests should cover original debt forgiveness, charge waiver, partial forgiveness, and full forgiveness.
- Correction tests should cover pristine opening amount correction, non-pristine principal correction, charge correction, and blocked or explicit handling for ambiguous total-only correction.
- Ledger tests should assert principal and charge deltas, not just final total balance, for forgiveness and correction actions.
- Tests should assert that forgiven and corrected amounts do not inflate cash paid totals.
- Reversal tests should prove the latest unreversed debt action can be reversed.
- Reversal tests should prove older debt actions are blocked while newer unreversed actions exist on the same debt.
- Reversal tests should prove actions on unrelated debts do not block each other.
- Reversal tests should prove old charge removal is available through charge waiver/correction paths rather than arbitrary old reversal.
- Payment-plan route tests should prove creating a payment plan no longer creates a debt row.
- Payment-plan route tests should prove plan payments, charges, write-offs, undo, and summary behavior work without debt rows.
- Migration tests should prove existing payment-plan data is preserved after removing debt coupling.
- Goal tests should prove goals can target payment plans directly without requiring a linked debt.
- Timeline and budget tests should prove debt obligations and payment-plan obligations still appear in the correct planning surfaces after decoupling.
- Frontend build verification should be run after removing old status badges, old status filters, and linked-debt payment-plan copy.
- Prior route tests for debt ledger reconciliation, debt actions, payment plans, goals, timeline, and budget summaries should be used as the main regression surface.

## Out of Scope

- Rebuilding the entire wallet ledger or financial event system.
- Changing the core budget backing philosophy.
- Reworking expected inflow lifecycle beyond preserving existing debt receivable behavior.
- Treating credit-card and overdraft wallet obligations as debt rows.
- Adding advanced payment-plan restructure workflows beyond what is required for decoupling.
- Adding legal collection workflows such as defaulted or in collection as first-class statuses.
- Adding user-facing closure reason badges.
- Building a full accounting-grade subledger UI for every internal ledger component.
- Manual production data repair outside the automated migration and reconciliation path.

## Further Notes

This PRD is intentionally architecture-heavy. The goal is not to add another layer of badges, policy indirection, or action types. The goal is to make the model boring and real:

- Debts are debts.
- Payment plans are payment plans.
- Archive is user filing behavior.
- Overdue is derived attention.
- Closed means the balance is zero.
- Ledger entries explain what happened.
- Reverse is for mistaken recent entries, not for later real-world changes.
- Cached balances are projections, not independent truth.

The most important engineering guardrail is that stored projection fields are allowed only when there is a clear authority and reconciliation path. For debt balances, the ledger is the authority and cached remaining amount is the projection. For payment plans, the plan-owned accounting model must provide the same clarity after decoupling.

Published locally under `docs/prd/` with the `ready-for-agent` label.
