# Epic 5 Issues: Overlay Project Architecture

Parent: [Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Epic 3 Taxonomy Hub and Epic 2 Budget Intelligence completion

## Issue 1: Make Overlay Project Category Limits Month-Scoped

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G24 - Overlay Month-Scoped Architecture](../../prd/g24-overlay-month-scoped-architecture.md)

### What to build

Replace flat overlay project category limits with month-scoped category reservation slices. A user should be able to reserve part of a parent category's selected-month spending permission for an overlay project, see that reservation reduce the parent category's free limit, and still record real expenses even when the project slice itself goes over its local limit.

The parent category remains the macro truth: `parent monthly limit = project reservations + general bucket`. Overlay project reservations are spending-permission reservations, not wallet money and not rollover cash.

### Acceptance criteria

- [x] Overlay projects store category reservations by project, parent category, budget year, and budget month.
- [x] Existing flat overlay category limits are migrated into deterministic month-scoped slices without losing ownership, category, amount, or project links.
- [x] Active overlay category-limit API paths create, update, list, and delete selected-month reservation slices instead of one global category limit.
- [x] Isolated project behavior remains separate and is not forced into overlay month-slice math.
- [x] A category/month cannot have duplicate reservation slices for the same overlay project.
- [x] Budget month reads aggregate all active overlay reservations for each parent category in that month.
- [x] Budget responses expose enough data for the UI to show parent limit, total project reserved, and free general limit.
- [x] Project list/detail responses expose selected-month category slices and aggregate total reserved scope.
- [x] Expense posting linked to an overlay project is never blocked only because the project slice is locally overspent.
- [x] Overlay overspending reduces the derived free general bucket for the same parent category/month.
- [x] Backend tests cover reservation aggregation, overspent project math, ownership isolation, migration safety, and no-rollover month boundaries.
- [x] Frontend API clients and query invalidation paths consume the month-scoped contracts without relying on the old flat limit shape.

### Blocked by

None - can start immediately after the epic prerequisites are satisfied.

---

## Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G25 - Overlay Taxonomy & Subcategory Inheritance](../../prd/g25-overlay-taxonomy-and-inheritance.md)

### What to build

Make overlay project subcategory planning inherit from the user's global taxonomy. Overlay projects should use global `UserSubcategory` tags plus month-scoped reservation slices, not custom project-only labels. A user can attach a global subcategory to an overlay project only when that tag is already present as a monthly subcategory lane under the same parent category for the selected budget month.

This keeps overlay projects as a lens over the main monthly budget rather than a second taxonomy.

### Acceptance criteria

- [x] Overlay project subcategory reservations store project, global subcategory, parent category, budget year, budget month, and limit amount.
- [x] Overlay project subcategory APIs accept global subcategory identifiers instead of custom subcategory names.
- [x] Creating or updating an overlay subcategory reservation requires the selected global tag to belong to the authenticated user.
- [x] Creating or updating an overlay subcategory reservation requires the selected global tag to belong to the same parent category as the project slice.
- [x] Creating or updating an overlay subcategory reservation requires a matching month-specific budget subcategory lane for the same parent budget month.
- [x] The backend hard-blocks project subcategory reservations that exceed the global monthly subcategory lane.
- [x] Overlay expense logging uses `project_id` plus the existing global `subcategory_id`; active overlay paths no longer require a project-only subcategory identifier.
- [x] Historical ledger rows keep readable subcategory context after the overlay taxonomy migration.
- [x] Isolated project subcategory behavior remains available for isolated-project scope and is not silently changed by overlay inheritance work.
- [x] Frontend project structure controls let users search/select eligible global subcategories for overlay projects and explain when a tag must first be added to the monthly budget.
- [x] Backend tests cover global-tag linkage, missing monthly lane rejection, cross-user rejection, cross-category rejection, hard-block limit validation, and ledger compatibility.
- [x] Frontend tests cover eligible tag selection, unavailable/missing tag copy, payload mapping, refreshed project details, and localized errors.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped

---

## Issue 3: Hard-Block Overlay Reservation Overbooking

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G25 - Overlay Taxonomy & Subcategory Inheritance](../../prd/g25-overlay-taxonomy-and-inheritance.md)

### What to build

Prevent users from reserving more overlay spending permission than the selected parent budget month actually has. Across all active overlay projects, the total reserved amount for a category/month must not exceed that parent category's monthly limit, and project reallocation must require real unreserved headroom in the target category.

This block applies to planning reservations only. Real expense posting remains truth-first and can still create red states.

### Acceptance criteria

- [x] Creating an overlay category reservation sums existing active overlay reservations for the same user, category, year, and month before saving.
- [x] Updating an overlay category reservation excludes the current slice and validates the proposed new amount against the parent monthly limit.
- [x] Creating or updating a reservation fails with a stable validation error when total reservations would exceed the parent monthly limit.
- [x] Creating or updating a reservation fails when the selected parent budget month does not exist.
- [x] Reservation validation is ownership-scoped and never counts another user's projects or budgets.
- [x] Project subcategory reservations cannot exceed their matching global monthly subcategory lane after considering existing project reservations.
- [x] Moving reservation amount between project categories validates that the target parent category has enough unreserved selected-month capacity.
- [x] The UI shows available selected-month headroom while editing overlay project reservations.
- [x] The UI prevents accidental overbooking before submit and still surfaces backend validation errors when another change races the user.
- [x] Tests cover overlapping projects, same-category collisions, cross-category reallocation, subcategory overbooking, missing parent budget, ownership isolation, and concurrent-style stale headroom failures.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped
- Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy

---

## Issue 4: Migrate Overlay Slices When Project Dates Change

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G24 - Overlay Month-Scoped Architecture](../../prd/g24-overlay-month-scoped-architecture.md)

### What to build

Make overlay project date edits preserve month-scoped reservation integrity. When a user changes an overlay project's start or target end date, reservation slices should be kept only inside the new project window, and any moved or removed slice must respect the real spending already attached to that project and month.

The user should never be allowed to make a date edit that strands historical spending outside the project window or shrinks a month slice below its actual spent amount.

### Acceptance criteria

- [x] Overlay project updates derive the old and new project month windows from user-local calendar months.
- [x] Date edits cannot move the project start after the earliest linked project expense.
- [x] Date edits cannot move the target end date before the latest linked project expense.
- [x] Slices outside the new month window are removed only when their actual spent amount is zero.
- [x] Slices outside the new month window with actual spent are preserved or the update is rejected with a stable validation error.
- [x] Any slice migration or pruning runs transactionally with the project date update.
- [x] Slice amounts are never reduced below actual spent for the same project, category/subcategory, and month.
- [x] Project detail and budget month responses remain consistent immediately after a successful date update.
- [x] The UI previews which selected-month reservations will remain, move, or be blocked before submitting date changes.
- [x] API failures leave the project dates and reservation slices unchanged in local UI state.
- [x] Backend tests cover narrowing, widening, moving, actual-spent guards, local month boundaries, and transaction rollback.
- [x] Frontend tests cover preview copy, blocked edits, successful refresh, and localized validation messages.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped

---

## Issue 5: Render Overlay Reservations in Budget Cards and Budget Details

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G27 - Overlay UI Matrix & Creation Wizard](../../prd/g27-overlay-ui-matrix-wizard.md)

### What to build

Update the Budget Workspace so overlay project complexity is visible at the right depth. Budget cards should stay clean and show only macro reservation math. Budget Details should reveal which active projects are reserving parts of the selected parent category for that month.

The parent progress bar must continue to represent total real spending against the parent limit, not a stack of project bars.

### Acceptance criteria

- [x] Budget cards show parent limit, total spent, total project reserved, and free general limit for the selected month.
- [x] Budget card progress remains based on total spent versus parent monthly limit.
- [x] Budget cards do not render stacked project progress bars.
- [x] A parent category can remain visually healthy when project spending is over its local reservation but total parent spending is still within the parent monthly limit.
- [x] Budget Details includes an Active Project Reservations section for the selected category/month.
- [x] Budget Details lists each overlapping project reservation with project title, reserved amount, actual spent, remaining or over amount, and status.
- [x] Multiple overlapping projects render as individual mini-bars without changing parent card progress math.
- [x] Empty, loading, error, desktop, and mobile states are supported.
- [x] User-facing copy uses spending permission and reservation language, not envelope cash language.
- [x] Budget, project, and analytics queries are invalidated after reservation changes so the UI does not show stale free limit.
- [ ] Frontend tests cover card macro math, detail mini-bars, local project overspend with healthy parent category, empty states, mobile layout, and stale-query refresh.
- [x] Frontend build passes.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped
- Issue 3: Hard-Block Overlay Reservation Overbooking

---

## Issue 5.5: Decouple Overlay and Isolated Project Typology

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G34 - Decouple Overlay and Isolated Project Typology](../../prd/g34-project-typology-decoupling.md), [G33 - Overlay Project Target Estimate vs Operational Reserved Scope](../../prd/g33-overlay-target-vs-operational-limits.md)

### What to build

Split overlay and isolated project financial semantics before completing the just-in-time overlay wizard. Sarflog should keep a shared project identity for ownership, lifecycle, dates, expenses, and ledger references, but project-type-specific money behavior must live behind explicit overlay and isolated contracts.

Overlay projects are limit-based budget lenses: they reserve monthly spending permission from parent budget categories and never own money. Isolated projects are dedicated project-funding containers: they can use stash/funding language and spend down project-specific funding. The completed slice should remove the need for overlay code to reason through isolated `total_limit` behavior, while preserving historical project ids and ledger/report compatibility.

### Checkpoint

Before implementing new typology structures, audit the already-completed Issue 1-5 work for old shared-project assumptions. The agent must preserve the completed behavior from those issues, but refactor their overlay logic into the new decoupled architecture where needed. Issue 5.5 is not complete if Issues 1-5 still depend on generic project financial fields, `is_isolated` branching, or shared response contracts in places that should now be overlay-specific or isolated-specific.

### Acceptance criteria

- [ ] Completed Issue 1-5 behavior is audited and refactored into the decoupled architecture instead of being left behind under old shared-project assumptions.
- [ ] Shared project identity remains stable for ownership, title, description, status, dates, expenses, entity-ledger rows, goal releases, and reports.
- [ ] Project type is explicit and validated; code does not rely on nullable financial fields to infer overlay versus isolated behavior.
- [ ] Isolated-project financial data is stored behind an isolated-specific structure or contract, including project-wide total/funding concepts where they remain valid.
- [ ] Overlay-project metadata is stored behind an overlay-specific structure or contract, including target estimate as planning context only.
- [ ] Overlay operational permission continues to come only from month-scoped category and subcategory reservation rows.
- [ ] Overlay projects cannot create, update, or report an isolated operational `total_limit`.
- [ ] Isolated projects are not forced through overlay monthly reservation rows or overlay headroom validation.
- [ ] Existing projects are backfilled deterministically into exactly one typology without changing project ids.
- [ ] Existing ledger rows, expenses, goal releases, project reservations, and reports remain readable after migration.
- [ ] Any compatibility layer for old shared fields is read-only, temporary, and tested; new Issue 6 work uses overlay-specific contracts.
- [ ] Overlay and isolated project services are separated enough that each service uses its own financial language and validation rules.
- [ ] Project create/update API contracts are typology-specific and reject fields that belong to the other project type.
- [ ] Frontend project cards and edit/create flows show only typology-appropriate controls and copy.
- [ ] Overlay UI uses limit, reservation, selected-month headroom, reserved so far, and target estimate language.
- [ ] Isolated UI uses funding, stash, released funding, remaining funding, and spend-down language.
- [ ] User-facing project date defaults and validations use the user's effective timezone.
- [ ] Backend tests cover migration backfill, ownership isolation, invalid cross-typology payloads, overlay reservation summaries, isolated funding summaries, and ledger/report compatibility.
- [ ] Frontend tests cover typology-specific project cards, create/edit controls, and rejection of stale generic `total_limit` assumptions in overlay paths.
- [ ] Docker verification passes for migration, focused backend tests, and frontend build.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped
- Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy
- Issue 3: Hard-Block Overlay Reservation Overbooking
- Issue 5: Render Overlay Reservations in Budget Cards and Budget Details

---

## Issue 6: Build the Just-In-Time Overlay Project Creation Wizard

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G27 - Overlay UI Matrix & Creation Wizard](../../prd/g27-overlay-ui-matrix-wizard.md), [G33 - Overlay Project Target Estimate vs Operational Reserved Scope](../../prd/g33-overlay-target-vs-operational-limits.md), [G34 - Decouple Overlay and Isolated Project Typology](../../prd/g34-project-typology-decoupling.md)

### What to build

Replace the overlay project creation flow with a just-in-time wizard that only asks the user to allocate the current active budget month. The user can choose project identity and dates, optionally enter a target estimate as planning metadata, select parent categories, reserve current-month headroom, and optionally attach global subcategory lanes without being asked to invent future-month money.

Future month slices are created later when those months are actually planned.

### Acceptance criteria

- [x] The overlay creation flow collects project title, description, start date, and target end date.
- [x] The overlay creation flow can collect an optional target estimate as non-operational planning context.
- [x] Overlay projects keep `total_limit` null; target estimate does not create budget permission or future-month slices.
- [x] Overlay project cards show reserved this month, reserved so far, and target estimate instead of isolated-project "No total limit" copy.
- [x] The wizard lets the user choose parent categories for the overlay project scope.
- [x] The allocation step renders inputs only for the current active budget month, even when project dates span future months.
- [x] The allocation step fetches selected-month parent budget headroom and validates proposed reservations live.
- [x] The wizard cannot submit reservations that exceed available selected-month parent-category headroom.
- [x] The optional micro-structure step lets the user attach eligible global monthly subcategory lanes to the overlay project.
- [x] If a needed global subcategory lane is missing from the selected budget month, the wizard routes the user to create or attach it through the Budget Workspace taxonomy flow.
- [x] The final review explains the current-month reservations that will be created and states that future months will be allocated when those months are set up.
- [x] Submitting the wizard creates the overlay project and its current-month category/subcategory slices transactionally or leaves no partial project behind.
- [x] Successful creation refreshes projects, budgets, budget details, dashboard summaries, and analytics as applicable.
- [x] API failures preserve draft input and show localized actionable errors.
- [x] Tests prove future months are not rendered, current-month headroom validation works, optional subcategory attachment maps to global tags, and successful submit creates the expected reservation slices.
- [x] Frontend build passes.

### Blocked by

- Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy
- Issue 3: Hard-Block Overlay Reservation Overbooking
- Issue 5: Render Overlay Reservations in Budget Cards and Budget Details
- Issue 5.5: Decouple Overlay and Isolated Project Typology

---

## Issue 7: Prompt New-Month Overlay Allocation During Month Setup

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G27 - Overlay UI Matrix & Creation Wizard](../../prd/g27-overlay-ui-matrix-wizard.md)

### What to build

Add the project-allocation prompt that lets active cross-month overlay projects grow one real month at a time. After a user previews or applies a new budget month, Sarflog should identify active overlay projects spanning that month and ask whether to reserve part of the newly planned parent category limits for each project.

This issue should use the existing month setup backend seam where available and expose a reusable frontend prompt that the later full Month Setup Wizard can own directly.

### Acceptance criteria

- [ ] Month setup preview/apply responses can identify active overlay projects whose date windows include the target month and do not yet have slices for that month.
- [ ] Project allocation prompts include project title, selected target month, eligible parent categories, parent monthly limit, already reserved amount, and available headroom.
- [ ] The user can skip allocation for a project/month without mutating existing slices.
- [ ] The user can create one or more selected-month overlay category slices from the prompt.
- [ ] Prompt submissions reuse the same overbooking validation as ordinary overlay reservation edits.
- [ ] Created slices refresh month setup preview state, budget month state, project details, and budget details.
- [ ] The prompt never asks for months that have not been set up or previewed.
- [ ] The prompt never creates future-month slices as a side effect of creating the project.
- [ ] UI copy makes it clear that the user is reserving part of the newly planned month, not moving wallet cash.
- [ ] Backend tests cover eligible project discovery, already-sliced project exclusion, skipped prompts, created slices, and overbooking rejection.
- [ ] Frontend tests cover prompt triggering after month setup, skip behavior, submit payloads, refreshed state, and localized errors.

### Blocked by

- Issue 3: Hard-Block Overlay Reservation Overbooking
- Issue 6: Build the Just-In-Time Overlay Project Creation Wizard

---

## Issue 8: Enforce Ledger-Safe Deletion & Resolution for Overlay Projects

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G26 - Overlay Ledger Integrity](../../prd/g26-overlay-ledger-integrity.md)

### What to build

Protect ledger history when deleting overlay projects. A project with no linked expenses (Pristine) can be hard-deleted immediately. If a project has linked financial events (Non-Pristine), clicking "Delete" must present a Resolution Screen with three options:
1. **Archive:** Safely hide the project while keeping expenses and ledger records intact.
2. **Detach Expenses:** Remove the `project_id` from all linked expenses (turning them into normal standalone expenses) and then hard-delete the project.
3. **Delete linked expenses and project (Danger Zone):** Force the user to type the project name to confirm. The UI should describe the user outcome while the backend preserves ADR-0011 reversal-ledger mechanics internally.

### Acceptance criteria

- [ ] Overlay project deletion checks for linked financial events before deleting.
- [ ] Pristine overlay projects can be hard-deleted immediately with no extra steps.
- [ ] Hard-deleting a pristine overlay project removes its category and subcategory reservation slices and refreshes parent budget limits.
- [ ] Non-pristine overlay project deletion triggers a UI Resolution modal instead of a direct API delete call.
- [ ] The Resolution modal lists the number of linked expenses and their total monetary value.
- [x] **Archive Option:** Updates project status to `ARCHIVED`.
- [x] Archived projects reject repeated archive actions with a stable `projects.already_archived` error.
- [ ] **Detach Option:** Strips `project_id` and `project_subcategory_id` from all linked expenses, then hard-deletes the project.
- [x] **Delete linked expenses option:** Requires type-to-confirm UX and uses user-facing copy while backend logic voids linked expenses with compliant reversal ledger legs before hard-deleting the project.
- [ ] Successful resolution refreshes projects, budgets, expenses list, and dashboard summaries.
- [ ] Backend tests cover pristine delete, archive state, safe detachment, and ADR-0011 compliant cascade voiding.
- [ ] Frontend tests cover the resolution modal trigger, the danger zone confirmation state, and API payload correctness.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped
- Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy

---

## Issue 9: Complete Overlay Projects with Auto-Sweep Reservations

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G26 - Overlay Ledger Integrity](../../prd/g26-overlay-ledger-integrity.md), [G23 - Project Completion Wrap-Up and Typology](../../prd/g23-project-completion-and-wrap-up.md)

### What to build

Make overlay project completion reclaim unused current and future reservation space without rewriting past months. When a user completes or wraps up an overlay project, Sarflog should shrink each current/future reservation slice to the actual amount spent in that slice, returning unused spending permission to the parent category's free general limit.

Past month slices remain historically preserved under the no-rollover rule.

### Acceptance criteria

- [x] Completion is a user-triggered action; projects are not auto-completed when the target end date arrives.
- [x] Overdue active projects can surface a ready-to-wrap prompt, but the prompt is a derived UI state, not a stored backend status.
- [x] Active projects can be completed early before `target_end_date` when the user intentionally wraps up or cancels the project.
- [x] Normal completion stores the completion as the user's local business date, using the backend effective timezone, without asking the user to type a date.
- [x] `completed_at` remains a date-only business field; technical audit timestamps remain timezone-aware UTC datetimes.
- [x] Paused/stopped overlay projects block new project expenses but continue to hold their reservation slices against parent budgets.
- [x] Paused/stopped overlay projects can be completed directly without first resuming them.
- [x] Issue 9 sweep runs for both overdue completion and early completion.
- [x] Fully unspent current/future slices are removed, because current monthly reservation tables require positive `limit_amount`.
- [x] Completing an overlay project computes actual spent by project, category/subcategory, year, and month.
- [x] Current and future category reservation slices are reduced to actual spent for the matching slice.
- [x] Current and future subcategory reservation slices are reduced to actual spent for the matching global subcategory slice.
- [x] Completely unspent current/future slices are reduced to zero or removed according to the chosen persistence convention.
- [x] Past month slices are not swept or rewritten during completion.
- [x] Sweep math treats refunds as reductions to actual spent where the ledger already represents a refund against the project.
- [x] Completion cannot set a completion date before linked project activity.
- [x] Completing the project marks it completed and prevents further ordinary reservation edits.
- [x] The parent budget's reserved amount and free general limit update immediately after sweep.
- [ ] The UI preview shows planned, actual, and reclaimed reservation amounts before confirmation.
- [ ] API failures leave project status and reservation slices unchanged.
- [ ] Backend tests cover under-budget sweep, unspent slice sweep, refund-adjusted actuals, past-month exclusion, linked-expense date guard, and transaction rollback.
- [ ] Frontend tests cover preview math, confirmation, refreshed budget/project state, and localized errors.

### Blocked by

- Issue 5: Render Overlay Reservations in Budget Cards and Budget Details
- Issue 8: Enforce Pristine Deletion for Overlay Projects

---

## Issue 10: Add Project Wrap-Up Summary and Typology-Safe Language

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G23 - Project Completion Wrap-Up and Typology](../../prd/g23-project-completion-and-wrap-up.md)

### What to build

Turn project completion into an intentional wrap-up workflow. Projects should remain active through the target end date, then surface a ready-to-wrap prompt after the date has passed. The wrap-up view should summarize planned versus actual performance and use language that keeps overlay projects distinct from isolated projects.

Overlay projects use limit/reservation language and progress fills up against permission. Isolated projects use funding/allocation language and progress drains down from a dedicated stash.

### Acceptance criteria

- [ ] Expense posting remains allowed through the full target end date in the user's effective timezone.
- [ ] The ready-to-wrap state is derived from target end date plus active project status; it is not stored as a new project status.
- [ ] Active projects past their target end date show a wrap-up prompt without auto-locking the project.
- [ ] A project wrap-up summary endpoint returns planned amount, actual spent, remaining or over amount, top spending categories/subcategories, and month-by-month burn data.
- [ ] Wrap-up summary metrics are ownership-scoped and exclude voided or unrelated ledger activity.
- [ ] The wrap-up modal renders clean loading, empty, error, desktop, and mobile states.
- [ ] Overlay wrap-up copy uses limit, reservation, spent, remaining, and reclaimed spending permission language.
- [ ] Isolated project copy uses funding, allocation, stash, spent, remaining funding, and sweep language without changing isolated project architecture in this epic.
- [ ] The wrap-up confirmation routes overlay projects through the auto-sweep completion flow.
- [ ] Completed projects are visibly read-only while preserving historical report access.
- [ ] Backend tests cover inclusive end-date posting, derived ready-to-wrap state, summary metrics, voided-event exclusion, and ownership isolation.
- [ ] Frontend tests cover the prompt, summary modal, typology-specific copy, completion routing, and completed read-only state.
- [ ] Frontend build passes.

### Blocked by

- Issue 9: Complete Overlay Projects with Auto-Sweep Reservations
