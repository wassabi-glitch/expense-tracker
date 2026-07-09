"""
Frozen Isolated Project Quarantine Contract
===========================================

**Status:** ACTIVE — enforced by ADR-0022
**ADR:** ``docs/adr/0022-freeze-isolated-projects-and-fund-project.md``
**Date frozen:** 2026-07-07

This module defines the **only** questions stable core modules are allowed to
ask about Isolated Projects while ADR-0022 remains active.

.. attention::

   **DO NOT expand this contract.**  If you are an agent reading this and you
   see an older Isolated Project or Fund Project PRD/issue file marked
   ``ready-for-agent``, **do not treat it as an active execution target.**
   ADR-0022 supersedes all older Isolated Project and Fund Project roadmap
   items.

   The freeze applies to:

   - direct Isolated Project creation and expansion
   - Fund Project goal creation and graduation UX
   - isolated project wallet-backed stash mechanics
   - isolated project category and micro-subcategory expansion
   - isolated project top-ups, rebalancing, wrap-up, and sweep flows
   - isolated project off-wallet spending and stash release decisions
   - EC-162 project-protection breach resolution
   - any new work that depends on Isolated Projects as a core money primitive

   Existing isolated project records remain readable where currently
   supported.  Existing routes that already perform isolated project
   operations (top-up, allocate, rebalance, sweep, wrap-up) continue to
   function but must not be extended with new behavior.

Allowed Compatibility Queries
-----------------------------

These are the **only** questions stable core modules may ask.  Every function
exposed through the quarantine ``__init__.py`` must be listed here with a
justification.

1. **Project type classification**

   ``is_isolated_project(project) -> bool``
     *Needed by:* budget permission (monthly-budget bypass), session drafts
     (isolated-project guards), overlay project service (type guards).

2. **Wallet-level allocation queries (read-only)**

   ``get_wallet_project_allocated_amount(db, owner_id, wallet_id) -> int``
     *Needed by:* wallets router (wallet free-to-allocate computation).

   ``get_project_wallet_allocated_amount(project) -> int``
     *Needed by:* project display (funding summary).

3. **Project-level funding queries (read-only)**

   ``get_project_funding_limit(project) -> int | None``
     *Needed by:* goals router (project-funding eligibility), project display.

   ``get_project_category_allocated_amount(project) -> int``
     *Needed by:* project display (allocated-vs-funding summary).

4. **Spending queries (read-only)**

   ``get_isolated_project_category_spent_amount(db, owner_id, project_id, category) -> int``
     *Needed by:* project update validation (category allocation guards).

   ``get_isolated_project_subcategory_spent_amount(db, owner_id, project_id, subcategory_id) -> int``
     *Needed by:* rebalance validation (subcategory allocation guards).

   ``get_isolated_project_total_spent(db, owner_id, project_id) -> int``
     *Needed by:* sweep/wrap-up summary.

5. **Validation helpers (read-only checks)**

   ``validate_project_limit_sum(total_limit, category_allocations, ...) -> None``
     *Needed by:* project update rules (funding-limit enforcement).

   ``validate_isolated_project_category_allocation_covers_spending(db, owner_id, project, category, limit_amount) -> None``
     *Needed by:* project update/category limit changes.

6. **Serialization helpers**

   ``project_wallet_allocations_out(project) -> list[ProjectWalletAllocationOut]``
     *Needed by:* project detail display.

   ``get_wallet_free_to_allocate_for_projects(db, owner_id, wallet) -> tuple[int, int, int, int]``
     *Needed by:* wallet allocation validation (existing routes).

Existing Write Operations (Frozen — Existing Routes Only)
---------------------------------------------------------

These operations are accessible for **existing route compatibility only**.
They are frozen: do not add new callers, parameters, or behavior.

- ``apply_isolated_project_top_up`` — existing top-up route only
- ``apply_isolated_project_category_allocation`` — existing category allocation route only
- ``apply_isolated_project_subcategory_allocation`` — existing subcategory allocation route only
- ``apply_isolated_project_rebalance`` — existing rebalance route only
- ``sweep_isolated_project_wallet_allocations`` — existing completion/sweep route only
- ``get_isolated_project_wrap_up_summary`` — existing wrap-up summary route only
- ``get_isolated_project_total_top_ups`` — existing wrap-up summary only
- ``validate_project_wallet_allocations`` — existing wallet allocation validation only

Explicitly NOT Allowed
----------------------

The quarantine MUST NOT expose and stable core MUST NOT add:

- New Isolated Project creation endpoints or service functions
- Fund Project goal graduation logic
- Top-up, rebalance, or sweep flows beyond the existing routes
- Stash release or off-wallet spending mechanics
- EC-162 project-protection breach resolution
- New isolated micro-subcategory behavior
- Any direct import of ``app.services.isolated_project_service`` internals
  by modules outside the quarantine

Overlay Project Boundary
------------------------

Overlay Project behavior lives in ``app.services.overlay_project_service.py``
and is **not frozen**.  It remains outside this quarantine.  The overlay
service may call ``is_isolated_project`` as a type guard but must not depend
on isolated project internals.

Revisit Criteria
----------------

After the core app is stable, ADR-0022 will be revisited with one of two
decisions:

- **Option A:** Remove Isolated Projects and Fund Project — delete this
  quarantine and all isolated project code.
- **Option B:** Promote Isolated Projects into a first-class protected-stash
  ledger — replace this quarantine with a full ``app/domains/projects/isolated/``
  domain package.

Until then, this contract is the **only** bridge between stable core modules
and frozen isolated project behavior.
"""
