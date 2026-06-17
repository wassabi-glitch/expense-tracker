# PRD: G8 - Expense Entry and Post-Save Repair UX

Labels: `ready-for-agent`

Source ECs: EC-109, EC-110, EC-123 only.

## Problem Statement

Sarflog already accepts that wallet reality beats budget metadata. A real expense must be saved even when it pushes a parent category or subcategory into the red. The remaining product gap is the user experience around that moment.

When a user enters an over-budget expense, the app should warn without blocking the save. After the save, the app should immediately show what went red and offer practical repair actions. Subcategory overspending needs the same treatment: it should save, turn visibly red, and offer same-parent repair options without forcing the user to abandon quick expense entry.

## Solution

Build a frictionless over-budget expense flow. The expense form shows non-blocking inline warnings when the selected category, amount, or subcategory will exceed the current plan. Save remains available. After a successful save, the UI shows a concise repair state for the affected parent category and subcategory.

Repair actions should let the user reallocate budget room, increase the relevant limit where allowed, or leave the plan red. Subcategory repair stays inside the parent category unless the user explicitly escalates to a parent-category action.

## User Stories

1. As an expense user, I want to save a real expense even if it exceeds my category budget, so that my wallet history stays truthful.
2. As an expense user, I want an inline warning before saving an over-budget expense, so that I understand the plan impact without being blocked.
3. As an expense user, I want the save button to remain active when the warning appears, so that recording reality stays one action.
4. As an expense user, I want the warning to update when I change amount, category, date, or subcategory, so that the warning matches the exact expense I am about to save.
5. As a budget user, I want the post-save state to show the affected category as red, so that I immediately see the plan damage.
6. As a budget user, I want a post-save action to move limit from another category, so that I can repair a parent-category overspend.
7. As a budget user, I want a post-save action to increase the affected category limit, so that I can intentionally change the plan when I have enough backing.
8. As a budget user, I want an option to leave the category red, so that I am not forced into fake cleanup.
9. As a subcategory user, I want an over-limit subcategory expense to save successfully, so that optional micro-tracking never blocks wallet truth.
10. As a subcategory user, I want a red subcategory state with negative remaining, so that I can see exactly how far the micro-plan is broken.
11. As a subcategory user, I want to move room from parent buffer or sibling subcategories, so that I can repair the subcategory without changing unrelated categories.
12. As a subcategory user, I want an increase-parent-limit option when the parent category has no room, so that I can deliberately escalate from micro repair to macro budget repair.
13. As a subcategory user, I want an option to ignore the red subcategory, so that I can keep the expense truthful and decide later.
14. As a mobile user, I want the warning and repair actions to be compact, so that quick expense entry stays fast.
15. As a maintainer, I want the UI to consume existing budget and subcategory state from APIs, so that frontend math does not fork from backend truth.
16. As a tester, I want behavior verified through expense creation and budget detail/month summary seams, so that tests cover user-visible outcomes instead of implementation details.

## Implementation Decisions

- Expense save must not be disabled because a parent category or subcategory will go over limit.
- Inline warnings are advisory. They should explain the overage amount and affected category or subcategory.
- Post-save repair actions should appear only after a successful save that creates or worsens an over-limit state.
- Parent-category repair actions are: reallocate from another parent category, increase the category limit, or leave red.
- Subcategory repair actions are: reallocate from the parent buffer or sibling subcategory, increase the parent category limit, or leave red.
- Subcategory repair must not silently mutate another parent category.
- Budget and subcategory detail displays should use negative remaining values instead of hiding overspend.
- The frontend should rely on backend-provided budget detail, subcategory remaining, and month summary state wherever those contracts already exist.
- Backend changes should be limited to missing API support for warning previews or repair actions. Do not rebuild budget math for this PRD.
- Copy should use existing budget language: `Over-Planned`, red state, remaining, and limit. Do not introduce envelope-funding language.

## Testing Decisions

- Prefer API-level tests for expense saves that exceed category and subcategory limits.
- Prefer UI/component tests or browser smoke checks for inline warning visibility, save availability, and post-save repair actions where the frontend stack supports it.
- Use existing budget detail and month summary endpoints as the highest verification seam for red states.
- Test that over-budget parent-category expense save succeeds and the category reports negative remaining.
- Test that over-limit subcategory expense save succeeds and the subcategory reports negative remaining.
- Test that same-parent subcategory reallocation can repair the red subcategory.
- Test that leaving red does not mutate budgets or subcategory limits.
- Run Docker-backed backend tests for backend behavior changes.
- Run `npm.cmd run build` for frontend changes.

## Out of Scope

- Any EC other than EC-109, EC-110, and EC-123.
- Any work outside over-budget expense entry, post-save repair, and subcategory repair UX.
- New budget backing formulas.
- Cross-parent subcategory reallocation.
- Automatic repair after save.
- Blocking real expenses because a budget or subcategory is red.

## Further Notes

This PRD publishes G8 locally under `docs/prd/` with the `ready-for-agent` label. No external issue tracker tool is available in this environment.
