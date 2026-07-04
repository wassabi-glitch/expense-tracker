# PRD: G35 - Project Money Mechanics Architecture Refactor

Labels: `ready-for-agent`, `architecture-note`

## Problem Statement

Sarflog has made meaningful progress separating Overlay Projects from Isolated Projects, but the current project architecture still uses some generic table, schema, route, and service language for mechanics that are financially different.

Overlay Projects reserve monthly spending permission from global budget categories. Isolated Projects allocate locked project stash into project-local funding buckets. When both mechanics are exposed through names like "limit" or generic project category/subcategory paths, the code becomes harder to reason about and easier to extend incorrectly.

This is especially risky before isolated micro-subcategories are implemented. Issue 3 will add the most detailed part of the isolated project funding model. If that feature is built on top of ambiguous naming and mixed service boundaries, Sarflog risks encoding more behavior into concepts that the team already finds confusing.

## Solution

Refactor the Projects architecture before implementing isolated micro-subcategories.

Sarflog should keep one shared project identity and lifecycle shell, but make overlay and isolated money mechanics explicit in storage, services, schemas, API language, tests, and frontend state naming.

The user-facing model should remain:

- **Overlay Project**: a project that reserves part of a monthly budget category or subcategory.
- **Isolated Project**: a project that spends down dedicated locked funding from a project stash.

The implementation should make those two models hard to confuse:

- Overlay mechanics should use reservation language.
- Isolated mechanics should use allocation and funding language.
- Shared project code should only contain ownership, identity, lifecycle, and stable ledger references.

## User Stories

1. As a budget user, I want Overlay Projects to clearly represent monthly reservations, so that I know they affect my monthly budget permission.
2. As a budget user, I want Isolated Projects to clearly represent project funding allocations, so that I know they spend down a locked stash.
3. As an isolated project user, I want category funding to be described as allocation, so that I do not confuse it with a recurring monthly limit.
4. As an overlay project user, I want category project amounts to be described as reservations, so that I understand they reserve monthly budget space.
5. As a project user, I want the same project identity and history to remain stable, so that existing expenses and reports do not break.
6. As an expense logger, I want expense rows to continue pointing to one project identity, so that I do not need to understand different project storage internals while entering expenses.
7. As a project reviewer, I want overlay category rows and isolated category rows to be separate concepts, so that project details do not mix budget permission with project funding.
8. As a project reviewer, I want overlay subcategory reservations and isolated subcategory allocations to be separate concepts, so that micro-budgeting remains understandable.
9. As a budget reviewer, I want isolated funding allocations to stay out of monthly budget reserved scope, so that budget months remain accurate.
10. As a budget reviewer, I want overlay reservations to continue reducing available monthly category capacity, so that monthly planning remains truthful.
11. As a user with historical projects, I want existing project ids, statuses, dates, and ledger references preserved, so that migration does not rewrite my history.
12. As a user with existing isolated category allocations, I want those allocations migrated into isolated funding terminology, so that my project remains readable after the refactor.
13. As a user with existing overlay reservation rows, I want those rows migrated into overlay reservation terminology, so that current overlay behavior is unchanged.
14. As a user with project subcategory history, I want old subcategory-linked expenses to remain readable, so that historical receipts and reports do not lose context.
15. As a developer, I want table names to reveal whether a row belongs to overlay or isolated mechanics, so that future changes do not require domain archaeology.
16. As a developer, I want service names to reveal whether a function handles reservations or allocations, so that validation logic stays in the correct place.
17. As a developer, I want schema and response names to use `reserved` for overlay and `allocated` for isolated, so that API consumers do not infer meaning from generic limits.
18. As a developer, I want shared project helpers to stay limited to common behavior, so that lifecycle code does not hide financial assumptions.
19. As a developer, I want Issue 3 to build isolated micro-subcategory allocations on a clean isolated-project foundation, so that new micro-subcategory behavior does not depend on overlay tables.
20. As a developer, I want compatibility shims to be temporary and explicit, so that old names do not keep spreading through new code.
21. As a tester, I want migration tests that prove project data survives the refactor, so that schema cleanup does not corrupt ledger history.
22. As a tester, I want behavior tests proving overlay math did not change, so that naming cleanup does not alter budget reservation behavior.
23. As a tester, I want behavior tests proving isolated math did not change, so that funding allocation behavior remains stable.
24. As a maintainer, I want the architecture diagrams and docs to match the code, so that future agents and humans can reason about Projects quickly.
25. As a product owner, I want this refactor finished before isolated micro-subcategories, so that Issue 3 can be implemented once on the intended architecture.

## Implementation Decisions

- Keep the shared project identity table for common ownership, title, description, status, dates, origin references, lifecycle, and stable references from expenses and ledger rows.
- Keep type-specific financial mechanics outside the shared project identity table.
- Rename or migrate overlay category monthly rows into an overlay-specific reservation concept. These rows represent monthly budget permission reserved by a project.
- Rename or migrate overlay subcategory monthly rows into an overlay-specific reservation concept. These rows should continue to reference the global/user taxonomy records used by monthly budgets.
- Rename or migrate isolated parent category rows into an isolated-specific allocation concept. These rows represent project stash funding assigned to a parent category.
- Rename or migrate isolated wallet funding rows into isolated-specific wallet allocation language. These rows remain the source of truth for the locked isolated project stash.
- Do not implement the full isolated micro-subcategory feature in this refactor. The refactor should create the architectural boundary that Issue 3 will use.
- If existing project-local subcategory rows are still needed for historical readability, preserve them as legacy-readable data and stop treating them as the forward path for isolated micro-subcategory allocation.
- The forward isolated micro-subcategory model should reference taxonomy records and isolated project allocation mechanics, not overlay monthly reservation rows or isolated-only free-text labels.
- Use `reserved_amount` or reservation wording for overlay-facing contracts and internals.
- Use `allocated_amount`, funding, or stash wording for isolated-facing contracts and internals.
- Split service boundaries so overlay validation lives with overlay reservation rules and isolated validation lives with isolated allocation rules.
- Keep public API compatibility only where necessary, but new contracts and response fields should speak the correct project type language.
- Update frontend helpers and state names so overlay rows are treated as reservations and isolated rows are treated as allocations.
- Preserve existing project ids and ledger references during migration. No historical expense should need a new project id.
- Treat dates touched by the refactor as user-facing business dates. New date defaults or validations must use the user's effective timezone.
- Verify schema migration and behavior in Docker against Postgres.

## Testing Decisions

- Good tests should verify public behavior and data preservation: migrated rows, API responses, project detail summaries, budget-month math, and ledger readability. They should not assert private helper structure.
- Add migration tests proving overlay reservation rows migrate to overlay-specific storage without changing behavior or project ids.
- Add migration tests proving isolated category allocation rows migrate to isolated-specific storage without changing funding, spent, or remaining values.
- Add migration tests proving isolated wallet allocation rows remain tied to the same projects and wallets after the naming/structure refactor.
- Add tests proving isolated funding allocations do not appear as monthly budget reserved scope.
- Add tests proving overlay reservations still reduce available monthly category/subcategory capacity.
- Add tests proving completed and archived project read-only behavior still works after service boundaries are split.
- Add tests proving historical ledger rows with project and project-subcategory references remain readable after migration.
- Add API tests proving response language exposes overlay reservations separately from isolated allocations.
- Add frontend tests for wizard/project-detail state builders so overlay rows are named and calculated as reservations while isolated rows are named and calculated as allocations.
- Prior art includes the Epic 5 overlay reservation tests, the Issue 2 isolated category allocation tests, and the existing migration-style project date tests.
- Run Docker verification for migrations, focused backend tests, focused frontend tests, and frontend build.

## Out of Scope

- Implementing Issue 3 isolated micro-subcategory creation, editing, deletion, and expense selection.
- Changing the product meaning of Overlay Projects.
- Changing the product meaning of Isolated Projects.
- Removing the shared project identity and lifecycle table.
- Rewriting historical ledger events beyond the minimum migration needed to preserve references.
- Redesigning project completion, top-up, rebalance, or sweep behavior.
- Changing the global budget category taxonomy.
- Changing the Taxonomy Hub feature itself.

## Further Notes

This refactor is mainly about making the architecture tell the truth.

The desired mental model is:

- Shared project shell: identity, owner, title, status, dates, history.
- Overlay project mechanics: monthly budget reservations.
- Isolated project mechanics: locked stash funding allocations.

The refactor should be small enough to verify as a no-behavior-change architecture slice, but strong enough that Issue 3 can add isolated micro-subcategories without leaning on overlay monthly reservation tables or project-local free-text labels.
