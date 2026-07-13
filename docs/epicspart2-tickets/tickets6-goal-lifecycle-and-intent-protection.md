# Tickets: Goal Lifecycle & Intent Protection

Source spec: `docs/epicspart2-specs/spec-6-goal-lifecycle-and-intent-protection.md`

These tickets implement Epic 6 from ADR 0008 while applying the ADR 0022 freeze boundary. They harden Goal intent rules, keep time-derived state out of stored status, suppress frozen Fund Project/Isolated Project paths, and align backend plus frontend behavior for Reserve, Planned Purchase, and Pay Obligation Goals.

Assumption: Epic 1 ledger foundation and Epic 2 Debt/Payment Plan obligation behavior are the active contracts. Work the frontier: any ticket whose blockers are complete can start.

## Proposed Breakdown

1. **Freeze Fund Project from active Goal surfaces**
   - Blocked by: None
   - What it delivers: users can no longer enter frozen Fund Project or Isolated Project Goal flows from active create/update/action surfaces.

2. **Derive Goal time state outside stored status**
   - Blocked by: Ticket 1
   - What it delivers: Goal status never stores `OVERDUE`; target-date badges are derived with the user's effective local date.

3. **Enforce Reserve Goal lifecycle**
   - Blocked by: Ticket 2
   - What it delivers: reserve Goals behave as perpetual protected-money containers with no deadline, no overdue state, and no automatic completion.

4. **Enforce Planned Purchase Goal lifecycle**
   - Blocked by: Ticket 2
   - What it delivers: planned purchase Goals support optional target dates, soft past-target warnings, and completion only through purchase recording.

5. **Enforce Pay Obligation Goal lifecycle**
   - Blocked by: Ticket 2
   - What it delivers: pay-obligation Goals require a payable Debt or Payment Plan target and delegate urgency to the linked obligation.

6. **Harden Goal archive, restore, delete, and read-only rules**
   - Blocked by: Tickets 3, 4, 5
   - What it delivers: archived Goals file away cleanly, release loose protected money, block money actions while archived, and delete only when safe.

7. **Align Goal UI with the intent matrix**
   - Blocked by: Tickets 1, 3, 4, 5, 6
   - What it delivers: Goal creation, target-date controls, badges, primary actions, and disabled states match the active intent/status contract.

8. **Finish Epic 6 lifecycle regression coverage**
   - Blocked by: Tickets 6, 7
   - What it delivers: backend and frontend tests prove the active Goal lifecycle contract and prevent frozen Project or stored-overdue regressions.

## Ticket 1: Freeze Fund Project From Active Goal Surfaces

**What to build:** Users should only see and create stable core Goal intents. Fund Project and Isolated Project behavior should not appear in active Goal creation, update, card actions, or navigation flows while that product area is frozen.

**Blocked by:** None - can start immediately.

- [x] Goal creation UI offers Reserve, Planned Purchase, and Pay Obligation choices only.
- [x] Goal creation UI does not show Fund Project, Project fund, graduation, or Isolated Project copy.
- [x] Backend Goal creation rejects new `FUND_PROJECT` submissions or quarantines them behind an explicit frozen/disabled response.
- [x] Backend Goal update rejects changing an active core Goal into `FUND_PROJECT`.
- [x] Active Goal card actions do not expose Project creation, Project navigation, graduation, or release-to-project actions.
- [x] Existing frozen Project records, if present, are not expanded by this ticket.
- [x] Existing frozen records are either hidden from active working views or shown as deferred/read-only without new money actions.
- [x] Tests prove a new user cannot create a Fund Project Goal through the public API.
- [x] Frontend tests prove the creation choices do not include Fund Project or Isolated Project language.
- [x] Documentation or inline product copy makes clear that Fund Project is frozen, not partially available.

## Ticket 2: Derive Goal Time State Outside Stored Status

**What to build:** Goal status should store explicit lifecycle actions only. Time-based labels such as on-track, due-soon, or past-target should be derived when Goals are read, using the user's effective local date.

**Blocked by:** Ticket 1: Freeze Fund Project from active Goal surfaces.

- [x] Goal storage and public status contracts do not include `OVERDUE` as a stored Goal status.
- [x] Any legacy `OVERDUE` Goal status path is removed, migrated, or mapped to `ACTIVE` plus derived display state.
- [x] Goal list/detail responses expose derived time/display state separately from stored status.
- [x] Derived time state is calculated from the user's effective timezone.
- [x] Derived time state is null for archived Goals.
- [x] Derived time state is null for completed planned purchases.
- [x] Derived time state is null for Reserve Goals.
- [x] Derived time state is null for Pay Obligation Goals unless the UI is showing linked obligation context from the obligation engine.
- [x] Planned Purchase Goals with a future target date can show on-track or due-soon display state while stored status remains `ACTIVE`.
- [x] Planned Purchase Goals with a past target date can show a soft past-target display state while stored status remains `ACTIVE`.
- [x] Tests prove no route returns `status = OVERDUE`.
- [x] Timezone-boundary tests prove derived state follows the user's local date.

## Ticket 3: Enforce Reserve Goal Lifecycle

**What to build:** Reserve Goals should behave as ongoing protected-money containers. They should not have deadlines, overdue state, or automatic completion just because the target amount was reached.

**Blocked by:** Ticket 2: Derive Goal time state outside stored status.

- [x] Reserve Goal creation ignores, rejects, or clears target-date input according to the final API contract.
- [x] Reserve Goal update does not allow adding a target date that creates urgency.
- [x] Reserve Goal list/detail responses return no time-derived urgency state.
- [x] Funding a Reserve Goal to its target keeps status `ACTIVE`.
- [x] Funding a Reserve Goal above target follows existing funding-limit rules without completing the Goal.
- [x] Using protected reserve money does not complete the Goal.
- [x] Returning protected reserve money reopens availability according to the existing funding rules.
- [x] Reserve Goal primary action is a reserve-use action, not complete, graduate, or purchase.
- [x] Archived Reserve Goals are read-only until restored.
- [x] Tests prove reaching target does not change Reserve status to `COMPLETED`.
- [x] Tests prove Reserve Goals cannot become overdue.
- [ ] Frontend tests prove Reserve target-date controls are hidden or disabled.

## Ticket 4: Enforce Planned Purchase Goal Lifecycle

**What to build:** Planned Purchase Goals should support one-time purchase saving. A target date is optional and advisory; completion happens through recording the purchase, not because a date passed.

**Blocked by:** Ticket 2: Derive Goal time state outside stored status.

- [x] Planned Purchase Goal creation accepts no target date or one optional target date.
- [x] Planned Purchase Goal update can edit the optional target date while the Goal remains editable.
- [x] A past target date never changes stored status away from `ACTIVE`.
- [x] A past target date can produce a soft display warning.
- [x] Planned Purchase Goal completion happens through the purchase-recording action.
- [x] Direct status updates cannot mark a Planned Purchase complete unless they follow the accepted product contract.
- [x] Recording a purchase links the resulting financial record to the Goal.
- [x] Recording a purchase consumes or releases protected Goal money according to existing funding rules.
- [x] Recording the same purchase twice is rejected.
- [x] Completed Planned Purchase Goals are read-only for purchase actions.
- [x] Archive and restore behavior works for active Planned Purchase Goals.
- [x] Tests prove target-date drift is display-only.
- [x] Tests prove purchase recording is the completion path.
- [ ] Frontend tests prove the primary action is record purchase and is disabled after completion.

## Ticket 5: Enforce Pay Obligation Goal Lifecycle

**What to build:** Pay Obligation Goals should prepare protected money for a real payable Debt or Payment Plan target. The linked obligation owns urgency, overdue behavior, and repayment truth.

**Blocked by:** Ticket 2: Derive Goal time state outside stored status.

- [x] Pay Obligation Goal creation requires exactly one supported payable obligation target.
- [x] Pay Obligation Goal creation rejects receivable Debts.
- [x] Pay Obligation Goal creation rejects closed, archived, or otherwise ineligible obligation targets.
- [x] Only one active Pay Obligation Goal may exist for the same obligation target.
- [x] Full-remaining tracking normalizes target amount from the linked obligation.
- [x] Fixed target tracking validates the target amount against the linked obligation.
- [x] Pay Obligation target date is inherited or normalized from the linked obligation target when available.
- [x] Users cannot create a separate Goal-owned overdue status for Pay Obligation Goals.
- [x] Pay Obligation list/detail responses expose linked obligation context needed for urgency without storing Goal overdue state.
- [x] Paying from a Pay Obligation Goal reduces the linked Debt or Payment Plan through existing obligation behavior.
- [x] A completed or settled target updates Goal progress and status according to the active contract.
- [x] Reversal or obligation balance changes resync Goal target/progress where existing obligation behavior supports it.
- [x] Tests prove receivable Debts are rejected.
- [x] Tests prove duplicate active Pay Obligation Goals are rejected.
- [x] Tests prove linked Debt or Payment Plan urgency stays outside Goal stored status.

## Ticket 6: Harden Goal Archive, Restore, Delete, And Read-Only Rules

**What to build:** Goal filing behavior should be consistent across active core intents. Archiving should safely remove a Goal from active work, return loose protected money according to existing rules, and prevent accidental mutation until restored.

**Blocked by:**

- Ticket 3: Enforce Reserve Goal lifecycle.
- Ticket 4: Enforce Planned Purchase Goal lifecycle.
- Ticket 5: Enforce Pay Obligation Goal lifecycle.

- [x] Users can archive active Reserve, Planned Purchase, and Pay Obligation Goals when allowed by the active contract.
- [x] Archiving returns or releases loose protected Goal money according to established funding rules.
- [x] Archived Goals are hidden from normal active lists unless the user asks for archived records.
- [x] Archived Goals are read-only for allocate, return, use reserve, record purchase, and pay-obligation payment actions.
- [x] Restoring a Goal clears archive state without changing its financial history.
- [x] Restored Goals recompute progress and derived display state from current facts.
- [x] Permanent delete requires archived status.
- [x] Permanent delete requires no protected money remains in the Goal.
- [x] Permanent delete requires no consumed/released history that makes deletion unsafe under the active contract.
- [x] Error messages distinguish archived-read-only, restore-required, delete-requires-archived, and delete-requires-empty cases.
- [x] Tests cover archive, restore, and delete for each active core intent.
- [x] Tests prove archived Goals cannot be mutated by money actions.

## Ticket 7: Align Goal UI With The Intent Matrix

**What to build:** The frontend Goal experience should mirror the backend intent/status matrix. Users should see the right creation choices, target-date controls, badge language, primary action, and disabled action reasons for each active core intent.

**Blocked by:**

- Ticket 1: Freeze Fund Project from active Goal surfaces.
- Ticket 3: Enforce Reserve Goal lifecycle.
- Ticket 4: Enforce Planned Purchase Goal lifecycle.
- Ticket 5: Enforce Pay Obligation Goal lifecycle.
- Ticket 6: Harden Goal archive, restore, delete, and read-only rules.

- [x] Goal creation choices are limited to Reserve, Planned Purchase, and Pay Obligation.
- [x] Reserve creation hides or disables target-date input.
- [x] Planned Purchase creation shows optional target-date input.
- [x] Pay Obligation creation requires choosing an eligible payable Debt or Payment Plan target.
- [x] Goal cards show stored status separately from derived time/display badges.
- [x] Reserve cards never show overdue or completed because of target progress.
- [x] Planned Purchase cards can show soft past-target copy while status remains active.
- [x] Pay Obligation cards show linked obligation urgency without presenting Goal-owned overdue state.
- [x] Primary actions are Use reserve, Record purchase, and Make payment for the three active intents.
- [x] Primary actions are disabled with useful reasons when the Goal has no protected money, is archived, is completed, or lacks an eligible linked target.
- [x] No active Goal UI text mentions isolated project stash, project graduation, create project, project top-up, or release to project.
- [x] Frontend tests cover creation choices, target-date controls, card state, primary actions, disabled states, and frozen Project suppression.

## Ticket 8: Finish Epic 6 Lifecycle Regression Coverage

**What to build:** Complete the regression suite and documentation pass that proves Goal lifecycle behavior is stable across backend and frontend surfaces. Future changes should fail tests before they reintroduce stored overdue statuses, frozen Project actions, or intent/status confusion.

**Blocked by:**

- Ticket 6: Harden Goal archive, restore, delete, and read-only rules.
- Ticket 7: Align Goal UI with the intent matrix.

- [x] Backend route tests cover create, update, list, archive, restore, delete, allocate, return, use reserve, record purchase, and pay obligation for active core intents.
- [x] Backend tests prove no active Goal route stores or returns `OVERDUE` as status.
- [x] Backend tests prove derived display state is timezone-aware.
- [x] Backend tests prove Reserve target behavior, Planned Purchase completion behavior, and Pay Obligation linked-target behavior together.
- [x] Backend tests prove Fund Project creation/update/action paths are frozen or inaccessible from public active flows.
- [x] Frontend tests prove creation choices, controls, badges, actions, and disabled states match the backend contract.
- [x] Frontend tests prove no Isolated Project or Fund Project copy appears in active Goal flows.
- [x] Regression coverage includes at least one archived Goal case for each active core intent.
- [x] Regression coverage includes at least one completed Planned Purchase case and one paid Pay Obligation case.
- [x] Documentation reflects that ADR 0007, Fund Project graduation, and Isolated Project mechanics are excluded from Epic 6.
- [x] Docker backend tests and frontend build/test commands are run or clearly documented if unavailable.
