# Epic 6 Issues: Isolated Projects & YNAB Envelopes

Parent: [Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Epic 5 Overlay Projects, especially typology decoupling, and Epic 3 Taxonomy Hub completion

## Freeze Notice

Epic 6 isolated-project work is frozen by [ADR 0022](../../adr/0022-freeze-isolated-projects-and-fund-project.md).

Do not treat the issues in this file as active execution targets until the feature is revisited. The future decision must either remove Isolated Projects/Fund Project or promote Isolated Projects into a first-class protected-stash ledger.

## Issue 1: Create Isolated Projects from Wallet-Backed Funding

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G34 - Decouple Overlay and Isolated Project Typology](../../prd/g34-project-typology-decoupling.md)

### What to build

Create the first complete isolated-project path around explicit wallet-backed funding. A user should choose the isolated project path from the Budgets page, enter project identity and target end date, allocate real available money from one or more wallets, and receive an isolated project whose total stash is derived only from those wallet allocation rows.

This is the foundation slice for EC-170 and EC-171: no fake "ghost goal" may be created for direct isolated projects, and the app must not ask for a typed target amount that can diverge from real locked funding.

### Acceptance criteria

- [x] Isolated project funding is stored in a dedicated wallet-allocation structure keyed by project, wallet, and amount.
- [x] A project cannot have duplicate wallet-allocation rows for the same wallet.
- [x] Wallet allocations are ownership-scoped and cannot reference another user's wallets or projects.
- [x] The isolated project total stash is derived as the sum of active wallet allocations; no direct target-amount field is accepted as operational funding for the G28 path.
- [ ] Existing isolated projects are migrated deterministically so they keep stable project ids and remain readable after the funding contract is introduced.
- [x] The backend create path accepts project identity, target end date, note/description, and wallet allocations for an isolated project.
- [x] The backend validates each wallet's free-to-allocate amount after protected goals and existing project locks.
- [x] Creating an isolated project fails with a stable validation error when requested allocations exceed wallet availability or global Free Money Now.
- [x] Project creation and wallet allocation persistence run transactionally or leave no partial project behind.
- [x] Project list and detail responses expose derived isolated funding totals and wallet-allocation rows without forcing isolated projects through overlay reservation rows.
- [x] The Budgets screen Create Project action opens a typology chooser with clear Overlay and Isolated choices.
- [x] The Overlay choice preserves the existing overlay creation path.
- [x] The Isolated choice opens the direct isolated identity and wallet-allocation flow.
- [x] The isolated wizard shows wallet balance, protected amount, free-to-allocate amount, entered allocation, and derived total stash.
- [ ] The target end date default and validation use the user's effective timezone.
- [x] UI copy uses funding, allocation, stash, and locked/free-money language instead of overlay reservation language.
- [ ] Backend tests cover migration safety, ownership isolation, derived stash math, insufficient free money, transaction rollback, and no ghost goal creation.
- [ ] Frontend tests cover typology selection, wallet allocation totals, disabled/blocked over-allocation, preserved overlay routing, and localized errors.
- [x] Docker verification passes for migration, focused backend tests, and frontend build.

### Blocked by

None - can start immediately after the epic prerequisites are satisfied.

---

## Issue 2: Allocate Isolated Stash into Project Parent Categories

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md)

### What to build

Add the next end-to-end wizard slice: after wallet quarantine, the user distributes the derived isolated stash across global parent categories such as Food, Transport, Home, or Entertainment. These category allocations are project-local funding buckets that roll up to global analytics, not monthly budget reservations and not wallet-to-category mappings.

The project should behave as a pooled vault: wallets fund the total stash, parent categories draw from that total stash, and categories are never tied to individual wallets.

### Architecture checkpoint

- [x] Isolated parent-category allocations use dedicated isolated-project storage separate from monthly budget and overlay reservation tables; they may reference the global parent category enum for unified reporting, but must not share overlay/monthly reservation rows.
- [ ] The Issue 2 storage boundary preserves a clean path for Issue 3 micro-subcategories: isolated micro-subcategory allocations should reference global taxonomy records from dedicated isolated-project allocation mechanics, not overlay subcategory monthly reservation rows or isolated-only free-text labels.

### Acceptance criteria

- [x] Isolated projects can store project-local parent category funding allocations.
- [x] Parent category allocations can use only valid global parent categories supported by the app.
- [x] Creating or updating isolated category allocations never creates overlay month-scoped reservation rows.
- [x] The sum of isolated parent category allocations cannot exceed the derived project stash unless the user goes through a top-up flow.
- [x] The backend exposes allocated, unallocated, spent, and remaining funding by parent category for isolated projects.
- [x] Project creation can persist wallet allocations and parent category allocations in one transaction.
- [x] Updating category allocations after creation is blocked for completed or archived projects.
- [x] Reducing a category allocation below actual linked project spending is rejected with a stable validation error.
- [x] The isolated wizard renders the parent-category allocation step after wallet quarantine and before micro-structure.
- [x] The wizard displays derived total stash, allocated amount, and unallocated amount while the user edits category rows.
- [x] The wizard prevents submit while category allocations exceed the derived stash.
- [x] Project detail renders isolated category funding with funding/spent/remaining language.
- [x] Budget month responses do not treat isolated category funding as monthly spending permission or overlay reserved scope.
- [ ] Backend tests cover category allocation creation, update guards, over-allocation rejection, completed/archived read-only behavior, analytics rollup data, and no overlay reservation leakage.
- [ ] Frontend tests cover category selection, allocation math, over-allocation UI, project detail display, and stale-query refresh after updates.
- [x] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 1: Create Isolated Projects from Wallet-Backed Funding

---

## Issue 2.5: Refactor Project Money Mechanics into Overlay Reservations and Isolated Allocations

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G35 - Project Money Mechanics Architecture Refactor](../../prd/g35-project-money-mechanics-refactor.md), [G36 - Complete Project Money Mechanics Separation](../../prd/g36-complete-project-money-mechanics-separation.md), [G34 - Decouple Overlay and Isolated Project Typology](../../prd/g34-project-typology-decoupling.md)

### What to build

Refactor the Projects architecture so the codebase clearly separates Overlay Project reservation mechanics from Isolated Project allocation mechanics before isolated micro-subcategories are implemented.

The completed slice should preserve the shared project identity and all existing user behavior, while making the type-specific money mechanics explicit in storage names, service boundaries, schemas, API responses, frontend state names, and tests. Overlay rows should speak reservation language because they reserve monthly budget permission. Isolated rows should speak allocation/funding language because they divide a locked project stash.

### Architecture checkpoint

- [x] The shared project identity remains the stable owner/title/status/date/lifecycle shell used by expenses, ledger rows, reports, and project lists.
- [x] Overlay project mechanics use explicit overlay reservation storage and service names for month-scoped category and subcategory budget reservations.
- [x] Isolated project mechanics use explicit isolated allocation storage and service names for wallet funding and parent category stash allocations.
- [x] The forward path for Issue 3 isolated micro-subcategories is explicit: taxonomy-governed isolated allocation mechanics, not overlay monthly reservation rows and not isolated-only free-text labels.

### Acceptance criteria

- [x] Existing project ids, statuses, dates, owner references, and ledger references are preserved through the refactor.
- [x] Existing overlay category reservation data is migrated or renamed into overlay-specific reservation storage without changing selected-month budget behavior.
- [x] Existing overlay subcategory reservation data is migrated or renamed into overlay-specific reservation storage without changing selected-month budget behavior.
- [x] Existing isolated wallet allocation data is migrated or renamed into isolated-specific wallet allocation storage without changing derived stash totals.
- [x] Existing isolated parent category allocation data is migrated or renamed into isolated-specific category allocation storage without changing allocated, unallocated, spent, or remaining funding totals.
- [x] Historical project subcategory references remain readable after the refactor, even if legacy project-local subcategory data is not the forward Issue 3 model.
- [x] Backend service boundaries distinguish overlay reservation validation from isolated allocation validation.
- [x] API response contracts and schema names expose overlay reserved amounts separately from isolated allocated amounts.
- [ ] Frontend state, helper, and display names distinguish overlay reservation rows from isolated allocation rows.
- [x] Overlay project creation, edit, completion, deletion, and budget-month summary behavior remain unchanged from the user's perspective.
- [x] Isolated project creation, parent category allocation, wallet funding, project detail, and budget isolation behavior remain unchanged from the user's perspective.
- [x] Isolated allocations do not create or read overlay month-scoped reservation rows.
- [x] Overlay reservations do not create or read isolated stash allocation rows.
- [x] Issue 3 can add isolated micro-subcategory allocations by referencing taxonomy records and isolated allocation mechanics without depending on overlay reservation tables.
- [ ] Migration tests cover row preservation, project id stability, ledger readability, overlay reservation behavior, and isolated allocation behavior.
- [x] Backend tests cover no behavior regression for overlay budget reserved scope, isolated funding summaries, read-only completed/archived guards, and no cross-type leakage.
- [x] Frontend tests cover overlay reservation naming/math and isolated allocation naming/math in the wizard/detail helper seams.
- [x] Docker verification passes for migration, focused backend tests, focused frontend tests, and frontend build.

### Extra completion checkpoints from G36

These checkpoints clarify the intended finish line. Because this project is not in production and development data does not need to be preserved, the agent should prefer clean deletion/replacement over long-lived compatibility shims.

- [x] `project_service.py` no longer owns both full financial models; shared behavior is extracted into a common project service, Overlay Project reservation logic lives in an overlay-specific service, and Isolated Project allocation logic lives in an isolated-specific service.
- [x] Old SQLAlchemy compatibility aliases are removed, including `ProjectWalletAllocation`, `ProjectCategoryLimit`, `ProjectCategoryMonthlyLimit`, and `ProjectSubcategoryMonthlyLimit`.
- [x] Old generic project relationships are removed or renamed at call sites, including generic `category_limits`, `monthly_category_limits`, `monthly_subcategory_limits`, and `wallet_allocations` relationship accessors.
- [x] New code cannot import or instantiate the old mixed project money-mechanics names.
- [ ] Overlay Project code uses reservation language end to end: route/function names, request schemas, response schemas, frontend helper state, tests, and table/model names.
- [ ] Isolated Project code uses allocation/funding language end to end: route/function names, request schemas, response schemas, frontend helper state, tests, and table/model names.
- [ ] Overlay-specific contracts use `reserved_amount` as the canonical money field instead of `limit_amount`.
- [ ] Isolated-specific contracts use `allocated_amount` as the canonical money field instead of `limit_amount`.
- [ ] If any backward-compatible `limit_amount` field remains during the transition, it is explicitly temporary and not used by new frontend code or new tests as the canonical field.
- [x] The old table names are not present after migration: `project_wallet_allocations`, `project_category_limits`, `project_category_monthly_limits`, and `project_subcategory_monthly_limits`.
- [x] `ProjectSubcategory` / `project_subcategories` is removed as the forward isolated micro-subcategory model.
- [x] If `project_subcategories` is temporarily kept only to unblock a narrow compile path, it is renamed/documented as legacy-only, no active creation route writes to it, and Issue 3 is blocked until it is replaced.
- [x] The forward Issue 3 model is explicit: `isolated_project_subcategory_allocations` should reference the shared project, parent category allocation/category, taxonomy/user subcategory record, allocated amount, active/archive state, and timestamps.
- [ ] Entity ledger, draft, debt, and payment-plan project micro-subcategory references are planned or migrated toward the new isolated project subcategory allocation model rather than the legacy project-local subcategory table.
- [ ] Generic `/category-limits` and `/subcategories` internals no longer contain mixed overlay/isolated financial branching unless they are thin backward-compatible wrappers delegating immediately to type-specific services.
- [x] Architecture guard tests fail if old model aliases or old table names are reintroduced.
- [x] Backend behavior tests prove overlay reservation math still works after service extraction.
- [x] Backend behavior tests prove isolated wallet and category allocation math still works after service extraction.
- [x] Frontend tests prove overlay helpers emit reservation payloads and isolated helpers emit allocation payloads.
- [x] Docker verification passes after the cleanup: migrations, focused backend tests, focused frontend tests, and frontend build.

### Blocked by

- Issue 2: Allocate Isolated Stash into Project Parent Categories

---

## Issue 3: Add Taxonomy-Governed Isolated Micro-Subcategories

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G35 - Project Money Mechanics Architecture Refactor](../../prd/g35-project-money-mechanics-refactor.md), [G21 - Subcategory Taxonomy Hub](../../prd/g21-subcategory-taxonomy-hub.md)

### What to build

### What to build

Let isolated projects optionally break parent category funding into project-specific micro subcategories, while still using the G21 Taxonomy Hub as the controlled naming and selection surface. A user can create or link one-off project tags such as "Drywall" or "Wedding DJ" without fragmenting free-text labels across the ledger.

The completed slice should preserve the distinction from overlay projects: overlay subcategories inherit monthly global budget lanes, while isolated micro-subcategories are funding breakdowns inside one isolated stash.

### Acceptance criteria

- [x] Isolated project micro-subcategories are created or linked through the Taxonomy Hub combobox flow, not raw ad hoc strings.
- [x] A project micro-subcategory belongs to exactly one isolated project and one parent category allocation.
- [x] Creating or updating a micro-subcategory requires the authenticated user to own the project and any linked taxonomy record.
- [x] A micro-subcategory cannot be attached to a parent category that is not allocated inside the isolated project.
- [x] Micro-subcategory funding cannot exceed the remaining parent category funding after other active micro-subcategories are counted.
- [x] Reducing a micro-subcategory below actual linked spending is rejected with a stable validation error.
- [x] Archiving or deactivating a micro-subcategory keeps historical expenses readable.
- [x] Overlay projects remain blocked from creating custom project-local subcategories through this flow.
- [x] The isolated wizard includes an optional micro-structure step after parent category allocation.
- [x] The UI supports creating or selecting taxonomy-governed micro-subcategories, assigning funding, editing, deleting safe pristine rows, and showing blocked states for rows with history.
- [x] Expense category selectors can load isolated project micro-subcategories for eligible isolated project expenses.
- [x] Backend tests cover taxonomy ownership, category mismatch rejection, over-allocation, historical readability, overlay blocking, and completed/archived project read-only behavior.
- [ ] Frontend tests cover combobox selection/create, allocation math, empty states, edit/delete guards, localized errors, and expense selector integration.
- [x] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 2.5: Refactor Project Money Mechanics into Overlay Reservations and Isolated Allocations

---

## Issue 4: Post Isolated Project Expenses Through the Pooled Vault

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G23 - Project Completion & Wrap-Up](../../prd/g23-project-completion-and-wrap-up.md)

### What to build

Wire isolated project expense posting to the pooled-vault model. A user should be able to record a real expense against an isolated project category or micro-subcategory and pay from any wallet that is eligible for the project, without the system pretending that a specific wallet funds a specific category.

The expense should bypass normal monthly budget reservation math, remain categorized for global analytics, and preserve the reality-first ledger model while requiring explicit repair when internal project funding would be exceeded.

### Acceptance criteria

- [ ] Expense creation and session finalization can tag expenses to an isolated project, parent category allocation, and optional micro-subcategory.
- [ ] Isolated project expense posting does not require or create a monthly budget row before saving the project-linked expense.
- [ ] Isolated project expenses are paid from real user wallets through the ordinary wallet ledger path.
- [ ] Any wallet eligible for the user and project can pay an isolated project expense; there is no wallet-to-category mapping.
- [ ] The backend computes isolated project spent and remaining funding by total stash, parent category, and micro-subcategory from posted ledger truth.
- [ ] Posting against a completed or archived isolated project is rejected.
- [ ] Expense posting remains allowed through the full target end date in the user's effective timezone.
- [ ] Expenses after the target end date are blocked unless the project is reopened or extended through the supported project lifecycle flow.
- [ ] An expense that would exceed an internal category or micro-subcategory allocation returns a stable resolution error that can drive rebalance or top-up UX.
- [ ] Isolated project spending can still roll up into global category analytics without reducing overlay reserved scope or monthly budget permission.
- [ ] Refunds or void/reversal flows reduce isolated project spent totals according to existing immutable ledger mechanics.
- [ ] Expense details and lists show isolated project context and micro-subcategory context where present.
- [ ] Backend tests cover pooled wallet payment, no monthly-budget requirement, category and subcategory overrun errors, inclusive target-end-date behavior, timezone boundaries, refunds/reversals, and ownership isolation.
- [ ] Frontend tests cover isolated project expense selection, micro-subcategory selection, resolution error display, refresh of project funding summaries, and localized errors.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 2: Allocate Isolated Stash into Project Parent Categories
- Issue 3: Add Taxonomy-Governed Isolated Micro-Subcategories

---

## Issue 5: Support Project Top-Ups Into Unassigned Stash and Internal Allocation

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G37 - Isolated Project Top-Ups and Unassigned Allocation](../../prd/g37-isolated-project-topups-and-unassigned-allocation.md)

### What to build

Give users the repair tools needed when an isolated project changes in real life. A user should be able to top up an active isolated project from one or more eligible wallets, with the new funding landing in unassigned project stash first. From there, the user can deliberately allocate unassigned project money into parent categories and micro-subcategories, or rebalance already-assigned project funding without touching wallet balances.

This keeps isolated projects strict without making top-up perform a hidden category decision. Unassigned project money increases total project funding, but it cannot be spent directly because isolated project expenses still require allocated category or micro-subcategory funding.

### Acceptance criteria

- [x] The backend exposes a project top-up action for active isolated projects.
- [x] A top-up can accept one or more funding wallets owned by the user.
- [x] Each top-up wallet amount must be available to allocate after existing wallet locks and protected money are considered.
- [x] Top-ups fail with stable validation errors when they exceed wallet free-to-allocate money or global Free Money Now.
- [x] Top-ups create or increase isolated project wallet-allocation rows as the source-of-truth lock for new funding.
- [x] Top-ups increase the derived total project stash and unassigned project funding without directly changing parent category or micro-subcategory allocations.
- [x] Project details expose total stash, assigned funding, unassigned funding, spent, remaining funding, category availability, and micro-subcategory availability.
- [x] The backend exposes an allocation action that assigns unassigned project funding into parent categories.
- [x] The backend exposes an allocation action that assigns available parent-category room into micro-subcategories.
- [x] Allocation cannot make assigned parent-category funding exceed the derived total project stash.
- [x] Micro-subcategory allocation cannot make assigned micro-subcategory funding exceed its parent category allocation.
- [x] The backend exposes an internal rebalance action that moves already-assigned funding between parent categories or between micro-subcategories without changing project wallet allocations.
- [x] Rebalancing cannot reduce any source category or micro-subcategory below actual non-voided spending already posted against it.
- [x] Isolated project expenses cannot spend directly from unassigned project funding; the selected parent category and optional micro-subcategory must have enough allocated availability.
- [x] Stable resolution errors distinguish "top up project", "assign unassigned funding", and "rebalance existing funding" repair paths.
- [x] Top-up, allocation, and rebalance actions are blocked for completed or archived isolated projects.
- [ ] Project details show top-up, allocation, and rebalance actions near isolated funding summaries, with live before/after totals.
- [ ] Resolution UX from isolated expense overruns can route the user into top-up, allocation, or rebalance and then retry or continue the original workflow.
- [ ] Backend tests cover multi-wallet top-up, wallet availability, ownership isolation, global Free Money Now guards, derived unassigned funding, allocation guards, micro-subcategory guards, unassigned-spend blocking, transaction rollback, rebalance guards, and completed/archived blocking.
- [ ] Frontend tests cover top-up/allocation/rebalance forms, before/after previews, unassigned-money guidance, over-allocation errors, resolution flow handoff, cache invalidation, mobile layout, and localized errors.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 3: Add Taxonomy-Governed Isolated Micro-Subcategories
- Issue 4: Post Isolated Project Expenses Through the Pooled Vault

---

## Issue 6: Graduate Fund Project Goals into Isolated Projects Without Double Funding

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G7 - Projects and Goal Deployment](../../prd/g7-projects-and-goal-deployment.md), [G38 - Fund Project Intent Guards and Graduation Baton Pass](../../prd/g38-fund-project-intent-guards-and-graduation-baton-pass.md)

### What to build

Make FUND_PROJECT goal graduation create isolated projects through the same wallet-backed funding model as direct isolated projects. When a goal becomes a project, the goal should be frozen as the saving-phase record, its released funding should become project wallet allocations, and all future increases should happen through project top-ups rather than reopened goal contributions.

This prevents EC-171's premature graduation double-funding trap and keeps Goal vs Project language clean.

### Acceptance criteria

- [x] Graduating a FUND_PROJECT goal creates an isolated project with stable references back to the origin goal.
- [x] The graduated project receives wallet-allocation rows that match the goal's released locked funding.
- [x] The origin goal is moved to its terminal graduated state and cannot accept new contributions, withdrawals, or funding edits.
- [x] Future funding increases for the project use the isolated project top-up action, not the origin goal.
- [x] Partial or premature graduation records the released funded amount as the initial project stash without creating a fake fully-funded target.
- [x] Goal graduation does not create duplicate wallet locks or double-count protected money.
- [x] Project category and micro-subcategory allocation can be completed during graduation or immediately after using the isolated project funding flow.
- [x] Project and goal detail responses make the relationship explicit without requiring the project to behave like an active goal.
- [x] UI copy explains that the goal has become a project execution stash and future additions belong to the project.
- [x] Backend tests cover full graduation, partial graduation, wallet allocation transfer, frozen goal behavior, no double counting, ownership isolation, and transaction rollback.
- [ ] Frontend tests cover the graduation flow, project funding setup continuation, frozen-goal copy, and project top-up routing.
- [x] Docker verification passes for focused backend tests and frontend build.

### Additional acceptance checkpoints from G38

- [x] `FUND_PROJECT` is the only goal intent allowed to use the graduation route; non-Fund intents are rejected with a stable validation error.
- [x] `FUND_PROJECT` goals cannot enter `COMPLETED` through any public goal mutation path; their terminal saving-phase lifecycle is `GRADUATED` or `ARCHIVED`.
- [x] A Fund Project goal remains stored as `ACTIVE` when its target date passes unless the user explicitly graduates or archives it.
- [x] Time-derived "past target date" or similar warning state for a Fund Project goal is derived at read time and does not mutate stored database lifecycle state.
- [x] A passed target date does not block Fund Project graduation.
- [x] After graduation, any goal allocation, return, consume, or equivalent saving-phase mutation route rejects further writes against the graduated goal.
- [x] Goal and project detail responses expose enough relationship data and copy hooks for the UI to explain the baton pass from goal incubator to project execution stash.
- [x] After graduation, the UI routes future funding additions toward isolated project top-up rather than reopening the origin goal flow.

### Blocked by

- Issue 1: Create Isolated Projects from Wallet-Backed Funding
- Issue 5: Support Project Top-Ups Into Unassigned Stash and Internal Allocation

---

## Issue 7: Redesign Isolated Project Cards and Action Menu Around Spend-Down Funding

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G23 - Project Completion & Wrap-Up](../../prd/g23-project-completion-and-wrap-up.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md)

### What to build

Redesign isolated project cards so they communicate the core mini-YNAB mental model at a glance: an isolated project is a protected stash of real wallet-backed funding that spends down over time. The card should stay lightweight and hand deeper breakdowns to future detail/reporting work.

This issue is now card-first. It should make the isolated project card answer:

```text
How much protected project funding is left?
How much has been spent from the funded stash?
Does the project need a funding action?
What action can I take from the card menu?
```

Overlay project cards must continue to behave like monthly permission/limit cards, while isolated project cards invert the psychology: overlay bars fill up toward a limit; isolated bars tick down as remaining funding shrinks.

```text
Overlay Project

Monthly budget permission
        |
        v
Project reserves selected-month scope
        |
        v
Progress fills up as spending approaches the limit

Card language:
limit, reservation, selected-month headroom, reserved scope
```

```text
Isolated Project

Wallet-backed funding
        |
        v
Protected project stash
        |
        v
Internal project categories and micro-subcategories
        |
        v
Progress drains down as spending uses the stash

Card language:
funding, stash, spent, remaining funding, top-up, allocate, rebalance, sweep
```

Recommended active isolated card shape:

```text
+------------------------------------------------+
| Kitchen Renovation        [Isolated] [Active]  |
| Protected project stash                        |
|                                                |
| 300K UZS remaining                             |
| 200K spent of 500K funded                      |
|                                                |
| [remaining funding bar ticking down]           |
|                                                |
| Ends Jul 29, 2026          [View details]      |
+------------------------------------------------+
```

Recommended completed isolated card shape:

```text
+------------------------------------------------+
| PC Build               [Isolated] [Completed]  |
| Final project stash                            |
|                                                |
| 300K UZS remaining at completion               |
| 4.7M spent of 5M funded                        |
|                                                |
| [read-only completed funding bar]              |
|                                                |
| Completed Jul 30, 2026     [View report]       |
+------------------------------------------------+
```

### Action menu strategy

Expose isolated-project actions using isolated funding language. Actions that already have backend support should be wired when the frontend flow can safely collect the required payload. Actions that belong to the product direction but are not backend-complete yet may appear as disabled/placeholder action words only when that helps preserve the menu vocabulary for Issue 8 and future details/reporting work.

```text
Top-up
= add real wallet-backed money into the isolated project stash

Allocate
= move unassigned project funding into an internal parent category or micro-subcategory

Rebalance
= move already assigned project funding between internal project buckets

Manage structure
= maintain the category and micro-subcategory layout

Archive
= retire/hide the project without destroying financial history

Wrap up / sweep
= finish the project and return unused funding to Free Money, planned for Issue 8
```

Recommended isolated project action matrix:

```text
+------------------+------------------------------+-------------------------+
| Project state    | Enabled actions              | Disabled/future labels  |
+------------------+------------------------------+-------------------------+
| Active           | Edit properties              | View details            |
|                  | Add top-up                   | Wrap up and sweep       |
|                  | Allocate unassigned funding  | View funding report     |
|                  | Rebalance funding            |                         |
|                  | Manage structure             |                         |
|                  | Archive                      |                         |
+------------------+------------------------------+-------------------------+
| Active, no       | Edit properties              | Allocate unassigned     |
| unassigned funds | Add top-up                   | funding                 |
|                  | Rebalance funding            | Wrap up and sweep       |
|                  | Manage structure             | View details            |
|                  | Archive                      | View funding report     |
+------------------+------------------------------+-------------------------+
| Completed        | Reopen / restore             | View report             |
|                  | Archive                      | Wrap up and sweep       |
+------------------+------------------------------+-------------------------+
| Archived         | Restore                      | View report             |
+------------------+------------------------------+-------------------------+
```

Do not show ordinary Delete for isolated projects in this slice unless the backend explicitly supports isolated deletion semantics. Current isolated project history, wallet locks, expenses, and future sweep behavior need a more careful deletion policy than overlay projects.

### Out of scope for this slice

The previous Issue 7 scope included project details, dashboard summaries, analytics grouping, and full funding reports. Those remain important, but they are no longer the core mission of this issue. This slice should not build the details page yet. It should leave clean copy, menu labels, API helper seams, and card-state hooks for later detail/reporting slices.

### Acceptance criteria

- [x] Isolated project cards use funding, stash, spent, remaining funding, top-up, allocate, rebalance, and sweep language.
- [x] Overlay project cards continue to use limit, reservation, selected-month headroom, and reserved-scope language.
- [x] Isolated project card progress displays as a spend-down bar: the filled portion represents `remaining_funding / funding_limit`, not `spent / funding_limit`.
- [x] Overlay project progress continues to fill up using selected-month spent versus selected-month reserved scope.
- [x] The isolated card's hero metric is remaining funding; the secondary line is spent of funded.
- [x] The isolated card avoids details-page density: no wallet allocation rows, full category allocation tables, micro-subcategory tables, top-up history, ledger rows, or sweep previews on the card.
- [x] The isolated card can show compact action states such as unassigned funding, goal-graduated origin, ready-to-wrap placeholder, completed read-only, or archived read-only without turning the card into a report.
- [x] Active isolated project 3-dot actions include Edit properties, Add top-up, Allocate unassigned funding when applicable, Rebalance funding, Manage structure, and Archive where the backend route/flow is available.
- [x] Isolated project menu labels include the future product actions View details, Wrap up and sweep, and View funding report as disabled/placeholder actions only if the corresponding backend/UI flow is not implemented yet.
- [x] Completed isolated project cards remain readable but visibly read-only, with mutation actions hidden or disabled except supported restore/archive-style lifecycle actions.
- [x] Archived isolated project cards expose restore behavior and avoid ordinary edit/top-up/allocation/rebalance actions.
- [x] Ordinary Delete is hidden or disabled for isolated projects unless isolated-specific deletion semantics are implemented; overlay deletion behavior remains unchanged.
- [x] Dashboard and budget surfaces do not count isolated funding as overlay reserved scope or monthly budget permission.
- [x] The card handles direct isolated projects and goal-graduated isolated projects without double-counting origin goal funding.
- [x] Empty, loading, error, mobile, and desktop states are supported.
- [x] API responses expose enough type-specific data for the frontend to render card-level isolated reporting without inferring from nullable overlay fields.
- [x] Backend tests cover card-summary funding math, top-up math needed by the card, refund/reversal reductions that affect remaining funding, origin-goal relationships, and no overlay reservation leakage.
- [x] Frontend tests cover isolated card language, progress direction, action-menu visibility by status, disabled future action labels, hidden isolated delete behavior, mobile layout, and stale-query refresh after wired actions.
- [x] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 4: Post Isolated Project Expenses Through the Pooled Vault
- Issue 5: Support Project Top-Ups Into Unassigned Stash and Internal Allocation
- Issue 6: Graduate Fund Project Goals into Isolated Projects Without Double Funding

---

## Issue 8: Wrap Up Isolated Projects and Sweep Unused Funding

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G23 - Project Completion & Wrap-Up](../../prd/g23-project-completion-and-wrap-up.md)

### What to build

Turn isolated project completion into an intentional wrap-up workflow. The project should remain active through the full target end date, then surface a ready-to-wrap prompt. The wrap-up view should summarize planned funding versus actual spending and let the user sweep leftover isolated funding back to Free Money before marking the project completed.

This slice must preserve user agency: no automatic completion, no surprise lockout for receipt lag, and no trapped liquidity after the project is done.

### Acceptance criteria

- [x] The ready-to-wrap state is derived from active status plus target end date being past in the user's effective timezone.
- [x] Projects are not automatically completed or locked when the target end date passes.
- [x] Expense posting remains allowed through the full target end date in the user's effective timezone.
- [x] A wrap-up summary endpoint returns total locked funding, total top-ups, actual spent, remaining funding, overrun amount where applicable, top parent categories, top micro-subcategories, and burn-down data.
- [x] Wrap-up summary metrics are ownership-scoped and exclude voided or unrelated ledger activity.
- [ ] The isolated wrap-up modal renders planned funding, actual spending, remaining funding, heavy hitters, and burn-down data using isolated funding language.
- [ ] The final wrap-up step previews the amount of unused funding that will be swept back to Free Money.
- [x] Completing with sweep releases remaining locked project funding from wallet allocations without changing historical expense ledger truth.
- [x] Sweep math is balanced for direct isolated projects and goal-graduated isolated projects.
- [x] Completing an overrun project does not create phantom returned money; it clearly reports the overrun and completes without a positive sweep.
- [x] Completion marks the project completed, stores the user's local completion business date, and prevents further ordinary edits or expenses.
- [x] Completion and sweep run transactionally or leave the project active with funding locks unchanged.
- [x] Completed project details remain readable for historical reporting.
- [x] Backend tests cover derived ready-to-wrap state, inclusive target-end-date posting, summary metrics, direct sweep, goal-graduated sweep, overrun completion, transaction rollback, local completion date, and ownership isolation.
- [ ] Frontend tests cover prompt display, summary modal, sweep preview, confirmation, completed read-only state, mobile layout, API failure handling, and localized errors.
- [x] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 7: Render Isolated Project Spend-Down Reporting
