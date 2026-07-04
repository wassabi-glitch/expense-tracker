# PRD: G36 - Complete Project Money Mechanics Separation

Labels: `ready-for-agent`, `architecture-note`

## Problem Statement

The G35 / Issue 2.5 refactor started the right move by renaming several project money-mechanics tables into overlay reservation and isolated allocation language. However, the implementation can still leave Sarflog in a confusing half-refactor state:

- A single project service can still own both Overlay Project and Isolated Project financial rules.
- Old model aliases can keep confusing names alive.
- Generic routes and schemas can still say "limit" while branching internally by project type.
- The legacy project-local subcategory table can still be used as the forward isolated micro-subcategory model.

Because this environment is not production and historical data does not need to be preserved at all costs, Sarflog should prefer a clean architecture over compatibility shims. The refactor should remove old concepts that have already been replaced by clearer tables and should make the next Issue 3 implementation hard to misunderstand.

## Solution

Finish the Project money-mechanics separation as a deliberate cleanup pass before Issue 3.

The desired architecture is:

- Shared Project shell for identity and lifecycle only.
- Overlay Project module for monthly budget reservations only.
- Isolated Project module for stash funding allocations only.
- Taxonomy-governed isolated micro-subcategory allocations as the forward path for Issue 3.

This means table renames are not enough. The implementation must also split backend service ownership, remove old aliases, remove or replace legacy project-local subcategory mechanics, and stop using generic "limit" language in new contracts.

The clean target is:

- Keep `projects`.
- Keep type-specific detail tables.
- Keep `overlay_project_category_reservations`.
- Keep `overlay_project_subcategory_reservations`.
- Keep `isolated_project_wallet_allocations`.
- Keep `isolated_project_category_allocations`.
- Add or reserve the forward model `isolated_project_subcategory_allocations` for Issue 3.
- Remove old table names and old model aliases.
- Remove `project_subcategories` as the forward project micro-subcategory table.

## User Stories

1. As a product owner, I want the Projects architecture to match the domain language, so that future agents do not mix Overlay and Isolated mechanics again.
2. As a budget user, I want Overlay Projects to only talk about reservations, so that I understand they reserve monthly budget permission.
3. As an isolated project user, I want Isolated Projects to only talk about allocations and funding, so that I understand they spend down a locked stash.
4. As a developer, I want overlay financial logic isolated in an overlay service, so that monthly reservation validation does not sit beside stash allocation validation.
5. As a developer, I want isolated financial logic isolated in an isolated service, so that wallet locks, category allocations, and future micro-subcategory allocations live together.
6. As a developer, I want the shared project service to contain only shared project identity and lifecycle behavior, so that common code does not hide type-specific money rules.
7. As a developer, I want old model aliases removed, so that new code cannot accidentally use obsolete concepts like generic project category limits.
8. As a developer, I want old table names removed, so that database inspection shows the real money model immediately.
9. As a developer, I want `limit_amount` removed from new isolated allocation contracts, so that isolated code speaks `allocated_amount`.
10. As a developer, I want `limit_amount` removed from new overlay reservation contracts, so that overlay code speaks `reserved_amount`.
11. As a developer, I want compatibility response fields to be intentionally deprecated or removed where tests allow, so that the frontend is forced onto correct language.
12. As a developer, I want API routes to stop using generic `/category-limits` naming for type-specific actions, so that routes express reservation versus allocation intent.
13. As a developer, I want Overlay Project routes to create and update reservations, so that budget-month behavior stays explicit.
14. As a developer, I want Isolated Project routes to create and update allocations, so that stash behavior stays explicit.
15. As a developer, I want `ProjectSubcategory` removed from the forward model, so that isolated micro-subcategories cannot remain free-text project-local labels.
16. As a developer, I want Issue 3's isolated micro-subcategory table to reference taxonomy records, so that project micro-subcategories use the G21 Taxonomy Hub.
17. As a developer, I want ledger rows and draft rows to reference the new isolated project subcategory allocation model when Issue 3 needs project micro-subcategory context.
18. As a developer, I want debts and payment plans to stop pointing at legacy project-local subcategory rows, so that financing context can use the same forward taxonomy-governed model.
19. As a tester, I want tests to fail if old aliases or old table names come back, so that the refactor does not regress.
20. As a tester, I want tests to prove overlay reservations never read isolated allocation rows, so that the two mechanics stay separate.
21. As a tester, I want tests to prove isolated allocations never read overlay reservation rows, so that the two mechanics stay separate.
22. As a frontend maintainer, I want overlay wizard state to use reservation names, so that UI code does not treat reservations as generic limits.
23. As a frontend maintainer, I want isolated wizard state to use allocation names, so that UI code does not treat allocations as generic limits.
24. As a future Issue 3 agent, I want exact tables and modules named in the issue, so that I do not invent another mixed abstraction.
25. As a maintainer, I want the cleanup to be allowed to drop development data, so that the architecture can become simple instead of compatibility-heavy.

## Implementation Decisions

- Keep the shared `projects` table. It remains the stable identity and lifecycle shell for project owner, title, description, type, status, dates, origin references, and ledger references.
- Keep `project_overlay_details` and `project_isolated_details` only for type-specific project metadata that is not a reservation/allocation row.
- Keep `overlay_project_category_reservations` as the only forward table for Overlay Project parent-category monthly reservations.
- Keep `overlay_project_subcategory_reservations` as the only forward table for Overlay Project taxonomy subcategory monthly reservations.
- Keep `isolated_project_wallet_allocations` as the only forward table for Isolated Project wallet-funded stash locks.
- Keep `isolated_project_category_allocations` as the only forward table for Isolated Project parent-category stash allocations.
- Add `isolated_project_subcategory_allocations` in this cleanup only if the team wants Issue 3 to start with a prepared table; otherwise G36 must document the exact intended table shape for Issue 3.
- The forward `isolated_project_subcategory_allocations` shape should reference the shared project id, parent category, taxonomy/user subcategory id, allocated amount, active/archive state, and timestamps.
- Remove or stop using `project_subcategories` as a forward table. Since this environment is not production, it may be dropped rather than preserved as legacy history.
- Remove old SQLAlchemy aliases such as `ProjectWalletAllocation`, `ProjectCategoryLimit`, `ProjectCategoryMonthlyLimit`, and `ProjectSubcategoryMonthlyLimit`.
- Remove old relationship aliases such as generic `project.category_limits`, `project.monthly_category_limits`, `project.monthly_subcategory_limits`, and `project.wallet_allocations` after call sites are moved to type-specific names.
- Split backend services into a shared project service plus type-specific services. The shared service should hold ownership, lifecycle, deletion preview, and ledger reference helpers. Overlay service should hold reservation validation/sweep/month migration. Isolated service should hold wallet allocation, category allocation, funding, and future micro-subcategory allocation rules.
- Split router intent where practical. Existing public routes can temporarily remain only if their function names, schemas, and internals clearly delegate to type-specific services; new routes should use allocation/reservation language.
- Replace `limit_amount` with `reserved_amount` in overlay-specific request/response models where the frontend can be updated in the same slice.
- Replace `limit_amount` with `allocated_amount` in isolated-specific request/response models where the frontend can be updated in the same slice.
- If backward compatibility fields are retained during this development pass, they must be clearly marked temporary and tests should assert the new fields are the canonical ones.
- Update frontend helper names and payload builders so overlay code emits reservation rows and isolated code emits allocation rows.
- Update tests so old table names, aliases, and forward `ProjectSubcategory` usage are treated as failures, not acceptable compatibility.
- Because data preservation is not required, prefer simple destructive migrations over complex dual-write or long-lived compatibility paths.

## Testing Decisions

- Good tests should check the architecture through public behavior and explicit architecture guardrails. They should not merely assert that old behavior still passes under new names.
- Add schema/table guard tests proving old forward tables are gone: no generic project wallet allocation table, no generic project category limit table, no generic project category monthly limit table, no generic project subcategory monthly limit table, and no forward project-local subcategory table if the cleanup drops it.
- Add model guard tests proving old SQLAlchemy aliases are gone.
- Add service-boundary tests or import guard tests proving overlay-specific functions live in the overlay service and isolated-specific functions live in the isolated service.
- Add API tests proving overlay requests and responses expose `reserved_amount` as the canonical field.
- Add API tests proving isolated requests and responses expose `allocated_amount` as the canonical field.
- Add frontend helper tests proving overlay wizard payloads use reservation language.
- Add frontend helper tests proving isolated wizard payloads use allocation language.
- Add backend behavior tests proving overlay reservation math remains correct after the service split.
- Add backend behavior tests proving isolated wallet/category allocation math remains correct after the service split.
- Add tests proving isolated category allocations do not create overlay reservation rows.
- Add tests proving overlay reservations do not create isolated allocation rows.
- Add tests proving completed/archived project write guards still apply after delegating to type-specific services.
- Add tests or explicit TODO guardrails for the Issue 3 isolated micro-subcategory allocation table if it is not created in this cleanup slice.
- Run Docker verification for migrations, backend tests, frontend tests, and frontend build.

## Out of Scope

- Building the full Issue 3 isolated micro-subcategory UX.
- Implementing top-ups, rebalancing, expense overrun repair, or wrap-up flows.
- Preserving development data from old mixed project tables.
- Keeping long-lived compatibility aliases for old project money-mechanics names.
- Reworking the core `FinancialEvent`, `WalletLedger`, or `EntityLedger` accounting model.
- Removing the shared `projects` identity table.

## Further Notes

Senior-engineer judgment: if data preservation is not required, the cleanest move is to delete the old forward abstractions rather than keep them as aliases.

Tables/concepts that should not survive as forward architecture:

- `project_wallet_allocations` because `isolated_project_wallet_allocations` replaces it.
- `project_category_limits` because `isolated_project_category_allocations` replaces it.
- `project_category_monthly_limits` because `overlay_project_category_reservations` replaces it.
- `project_subcategory_monthly_limits` because `overlay_project_subcategory_reservations` replaces it.
- `project_subcategories` because the forward isolated micro-subcategory model should be taxonomy-governed isolated allocation rows, not project-local free-text rows.

The shared `EntityLedger` references should remain, but their project micro-subcategory pointer should move to the new isolated project subcategory allocation model when Issue 3 is implemented.
