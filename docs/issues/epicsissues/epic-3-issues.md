# Epic 3 Issues: Budget Control & Taxonomy Hub

Parent: [Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Epic 2 completion

## Issue 1: Permit Over-Planned Budgets with Look-Ahead Warnings

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md)

### What to build

Adopt permissive overplanning for ordinary budget creation and limit increases. A user may save a spending-permission plan that exceeds current plan backing, while the Budget Workspace clearly warns that the proposed plan is over-planned and guides the user toward recording an Expected Inflow or repairing the plan.

The warning must preserve the reality-first distinction between a valid saved plan and a healthy backed plan: saving is allowed, but the shortfall remains visible and is never presented as covered money.

### Acceptance criteria

- [ ] Creating a budget succeeds when the resulting monthly budget total exceeds available plan backing.
- [ ] Increasing an existing budget succeeds when the resulting monthly budget total exceeds available plan backing.
- [ ] Existing validation for ownership, valid expense categories, duplicate budgets, valid month windows, and positive limits remains enforced.
- [ ] After an over-planned create or update, the month summary reports `over_planned` with the authoritative backing shortfall and cause data.
- [ ] The create and update forms show a prominent look-ahead warning when the proposed limit would exceed plan backing.
- [ ] The warning states that the user is planning more than they have, shows the shortfall, and offers a route to record an Expected Inflow.
- [ ] The warning does not disable or hide the save action; the user can deliberately save the mathematically unhealthy plan.
- [ ] Successful mutations refresh the budget list and month-summary state so the saved red state is immediately visible.
- [ ] Backend tests cover permissive creation and increases while proving unrelated validation still rejects invalid requests.
- [ ] Frontend tests cover warnings for both create and update flows and prove the user can continue without first adding an inflow.
- [ ] New user-facing warning copy is available in supported translations.

### Blocked by

None - can start immediately after the Epic 2 prerequisite is satisfied.

---

## Issue 2: Proactively Reallocate Parent-Category Limits

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G14 user stories 1-3

### What to build

Expose the existing parent-category reallocation capability directly in the Budget Workspace. A user reviewing one month can move available spending permission from a source parent category to a different target parent category before either category becomes overspent.

### Acceptance criteria

- [x] Parent budget cards expose a clear proactive Reallocate action on supported desktop and mobile layouts.
- [x] The reallocation flow selects source and target budgets from the same calendar month.
- [x] The source selector includes only budgets with available remaining permission.
- [x] The target cannot be the same category as the source.
- [x] The amount must be positive and cannot exceed the source budget's authoritative available amount.
- [x] Submission maps to the existing parent reallocation API contract with source category, target category, amount, year, and month.
- [x] A successful reallocation refreshes the affected budget cards, details, and month summary, including reallocated-in and reallocated-out values.
- [x] API failures leave the displayed limits unchanged and produce a localized actionable error.
- [x] Frontend tests cover action visibility, source/target rules, amount validation, payload mapping, successful refresh, and failure handling.
- [x] No new backend reallocation behavior is introduced by this slice.

### Blocked by

None - can start immediately after the Epic 2 prerequisite is satisfied.

---

## Issue 3: Remove a Monthly Subcategory Lane Without Deleting Its Tag

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G21 user story 2

### What to build

Align subcategory removal with the month-scoped domain model. Removing a subcategory from a selected budget month removes only that month's spending-permission lane. The global tag, linked ledger history, and limits in other months remain intact and available for later reuse.

### Acceptance criteria

- [x] Monthly subcategory removal identifies both the global subcategory and the selected parent budget context.
- [x] The backend validates that the budget and subcategory belong to the authenticated user and share the same parent category.
- [x] Removal deletes only the matching month-specific subcategory limit.
- [x] The global subcategory record is never deleted by the monthly budget removal route.
- [x] Existing financial events and ledger entries retain their subcategory reference and historical label.
- [x] Limits for the same tag in other budget months remain unchanged.
- [x] A tag with linked expenses can still be removed from the selected month's plan.
- [x] The Budget Workspace sends the selected budget context and stops presenting the removed tag as an assigned monthly lane.
- [x] The preserved tag remains available to reuse and remains visible wherever historical tags are intentionally shown.
- [x] Integration tests prove preservation of the tag, ledger history, and other months' limits.
- [x] Frontend tests prove that removal updates only the selected month's active plan.

### Blocked by

None - can start immediately after the Epic 2 prerequisite is satisfied.

---

## Issue 4: Search, Reuse, or Create Subcategories from the Budget Workspace

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G21 user story 1

### What to build

Replace free-form-only subcategory creation with a searchable choose-or-create flow. A user can find an existing active global tag that is not assigned to the selected month, attach it to that month's budget, or explicitly create a genuinely new tag without fragmenting taxonomy history.

### Acceptance criteria

- [x] The add-subcategory control searches reusable global tags for the selected parent category.
- [x] Tags already assigned to the selected budget month are clearly excluded or shown as unavailable.
- [x] Archived tags do not appear in the active budget selector.
- [x] Selecting an existing tag sends its identifier and creates only the month-specific limit; it does not create another global tag.
- [x] Explicitly creating a new tag sends its name and creates the global tag plus the selected month's limit.
- [x] If a submitted name matches an existing user tag in the same category, the backend reuses that tag instead of exposing a database integrity error.
- [x] A supplied existing tag identifier must belong to the authenticated user and the budget's parent category.
- [x] The existing rule that total subcategory limits cannot exceed the parent category limit remains enforced.
- [x] The combobox supports keyboard search, an empty state, and an explicit Create New choice.
- [x] Backend tests cover selecting an existing tag, duplicate-safe name handling, cross-user and cross-category rejection, and genuinely new tag creation.
- [x] Frontend tests distinguish Select Existing from Create New payloads and verify the refreshed monthly lane list.

### Blocked by

None - can start immediately after the Epic 2 prerequisite is satisfied.

---

## Issue 5: Browse the Subcategory Taxonomy Hub and Lifetime Scorecards

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G21 user stories 3-4

### What to build

Add a dedicated Subcategory Taxonomy Hub accessible as a tab or view directly within the Budgets workspace. The Hub lists every global subcategory owned by the user, groups tags by parent expense category, and presents lifetime usage facts that help the user understand and clean up their taxonomy.

### Acceptance criteria

- [x] The taxonomy API returns all global tags owned by the authenticated user, including archived tags.
- [x] Each tag includes its identifier, name, parent category, active state, creation metadata, first used date, last used date, transaction count, and lifetime spent.
- [x] Lifetime facts are derived from the user's relevant posted financial-event ledger history and exclude other users' or voided data.
- [x] Never-used tags return a stable empty scorecard rather than failing or disappearing.
- [x] Results have deterministic parent-category and tag ordering suitable for the UI.
- [x] The Budgets workspace exposes a clear tab or navigation toggle to switch between Monthly Plans and the Subcategory Taxonomy Hub.
- [x] The Hub groups tags by localized parent category and visibly distinguishes active and archived tags.
- [x] Each row renders the lifetime scorecard without recalculating ledger aggregates in the browser.
- [x] Loading, empty, error, desktop, and mobile states are supported.
- [x] Backend tests cover aggregate accuracy, never-used tags, archived tags, ownership isolation, and voided history.
- [x] Frontend tests cover grouping, scorecard rendering, active-state presentation, and empty/error states.
- [x] New user-facing copy is available in supported translations.

### Blocked by

None - can start immediately after the Epic 2 prerequisite is satisfied.

---

## Issue 6: Rename and Archive Taxonomy Tags

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G21 user stories 5 and 7

### What to build

Let users maintain global tags from the Taxonomy Hub without rewriting financial history. Renaming changes the shared label seen by past and future reports, while archiving removes a tag from active planning selectors but preserves its identity, ledger references, scorecard, and ability to be restored.

### Acceptance criteria

- [x] A dedicated taxonomy mutation updates a user-owned tag's name, active state, or both.
- [x] Renaming preserves the tag identifier and all linked ledger and monthly-limit records.
- [x] A rename that would collide with another tag in the same user/category taxonomy returns a stable validation error.
- [x] Archiving toggles active state and never hard-deletes the global tag or its history.
- [x] Archived tags remain visible in the Taxonomy Hub and can be restored.
- [x] Archived tags are excluded from active budget and expense selectors while existing historical records continue to display their label.
- [x] Renamed tags display their new name consistently in the Hub, budget lanes, expense history, and reports that resolve the shared tag.
- [x] The Hub exposes accessible rename, archive, and restore actions with confirmation where appropriate.
- [x] Successful mutations refresh taxonomy data and every active selector affected by the change.
- [x] Backend tests cover ownership, uniqueness, rename propagation, archive preservation, and restoration.
- [x] Frontend tests cover rename, archive, restore, selector refresh, and localized error handling.

### Blocked by

- Issue 4: Search, Reuse, or Create Subcategories from the Budget Workspace
- Issue 5: Browse the Subcategory Taxonomy Hub and Lifetime Scorecards

---

## Issue 7: Merge Duplicate Taxonomy Tags Transactionally

**Type:** AFK

### Parent

[Epic 3 - Budget Control & Taxonomy Hub](../../epics/epic-3-budget-control.md), G21 user story 6

### What to build

Add an explicit Taxonomy Hub merge flow for consolidating duplicate global tags. The user selects one surviving target and one or more source tags from the same parent category. The backend reassigns historical expense-ledger references to the target and removes the source tags as one atomic operation.

### Acceptance criteria

- `[x]` A merge request requires one surviving target and at least one distinct source tag.
- `[x]` The target and every source must belong to the authenticated user and the same parent expense category.
- `[x]` Duplicate source identifiers, a target included among its sources, cross-user tags, and cross-category merges are rejected before mutation.
- `[x]` Every historical Entity Ledger reference to a source tag is reassigned to the target tag.
- `[x]` Source global tags are deleted only after all ledger references have been reassigned successfully.
- `[x]` Source monthly-limit rows are removed with their deleted source tags; existing target monthly limits remain unchanged.
- `[x]` The merge runs in one database transaction and a failure at any point rolls back ledger reassignment and tag deletion.
- `[x]` After a merge, reports and the target's lifetime scorecard include the consolidated source history.
- `[x]` The Hub lets the user select duplicate sources, choose the surviving target, review the impact, and explicitly confirm the irreversible merge.
- `[x]` Successful merging refreshes the Hub, active selectors, budget details, and affected reporting queries.
- `[x]` Backend tests cover a successful multi-source merge, validation failures, ownership isolation, target-limit preservation, and forced transactional rollback.
- `[x]` Frontend tests cover selection rules, confirmation, payload mapping, refreshed consolidated results, and failure handling.

### Blocked by

- Issue 5: Browse the Subcategory Taxonomy Hub and Lifetime Scorecards
