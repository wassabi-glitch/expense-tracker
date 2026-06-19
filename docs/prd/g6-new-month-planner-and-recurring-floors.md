# PRD: G6 - New Month Planner and Recurring Floors

Labels: `ready-for-agent`

## Problem Statement

Sarflog can explain whether a monthly budget plan is backed by real free money, expected inflows, valid spent, cash-only reserves, category floors, and month-scoped subcategory limits. The next weak spot is month setup itself.

Today, a new month can still feel like stale budget metadata appeared by accident. Users need an explicit planner that makes the choice clear: start from zero, copy the previous lifestyle, or copy and repair the plan with obligation floors. Users also need recurring expense projections that make habit cost visible without mutating budget, wallet, expense, or debt truth.

## Solution

Add an explicit new-month planner. The planner exposes setup modes for plan from scratch, copy previous month, and smart auto-fill. It reuses G3 month backing math, G4 expected inflow lifecycle and debt warnings, and G5 month-scoped subcategory limits.

No automatic rollovers ship in v1. Unused budget room returns to unallocated capacity. Category-linked payable debts and recurring expenses appear as category floors during month setup. Cash-only debts remain pre-flight reserve pressure, not category limits. Recurring cost projections are returned by a backend projection contract so web, mobile, tests, and future timeline work share one schedule interpretation.

## User Stories

1. As a budget user, I want unused budget room to disappear at month end, so that I intentionally decide what to do with saved money.
2. As a budget user, I want to start a month from scratch, so that I can rebuild my plan when my life changed.
3. As a budget user, I want to copy the previous month, so that I can quickly reuse a stable spending plan.
4. As a budget user, I want copied plans to run a pre-flight check immediately, so that I see when last month's lifestyle no longer fits this month's money.
5. As a budget user, I want smart auto-fill to satisfy required category floors, so that obvious debt and recurring obligations are not underfunded.
6. As a budget user, I want category-linked payable debts to appear as category floors, so that repayments recorded as expenses are planned inside the budget category they consume.
7. As a budget user, I want cash-only debts to remain reserve pressure, so that wallet-draining obligations do not masquerade as grocery or transport budgets.
8. As a budget user, I want recurring expenses due this month to appear as category floors, so that subscriptions and repeating bills are visible before I overspend.
9. As a budget user, I want month setup to use my local calendar month, so that the first day of the month is correct in my timezone.
10. As a budget user, I want copied subcategory limits to stay month-scoped, so that new-month setup does not mutate historical subcategory limits.
11. As a budget user, I want smart auto-fill to preserve parent/subcategory invariants, so that subcategory totals cannot exceed parent category limits.
12. As a budget user, I want recurring details to show habit cost projections, so that I understand short-term and long-term cost.
13. As a recurring user, I want default projections that match the recurring frequency, so that daily, weekly, monthly, and yearly habits are not shown with misleading horizons.
14. As a recurring user, I want saved custom projection horizons, so that I can inspect unusual horizons like 299 days or 50 weeks.
15. As a maintainer, I want setup and projection APIs to reuse existing budget and recurring math, so that future refactors do not duplicate financial rules.
16. As a tester, I want route-level tests through budget and recurring endpoints, so that G6 behavior is verified through public interfaces.

## Implementation Decisions

- Keep budgets as monthly spending permissions, not cash envelopes.
- Disable automatic budget rollover behavior for v1. Do not create rollover/cap/sweep ledger effects as an implicit month transition.
- Keep `/budgets/month-summary` as the public seam for G3 pre-flight math.
- Add a narrow month setup seam for explicit setup modes. All modes obey the "Permissive Overplanning" rule: the system NEVER hard-blocks the user from saving a plan that exceeds their capacity. Instead, it displays a "Look-Ahead Warning" prompting them to log an Expected Inflow.
- **Mode 1: Plan from Scratch:** Sets proposed category limits to zero. However, if there are active Overlay Projects that slice from a category, that slice acts as a mandatory Category Floor. The system must enforce that minimum floor (e.g., $500 for Paris Trip Overlay) and warn the user.
- **Mode 2: Copy Previous Month (Dumb Copy):** Explicitly copies limits from the previous month. The UI must visualize any active Category Floors (like Overlays or Debts) that are silently eating into this copied limit, warning the user of "Silent Starvation".
- **Mode 3: Smart Auto-Fill (Smart Copy):** Copies the previous month but performs Category Floor repair. It aggregates standard Recurring Expenses AND Overlay Project Slices into the Category Floor calculation, automatically bumping limits up to at least the computed floor amount to prevent mathematical paradoxes.
- Do not silently reserve category floors globally. Floors remain visible category minimums; G3 backing math remains the source of truth for over-planned state.
- Bucket 1 payable debts are classified by repayment accounting route. If repayment posts a categorized expense, it is a budget category floor.
- Bucket 2 cash-only debts remain cash reserve pressure.
- Use the user's effective timezone for current month defaults and pre-flight setup behavior.
- Add a backend recurring projection contract. Projection rows count scheduled occurrences over a horizon and multiply by amount.
- Saved custom recurring projection definitions are preference metadata only; they do not alter due dates, floors, budgets, wallets, debts, or expenses.

## Testing Decisions

- Prefer API-level tests through budget setup, month summary, and recurring endpoints.
- The first tracer bullet should prove unused prior-month budget room does not roll into the next month.
- Follow-up budget tests should prove setup preview modes, copy previous month, smart auto-fill floors, pre-flight warnings, and subcategory copy behavior.
- Recurring projection tests should verify public response rows for default horizons and custom saved horizons without asserting on internal helper structure.
- Docker-backed backend tests are the verification source because Redis, API, frontend, and DB run in Docker.

## Out of Scope

- Sinking fund rollover behavior.
- Automatic goal allocation of unused budget room.
- Full frontend month setup wizard in the first backend slices.
- Exact goal-delay or opportunity-cost claims.
- Future timeline aggregation beyond recurring projection detail.
- Changing recurring schedule semantics outside projection display.

## Further Notes

This PRD implements G6 from `docs/EC_IMPLEMENTATION_PLAN.md` and is grounded in EC-126, EC-131, EC-133, and EC-136. It builds on completed G3/G4/G5 behavior and preserves the rule that wallet reality beats plan metadata.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
