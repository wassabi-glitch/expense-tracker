# Epic 7: Overlay Project UX & Lifecycle Polish

**Status:** Not Started  
**Depends On:** Epic 6 (Goal Lifecycle — for Goal → Project graduation path)

## Goal
Polish the user-facing experience and lifecycle safety of Overlay Projects. The core Overlay architecture (month-scoped slices, category inheritance, ledger integrity) was defined in the PRD-based epics. This ADR epic focuses on how users *discover*, *interact with*, and *safely close or delete* projects — the product-boundary refinements that make the system feel intuitive rather than intimidating.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0020 — Overlay Project UX Architecture: Two-Layer Disclosure & JIT Onboarding](../adr/0020-overlay-project-ux-architecture.md)**
   - Establishes the UX structural rules for all project features:
     - **Just-In-Time Onboarding:** Overlay Projects are completely hidden during new-user onboarding. Core loop first (Wallet → Categories → First Expense). Projects are discovered naturally via a "Create Project" button on the Budgets screen after baselines are established.
     - **Layer 1 — Budgets Screen:** Minimal status cards answering only "What needs my attention this month?" No dense historical data, no heavy configuration UI.
     - **Layer 2 — Dedicated Details Page (`/projects/:id`):** All complex operations live here — editing target dates, re-allocating category slices, viewing the full cross-month expense ledger, triggering auto-sweep, and executing deletion/resolution flows.

2. [ ] **[ADR 0019 — Overlay Project Deletion Resolution UX](../adr/0019-overlay-project-deletion-resolution-ux.md)**
   - Refines the deletion and resolution flows that live on ADR 0020's Layer 2 Details page:
     - **State-Aware Actions:** Archived projects must not present "Archive" as an available action. Backend rejects repeated archives with `projects.already_archived` or treats idempotently. UI hides/disables already-completed actions.
     - **Deletion Preview:** The modal must show concrete affected expense rows (id, title, date, amount, category) — not just aggregate count and total. Users need to see *which* expenses will be detached or deleted before committing.
     - **User Language, Not Ledger Language:** UI copy says "Archive project", "Detach expenses", "Delete linked expenses", "Accounting history is preserved for accuracy." Avoids "Void", "Cascade void", "Reversal", "Ledger entries." Backend and tests retain precise ledger terminology internally.

3. [ ] **[ADR 0021 — Defer Project List Filtering, Search & Pagination](../adr/0021-project-list-filtering-search-pagination-deferred.md)**
   - An explicit, documented deferral decision:
     - Project list management (status filters, text search, pagination) is deferred to a future slice.
     - The current lifecycle work stays focused on state rules, restore behavior, completion, and deletion-resolution language.
     - Archived/completed projects will still appear in the main list until the future filtering slice is built.
     - When implemented: backend filters for status/type, frontend status filter (Active/Paused/Completed/Archived/All), frontend text search first, backend search + pagination only when volume requires it.

## Why This Order
- ADR 0020 establishes the two-layer UX structure first. Without it, there's no "Details page" for the deletion resolution to live on.
- ADR 0019 refines the deletion/resolution flows *within* that Details page. It's a polish pass on an already-functional feature — tightening state-awareness, adding expense previews, and humanizing copy.
- ADR 0021 is a conscious deferral — it documents what we're *not* building now and why, giving the future slice a clear product direction without bloating the current epic.

## Execution Rules
- ADR 0020's Layer 2 Details page (`/projects/:id`) must be a dedicated route with its own data fetching, not a modal or drawer on the Budgets screen. This is critical for performance isolation and scalability.
- ADR 0019's deletion preview requires expanding `ProjectDeletionPreviewOut` to include a list of linked expense objects, not just counts.
- ADR 0021 is documentation-only — no implementation work required. Its value is preventing scope creep during the lifecycle polish.
