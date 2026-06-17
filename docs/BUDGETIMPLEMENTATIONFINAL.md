# Budget Implementation Final Decision

Date: 2026-06-08

This document is the final product and implementation decision for Sarflog
budgeting after reviewing:

- `docs/PRODUCT.md`
- `docs/BUDGETSTEP2.md`
- `docs/budget-model.md`
- the external budget, architecture, UX, persona, expected-income, and
  materialization notes supplied on 2026-06-08

Multicurrency notes were intentionally excluded from this decision.

---

## 1. Executive Decision

Sarflog budgets are monthly spending limits, not wallet-backed envelopes.

The budget system must answer three separate questions:

```text
+------------------+-----------------------------------------------+
| Question         | System that answers it                         |
+------------------+-----------------------------------------------+
| Can I pay?       | Wallets, credit, overdraft, payment capacity   |
| Should I spend?  | Budgets, sub-limits, plan health               |
| What changed?    | Goals, debts, projects, refunds, wallet truth  |
+------------------+-----------------------------------------------+
```

Final core philosophy:

```text
Wallets          = reality
Goals            = protected real money
Budgets          = monthly spending permission
Sub-limits       = lanes inside a category budget
Expected income  = future planning support, not money today
Credit/overdraft = borrowed payment capacity, not budget room
Projects         = scoped missions, either overlay or isolated
Rollover         = carried permission, not cash
```

The old Step 2 decision to defer expected income is now reversed.

Expected income must be implemented as a narrow planning feature because
without it Sarflog can only say "cash-covered" or "not allowed yet". That
makes the app too rigid for salaried users paid after the 1st, freelancers,
and anyone with normal month timing.

---

## 2. Final Rule Set

### Rule 1 - Budgets are not money

Creating a budget does not move wallet money.

```text
Create Food budget: 3,000,000

This means:
  "I permit up to 3,000,000 Food spending this month."

This does NOT mean:
  "Sarflog moved 3,000,000 into a Food wallet."
```

### Rule 2 - Active budget permission must not be absurd

Budgets are not money, but the app still must prevent fantasy plans.

Final backend rule:

```text
active monthly effective budget total after the requested change
<=
free money now + expected earned income remaining this month
```

This is an eligibility ceiling, not spendable money.

If the requested create/update/materialization would break this rule, the
backend must reject it. It is not a warning. It is not a soft status. It is a
hard product invariant.

```text
Reject:
  free money now:       861,852,283
  expected income:                0
  requested budgets: 10,700,000,000

Reason:
  requested budgets exceed valid backing by 9,838,147,717
```

The UI must never show a single "free + expected" number as if it is cash.
It should show the parts separately and block the action:

```text
Free money now:       861,852,283
Expected income:                0
Allowed backing:      861,852,283
Requested budgets: 10,700,000,000
Short by:          9,838,147,717

Action blocked:
  Add expected income or lower the budget limits.
```

### Rule 3 - Expected income is earned income only

Expected income increases planning eligibility only if it is linked to an
income source.

```text
COUNTS:
  salary
  freelance payment
  business revenue
  allowance/support marked as income

NEVER COUNTS:
  loan disbursement
  money a friend owes you
  expected refund
  asset sale
  wallet correction
  transfer
  credit limit
  overdraft limit
```

One-sentence rule:

```text
If it is not from an IncomeSource, it is not expected income for budgets.
```

### Rule 4 - Expected income supports classification, not allocation

Expected income must not:

```text
- auto-fund budgets
- auto-fund goals
- auto-pay debts
- increase wallet balances
- become "budget cash"
- be shown as money available today
```

It answers one question:

```text
Can this monthly plan work if the expected earned income arrives?
```

### Rule 5 - Credit and overdraft never increase budget room

Credit/overdraft can allow payment. They do not make the plan healthier.

```text
Credit card purchase:
  hits monthly category budget immediately
  increases liability

Credit card repayment:
  moves money from asset wallet to liability wallet
  does not hit category budget again
```

Borrowing pressure is a separate warning.

### Rule 6 - Rollover is carried permission

Rollover increases the effective monthly limit.

It does not increase free money.

```text
Food base limit:        3,000,000
Rollover from May:        800,000
Food effective limit:   3,800,000

This is extra permission.
It is healthy only if free money and expected income can support it.
```

### Rule 7 - Reallocation is zero-sum

Reallocation moves base limit from one category to another in the same month.
It should not change total plan health.

```text
Dining:    1,000,000 -> 700,000
Groceries: 2,000,000 -> 2,300,000

Total permission: unchanged
```

### Rule 8 - Sub-limits are lanes, not budgets

Sub-limits split a parent category limit.

```text
Food budget:          3,000,000
  Groceries:          1,800,000
  Dining Out:           700,000
  Coffee/snacks:        300,000
  Unassigned room:      200,000
```

The parent category remains the accounting budget.

### Rule 9 - Project behavior stays split

```text
Overlay project:
  hits monthly budgets
  reuses monthly categories/sub-limits
  acts like a reporting/planning lens

Isolated project:
  does not hit monthly budgets
  can have project-local limits/sub-limits
  acts like a separate project budget world
```

### Rule 10 - Goal-funded spending does not double-hit normal budgets

Goal-funded purchases and isolated/goal-funded project spending should keep
category analytics, but should not consume normal monthly category room.

---

## 3. Budget Materialization: Final Solution

The materialization problem:

```text
At the start of a new month, should Sarflog clone last month's budgets?
```

Bad solution A:

```text
Always clone.

Problem:
  User may have 861M free money and attempt 10.7B budgets.
  If Sarflog accepts that active plan, the app looks broken and dishonest.
  This must be rejected before active budgets are created.
```

Bad solution B:

```text
Always block and show an empty month.

Problem:
  User loses context.
  They cannot see what last month's plan was.
  The app feels hostile instead of strict.
```

Bad solution C:

```text
Clone as active but mark "awaiting funding".

Problem:
  This creates a ghost active plan.
  Users may think they still have budget permission.
  It weakens the hard cap.
```

### Final solution: Conditional Materialization With Review Preview

Sarflog should not silently create absurd active budgets.

But it also should not forget the user's prior structure.

At month start, run this logic:

```text
                +-----------------------------+
                | New month needs budgets?    |
                +-------------+---------------+
                              |
                              v
                +-----------------------------+
                | Compute proposed clone      |
                | from previous month         |
                | base limits + rollover      |
                +-------------+---------------+
                              |
                              v
                +-----------------------------+
                | Compute backing             |
                | free money now              |
                | + expected earned income    |
                +-------------+---------------+
                              |
               +--------------+--------------+
               |                             |
               v                             v
+----------------------------+   +-----------------------------+
| Proposed effective total   |   | Proposed effective total    |
| <= backing                 |   | > backing                   |
+-------------+--------------+   +--------------+--------------+
              |                                 |
              v                                 v
+----------------------------+   +-----------------------------+
| Auto-materialize active    |   | Do NOT create active        |
| budgets silently           |   | budgets                     |
+----------------------------+   +--------------+--------------+
                                               |
                                               v
                              +-----------------------------+
                              | Show materialization review |
                              | using previous plan as      |
                              | proposed limits             |
                              +-----------------------------+
```

### What "review preview" means

The review preview is not active budget permission.

It is a computed proposal from last month:

```text
Suggested July plan from June:

Food:        3,000,000
Transport:  1,000,000
Utilities:  1,000,000
Dining:     1,000,000

Total suggested: 6,000,000
Current backing: 1,200,000
Missing:        4,800,000
```

Actions:

```text
[Add expected income]
[Review and lower limits]
[Start from zero]
```

This is better than both "pending funding" and "hard empty month":

```text
+----------------------+-------------------------+----------------------------+
| Approach             | Strictness              | UX                         |
+----------------------+-------------------------+----------------------------+
| Always clone         | weak                    | smooth but dishonest       |
| Hard empty month     | strong                  | honest but contextless     |
| Pending active clone | medium                  | confusing ghost plan       |
| Review preview       | strong                  | honest and contextual      |
+----------------------+-------------------------+----------------------------+
```

### Materialization rules

1. If current month active budgets already exist, do nothing.
2. If no active budgets exist, compute previous-month proposal.
3. Simulate rollover/cap effects before deciding.
4. If proposed effective total fits backing, create active budgets.
5. If not, show review preview and block active auto-clone.
6. User can add expected income, lower limits, or start from zero.
7. Once the proposal fits backing, user can activate it.
8. Never show preview limits as active budget room.

### Backend shape for materialization

Minimal implementation does not need a new persistent proposal table.

Use computed preview endpoints first:

```text
GET  /budgets/materialization-preview?budget_year=YYYY&budget_month=M
POST /budgets/materialize
```

Preview response:

```text
budget_year
budget_month
source_budget_year
source_budget_month
free_money_now
expected_income_total
proposed_base_limit_total
proposed_rollover_total
proposed_effective_limit_total
backing_total
shortfall
can_materialize
categories[]
```

Materialize request:

```text
mode = previous_plan | custom_plan | start_empty
expected_income_ids?  # optional context only
custom_limits?        # category -> amount
```

Later, if users need to save partially edited proposals across sessions, add:

```text
BudgetMaterializationProposal
```

Do not add it first unless needed.

---

## 4. Expected Income Model

### Data model

```text
ExpectedIncome
  id
  owner_id
  income_source_id     required
  amount
  expected_date
  budget_year
  budget_month
  status               EXPECTED | RECEIVED | MISSED | CANCELLED
  matched_event_id     nullable FinancialEvent id
  note                 nullable
  created_at
  updated_at
```

Naming:

```text
EXPECTED  = income is expected and counts for plan status
RECEIVED  = matched to real income; no longer counts as expected
MISSED    = did not arrive; does not count
CANCELLED = user removed expectation; does not count
```

### API shape

```text
GET    /expected-incomes?budget_year=YYYY&budget_month=M
POST   /expected-incomes
PATCH  /expected-incomes/{id}
DELETE /expected-incomes/{id}
POST   /expected-incomes/{id}/mark-received
POST   /expected-incomes/{id}/mark-missed
POST   /expected-incomes/{id}/cancel
```

Matching to actual income can start manually.

Do not build complex auto-matching in v1.

### Month summary additions

Add fields to `/budgets/month-summary`:

```text
expected_income_total
expected_income_remaining
expected_income_items[]
plan_backing_total          internal-ish, optional; avoid prominent UI
plan_shortfall
cash_gap_to_budget_total
```

Do not display `free + expected` as one big happy number.

Display the breakdown:

```text
Free money now:        1,200,000
Expected income:
  Salary Jun 15:       8,000,000
Monthly budget total:  7,000,000
Status: Waiting on income
```

---

## 5. Plan Statuses

There are two status systems. Keep them separate.

### A. Month plan status

Applies to the whole month.

Backend enum target:

```text
COVERED_WITH_CUSHION
COVERED_NO_CUSHION
WAITING_ON_INCOME
OVER_PLANNED
```

UI labels:

```text
+-----------------------+--------------------------------------------------+
| Backend enum          | UI label                                         |
+-----------------------+--------------------------------------------------+
| COVERED_WITH_CUSHION | Cash covered                                     |
| COVERED_NO_CUSHION   | No cushion                                       |
| WAITING_ON_INCOME    | Waiting on income                                |
| OVER_PLANNED         | Over-Planned for active plans; blocked for new   |
+-----------------------+--------------------------------------------------+
```

Meaning:

```text
COVERED_WITH_CUSHION
  Free money now is greater than active monthly effective budget total.

COVERED_NO_CUSHION
  Free money now exactly covers active monthly effective budget total.

WAITING_ON_INCOME
  Free money now is not enough, but free money now + expected earned income
  remaining this month covers active monthly effective budget total.

OVER_PLANNED
  Active monthly effective budget total exceeds free money now + expected
  earned income remaining this month.
```

Important:

```text
OVER_PLANNED is for existing active plans that became invalid after reality
changed, legacy migrated data, or draft/materialization preview states.

New create/update/materialization requests that would produce OVER_PLANNED
must be rejected before they become active budgets.
```

Borrowing pressure is not a plan status. It is a separate flag:

```text
Borrowing pressure:
  Some budgeted spending was paid by credit, liability wallet,
  or overdraft-backed negative asset wallet.
```

Implementation note:

```text
Current code has 3 statuses:
  COVERED_WITH_CUSHION
  COVERED_NO_CUSHION
  OVER_PLANNED

Add exactly one new active plan status:
  WAITING_ON_INCOME
```

### B. Category budget status

Applies to one category card.

Keep the current concept:

```text
+----------------+-------------------------------+
| UI label       | Condition                      |
+----------------+-------------------------------+
| On Track       | used < 70%                     |
| Close to Limit | used >= 70% and < 90%          |
| High Risk      | used >= 90% and < 100%         |
| Over Budget    | used >= 100%                   |
+----------------+-------------------------------+
```

Do not mix category statuses with month plan statuses.

---

## 6. Capacity And Validation

### Internal formulas

```text
owned_money_now =
  sum positive active owned asset wallet balances

protected_goal_money =
  active unreleased goal allocations

free_money_now =
  max(owned_money_now - protected_goal_money, 0)

expected_income_remaining =
  sum EXPECTED income for the budget month

backing_total =
  free_money_now + expected_income_remaining

monthly_effective_budget_total =
  sum category effective limits
  (base + rollover - cap_trim - sweep)

plan_shortfall =
  monthly_effective_budget_total - backing_total
```

Do not include:

```text
credit limits
overdraft limits
liability wallet limits
expected loans
expected debt repayments
expected refunds
expected asset sales
transfers
wallet corrections
unreleased project funding unless explicitly part of project rules
```

### Create budget validation

On `POST /budgets/`:

```text
new_effective_total_after_create <= backing_total
```

If not:

```text
400 budgets.plan_exceeds_backing
```

Response detail should include:

```text
attempted_total
backing_total
shortfall
free_money_now
expected_income_remaining
```

### Update budget validation

On `PATCH /budgets/item`:

```text
delta = new_monthly_limit - old_monthly_limit

if delta <= 0:
  allow

if delta > 0:
  require effective_total_after_update <= backing_total
```

Do not block reductions that fix the plan.

### Reallocation validation

Reallocation is zero-sum, so it does not need backing validation.

It still needs:

```text
source effective available >= amount
same owner
same year/month
different category
```

### Existing active plan loses backing

Do not delete or mutate already-active budgets when reality changes after the
fact.

Examples:

```text
expected income is marked MISSED
user spends cash before payday
goal allocation protects more money
wallet balance drops
```

In those cases:

```text
status changes to OVER_PLANNED
UI asks user to reduce limits or add valid expected income
new/increased budget limits remain blocked until fixed
```

This is the only acceptable invalid state:

```text
Allowed:
  A previously valid active plan becomes invalid because backing disappeared.

Not allowed:
  User creates or updates budgets into an invalid state.
```

---

## 7. Rollover Final Decision

Use `BudgetLedger`, not wallet transactions, for budget-only chain effects.

Do not create `FinancialEvent` or `WalletLedger` rows for rollover.

Reason:

```text
Rollover changes budget permission.
It does not move wallet money.
```

The right structure is:

```text
Budget
  base monthly limit

BudgetLedger
  ROLLOVER
  CAP_TRIM
  SWEEP (deferred)

FinancialEvent / WalletLedger
  real money movement only
```

This reconciles the auditability argument with the "budgets are not money"
philosophy.

Add idempotency to BudgetLedger recomputation later:

```text
budget_ledger_key =
  owner_id + category + budget_year + budget_month + entry_type + source_month
```

Rollover effect on plan health:

```text
base limits      = user plan
rollover         = carried permission
effective limits = what the category can spend this month

Plan health compares effective limits against backing.
```

So rollover can push a plan from "Cash covered" to "Waiting on income".
If rollover would push a newly materialized plan beyond backing, active
materialization is blocked and the user sees the review preview instead.
If backing disappears after the plan was already valid, the existing plan moves
to `OVER_PLANNED`, rendered as "Over-Planned".

---

## 8. Sub-Limits Final Decision

Use product wording:

```text
Sub-limits
Category breakdown
Monthly lanes
```

Avoid:

```text
Subcategory budget
Envelope
Child envelope
Budget cash
```

### Data model target

Current implementation stores a limit directly on `UserSubcategory`.

That can work short term, but the final clean model should separate identity
from monthly limit:

```text
UserSubcategory
  id
  owner_id
  category
  name
  is_active

BudgetSubcategoryLimit
  id
  budget_id
  subcategory_id
  monthly_limit
  is_active_for_budget
```

Why this is better:

```text
Subcategory name persists across months.
Limit can differ by month.
Materialization can clone sub-limit structure safely.
Historical months remain stable.
Deleting/deactivating a sub-limit does not rewrite old months.
```

MVP can keep `UserSubcategory.monthly_limit`, but the final target should be
the monthly join table above.

### UI placement

Do not show sub-limits as noisy pills on cards.

Do not make a tiny "create subcategory" modal the main surface.

Sub-limits belong inside Budget Details:

```text
+---------------------------------------------------------------+
| Budget Details: Food - June 2026                              |
+--------------------------------------+------------------------+
| Overview                             | Actions                |
| - spent / effective limit            | - Update limit         |
| - base / rollover / trim             | - Add sub-limit        |
| - plan impact                        | - Reallocate room      |
|                                      | - Delete budget        |
| Sub-limits                           |                        |
| [Groceries] 1.2M / 1.8M [======----] |                        |
| [Dining]    0.8M / 0.7M [==========] |                        |
| [Unassigned] 0.3M                    |                        |
|                                      |                        |
| Recent budget activity               |                        |
+--------------------------------------+------------------------+
```

---

## 9. Budget Page UI Flow

### Dashboard top

Show the month-level truth first:

```text
+------------------+------------------+------------------+------------------+
| Free money now   | Expected income  | Budget total     | Plan status      |
| 861.9M           | 0                | 800M             | No cushion       |
| owned - goals    | income only      | effective limits | 61.9M room       |
+------------------+------------------+------------------+------------------+
```

If the user attempts an absurd budget total, do not show it as an accepted
plan. Block it:

```text
+------------------------------------------------------------------------+
| Cannot set this budget                                                  |
| Requested monthly budgets exceed valid backing by 9,838,147,717.        |
| Add expected income or lower the limit.                                 |
| [Add expected income] [Edit amount]                                     |
+------------------------------------------------------------------------+
```

If waiting on income:

```text
+------------------------------------------------------------------------+
| Waiting on income                                                       |
| Your budgets exceed current free money by 5,800,000.                   |
| They fit if expected income arrives:                                    |
| - Salary, Jun 15: 8,000,000                                             |
| [Add income] [Adjust budgets]                                           |
+------------------------------------------------------------------------+
```

If an existing plan is over-planned because backing disappeared:

```text
+------------------------------------------------------------------------+
| Over-Planned                                                            |
| This plan exceeds valid backing. Reduce limits or add valid expected     |
| income before increasing any budgets.                                   |
| [Add expected income] [Review limits]                                   |
+------------------------------------------------------------------------+
```

### Budget cards

Cards are scanning surfaces, not admin dashboards.

Final desktop card:

```text
+------------------------------------------------+
| Transport                         On Track     |
| June 2026                                      |
| 400,000 / 50,000,000 UZS                      |
| [===========-----------------------------]     |
| 49,600,000 remaining                          |
|                                                |
| [View Expenses]                         [...]  |
+------------------------------------------------+
```

The bottom action rail appears on desktop hover/focus.

Visible:

```text
View Expenses
```

Overflow:

```text
View details
Update limit
Add sub-limit
----------------
Delete budget
```

This follows the general pattern used by mature product UIs: keep primary
actions visible, move secondary/admin actions into contextual overflow, and
separate destructive actions.

### View Expenses

This should become a wide modal, not just a route.

```text
+-----------------------------------------------------------------------+
| Food - June 2026                                          [close]     |
| 2,300,000 spent / 3,000,000 limit    700,000 remaining                |
+-----------------------------------------------------------------------+
| Search expenses...     [All] [Refunds] [Credit paid] [Projects]       |
+-----------------------------------------------------------------------+
| Date       Title                  Wallet        Budget impact         |
| Jun 02     Korzinka groceries     Humo          -420,000              |
| Jun 04     Refund: groceries      Humo          +80,000               |
| Jun 08     Dining out             Credit card   -180,000  borrowed    |
+-----------------------------------------------------------------------+
| Net budget impact: 520,000                                            |
+-----------------------------------------------------------------------+
```

Rows should link to Expense Details.

### View Details

Budget Details should become a premium wide modal/sheet, not a dry full page.

Tabs or sections:

```text
Overview
Expenses
Sub-limits
Rollover
Projects
Activity
```

Actions inside details are context-specific and not counterintuitive:

```text
Sub-limits section -> Add sub-limit
Rollover section   -> edit rollover settings
Header actions     -> Update limit, Delete
```

Card-level overflow remains for quick access.

---

## 10. Expense Flow And Budgets

Normal expense:

```text
requires monthly category budget
hits wallet
hits monthly budget
may hit overlay project
may hit sub-limit
```

Refund:

```text
hits wallet as inflow
reduces signed budget usage
keeps link to original expense
```

Credit card expense:

```text
hits category budget now
increases liability now
repayment later does not hit category budget
```

Isolated project expense:

```text
hits wallet
hits project
keeps category analytics
does not require normal monthly budget
does not hit monthly budget
```

Goal-funded purchase:

```text
hits wallet
consumes goal funding
keeps category analytics
does not hit normal monthly budget
```

---

## 11. Backend Implementation Order

### Phase 2B - Expected Income and Plan Health

1. Add `ExpectedIncome` model and migration.
2. Add expected-income CRUD endpoints.
3. Add expected-income test helpers.
4. Add budget plan backing helpers:

```text
get_expected_income_remaining(...)
get_budget_plan_backing(...)
validate_budget_plan_capacity(...)
```

5. Update `/budgets/month-summary`.
6. Add `WAITING_ON_INCOME` status.
7. Rename UI labels to clearer copy.
8. Add create/update budget backing validation.
9. Add materialization preview endpoint.
10. Update materialization to conditional active clone.

### Phase 2C - Budget UI Premium Surfaces

1. Build View Expenses modal.
2. Convert Budget Details to wide modal/sheet.
3. Move sub-limit management into Budget Details.
4. Keep card action rail clean.
5. Add expected-income banner and creation flow.

### Phase 2D - Sub-Limit Model Cleanup

1. Keep current `UserSubcategory.monthly_limit` short term.
2. Add `BudgetSubcategoryLimit` when month-specific sub-limits are needed.
3. Migrate existing limits into current/future month rows.
4. Update materialization to clone sub-limit plan.

### Phase 2E - Rollover and Alert Consistency

1. Ensure budget alerts use effective limit, not raw monthly limit.
2. Show rollover as carried permission.
3. Keep BudgetLedger, not wallet transaction rows, for rollover.
4. Defer sweep until Goals/Projects are stable.

---

## 12. Tests Required

### Expected income

- Create expected income linked to IncomeSource.
- Reject or ignore expected loan/debt/refund/asset sale for budget backing.
- Expected income increases plan eligibility.
- Received expected income no longer counts as expected.
- Missed expected income downgrades plan health.
- Cancelled expected income does not count.

### Budget capacity

- Creating budget above free money fails if no expected income.
- Creating budget above free money succeeds if expected earned income covers it.
- Creating budget above free money + expected income fails.
- Increasing a budget limit beyond backing fails.
- Reducing a budget limit always succeeds.
- Reallocation remains zero-sum and does not require backing increase.

### Month summary

- Cash covered status when budgets fit free money.
- No cushion status when budgets exactly/tightly fit free money.
- Waiting on income when budgets exceed cash but fit expected income.
- OVER_PLANNED status, rendered as Over-Planned, when an existing valid plan loses backing after reality changes.
- Create/update/materialization rejects budgets that would exceed free money + expected income.
- Borrowing pressure is independent from plan status.
- Credit and overdraft do not increase backing.

### Materialization

- New month auto-materializes when proposed effective total fits backing.
- New month does not active-materialize when proposed total exceeds backing.
- Preview returns previous-month proposed categories and shortfall.
- Adding expected income can make preview materializable.
- Custom reduced limits can materialize.
- Start-empty creates no active category limits except explicit user choices.

### Rollover

- Rollover increases effective limit.
- Rollover can move plan from cash covered to waiting on income.
- If rollover pushes a new materialization beyond backing, materialization is
  blocked and shown as review preview.
- Cap trim reduces effective limit.
- Alerts compare spend to effective limit.

### Sub-limits

- Sub-limit totals cannot exceed parent budget limit.
- Expense with sub-limit hits parent and sub-limit.
- Expense without sub-limit hits parent and unassigned room.
- Isolated project local sub-limits do not affect monthly sub-limits.
- Historical expenses block hard delete or force deactivation.

---

## 13. Non-Goals

Do not build these in the next implementation pass:

```text
expected refunds as planning capacity
expected debt repayments as planning capacity
expected loan disbursement as planning capacity
expected asset sales as planning capacity
automatic salary allocation
automatic goal funding from expected income
automatic debt payment from expected income
confidence scoring for expected income
AI income prediction
complex timeline forecast
sweep-to-goal automation
physical wallet transactions for rollover
full multicurrency budget model
mobile/tablet budget redesign
```

---

## 14. Proof And Product References

The final decision is not a clone of any one app. It combines strict financial
truth with practical planning for local salary timing.

External reference points:

```text
YNAB:
  Strong proof for strictness.
  Their method emphasizes assigning only money currently owned.
  This supports Sarflog's "free money now" and hard-friction instincts.
  https://www.ynab.com/the-four-rules
  https://www.ynab.com/guide/where-does-my-money-go

Monzo:
  Strong proof for separating money into pots/jars and using spending
  targets/trends as a tracking layer.
  Salary Sorter also shows that salary allocation is safest after money
  arrives, not before.
  https://monzo.com/help/budgeting-overdrafts-savings/trends-spending-and-balance-web
  https://monzo.com/salary-sorter

Revolut:
  Strong proof for quick-glance analytics plus deeper dive surfaces,
  and for separating pockets/analytics/future planning.
  https://www.revolut.com/pockets/

Material Design:
  Strong proof for contextual overflow menus and keeping primary actions
  separate from secondary actions.
  https://m1.material.io/components/menus.html
```

How Sarflog differs:

```text
YNAB is stricter: only current money.
Monzo/Revolut are smoother: targets, pots, analytics.

Sarflog final model:
  current money remains reality,
  expected earned income supports plan status,
  active budgets cannot become fantasy permission,
  future income is never shown as spendable today.
```

This is the best fit for Uzbek/local salary timing:

```text
User paid on 1st:
  usually Cash covered.

User paid on 15th:
  often Waiting on income.

Freelancer:
  moves between OVER_PLANNED/Over-Planned, Waiting on income, and Cash covered.

Debt-heavy user:
  expected loans and repayments do not inflate normal budget permission.
```

---

## 15. Final UX Copy

Use:

```text
Free money now
Expected income
Monthly budget total
Budget room after plan
Cash covered
No cushion
Waiting on income
Over-Planned
Borrowing pressure
Carried permission
Sub-limit
Category breakdown
View Expenses
View details
```

Avoid:

```text
Envelope balance
Budget cash
Move budget money
Allocate salary
Credit-backed budget
Expected money-in
Envelope funding language for budget plan health
Subcategory envelope
Database terms
Ledger terms
```

`OVER_PLANNED` is the backend status for existing active plans that exceed
valid backing. User copy should say:

```text
Over-Planned
```

or:

```text
This plan exceeds valid backing. Reduce limits or add valid expected income.
```

---

## 16. Final Acceptance Criteria

The budget system is correct when:

```text
[ ] Budgets are never presented as wallet money.
[ ] Expected earned income exists and powers Waiting on income.
[ ] Expected non-income never powers budget backing.
[ ] Budget create/update cannot create fantasy active permission.
[ ] Month materialization cannot silently clone an absurd active plan.
[ ] Materialization preview preserves context when auto-clone is blocked.
[ ] Rollover is shown as carried permission.
[ ] Credit and overdraft never increase budget backing.
[ ] Borrowing pressure is separate from budget status.
[ ] Category cards stay clean and action-light.
[ ] View Expenses explains what moved the category.
[ ] Budget Details explains base, rollover, sub-limits, projects, activity.
[ ] Sub-limits are visibly subordinate to parent category budgets.
[ ] Overlay projects hit monthly budgets.
[ ] Isolated projects do not hit monthly budgets.
[ ] Goal-funded spending does not double-hit normal monthly budgets.
```

This final decision supersedes the "expected income deferred" section in
`docs/BUDGETSTEP2.md`.
