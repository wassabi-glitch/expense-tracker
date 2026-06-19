# Epic 3: Budget Control & Taxonomy Hub

**Status:** Not Started  
**Depends On:** Epic 2 completion

## Goal
Now that the user has intelligent backing formulas and a chronological timeline (Epic 2), they need the tools to easily manipulate their budgets and organize their spending tags. This epic provides the proactive "steering wheel" for parent categories and builds a rock-solid, bug-free taxonomy foundation for subcategories, paving the way for the complex month-scoped overlay architecture in Epic 4.

## PRDs Included

1. [ ] **Permissive Mid-Month Budget Creation & UX Updates**
   - *Budget Control:* Remove the hypocritical hard-blocks on `POST /budgets/` and `PUT /budgets/`. Introduce the "Permissive Overplanning" philosophy with unignorable "Look-Ahead Warnings" when users try to add or increase budgets mid-month beyond their capacity.
2. [ ] **[G14 - Reallocate Parent Budgets UI](../prd/g14-reallocate-parent-budgets-ui.md)**
   - *Budget Control:* Introduce a proactive "Reallocate Limits" feature on the Budgets dashboard, allowing users to shift funds between top-level parent categories before overspending occurs.
3. [ ] **[G21 - Subcategory Taxonomy Hub](../prd/g21-subcategory-taxonomy-hub.md)**
   - *Taxonomy Foundation:* Fix the deletion bug (preserve global tags when deleting monthly limits), replace the raw text input with a searchable Combobox, and build the dedicated Taxonomy Hub for archiving, renaming, and merging tags.

## Execution Rules
- G14 is a purely frontend bridging task and can be executed quickly.
- G21 requires careful backend database transaction handling, especially for the "Merge" feature.
