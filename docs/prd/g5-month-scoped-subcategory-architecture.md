# PRD: G5 - Month-Scoped Subcategory Architecture

Labels: `ready-for-agent`

## Problem Statement

Sarflog treats parent budgets as monthly spending permissions, but subcategory limits are still stored as global metadata on user-created subcategory tags. That means editing `Transport -> Taxi` in a later month can rewrite how an earlier month appears, corrupting budget history and making month-by-month decisions untrustworthy.

Subcategories also need to remain optional micro-trackers. A user must be able to spend directly against a parent category without choosing a subcategory, and subcategory overspending should make the plan visually red and actionable without blocking the save of real-life expense truth.

## Solution

Split subcategory identity from monthly limit state. `UserSubcategory` remains the user's reusable tag under a hardcoded parent category. A budget-specific subcategory limit row stores that tag's limit for one parent budget month.

Budget detail and subcategory routes continue to expose `monthly_limit`, `spent`, `remaining`, and `is_over_limit`, but those values are derived from the selected budget month. When a new month is lazily materialized, it copies the previous month's subcategory limit rows so the user starts from a familiar plan without mutating history.

## User Stories

1. As a budget user, I want my custom subcategories to be reusable tags, so that I can personalize spending without changing global category reporting.
2. As a budget user, I want subcategory limits to belong to a specific budget month, so that later edits do not rewrite historical months.
3. As a budget user, I want a new month to copy last month's subcategory limits, so that setup is fast but still month-specific.
4. As a budget user, I want the sum of subcategory limits to stay within the parent category limit, so that micro-plans cannot promise more than the parent plan allows.
5. As a budget user, I want spending without a subcategory to be allowed, so that quick real-life entry is not blocked by optional tagging.
6. As a budget user, I want subcategory overspending to show negative remaining, so that I can see which micro-plan is red.
7. As a budget user, I want subcategory overspending to save successfully, so that wallet reality remains the source of truth.
8. As a budget user, I want repair actions to stay inside the parent category first, so that moving money between subcategories does not silently mutate unrelated parent budgets.
9. As a budget user, I want parent category overspending to still affect global plan backing, so that G3 budget math remains honest.
10. As a maintainer, I want budget detail to remain the highest API seam for subcategory reporting, so that frontend dashboards do not duplicate limit math.
11. As a tester, I want route-level regression coverage for historical subcategory limits, so that future refactors cannot reintroduce global limit mutation.

## Implementation Decisions

- Keep global parent categories hardcoded and user subcategories custom-created.
- Treat `UserSubcategory` as tag identity only: owner, parent category, name, active state, and creation time.
- Add a budget-month limit record keyed by parent budget and subcategory.
- Continue returning `monthly_limit` on budget subcategory API responses for frontend compatibility, but source it from the selected budget month.
- Use absence of a budget-specific limit row to mean the subcategory has no explicit monthly limit.
- Enforce the subcategory total invariant inside the selected parent budget month.
- Copy prior-month budget subcategory limits during lazy budget materialization.
- Do not require subcategory selection on expense save.
- Do not hard-block ordinary expense save when a subcategory limit goes red.
- Keep cross-parent reallocation out of subcategory actions; users must adjust parent budgets first.

## Testing Decisions

- Prefer API-level tests through budget detail and budget subcategory routes.
- The first tracer bullet proves a later-month limit change does not mutate an earlier month's budget detail.
- Follow-up tests should cover lazy month copying, parent limit sum validation per month, optional parent-only spending, and visual overspend fields.
- Expense tests are only required when changing expense posting or split/session save behavior.
- Docker-backed backend tests are the verification source for Redis/API/DB behavior.

## Out of Scope

- Full frontend reallocation UI.
- Cross-category subcategory moves.
- Automatic parent budget increases from subcategory repair actions.
- Retroactively reconstructing historically different subcategory limits that were already overwritten before this migration.
- G6 new-month setup modes beyond lazy copy behavior.

## Further Notes

This PRD implements G5 from `docs/EC_IMPLEMENTATION_PLAN.md` and is grounded in EC-120 through EC-125. It preserves G3's parent category backing math and the product rule that budgets are monthly spending permissions, not cash envelopes.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
