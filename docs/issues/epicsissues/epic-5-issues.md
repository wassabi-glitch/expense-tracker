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

- [ ] Overlay projects store category reservations by project, parent category, budget year, and budget month.
- [ ] Existing flat overlay category limits are migrated into deterministic month-scoped slices without losing ownership, category, amount, or project links.
- [ ] Active overlay category-limit API paths create, update, list, and delete selected-month reservation slices instead of one global category limit.
- [ ] Isolated project behavior remains separate and is not forced into overlay month-slice math.
- [ ] A category/month cannot have duplicate reservation slices for the same overlay project.
- [ ] Budget month reads aggregate all active overlay reservations for each parent category in that month.
- [ ] Budget responses expose enough data for the UI to show parent limit, total project reserved, and free general limit.
- [ ] Project list/detail responses expose selected-month category slices and aggregate total reserved scope.
- [ ] Expense posting linked to an overlay project is never blocked only because the project slice is locally overspent.
- [ ] Overlay overspending reduces the derived free general bucket for the same parent category/month.
- [ ] Backend tests cover reservation aggregation, overspent project math, ownership isolation, migration safety, and no-rollover month boundaries.
- [ ] Frontend API clients and query invalidation paths consume the month-scoped contracts without relying on the old flat limit shape.

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

- [ ] Overlay project subcategory reservations store project, global subcategory, parent category, budget year, budget month, and limit amount.
- [ ] Overlay project subcategory APIs accept global subcategory identifiers instead of custom subcategory names.
- [ ] Creating or updating an overlay subcategory reservation requires the selected global tag to belong to the authenticated user.
- [ ] Creating or updating an overlay subcategory reservation requires the selected global tag to belong to the same parent category as the project slice.
- [ ] Creating or updating an overlay subcategory reservation requires a matching month-specific budget subcategory lane for the same parent budget month.
- [ ] The backend hard-blocks project subcategory reservations that exceed the global monthly subcategory lane.
- [ ] Overlay expense logging uses `project_id` plus the existing global `subcategory_id`; active overlay paths no longer require a project-only subcategory identifier.
- [ ] Historical ledger rows keep readable subcategory context after the overlay taxonomy migration.
- [ ] Isolated project subcategory behavior remains available for isolated-project scope and is not silently changed by overlay inheritance work.
- [ ] Frontend project structure controls let users search/select eligible global subcategories for overlay projects and explain when a tag must first be added to the monthly budget.
- [ ] Backend tests cover global-tag linkage, missing monthly lane rejection, cross-user rejection, cross-category rejection, hard-block limit validation, and ledger compatibility.
- [ ] Frontend tests cover eligible tag selection, unavailable/missing tag copy, payload mapping, refreshed project details, and localized errors.

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

- [ ] Creating an overlay category reservation sums existing active overlay reservations for the same user, category, year, and month before saving.
- [ ] Updating an overlay category reservation excludes the current slice and validates the proposed new amount against the parent monthly limit.
- [ ] Creating or updating a reservation fails with a stable validation error when total reservations would exceed the parent monthly limit.
- [ ] Creating or updating a reservation fails when the selected parent budget month does not exist.
- [ ] Reservation validation is ownership-scoped and never counts another user's projects or budgets.
- [ ] Project subcategory reservations cannot exceed their matching global monthly subcategory lane after considering existing project reservations.
- [ ] Moving reservation amount between project categories validates that the target parent category has enough unreserved selected-month capacity.
- [ ] The UI shows available selected-month headroom while editing overlay project reservations.
- [ ] The UI prevents accidental overbooking before submit and still surfaces backend validation errors when another change races the user.
- [ ] Tests cover overlapping projects, same-category collisions, cross-category reallocation, subcategory overbooking, missing parent budget, ownership isolation, and concurrent-style stale headroom failures.

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

- [ ] Overlay project updates derive the old and new project month windows from user-local calendar months.
- [ ] Date edits cannot move the project start after the earliest linked project expense.
- [ ] Date edits cannot move the target end date before the latest linked project expense.
- [ ] Slices outside the new month window are removed only when their actual spent amount is zero.
- [ ] Slices outside the new month window with actual spent are preserved or the update is rejected with a stable validation error.
- [ ] Any slice migration or pruning runs transactionally with the project date update.
- [ ] Slice amounts are never reduced below actual spent for the same project, category/subcategory, and month.
- [ ] Project detail and budget month responses remain consistent immediately after a successful date update.
- [ ] The UI previews which selected-month reservations will remain, move, or be blocked before submitting date changes.
- [ ] API failures leave the project dates and reservation slices unchanged in local UI state.
- [ ] Backend tests cover narrowing, widening, moving, actual-spent guards, local month boundaries, and transaction rollback.
- [ ] Frontend tests cover preview copy, blocked edits, successful refresh, and localized validation messages.

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

- [ ] Budget cards show parent limit, total spent, total project reserved, and free general limit for the selected month.
- [ ] Budget card progress remains based on total spent versus parent monthly limit.
- [ ] Budget cards do not render stacked project progress bars.
- [ ] A parent category can remain visually healthy when project spending is over its local reservation but total parent spending is still within the parent monthly limit.
- [ ] Budget Details includes an Active Project Reservations section for the selected category/month.
- [ ] Budget Details lists each overlapping project reservation with project title, reserved amount, actual spent, remaining or over amount, and status.
- [ ] Multiple overlapping projects render as individual mini-bars without changing parent card progress math.
- [ ] Empty, loading, error, desktop, and mobile states are supported.
- [ ] User-facing copy uses spending permission and reservation language, not envelope cash language.
- [ ] Budget, project, and analytics queries are invalidated after reservation changes so the UI does not show stale free limit.
- [ ] Frontend tests cover card macro math, detail mini-bars, local project overspend with healthy parent category, empty states, mobile layout, and stale-query refresh.
- [ ] Frontend build passes.

### Blocked by

- Issue 1: Make Overlay Project Category Limits Month-Scoped
- Issue 3: Hard-Block Overlay Reservation Overbooking

---

## Issue 6: Build the Just-In-Time Overlay Project Creation Wizard

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G27 - Overlay UI Matrix & Creation Wizard](../../prd/g27-overlay-ui-matrix-wizard.md)

### What to build

Replace the overlay project creation flow with a just-in-time wizard that only asks the user to allocate the current active budget month. The user can choose project identity and dates, select parent categories, reserve current-month headroom, and optionally attach global subcategory lanes without being asked to invent future-month money.

Future month slices are created later when those months are actually planned.

### Acceptance criteria

- [ ] The overlay creation flow collects project title, description, start date, and target end date.
- [ ] The wizard lets the user choose parent categories for the overlay project scope.
- [ ] The allocation step renders inputs only for the current active budget month, even when project dates span future months.
- [ ] The allocation step fetches selected-month parent budget headroom and validates proposed reservations live.
- [ ] The wizard cannot submit reservations that exceed available selected-month parent-category headroom.
- [ ] The optional micro-structure step lets the user attach eligible global monthly subcategory lanes to the overlay project.
- [ ] If a needed global subcategory lane is missing from the selected budget month, the wizard routes the user to create or attach it through the Budget Workspace taxonomy flow.
- [ ] The final review explains the current-month reservations that will be created and states that future months will be allocated when those months are set up.
- [ ] Submitting the wizard creates the overlay project and its current-month category/subcategory slices transactionally or leaves no partial project behind.
- [ ] Successful creation refreshes projects, budgets, budget details, dashboard summaries, and analytics as applicable.
- [ ] API failures preserve draft input and show localized actionable errors.
- [ ] Tests prove future months are not rendered, current-month headroom validation works, optional subcategory attachment maps to global tags, and successful submit creates the expected reservation slices.
- [ ] Frontend build passes.

### Blocked by

- Issue 2: Enforce Overlay Subcategory Inheritance from the Global Taxonomy
- Issue 3: Hard-Block Overlay Reservation Overbooking
- Issue 5: Render Overlay Reservations in Budget Cards and Budget Details

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

## Issue 8: Enforce Pristine Deletion for Overlay Projects

**Type:** AFK

### Parent

[Epic 5 - Overlay Project Architecture](../../epics/epic-5-overlay-projects.md), [G26 - Overlay Ledger Integrity](../../prd/g26-overlay-ledger-integrity.md)

### What to build

Protect ledger history by allowing hard deletion only for pristine overlay projects. If an overlay project has no linked financial reality, deletion should release its reservation slices. If the project has any linked expenses or ledger activity, deletion must be blocked and the user should be guided to complete or wrap up the project instead.

### Acceptance criteria

- [ ] Overlay project deletion checks for linked financial events or entity-ledger rows before deleting.
- [ ] Pristine overlay projects can be hard-deleted.
- [ ] Hard-deleting a pristine overlay project removes its category and subcategory reservation slices.
- [ ] Hard-deleting a pristine overlay project refreshes parent budget reserved/free limit math immediately.
- [ ] Non-pristine overlay project deletion returns a stable forbidden error explaining that the project must be completed or wrapped up.
- [ ] Non-pristine deletion leaves the project, reservation slices, ledger rows, expenses, subcategory references, and reports unchanged.
- [ ] Delete actions in the UI are enabled only for pristine overlay projects.
- [ ] Non-pristine overlay project UI shows a disabled delete action with an explanation and a route to wrap up/complete.
- [ ] Successful delete refreshes projects, budgets, budget details, dashboard summaries, and analytics as applicable.
- [ ] Backend tests cover pristine delete, non-pristine blocked delete, reservation release, ownership isolation, and no ledger orphaning.
- [ ] Frontend tests cover delete action visibility, disabled reason, confirmation, success refresh, and API error handling.

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

- [ ] Completing an overlay project computes actual spent by project, category/subcategory, year, and month.
- [ ] Current and future category reservation slices are reduced to actual spent for the matching slice.
- [ ] Current and future subcategory reservation slices are reduced to actual spent for the matching global subcategory slice.
- [ ] Completely unspent current/future slices are reduced to zero or removed according to the chosen persistence convention.
- [ ] Past month slices are not swept or rewritten during completion.
- [ ] Sweep math treats refunds as reductions to actual spent where the ledger already represents a refund against the project.
- [ ] Completion cannot set a completion date before linked project activity.
- [ ] Completing the project marks it completed and prevents further ordinary reservation edits.
- [ ] The parent budget's reserved amount and free general limit update immediately after sweep.
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
