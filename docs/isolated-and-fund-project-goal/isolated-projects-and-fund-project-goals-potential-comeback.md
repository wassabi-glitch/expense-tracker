# Isolated Projects And Fund Project Goals: Potential Comeback

Date: 2026-07-14

Status: idea note, not an active implementation plan

Related decision: `docs/adr/0022-freeze-isolated-projects-and-fund-project.md`

## Core Idea

Isolated Projects may become viable again if they stop acting like a second
envelope-budgeting system.

The old model tried to make the saved project money behave like a miniature
budget planner:

```text
Project saved pile
  -> allocate to project categories
  -> optionally allocate to project subcategories
  -> then allow expenses only inside those project allocations
```

That created too much complexity because the project had to coordinate:

- wallet-backed project funding
- monthly budget categories
- project-specific category allocations
- project-specific subcategory allocations
- real payment wallets
- monthly budget bypass behavior
- top-up, rebalance, release, and wrap-up flows

The simpler comeback idea is:

```text
Project saved pile
  -> one pooled project funding balance
  -> expenses spend from the project pile
  -> expense categories remain labels/reporting dimensions
  -> monthly category limits are not consumed
```

In this model, the user does not pre-plan how the project pile will be split
across Food, Transport, Hotel, Family, Electronics, or any other category.
They only record actual project expenses as they happen.

## Simple Example

A user saves money for a Dubai Trip.

```text
Dubai Trip saved pile:       10,000,000
Spent so far:                 3,200,000
Remaining project money:      6,800,000
```

That is enough for the main spending control.

The project does not need this setup step:

```text
Food project allocation:       2,000,000
Transport project allocation:  1,500,000
Hotel project allocation:      4,000,000
Activities allocation:         2,500,000
```

Instead, the user records real spending:

```text
Expense: Airport taxi
Amount: 300,000
Category: Transport
Project: Dubai Trip

Effect:
- wallet money goes down by 300,000
- Dubai Trip remaining project money goes down by 300,000
- monthly Transport budget limit is not consumed
- Transport remains useful for reporting and analytics
```

## Mental Model

The project pile is the spending source of intent.
The expense category is the reporting label.
The payment wallet is the real-world cash/card source.

```text
                  records real outflow
Payment wallet ----------------------------+
                                           |
                                           v
                                    Project expense
                                           |
                     +---------------------+---------------------+
                     |                                           |
                     v                                           v
        reduces isolated project pile              keeps category label
        but not monthly category budget            for analytics/reporting
```

## Old Model Versus New Model

### Old Model

```text
Fund Project Goal / Direct Project Funding
                 |
                 v
        Isolated project stash
                 |
        +--------+---------+
        |        |         |
        v        v         v
      Food   Transport   Hotel
        |        |         |
        v        v         v
    expenses expenses  expenses
```

Problems:

- The user had to guess project category needs before reality happened.
- Category allocation and rebalancing became required product flows.
- Spending could fail because project category funding was not assigned, even
  when the project still had saved money.
- The system had to explain why a project had money but a category inside the
  project did not.
- Wallet funding and real payment wallets became harder to reason about.

### New Model

```text
Fund Project Goal / Direct Project Funding
                 |
                 v
        Isolated project pile
                 |
        +--------+---------+---------+
        |        |         |         |
        v        v         v         v
      Food   Transport   Hotel   Anything else
    expense   expense   expense    expense
```

Rules:

- The project has one saved pile.
- Any valid expense category can be used on a project expense.
- The category does not need project-specific pre-allocation.
- The expense does not hit monthly category limits.
- The project total spent should not exceed the project pile unless an explicit
  overrun policy exists.

## Quick Add Flow

The Quick Add expense form can support this model without requiring a special
project budgeting screen.

```text
User enters:
- title: Airport taxi
- amount: 300,000
- category: Transport
- wallet: Cash
- project: Dubai Trip

Posting result:
- Wallet Cash decreases by 300,000
- Financial event is posted
- Entity ledger keeps category = Transport
- Entity ledger keeps project_id = Dubai Trip
- Entity ledger has no monthly budget_id
- Dubai Trip spent increases by 300,000
- Dubai Trip remaining money decreases by 300,000
```

Diagram:

```text
+------------------+       +-----------------------+
| Quick Add Expense| ----> | Expense Posting       |
+------------------+       +-----------------------+
                                |
                                v
                       +------------------+
                       | Is project       |
                       | isolated?        |
                       +------------------+
                         | yes       | no
                         v           v
              +----------------+   +----------------------+
              | skip monthly   |   | resolve monthly      |
              | budget impact  |   | budget normally      |
              +----------------+   +----------------------+
                         |
                         v
              +--------------------------+
              | reduce project remaining |
              | by posted expense amount |
              +--------------------------+
```

## Session Draft Flow

Session Drafts become especially useful for this model because a receipt can
contain mixed project-intended items.

Example:

```text
Receipt title: Dubai mall
Wallet: Visa card

Items:
- Lunch, 180,000, Dining Out, project = Dubai Trip
- Metro card, 70,000, Transport, project = Dubai Trip
- Toothpaste, 25,000, Personal Care, project = none
```

Posting result:

```text
Dubai Trip pile reduced by: 250,000
Monthly Dining Out budget impact: 0
Monthly Transport budget impact: 0
Monthly Personal Care budget impact: 25,000
Visa wallet outflow: 275,000
```

Diagram:

```text
Session Draft
  |
  +-- Item 1: Dining Out, Dubai Trip ----> project pile only
  |
  +-- Item 2: Transport, Dubai Trip -----> project pile only
  |
  +-- Item 3: Personal Care, no project -> monthly budget
  |

One posted financial event with multiple entity legs
```

## Fund Project Goal Comeback

Fund Project Goals can also become simpler.

Old idea:

```text
Goal saves money
  -> graduates into isolated project
  -> released funding is split into project categories
  -> expenses spend inside those project categories
```

New idea:

```text
Goal saves money
  -> graduates into isolated project pile
  -> expenses spend from the single project pile
  -> categories remain labels, not project allocations
```

Example:

```text
Goal: Fund Dubai Trip
Target: 10,000,000
Saved: 10,000,000

Graduation:
Creates project "Dubai Trip"
Project pile: 10,000,000
Goal status: graduated/closed

Later expense:
Hotel booking, 3,000,000, Travel, Dubai Trip

Project pile after expense:
7,000,000
```

## Product Language

Prefer language like:

```text
Project saved pile
Project money
Remaining project money
Paid from project money
This will not affect monthly category limits
```

Avoid language like:

```text
Project category allocation
Assign unassigned funding
Rebalance project category
Micro-subcategory funding
Released project budget category
```

The comeback only works if the UI no longer asks the user to build a second
budget inside the project.

## What Still Needs Careful Design Later

The wallet problem still exists, but it is smaller than before.

Important future questions:

- What happens when project funding was protected from Wallet A, but the
  actual project expense is paid from Wallet B?
- Should project expenses be allowed from any wallet?
- Should the system warn when the payment wallet did not back the project pile?
- Should project backing be consumed proportionally across backing wallets?
- Should project backing be treated as protection-only until project wrap-up?
- What happens if the project pile is exhausted but the user logs another
  project expense?
- Does overrun become allowed with a warning, blocked, or converted into normal
  monthly budget pressure?
- How should refunds restore project pile balance?
- How should project completion release remaining protected money?

Initial preference:

```text
Treat the project pile as protected intent money, not as a second wallet.
Allow real expenses to be paid from whichever wallet was actually used.
Keep wallet ledger truth separate from project-intent consumption.
```

This keeps the user-facing model simple while leaving room for a later,
explicit wallet protection design.

## Potential Backend Direction

This is not an implementation plan yet, but the likely backend direction is:

- Keep project-linked expense ledger rows.
- For isolated project expenses, keep `budget_id = null` so monthly budget
  limits are bypassed.
- Keep `category` on the entity ledger row for analytics.
- Stop requiring isolated category allocation before posting a project expense.
- Stop requiring isolated subcategory allocation before posting a project
  expense.
- Keep total project pile enforcement as the main project spending guard.
- Preserve old category/subcategory allocation rows as legacy/read-only until a
  migration decision is made.

The key behavioral rule:

```text
If project is isolated:
  validate project is active and date is inside project bounds
  validate total project remaining money can cover the expense
  post expense with project_id and category
  do not attach monthly budget_id
```

## Potential Frontend Direction

Quick Add and Session Drafts should make the project choice feel lightweight:

```text
Category: Transport
Project: Dubai Trip

Hint:
Paid from Dubai Trip project money.
This will not affect your monthly Transport limit.
```

The Project page should show:

```text
Saved pile
Spent
Remaining
Top categories by actual spending
Recent project expenses
```

It should not ask the user to distribute the pile before spending.

## Decision To Make Before Implementation

Before unfreezing the feature, make one explicit product decision:

```text
Isolated Projects are not mini-budgets.
They are protected project-intent piles.
Categories on isolated expenses are reporting labels only.
```

If that decision holds, the feature can come back with much less conceptual
weight than the previous version.
