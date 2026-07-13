# Spec 6: Goal Lifecycle & Intent Protection

Source epic: Epic 6 Goal Lifecycle & Intent Protection

Source decisions: ADR 0008, with ADR 0022 applied as the freeze boundary.

Excluded by request: ADR 0007, Fund Project graduation, release-to-project behavior, and all Isolated Project behavior.

## Problem Statement

Sarflog Goals are protected real money containers. Users put wallet-backed money into a Goal so that it stops feeling spendable until they intentionally use it, return it, or archive the Goal.

The current risk is that Goals can look like one generic feature even though different Goal intents mean very different things:

- A reserve fund is ongoing protection. It should not become overdue or completed just because a date passed or the target was reached.
- A planned purchase is a one-time saving mission. It may have a target date, but missing that date should not rewrite the Goal status.
- A pay-obligation Goal is money prepared for a Debt or Payment Plan. The linked obligation owns urgency and overdue behavior, not the Goal card.
- Fund Project and Isolated Project behavior exists in older docs and code, but it is frozen and must not drive this epic.

If Epic 6 is not clarified, the product can drift into stored `OVERDUE` statuses, target-date rules that punish the wrong intents, frontend actions that expose frozen Project mechanics, or backend routes that allow impossible status transitions. That would make Goals feel unreliable even if the raw money math is mostly correct.

The user-facing problem is simple: a user should always understand what kind of Goal they created, what action is available next, whether the Goal needs attention, and why the app is or is not showing a target date. The database should store only durable facts and explicit user actions, not time-derived moods.

## Solution

Implement the active Goal intent/status contract from ADR 0008 while excluding ADR 0007 and all frozen Isolated/Fund Project work.

From the user's perspective, Sarflog should behave like this:

- Users can create active core Goals for reserves, planned purchases, and pay-obligation saving.
- The Goal creation flow should not invite users into Fund Project or Isolated Project behavior while that product area is frozen.
- Reserve Goals are perpetual protected-money containers.
- Reserve Goals hide or disable target dates.
- Reserve Goals remain active when fully funded.
- Planned Purchase Goals may have an optional target date.
- Planned Purchase Goals may show a soft past-target-date warning, but the database status stays `ACTIVE` until the user records the purchase or archives the Goal.
- Pay Obligation Goals must be tied to a payable Debt or Payment Plan target.
- Pay Obligation Goals inherit their urgency from the linked Debt or Payment Plan.
- Pay Obligation Goals do not have their own overdue lifecycle.
- Archived Goals are filed away and read-only for money actions until restored.
- Goal status never becomes `OVERDUE` in storage.
- Goal time labels such as on-track, due-soon, or past-target are derived from the user's effective local date when the Goal is read.

From the engineering perspective, this epic is a contract-hardening pass:

- Constrain active Goal intents to the stable core.
- Remove or hide frozen Project intent surfaces from new user flows.
- Preserve existing Goal funding and use flows where they serve active core intents.
- Make intent-specific validation explicit at create, update, and action boundaries.
- Keep time-derived state out of persisted Goal status.
- Use the user's effective timezone for any derived target-date display state.
- Align frontend Goal cards, creation choices, action buttons, and target-date controls with the backend contract.

The highest-level testing seam should be Goal route behavior for create, update, list, archive, restore, delete, allocate, return, use reserve, record purchase, and pay obligation. Focused service-level tests are appropriate for dense intent-policy and derived-time-state rules. Frontend tests should cover the Goal creation choices, target-date controls, card badges, primary actions, disabled states, and frozen Project suppression.

## User Stories

1. As a user, I want to choose from clear Goal types, so that I understand what kind of money protection I am creating.
2. As a user, I want frozen Fund Project choices hidden, so that I am not guided into unfinished Project mechanics.
3. As a user, I want a reserve Goal to behave like ongoing protection, so that emergency money does not expire.
4. As a user, I want reserve Goals to hide target dates, so that I do not think an emergency fund has a deadline.
5. As a user, I want a reserve Goal to stay active after reaching its target, so that hitting the target does not imply the fund is finished.
6. As a user, I want to keep adding to a reserve Goal after it reaches target when the app allows it, so that I can maintain a cushion.
7. As a user, I want to use money from a reserve Goal without completing the Goal, so that the reserve remains reusable.
8. As a user, I want returned reserve money to become available again, so that I can correct or loosen protection.
9. As a user, I want planned purchase Goals to support an optional target date, so that I can aim for a purchase window without creating a hard obligation.
10. As a user, I want a planned purchase Goal with a missed target date to remain active, so that I can still buy the item later.
11. As a user, I want past-target planned purchases to show a soft warning, so that I notice the plan drifted.
12. As a user, I do not want past-target planned purchases stored as overdue, so that status does not depend on a midnight job.
13. As a user, I want a planned purchase Goal to complete only when I record the purchase, so that completion means the saving mission was used.
14. As a user, I want a completed planned purchase Goal to become read-only for purchase actions, so that I cannot record the same purchase twice.
15. As a user, I want planned purchase progress to show remaining amount, so that I know how much more to protect.
16. As a user, I want pay-obligation Goals to require a real payable Debt or Payment Plan, so that debt saving is attached to an actual obligation.
17. As a user, I want pay-obligation Goals to reject receivable Debts, so that money owed to me is not treated as a debt I need to pay.
18. As a user, I want only one active pay-obligation Goal per obligation target, so that the same debt is not double-reserved.
19. As a user, I want pay-obligation target amount to track the linked obligation when configured that way, so that Goal progress stays aligned with debt reality.
20. As a user, I want pay-obligation target dates to come from the linked obligation where appropriate, so that the Goal does not invent a separate deadline.
21. As a user, I want overdue warnings for pay-obligation saving to come from the Debt or Payment Plan, so that the real obligation owns urgency.
22. As a user, I want a pay-obligation Goal payment to reduce the linked obligation, so that protected money turns into real repayment.
23. As a user, I want a pay-obligation Goal to complete only when the relevant repayment target is satisfied, so that completion reflects real obligation progress.
24. As a user, I want an archived Goal to be hidden from my normal working view, so that old or paused Goals do not clutter daily planning.
25. As a user, I want archiving a Goal to release any loose protected money according to the existing funding rules, so that money is not trapped.
26. As a user, I want archived Goals to be read-only, so that I do not accidentally change filed-away financial records.
27. As a user, I want to restore an archived Goal, so that I can bring it back without recreating history.
28. As a user, I want permanent delete to be allowed only for safe archived Goals, so that I do not erase money-bearing history.
29. As a user, I want Goal status labels to be consistent across cards, detail views, and forms, so that the same Goal does not tell different stories.
30. As a user, I want action buttons to match the Goal intent, so that reserve, purchase, and debt-saving Goals do not expose the wrong action.
31. As a user, I want disabled Goal actions to explain why they are unavailable, so that I know whether I need funding, restoration, or a different flow.
32. As a user, I want Goal dates and warning badges to use my local day, so that the app does not mark a Goal early or late because of server timezone.
33. As a user, I want Goal funding totals to remain available on every Goal, so that I can see protected, returned, consumed, and remaining money clearly.
34. As a developer, I want `OVERDUE` excluded from stored Goal status, so that time-derived state cannot drift from reality.
35. As a developer, I want a single intent-policy contract for Goal create, update, and actions, so that rules do not differ by route.
36. As a developer, I want Goal list responses to expose derived display state separately from stored status, so that UI badges do not become persistence truth.
37. As a developer, I want frontend creation choices generated from the active intent set, so that frozen intents do not leak back through copy or tests.
38. As a developer, I want frontend Goal actions derived from intent and status, so that cards cannot show impossible actions.
39. As a developer, I want route-level tests for each active intent, so that regressions are caught at the product boundary.
40. As a developer, I want frontend tests for the Goal wizard and card state, so that users are not shown frozen Project mechanics.
41. As a developer, I want timezone-boundary tests for derived time state, so that target-date warnings follow the user's effective local date.
42. As a developer, I want legacy or frozen Project code isolated from active Goal behavior, so that future agents do not deepen a frozen money engine by accident.

## Implementation Decisions

- Treat ADR 0008 as the active Goal lifecycle decision for this epic.
- Treat ADR 0022 as the boundary that freezes Fund Project and Isolated Project work.
- Do not implement ADR 0007 in this spec.
- Do not add historical Goal start dates in this spec.
- Do not add Goal-to-Project graduation behavior in this spec.
- Do not add release-to-project behavior in this spec.
- Do not add Isolated Project funding, stash, top-up, spend-down, or wrap-up behavior in this spec.
- The active public Goal intents for this epic are `RESERVE`, `PLANNED_PURCHASE`, and `PAY_OBLIGATION`.
- `FUND_PROJECT` is frozen for new user-facing work.
- Existing frozen Project records or code paths may be preserved only as legacy/deferred surfaces when removal is too risky.
- New Goal creation should not offer `FUND_PROJECT`.
- Backend create and update behavior should reject or quarantine new `FUND_PROJECT` use unless a later unfreeze decision supersedes this spec.
- Active Goal statuses are explicit human-action statuses, not time statuses.
- `OVERDUE` must not be a stored Goal status.
- Any existing stored or API-facing `OVERDUE` Goal status concept should be migrated, removed, or mapped to a derived display field.
- `GRADUATED` is not an active status for the core intents in this spec.
- If `GRADUATED` remains for legacy frozen records, active core flows must not create it.
- Goal read models may expose a derived time/display state separate from stored status.
- Derived time/display state must be computed from the user's effective local date.
- Derived time/display state must never require a midnight cron job.
- Reserve Goals must not require, display, or derive urgency from `target_date`.
- Reserve Goals must remain `ACTIVE` when their protected amount reaches target.
- Reserve Goals must not be completed automatically.
- Planned Purchase Goals may have an optional `target_date`.
- Planned Purchase Goals with a past target date remain `ACTIVE` until explicit completion or archive.
- Planned Purchase target-date warnings are display state only.
- Planned Purchase Goals complete through the purchase-recording flow, not by setting a date-derived status.
- Planned Purchase Goals should reject duplicate purchase completion.
- Pay Obligation Goals must link to either a payable Debt or a supported Payment Plan target.
- Pay Obligation Goals must reject receivable Debts.
- Pay Obligation Goals must prevent duplicate active Goals for the same obligation target.
- Pay Obligation target amount must be normalized from the linked obligation when using full-remaining tracking.
- Pay Obligation target date should be inherited from the linked obligation or next scheduled target when available.
- Pay Obligation Goals do not own overdue state; Debt and Payment Plan engines own urgency.
- Pay Obligation payment actions must reduce the linked obligation through the existing obligation payment behavior.
- Goal archive is a filing action.
- Archived Goals are read-only for money actions until restored.
- Archiving should release or return loose protected Goal money according to the established Goal funding rules.
- Restoring a Goal should clear archive state without inventing a new lifecycle transition.
- Permanent deletion should require the Goal to be archived and free of protected, consumed, or released money that would make deletion unsafe.
- Frontend Goal creation copy, labels, descriptions, target-date controls, and primary actions must be intent-driven.
- Frontend should not expose Project creation, Project navigation, graduation copy, or Isolated Project language in active Goal flows.
- Goal action availability should be computed from intent, status, funding state, and linked obligation state.
- User-facing date behavior must use the effective user timezone.
- The spec should preserve existing premium/rate-limit boundaries around Goal writes.
- The spec should preserve existing wallet protection rules for Goal funding and use.

## Testing Decisions

- Tests should assert external behavior and financial invariants rather than private helper implementation.
- The preferred backend seam is route-level behavior for Goal create, update, list, archive, restore, delete, allocate, return, use reserve, record purchase, and pay obligation.
- Focused service-level tests are appropriate for intent-policy decisions and derived display-state rules when route tests would be repetitive.
- Frontend tests should cover Goal creation choices, target-date controls, card copy, primary action selection, disabled actions, and frozen Project suppression.
- Goal status tests should prove no stored or returned status value is `OVERDUE`.
- Derived time-state tests should prove past-target Planned Purchase Goals return display warning state while stored status remains `ACTIVE`.
- Reserve tests should prove reaching target does not complete the Goal and does not create overdue state.
- Planned Purchase tests should prove optional target date, soft past-target warning, purchase completion, duplicate completion blocking, and archive behavior.
- Pay Obligation tests should prove required payable link, receivable rejection, duplicate active Goal rejection, target normalization, payment behavior, and obligation-owned urgency.
- Archive tests should prove loose protected money is released or returned, archived Goals are read-only, restored Goals can be used again, and delete requires a safe archived Goal.
- Frozen Project tests should prove users cannot create new Fund Project Goals from active surfaces.
- Frozen Project tests should prove graduation and release-to-project behavior are not deepened by this epic.
- Timezone tests should use the existing effective user timezone helpers and should include at least one boundary case where server date and user date could differ.
- Existing Goal route tests, Debt route tests, Payment Plan tests, wallet protection tests, and frontend Goal UI state tests are prior art.
- Docker should be the default verification environment for backend tests and frontend builds when executing these tickets.

## Out of Scope

- ADR 0007 implementation.
- Historical Goal start dates.
- Imported pre-existing Goal history.
- Off-wallet fulfillment interception.
- Auto-reimbursement or ghost-transfer cleanup.
- Goal-to-Project graduation.
- Release-to-project behavior.
- Isolated Project creation, funding, stash mechanics, top-ups, spend-down, wrap-up, or protection-breach resolution.
- Project local category or micro-subcategory behavior.
- Overlay Project lifecycle behavior outside Goal UI suppression of frozen Fund Project paths.
- Rebuilding the wallet ledger, immutable ledger foundation, Debt architecture, or Payment Plan architecture.
- New Debt or Payment Plan payment models beyond what Pay Obligation Goals need to call existing obligation behavior.
- Multi-currency Goal redesign.
- Bank import, statement matching, or automatic Goal recommendation.
- New analytics dashboards beyond Goal lifecycle display state and existing Goal funding summaries.
- Production-grade migration guarantees for obsolete development-only Fund Project data unless a later implementation ticket explicitly requires them.

## Further Notes

The core mental model should stay small:

- Goal status says what the user explicitly did.
- Goal intent says what kind of protected money this is.
- Target date is input to display state, not a stored lifecycle.
- Reserve is ongoing protection.
- Planned Purchase is one-time saving until purchase is recorded.
- Pay Obligation is saving toward a real payable obligation.
- Debt and Payment Plan urgency belongs to the obligation, not the Goal.
- Fund Project and Isolated Project are frozen until a later product decision revives or removes them.

This epic should make Goals calmer, not larger. The win is not more lifecycle states. The win is fewer impossible states.
