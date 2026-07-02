# PRD: G33 - Overlay Project Target Estimate vs Operational Reserved Scope

Labels: `ready-for-agent`, `architecture-note`

## Problem Statement

Overlay projects need two different numbers that can look similar but mean very different things:

1. A user may want a psychological planning number, such as "This trip should cost around 5,000,000 UZS."
2. Sarflog must enforce only real monthly spending permission, such as "This July project slice reserves 200,000 UZS from July Groceries."

If these are collapsed into one field called `total_limit`, the product becomes confusing. Users may think they have permission to spend against a future total that has not been allocated from any real monthly budget. That violates Sarflog's reality-first permission model.

## Core Decision

Overlay projects should use a **combination model**:

- **Operational reserved scope** is derived from real monthly project slices.
- **Target estimate** is optional user-entered metadata.

The operational number is the source of truth for budget pressure. The target estimate is planning context only.

## Terminology

### Operational Reserved Scope

Operational reserved scope means the sum of actual month-scoped overlay reservations already created for the project.

It answers:

- "How much monthly spending permission has this project reserved so far?"
- "How much permission is reserved in this selected month?"
- "How much of the parent category's monthly limit is currently set aside for project tracking?"

It is derived from rows such as `ProjectCategoryMonthlyLimit` and `ProjectSubcategoryMonthlyLimit`.

It is real operational data because it comes from an actual monthly budget.

### Target Estimate

Target estimate means the user's expected total project cost.

It answers:

- "What do I think this project might cost overall?"
- "How large is this project in my head?"
- "Am I roughly on track compared with my original expectation?"

It is optional metadata. It does not create budget permission. It does not increase spending capacity. It does not reserve current or future monthly category limits.

Avoid calling this a "limit" in the UI. Use names like:

- Target estimate
- Expected total cost
- Project cost estimate

Avoid:

- Total limit
- Funded amount
- Project balance
- Project cash

## Why The Difference Matters

Sarflog budgets are spending permission, not physical money containers.

An overlay project does not own cash. It marks part of a monthly category's permission as project-related. Spending still posts as ledger truth and still belongs to the parent monthly budget.

If Sarflog shows a project "total limit" of 5,000,000 UZS before those months are allocated, the user may reasonably believe they have 5,000,000 UZS of usable permission. That is false unless real monthly slices have been created.

## Real-Life Scenario 1: One-Month BBQ Project

The user has:

- July Groceries monthly permission: `1,000,000`
- BBQ project reservation from July Groceries: `200,000`

This means:

- General Groceries permission for July: `800,000`
- BBQ project permission inside July Groceries: `200,000`
- Total July Groceries permission remains: `1,000,000`

Then the user spends:

- `100,000` on BBQ groceries
- `500,000` on normal groceries

Result:

- Total July Groceries usage: `600,000`
- Parent Groceries remaining: `400,000`
- BBQ project reserved remaining: `100,000`
- General Groceries remaining: `300,000`

Nothing physical moved between pockets. The project simply labeled part of July's Groceries permission as project-related.

If the user entered a target estimate of `500,000` for the BBQ project, that estimate stays separate:

- Target estimate: `500,000`
- Reserved this month: `200,000`
- Spent this month: `100,000`
- Reserved so far: `200,000`

The target estimate helps the user think. The reservation controls budget pressure.

## Real-Life Scenario 2: Multi-Month Trip

The user creates a trip from July 1 to August 15.

They estimate:

- Trip target estimate: `5,000,000`

In July, they reserve:

- `500,000` from July Groceries
- `500,000` from July Dining Out

July operational reserved scope:

- Reserved this month: `1,000,000`
- Reserved so far: `1,000,000`
- Target estimate: `5,000,000`

In August, Sarflog must not automatically carry July's unused permission forward. August has its own monthly plan. During August setup, the user may reserve a new slice:

- `700,000` from August Transport
- `300,000` from August Dining Out

After August allocation:

- Reserved this month for August: `1,000,000`
- Reserved so far across created slices: `2,000,000`
- Target estimate: `5,000,000`

The target estimate does not grow. The operational reserved scope grows only when real monthly slices are created.

## Real-Life Scenario 3: Project Overspends Its Slice

The user has:

- July Groceries monthly permission: `1,000,000`
- Project reservation from July Groceries: `200,000`

The user spends:

- `250,000` on project-linked Groceries
- `500,000` on normal Groceries

Result:

- Total July Groceries usage: `750,000`
- Parent Groceries still has `250,000` remaining
- Project is over its July reserved slice by `50,000`
- General Groceries capacity effectively absorbs that extra `50,000`

The expense must not be blocked just because the project slice is exceeded. Sarflog saves truth first. The consequence is visible reduced general category capacity and an over-reserved/over-spent project state.

## UI Rules

Overlay project cards should not say "No total limit."

Instead, show:

- Reserved this month
- Reserved so far
- Spent this month or spent total, depending on selected context
- Remaining this month
- Target estimate, if set

Recommended card language:

```text
Reserved this month: 1,000,000 UZS
Reserved so far: 1,000,000 UZS
Target estimate: 5,000,000 UZS
```

If no target estimate is set:

```text
Reserved this month: 1,000,000 UZS
Reserved so far: 1,000,000 UZS
Target estimate: Not set
```

Do not display:

```text
No total limit
```

That phrase is technically true only if the old `total_limit` field is null, but it communicates the wrong product meaning for overlay projects.

## Data Model Guidance

Use existing operational fields for truth:

- `selected_month_reserved_amount`
- `total_reserved_scope`
- `category_breakdown[].limit_amount`
- `category_breakdown[].spent`
- `category_breakdown[].remaining`

Add a separate optional metadata field if needed:

- `target_estimate`
- or `estimated_total_cost`

This field should:

- Be nullable.
- Be editable while the project is active.
- Never create monthly reservations.
- Never be used as a hard blocker for expense posting.
- Be clearly labeled as an estimate in frontend copy.

## Acceptance Criteria

- Overlay project UI distinguishes operational reserved scope from target estimate.
- Overlay project cards do not use isolated-project `total_limit` language.
- The project wizard may optionally ask for a target estimate, but this field must be labeled as non-operational planning context.
- Current-month allocation remains mandatory for operational overlay creation.
- Future-month allocations are created only when those months are set up.
- Tests prove overlay cards render reserved scope even when `total_limit` is null.

## Non-Goals

- Do not turn overlay projects into cash envelopes.
- Do not roll unused monthly project permission into future months.
- Do not enforce target estimate as a hard spending limit.
- Do not create future-month reservations during initial project creation.

## Senior Engineering Judgment

The target estimate exists for human psychology. It helps users name the size of a project before all monthly plans exist.

The operational reserved scope exists for financial correctness. It is the only number that should affect monthly budget pressure because it is backed by actual monthly spending permission.

Keeping these concepts separate protects both sides of the product:

- The user gets a planning anchor.
- The ledger and budget model stay honest.

Mixing them would create fake permission and future-month confusion. Separating them gives Sarflog a clean mental model: **estimate the whole project, reserve real monthly permission one month at a time.**
