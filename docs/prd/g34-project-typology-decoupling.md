# PRD: G34 - Decouple Overlay and Isolated Project Typology

Labels: `ready-for-agent`, `architecture-note`

## Problem Statement

Sarflog currently uses one shared project shape for two project types that mean different financial things:

1. **Overlay projects** are limit-based budget lenses. They reserve part of a real monthly category limit, but they do not own money.
2. **Isolated projects** are closer to envelope budgeting. They use dedicated project funding or stash-like money, and spending drains that project funding.

When both project types share generic fields such as `total_limit` and a boolean type switch, the product becomes easy to misuse. Overlay projects can accidentally inherit envelope language, isolated projects can be dragged into overlay reservation math, and future work has to keep adding defensive conditionals instead of expressing the domain clearly.

This problem is highest-risk before the just-in-time overlay creation wizard because Issue 6 will make overlay creation, validation, copy, and API contracts user-facing. Building that wizard on the shared project model would lock more code into the wrong abstraction and force a later rewrite.

## Solution

Decouple project typology before finishing the JIT overlay wizard.

Sarflog should keep a shared project identity and lifecycle concept where it is truly common, but move type-specific financial meaning into type-specific structures and service boundaries.

The user-facing model should be:

- **Overlay project** = reserve monthly spending permission from parent budget categories.
- **Isolated project** = spend from dedicated project funding.

Overlay projects should never use project-wide total-limit behavior for operational spending permission. Isolated projects may keep project-wide funding and stash-like behavior, but that behavior must be isolated from overlay reservations.

## User Stories

1. As a budget user, I want overlay projects to reserve monthly spending permission, so that I do not confuse project tracking with physical money.
2. As a budget user, I want isolated projects to show dedicated project funding, so that I know what money is available for that project.
3. As a budget user, I want overlay project copy to use reservation and limit language, so that I understand the project is part of the monthly budget.
4. As a budget user, I want isolated project copy to use funding and stash language, so that I understand spending drains dedicated project money.
5. As a budget user, I want the project creation flow to choose the correct financial model up front, so that I do not accidentally create the wrong kind of project.
6. As an overlay project user, I want current-month category reservations to be the only operational budget permission created during project setup, so that future-month money is not invented.
7. As an overlay project user, I want target estimate to remain planning metadata, so that it does not behave like spendable permission.
8. As an isolated project user, I want project funding to remain separate from monthly category reservation math, so that my dedicated project money is not treated like a budget slice.
9. As a goal-funded project user, I want released goal funding to remain tied to isolated project behavior, so that goal releases do not become overlay reservations.
10. As an expense logger, I want project-linked expenses to keep pointing to one stable project identity, so that ledger history remains intact after typology decoupling.
11. As a budget reviewer, I want overlay spending to reduce the parent budget category's real remaining capacity, so that monthly budget truth stays accurate.
12. As a budget reviewer, I want isolated project spending to report against dedicated funding, so that it does not masquerade as overlay monthly permission.
13. As a user reviewing historical projects, I want old project reports to remain readable, so that migration does not erase prior context.
14. As a user editing a project, I want only fields relevant to that project type, so that overlay projects do not show isolated total-limit controls.
15. As a user editing an isolated project, I want funding fields to remain available where they are meaningful, so that isolated workflows do not lose useful behavior.
16. As a user editing an overlay project, I want reservation slices edited through overlay-specific controls, so that the system validates monthly headroom correctly.
17. As a user completing an overlay project, I want completion to reclaim unused current and future spending permission, so that parent budgets regain free limit.
18. As a user completing an isolated project, I want completion to respect dedicated project funding, so that leftover project money is handled as project funding, not budget reservation.
19. As a user deleting a pristine overlay project, I want its reservation slices released, so that parent budget math updates immediately.
20. As a user deleting a pristine isolated project, I want its dedicated funding behavior handled separately, so that overlay reservation cleanup does not run against it.
21. As a user with project expenses, I want deletion blocked when financial history exists, so that ledger history remains protected.
22. As a developer, I want overlay and isolated services separated, so that each service speaks one financial language.
23. As a developer, I want shared lifecycle helpers only for behavior that is genuinely common, so that the codebase does not hide financial differences behind generic helpers.
24. As a developer, I want schema constraints to prevent overlay projects from having isolated-only operational fields, so that invalid states cannot be silently stored.
25. As a developer, I want schema constraints to prevent isolated projects from requiring overlay reservation rows, so that isolated behavior stays independent.
26. As a developer, I want existing project identifiers preserved, so that expenses, entity ledger rows, goal releases, and reports do not need destructive rewrites.
27. As a developer, I want migration backfill to be deterministic, so that every existing project lands in exactly one type-specific detail structure.
28. As a developer, I want API responses to expose type-specific financial fields explicitly, so that frontend code does not infer meaning from nulls.
29. As a developer, I want frontend forms to be type-specific, so that future Issue 6 work does not depend on `is_isolated` branching inside one generic wizard.
30. As a tester, I want Docker/Postgres migration coverage for the decoupling, so that production schema changes are verified in the same environment the app uses.
31. As a tester, I want backend integration tests for both project types, so that overlay and isolated behavior cannot regress into each other.
32. As a tester, I want frontend build and focused UI tests, so that project cards and creation flows use the correct language.
33. As a support/debugging user, I want project type to be obvious in API data, so that confusing states can be diagnosed quickly.
34. As a product owner, I want Issue 6 blocked until typology is decoupled, so that the JIT overlay wizard is built on the final overlay model.
35. As a future maintainer, I want project terminology to match the money model, so that new features do not recreate total-limit confusion.

## Implementation Decisions

- Keep a shared project identity for ownership, title, description, lifecycle status, dates, and stable references from expenses and ledger rows.
- Replace the boolean-centered project model with an explicit project type concept that can be validated and queried without guessing from nullable fields.
- Move isolated-project financial meaning into an isolated-project detail structure. Isolated-only fields include project-wide total/funding concepts and any stash-like reporting fields.
- Move overlay-project metadata into an overlay-project detail structure. Overlay-only fields include target estimate and other planning context that does not create spending permission.
- Keep overlay operational truth in month-scoped category and subcategory reservation rows. Those rows remain the source of truth for budget pressure.
- Backfill existing projects deterministically: currently isolated projects receive isolated details, currently overlay projects receive overlay details, and existing ledger/project references keep the same shared project identity.
- Do not let overlay projects keep or accept isolated total-limit behavior after migration. If a historical overlay project has a legacy total-limit value, migrate it into non-operational planning metadata only when that preserves user intent; otherwise leave operational permission entirely in reservation rows.
- Do not let isolated projects require overlay monthly reservation rows. Isolated project reporting should not depend on budget reservation aggregation.
- Split project services by financial typology. Shared helpers should be limited to genuinely common lifecycle and ownership behavior.
- Split project creation/update contracts by typology. Overlay creation should speak reservations, monthly headroom, and target estimate. Isolated creation should speak dedicated funding and isolated project limits.
- Preserve a compatibility layer only where necessary for existing routes during the transition, but new Issue 6 work should call overlay-specific contracts.
- Update frontend project cards and edit flows so overlay and isolated cards do not share financial copy or controls.
- Treat project dates as user-facing business dates. Any date default or validation added during this work must use the user's effective timezone.
- Verify migrations and tests inside Docker against Postgres, because this is a schema and ledger-history-sensitive change.

## Testing Decisions

- Good tests should exercise public behavior: API requests, response contracts, migrated data, and rendered user-facing project language. They should not assert private helper structure.
- Add migration tests that prove existing isolated and overlay projects backfill into the correct type-specific structures without changing project ids or ledger references.
- Add backend integration tests that prove overlay projects cannot receive isolated total-limit behavior and isolated projects are not forced through overlay reservation math.
- Add backend tests that prove overlay project summaries still derive operational permission from month-scoped reservation rows.
- Add backend tests that prove isolated project summaries still derive funding/stash behavior from isolated project data and goal release facts where applicable.
- Add ownership tests for both project types so one user cannot read or mutate another user's project details.
- Add date-boundary tests where project dates affect behavior, using explicit `X-Timezone` headers and existing timezone test helpers.
- Add frontend tests for project card copy: overlay cards use reservation/limit language, isolated cards use funding/stash language.
- Add frontend tests for project creation entry points so the JIT overlay wizard does not expose isolated total-limit controls.
- Run Docker verification: migrations, focused backend tests, and frontend build.

## Out of Scope

- Redesigning the entire project lifecycle.
- Changing the meaning of existing overlay monthly reservation rows.
- Turning overlay projects into cash envelopes.
- Turning isolated projects into monthly budget reservations.
- Rewriting historical ledger events beyond the minimum references needed for typology-safe reporting.
- Implementing the full JIT overlay creation wizard; this PRD creates the architecture it should use.
- Implementing new-month overlay allocation prompts; those remain later Epic 5 work.
- Implementing project deletion, completion, and wrap-up policy changes beyond preserving type-specific behavior.

## Further Notes

This decoupling is not polish. It protects the core product language:

- Overlay project: "I reserved part of this month's spending permission."
- Isolated project: "I have dedicated project funding to spend down."

The shared project table can remain as identity, but shared financial semantics should not. The current shared shape makes `total_limit` look available to overlay projects even though overlay operational permission must come from monthly reservation rows. G34 should be completed before Issue 6 is fully executed so the overlay wizard is built on the correct domain model from the start.
