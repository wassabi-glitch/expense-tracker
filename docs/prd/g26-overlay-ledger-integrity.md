# PRD: G26 - Overlay Ledger Integrity (Wrap-Up & Safe Deletion)

Labels: `ready-for-agent`

## Problem Statement

When a user finishes an Overlay project under budget, the unused limits remain "trapped" in their reserved state, starving the parent budget of liquidity. Additionally, if a user tries to delete an active project that already has real-life expenses attached (a sunk cost), doing a "hard delete" would orphan those expenses and destroy historical context, violating the immutable ledger philosophy.

## Solution

Introduce **Pristine Deletion** and **Auto-Sweep Completion**. Hard deletion is strictly reserved for untouched projects. If a project has any financial reality attached, it must be "Completed Early" instead of deleted. Completing a project triggers the Auto-Sweep: it shrinks all reserved limits down to match actual spending, instantly flushing the unspent reservations back to the parent Global Budget.

## User Stories

1. As a user, I want hard deletion of a pristine project to instantly release all reservations, so my budget returns to normal.
2. As a user, I want the system to block hard deletion if a project has expenses attached, so my historical intent is preserved from accidental erasure.
3. As a user, I want to be able to "Complete" a canceled project early to stop tracking it, so I can gracefully handle sunk costs.
4. As a user, I want completing a project to trigger an Auto-Sweep, where my project limits shrink to match my actual spending, so unspent limits are instantly returned to my global budget.
5. As a user, I want refunds to naturally reduce my `actual_spent` balance, so that I can safely shrink project limits further if I get my money back.

## Implementation Decisions

- **DELETE Endpoint Guardrail:** `DELETE /projects/{id}` must check the `EntityLedger` for any expenses matching `project_id`. If `count > 0`, return `403 Forbidden` explaining that the project must be completed instead.
- **The Auto-Sweep Hook:** In `POST /projects/{id}/complete` (expanding on G23), query all `ProjectCategoryMonthlyLimit` and `ProjectSubcategoryMonthlyLimit` rows for the current and future months.
- **Sweep Math:** For each slice, calculate `actual_spent`. Set `limit_amount = actual_spent` (or 0 if unspent). This effectively sets `remaining = 0` for the project, thereby reducing the `reserved_limits` on the parent budget and increasing the free capacity.
- **Past Months Exclusion:** Do not sweep past months. Past month slices flush back to their respective origin months inherently when the project wraps up, preserving the G12 no-rollover rule.

## Testing Decisions

- Test `DELETE /projects/{id}` with an empty project (success) and a project with 1 expense (failure).
- Test `POST /projects/{id}/complete` on a project with 1M reserved and 100k spent. Assert that the `limit_amount` drops to 100k and the parent budget's unreserved capacity increases by 900k.
- Prior art: G23 Project Completion mechanics.

## Out of Scope

- Sweeping logic for Isolated projects (which uses real `Free Money Now` sweeping as defined in G23). This PRD strictly covers Overlay limit reservations.

## Further Notes

This auto-sweep gives users a dopamine hit of "reclaimed budget" at the exact moment they finish a project, making the G23 wrap-up flow extremely psychologically rewarding.
