# PRD: G25 - Overlay Taxonomy & Subcategory Inheritance

Labels: `ready-for-agent`

## Problem Statement

Overlay projects risk breaking the global taxonomy (G21) if allowed to use custom, orphaned text strings for subcategories. Furthermore, power users running 5-6 overlapping projects at once face the "Multi-Project Collision" problem: they can easily "overbook" a parent category by setting project limits that far exceed their actual Global Budget capacity, creating a fantasy plan that contradicts Sarflog's realism philosophy.

## Solution

Enforce **Global Supremacy** and strict inheritance. Project subcategories must use global `UserSubcategory` tags. To create a Project Subcategory Limit, that subcategory must first exist in the Global Monthly Budget. To reserve limits for multiple overlapping projects, the Global Budget must have enough "Free" (unreserved) headroom. We enforce a "Hard Block" against overbooking.

## User Stories

1. As a power user, I want project subcategories to strictly inherit from global subcategories, so my taxonomy stays clean.
2. As a power user, I want the system to prompt me to create a global subcategory if I try to use it in a project and it doesn't exist, so setup is seamless.
3. As a power user, I want 100% of my project subcategory limit to map to the global subcategory limit, so they stay perfectly synced.
4. As a power user, I want the system to Hard Block me from reserving more money across projects than my global budget allows (Option A), so I don't accidentally overplan.
5. As a power user, I want project reallocation (G14 style) to require global headroom, so projects don't silently inflate global limits without my consent.

## Implementation Decisions

- **Schema Changes:** Replace `ProjectSubcategory` with `ProjectSubcategoryMonthlyLimit`. Drop custom `name` and `category` fields. Add `user_subcategory_id`, `budget_year`, `budget_month`, `limit_amount`.
- **Ledger Cleanup:** Drop `project_subcategory_id` from `EntityLedger` entirely. All expenses use the unified `subcategory_id` along with `project_id`.
- **The Hard Block Validation:** On `POST /projects` or `PUT /projects/limits`, the backend must sum all existing reservations for that category/month. If `New Reservation + Existing Reservations > Global Budget Limit`, return `400 Validation Error`.
- **Proactive Reallocation Rule:** Shifting limits *between* project categories requires checking if the target Global Category has enough unreserved capacity. If not, the user must perform a G14 parent-level reallocation first.

## Testing Decisions

- Write API integration tests for the project limits endpoint ensuring a `400 Bad Request` is thrown when overbooking the parent limit.
- Write tests ensuring that adding a project subcategory correctly links to the `UserSubcategory` entity, throwing an error if the parent `BudgetSubcategoryLimit` does not exist for that month.

## Out of Scope

- Core monthly slicing architecture (See G24).
- The Project UI Wizard (See G27).

## Further Notes

This PRD acts as the ultimate enforcer of G21. The project becomes a pure "lens" focusing on the main budget. It is mathematically impossible for the project to go out of sync with the main budget because the project is literally made out of the main budget.
