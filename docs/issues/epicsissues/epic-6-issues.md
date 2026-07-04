# Epic 6 Issues: Isolated Projects & YNAB Envelopes

Parent: [Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Epic 5 Overlay Projects, especially typology decoupling, and Epic 3 Taxonomy Hub completion

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

## Issue 3: Add Taxonomy-Governed Isolated Micro-Subcategories

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G21 - Subcategory Taxonomy Hub](../../prd/g21-subcategory-taxonomy-hub.md)

### What to build

Let isolated projects optionally break parent category funding into project-specific micro subcategories, while still using the G21 Taxonomy Hub as the controlled naming and selection surface. A user can create or link one-off project tags such as "Drywall" or "Wedding DJ" without fragmenting free-text labels across the ledger.

The completed slice should preserve the distinction from overlay projects: overlay subcategories inherit monthly global budget lanes, while isolated micro-subcategories are funding breakdowns inside one isolated stash.

### Acceptance criteria

- [ ] Isolated project micro-subcategories are created or linked through the Taxonomy Hub combobox flow, not raw ad hoc strings.
- [ ] A project micro-subcategory belongs to exactly one isolated project and one parent category allocation.
- [ ] Creating or updating a micro-subcategory requires the authenticated user to own the project and any linked taxonomy record.
- [ ] A micro-subcategory cannot be attached to a parent category that is not allocated inside the isolated project.
- [ ] Micro-subcategory funding cannot exceed the remaining parent category funding after other active micro-subcategories are counted.
- [ ] Reducing a micro-subcategory below actual linked spending is rejected with a stable validation error.
- [ ] Archiving or deactivating a micro-subcategory keeps historical expenses readable.
- [ ] Overlay projects remain blocked from creating custom project-local subcategories through this flow.
- [ ] The isolated wizard includes an optional micro-structure step after parent category allocation.
- [ ] The UI supports creating or selecting taxonomy-governed micro-subcategories, assigning funding, editing, deleting safe pristine rows, and showing blocked states for rows with history.
- [ ] Expense category selectors can load isolated project micro-subcategories for eligible isolated project expenses.
- [ ] Backend tests cover taxonomy ownership, category mismatch rejection, over-allocation, historical readability, overlay blocking, and completed/archived project read-only behavior.
- [ ] Frontend tests cover combobox selection/create, allocation math, empty states, edit/delete guards, localized errors, and expense selector integration.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 2: Allocate Isolated Stash into Project Parent Categories

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

## Issue 5: Support Cascading Project Top-Ups and Internal Rebalancing

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md)

### What to build

Give users the repair tools needed when an isolated project changes in real life. A user should be able to top up project funding from a selected wallet and have the money flow through the proper cascade: wallet lock, total project stash, parent category, and optional micro-subcategory. They should also be able to rebalance already-locked project funding between categories or micro-subcategories without touching wallet balances.

This keeps isolated projects strict without trapping users when contractor prices, travel costs, or event needs change.

### Acceptance criteria

- [ ] The backend exposes a cascading top-up action for active isolated projects.
- [ ] A top-up requires a funding wallet owned by the user and an amount that is available to allocate.
- [ ] A top-up can target the project stash only, a parent category allocation, or a micro-subcategory allocation.
- [ ] A targeted micro-subcategory top-up also increases the matching parent category allocation and total project stash in the same transaction.
- [ ] A targeted parent category top-up also increases the total project stash in the same transaction.
- [ ] Project wallet-allocation rows are created or increased as the source-of-truth lock for new top-up funding.
- [ ] Top-ups fail with stable validation errors when they exceed wallet free-to-allocate money or global Free Money Now.
- [ ] The backend exposes an internal rebalance action that moves already-locked funding between project categories or micro-subcategories without changing project wallet allocations.
- [ ] Rebalancing cannot make any source category or micro-subcategory negative after actual spending is considered.
- [ ] Top-up and rebalance actions are blocked for completed or archived isolated projects.
- [ ] Project details show top-up and rebalance actions near isolated funding summaries, with live before/after totals.
- [ ] Resolution UX from isolated expense overruns can route the user into top-up or rebalance and then retry or continue the original workflow.
- [ ] Backend tests cover stash-only top-up, category top-up, micro-subcategory cascade, wallet availability, ownership isolation, transaction rollback, rebalance guards, and completed/archived blocking.
- [ ] Frontend tests cover top-up/rebalance forms, before/after previews, over-allocation errors, resolution flow handoff, cache invalidation, and localized errors.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 3: Add Taxonomy-Governed Isolated Micro-Subcategories
- Issue 4: Post Isolated Project Expenses Through the Pooled Vault

---

## Issue 6: Graduate Fund Project Goals into Isolated Projects Without Double Funding

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md), [G7 - Projects and Goal Deployment](../../prd/g7-projects-and-goal-deployment.md)

### What to build

Make FUND_PROJECT goal graduation create isolated projects through the same wallet-backed funding model as direct isolated projects. When a goal becomes a project, the goal should be frozen as the saving-phase record, its released funding should become project wallet allocations, and all future increases should happen through project top-ups rather than reopened goal contributions.

This prevents EC-171's premature graduation double-funding trap and keeps Goal vs Project language clean.

### Acceptance criteria

- [ ] Graduating a FUND_PROJECT goal creates an isolated project with stable references back to the origin goal.
- [ ] The graduated project receives wallet-allocation rows that match the goal's released locked funding.
- [ ] The origin goal is moved to its terminal graduated state and cannot accept new contributions, withdrawals, or funding edits.
- [ ] Future funding increases for the project use the isolated project top-up action, not the origin goal.
- [ ] Partial or premature graduation records the released funded amount as the initial project stash without creating a fake fully-funded target.
- [ ] Goal graduation does not create duplicate wallet locks or double-count protected money.
- [ ] Project category and micro-subcategory allocation can be completed during graduation or immediately after using the isolated project funding flow.
- [ ] Project and goal detail responses make the relationship explicit without requiring the project to behave like an active goal.
- [ ] UI copy explains that the goal has become a project execution stash and future additions belong to the project.
- [ ] Backend tests cover full graduation, partial graduation, wallet allocation transfer, frozen goal behavior, no double counting, ownership isolation, and transaction rollback.
- [ ] Frontend tests cover the graduation flow, project funding setup continuation, frozen-goal copy, and project top-up routing.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 1: Create Isolated Projects from Wallet-Backed Funding
- Issue 5: Support Cascading Project Top-Ups and Internal Rebalancing

---

## Issue 7: Render Isolated Project Spend-Down Reporting

**Type:** AFK

### Parent

[Epic 6 - Isolated Projects & YNAB Envelopes](../../epics/epic-6-isolated-projects.md), [G23 - Project Completion & Wrap-Up](../../prd/g23-project-completion-and-wrap-up.md), [G28 - Isolated Project Wizard](../../prd/g28-isolated-project-wizard.md)

### What to build

Make isolated project reporting feel like a dedicated stash being spent down. Budget cards, project cards, project details, dashboard summaries, and analytics should clearly distinguish isolated funding from overlay reservations, showing how much funding was locked, spent, remaining, topped up, or overrun.

The completed slice should make the mini-YNAB behavior visible without turning isolated project funding into monthly budget permission.

### Acceptance criteria

- [ ] Isolated project cards use funding, stash, spent, remaining funding, top-up, and sweep language.
- [ ] Overlay project cards continue to use limit, reservation, selected-month headroom, and reserved-scope language.
- [ ] Isolated project progress displays as a spend-down from available funding for the G28 wallet-backed funding path.
- [ ] Project details show wallet allocations, parent category allocations, micro-subcategory allocations, actual spending, remaining funding, and overrun states.
- [ ] Dashboard and budget surfaces do not count isolated funding as overlay reserved scope or monthly budget permission.
- [ ] Analytics can group isolated project spending by global parent category and taxonomy-governed micro-subcategory without losing the project context.
- [ ] Funding summaries include direct isolated projects and goal-graduated isolated projects without double counting origin goal funding.
- [ ] Empty, loading, error, mobile, and desktop states are supported.
- [ ] Completed isolated projects remain readable but visibly read-only.
- [ ] API responses expose enough type-specific data for the frontend to render isolated reporting without inferring from nullable overlay fields.
- [ ] Backend tests cover funding summary math, top-up math, refund/reversal reductions, origin-goal relationships, and no overlay reservation leakage.
- [ ] Frontend tests cover card language, progress direction, detail breakdowns, dashboard/budget isolation, analytics labels, mobile layout, and stale-query refresh.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 4: Post Isolated Project Expenses Through the Pooled Vault
- Issue 5: Support Cascading Project Top-Ups and Internal Rebalancing
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

- [ ] The ready-to-wrap state is derived from active status plus target end date being past in the user's effective timezone.
- [ ] Projects are not automatically completed or locked when the target end date passes.
- [ ] Expense posting remains allowed through the full target end date in the user's effective timezone.
- [ ] A wrap-up summary endpoint returns total locked funding, total top-ups, actual spent, remaining funding, overrun amount where applicable, top parent categories, top micro-subcategories, and burn-down data.
- [ ] Wrap-up summary metrics are ownership-scoped and exclude voided or unrelated ledger activity.
- [ ] The isolated wrap-up modal renders planned funding, actual spending, remaining funding, heavy hitters, and burn-down data using isolated funding language.
- [ ] The final wrap-up step previews the amount of unused funding that will be swept back to Free Money.
- [ ] Completing with sweep releases remaining locked project funding from wallet allocations without changing historical expense ledger truth.
- [ ] Sweep math is balanced for direct isolated projects and goal-graduated isolated projects.
- [ ] Completing an overrun project does not create phantom returned money; it clearly reports the overrun and completes without a positive sweep.
- [ ] Completion marks the project completed, stores the user's local completion business date, and prevents further ordinary edits or expenses.
- [ ] Completion and sweep run transactionally or leave the project active with funding locks unchanged.
- [ ] Completed project details remain readable for historical reporting.
- [ ] Backend tests cover derived ready-to-wrap state, inclusive target-end-date posting, summary metrics, direct sweep, goal-graduated sweep, overrun completion, transaction rollback, local completion date, and ownership isolation.
- [ ] Frontend tests cover prompt display, summary modal, sweep preview, confirmation, completed read-only state, mobile layout, API failure handling, and localized errors.
- [ ] Docker verification passes for focused backend tests and frontend build.

### Blocked by

- Issue 7: Render Isolated Project Spend-Down Reporting
