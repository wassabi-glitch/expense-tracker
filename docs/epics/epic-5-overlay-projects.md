# Epic 5: Overlay Project Architecture

**Status:** Not Started  
**Depends On:** Epic 3 (Taxonomy Hub) & Epic 2 (Budget Intelligence)

## Goal
Transform Sarflog's project capabilities from simple isolated budgets into intelligent, month-scoped **Overlay Projects**. Overlay Projects allow users to track cross-cutting expenses (e.g., "Paris Trip") by drawing limits directly from their standard parent categories across multiple months, solving the "Just-In-Time" allocation paradox and preserving the core monthly ledger's integrity.

## PRDs Included

1. [ ] **[G24 - Overlay Month-Scoped Architecture](../prd/g24-overlay-month-scoped-architecture.md)**
   - *Core Engine:* Establish the month-scoped limits (slices) for Overlay projects, solving the EC-161 JIT Allocation Paradox by only allocating from the current active month.
2. [ ] **[G25 - Overlay Taxonomy & Inheritance](../prd/g25-overlay-taxonomy-and-inheritance.md)**
   - *Taxonomy:* Bind Overlay projects to the standard Parent Categories to draw limits, leveraging the clean subcategory taxonomy from Epic 3.
3. [ ] **[G26 - Overlay Ledger Integrity](../prd/g26-overlay-ledger-integrity.md)**
   - *Safety Guardrails:* Implement Pristine Deletion (EC-160) and block mutations that would corrupt the underlying monthly ledger math.
4. [ ] **[G27 - Overlay UI Matrix Wizard](../prd/g27-overlay-ui-matrix-wizard.md)**
   - *User Experience:* Build the matrix-style wizard that allows users to fund the current month's "slice" of the overlay project without touching future months.
5. [ ] **[G23 - Project Completion & Wrap-Up](../prd/g23-project-completion-and-wrap-up.md)**
   - *Lifecycle:* Implement the workflow to cleanly close out a project when its dates have passed, sweeping any unused overlay limits back to the parent categories.

## Relevant Edge Cases
These ECs were captured during architecture review and must be strictly adhered to during execution:
- **EC-160: Overlay Ledger Integrity via Pristine Deletion**
  - Defines the exact rules for when an Overlay Project can be safely deleted versus when it must be frozen to protect financial history.
- **EC-161: Just-In-Time (JIT) Project Allocation and Future Month Paradox**
  - Prevents the UI from asking users to fund future months (e.g., August) when they haven't even run the Month Setup Wizard for that month yet.

## Execution Rules
- G24 and G25 represent the critical backend infrastructure and database schema updates. They must be executed first.
- Ensure integration tests cover the EC-160 deletion guardrails before moving to the G27 Frontend UI.
