# Budget Model

This is my current understanding of the **budget architecture** from:

- `app/models.py`
- `app/routers/budget.py`
- `app/services/budget_service.py`

I am writing this from the code, not from what the current frontend happens to show.

---

## 1. Core philosophy

The budget system is **parent-category monthly envelope first**.

That means one budget is:

- one owner
- one category
- one month
- one year

Example:

- `Groceries`
- `May 2026`
- `2,000,000`

That is the parent envelope.

Subcategories are **not top-level budgets**.
They are partitions inside a category budget.

Projects are **not budgets themselves** either.
They are an additional planning/execution layer that may or may not affect monthly budgets depending on `is_isolated`.

---

## 2. Main budget tables

### `Budget`

Relevant fields:

- `category`
- `monthly_limit`
- `budget_year`
- `budget_month`
- `auto_created`
- `max_envelope_balance`
- `max_rollover_amount`
- `rollover_mode`
- `sweep_target_goal_id`

Meaning:

- `monthly_limit`
  - the base parent envelope amount
- `auto_created`
  - budget was materialized automatically from continuity rules
- `max_envelope_balance`
  - cap on how large next month’s envelope can become
- `max_rollover_amount`
  - controls rollover size
- `rollover_mode`
  - `FIXED` or `PERCENT`
- `sweep_target_goal_id`
  - optional configured sweep target goal

### `UserSubcategory`

Relevant fields:

- `owner_id`
- `category`
- `name`
- `is_active`
- `monthly_limit`

Meaning:

- subcategory belongs to a category
- it is user-defined
- it may have its own monthly cap

### `BudgetLedger`

This is very important.

It stores month-chain effects, not raw spending.

Relevant fields:

- `category`
- `budget_year`
- `budget_month`
- `amount`
- `entry_type`

Current effect types used in code:

- `ROLLOVER`
- `SWEEP`
- `CAP_TRIM`

Meaning:

- this is what modifies the effective envelope over time

---

## 3. Parent budget model

Budgets are unique by:

- owner
- category
- year
- month

So you cannot have two `Groceries` budgets for the same month.

That means the budget system is fundamentally:

- **one category -> one budget envelope -> one month**

This is why the UI should not mislead the user into thinking subcategories are independent sibling budgets.

---

## 4. Effective limit is not just monthly limit

The budget system distinguishes:

- base monthly limit
- effective monthly limit

The service computes:

`effective_limit = monthly_limit + rollover - sweep - cap_trim`

Then:

- `remaining = effective_limit - spent`
- `effective_available = max(remaining, 0)`

So the user-facing amount is not just the raw `monthly_limit`.

This is why budget cards should explain:

- base plan
- month-chain effects
- actual available envelope

---

## 5. Spending and isolated projects

Budget spending calculation uses `_isolated_project_spend_filter()`.

Meaning:

- expenses linked to `is_isolated=true` projects do **not** count against monthly budget envelopes
- expenses with:
  - no project
  - non-isolated project
  - null project relation

do count against monthly budget envelopes

This is a major part of the philosophy.

### Real-world example

#### Non-isolated project

Project:

- `Wedding Preparation`
- `is_isolated = false`

Expense:

- Flowers 700k

Effect:

- counts against wedding project
- also counts against monthly category budget

#### Isolated project

Project:

- `Kitchen Renovation`
- `is_isolated = true`

Expense:

- Oven 4M

Effect:

- counts against project
- does **not** consume monthly household budget space

---

## 6. Budget creation / update philosophy

### Create budget

Route:

- `POST /budgets/`

Important checks:

- unique per owner/category/month
- month window validation
- rollover fields validation
- optional sweep goal must exist

Then:

- budget is created
- `recompute_budget_chain(...)`
- output is returned with computed values

### Update budget

Route:

- `PATCH /budgets/item`

Can update fields like:

- `monthly_limit`
- rollover fields
- envelope cap
- sweep target goal

Then chain is recomputed again.

So the budget chain is intended to be recomputation-driven, not hand-maintained in UI memory.

---

## 7. Lazy month materialization

This is one of the most important behaviors.

Function:

- `materialize_budget_for_month(...)`

Meaning:

- if budget for a future month does not exist
- service can recursively look backward
- find previous month source budget
- clone continuity fields
- create missing month automatically

Cloned fields include:

- `monthly_limit`
- `max_envelope_balance`
- `max_rollover_amount`
- `rollover_mode`
- `sweep_target_goal_id`

This is why expense creation can sometimes create missing future monthly budget continuity instead of just failing.

### Real-world example

You had:

- Groceries April
- Groceries May

But no June budget row yet.

Then on June 2 you create a valid expense in Groceries.

Backend can:

- materialize June from May continuity
- then allocate the expense

So the app should not force the user to manually create every month first if continuity exists.

---

## 8. Rollover / sweep / cap philosophy

### `_rollover_policy_amount`

If leftover is positive:

- no max rollover -> all leftover may roll
- `FIXED` mode -> cap by absolute amount
- `PERCENT` mode -> cap by percent of leftover

### `max_envelope_balance`

This limits how large the next envelope can become.

So even if leftover exists, rollover can be trimmed by the next month balance cap.

### `SWEEP` vs `CAP_TRIM`

If excess leftover exists after allowed rollover:

- if budget has `sweep_target_goal_id`, excess is recorded as `SWEEP`
- otherwise excess becomes `CAP_TRIM`

Important note:

Right now this is still budget-ledger logic.
It does **not** automatically mean real wallet cash moved.

That distinction matters philosophically.

---

## 9. Reallocation philosophy

Route:

- `POST /budgets/reallocate`

Behavior:

- moves base monthly limit from one category to another
- only inside the same month/year
- from and to categories must differ
- source must have enough effective available room

Implementation detail:

- source monthly limit is reduced
- target monthly limit is increased
- chain recomputed for both categories

### Real-world example

May budgets:

- Dining Out = 1,000,000
- Groceries = 2,000,000

User wants:

- move 300,000 from Dining Out to Groceries

Result:

- Dining Out base limit becomes 700,000
- Groceries base limit becomes 2,300,000

This is not a wallet transfer.
It is envelope reallocation.

---

## 10. Recalculate philosophy

Route:

- `POST /budgets/recalculate`

This is a chain repair / refresh endpoint for one category.

Meaning:

- recompute that category’s monthly chain
- return rebuilt computed outputs

This is useful because the budget model is continuity-based.

---

## 11. Subcategory philosophy

This is the area that the current frontend explains poorly.

### What subcategories are

Subcategories are:

- child partitions inside a parent category budget

They are **not** top-level monthly budgets.

### How they are created

Routes:

- `GET /budgets/{budget_id}/subcategories`
- `POST /budgets/{budget_id}/subcategories`
- `PATCH /budgets/subcategories/{subcategory_id}`
- `DELETE /budgets/subcategories/{subcategory_id}`

Creation requires:

- parent budget exists
- subcategory category must match parent budget category
- total child limits cannot exceed parent monthly limit

### Important nuance

`UserSubcategory` itself is stored by:

- owner
- category
- name

not by month.

But operationally, create/update flows are parent-budget contextual.

So conceptually it behaves like:

- “subcategory partition under category planning”

and not like:

- “a totally separate free-floating budget row”

### Real-world example

Parent budget:

- Groceries May 2026 = 2,000,000

Children:

- Meat = 800,000
- Dairy = 500,000
- Vegetables = 300,000

Meaning:

- the Groceries parent still exists
- subcategories partition the envelope

---

## 12. Subcategory spend rules

Subcategory spend is validated by month.

If subcategory has a monthly limit:

- spend in that month cannot exceed it

But:

- if linked project is isolated, subcategory limit validation is bypassed

That is consistent with parent budget behavior.

### Real-world example

Subcategory:

- `Meat`
- monthly limit = 800,000

User already spent:

- 750,000

Then tries:

- another 100,000 in Meat

Result:

- rejected

Unless that spending belongs to an isolated project, in which case the monthly envelope rules are intentionally bypassed.

---

## 13. Budget detail philosophy

`get_budget_detail(...)` returns more than just the budget row.

It includes:

- computed budget state
- subcategories
- recent activity
- project spending overlay
- expense count

### Recent activity

Shows recent events affecting this budget, including:

- title
- amount
- type
- date
- session state
- subcategory
- project
- merge group

### Project spending

Shows project-linked spend inside this budget, but only for non-isolated budget-visible project effects.

This supports the idea that budget detail is a planning inspection surface, not just a form.

---

## 14. Project budget overlay philosophy

Route:

- `GET /budgets/projects`

This returns project-level budget summaries:

- project totals
- released funding
- remaining funding
- project category breakdown

So the budget domain is aware that monthly planning and project planning overlap, but they are not identical.

---

## 15. What this means for UI

This is the biggest frontend takeaway from the backend design.

### The budget page should teach:

1. parent budget first
2. subcategories are child partitions inside that parent
3. monthly limit is not the whole story
4. effective available depends on rollover / sweep / cap trim
5. isolated projects bypass monthly budget pressure

### The current frontend gap

The current page still does not explain clearly enough:

- where to add subcategories
- that subcategories belong under a parent budget
- why effective limit may differ from base limit

So the right UI path should probably be:

- parent budget card
- `Manage Subcategories`
- detail panel/page showing:
  - base limit
  - rollover
  - sweep
  - cap trim
  - effective limit
  - subcategory partitions
  - recent activity
  - project overlay

---

## 16. Real-world examples

### Example 1: Normal monthly budget

- Groceries May 2026 = 2,000,000
- spent = 1,500,000
- remaining = 500,000

Simple parent envelope case.

### Example 2: Parent + subcategories

- Groceries May 2026 = 2,000,000
- Meat = 800,000
- Dairy = 500,000
- Vegetables = 300,000

This is the same parent envelope, but partitioned internally.

### Example 3: Rollover

April Groceries:

- effective limit = 2,000,000
- spent = 1,600,000
- leftover = 400,000

If policy allows full rollover:

May effective budget gets a `ROLLOVER` entry.

### Example 4: Cap trim

If raw rollover would push next month above allowed envelope cap:

- extra leftover is trimmed
- recorded as `CAP_TRIM`

### Example 5: Non-isolated project spend

Project:

- Wedding Preparation
- `is_isolated = false`

Expense:

- Flowers 700,000

This appears in both:

- project spend
- relevant monthly budget pressure

### Example 6: Isolated project spend

Project:

- Kitchen Renovation
- `is_isolated = true`

Expense:

- Oven 4,000,000

This affects the project, not the monthly household envelope.

---

## 17. My current working conclusion

My current understanding is:

- **Budgets are parent monthly category envelopes**
- **Subcategories are child partitions inside those envelopes**
- **Effective availability is computed, not just stored**
- **Budget chain continuity and lazy future-month materialization are important**
- **Isolated project spend is deliberately excluded from monthly budget pressure**

The main frontend work that should follow from this is:

- make subcategory management explicit
- teach parent/child structure visually
- stop presenting budgets like flat CRUD cards only
- show effective planning state, not just raw monthly limit

