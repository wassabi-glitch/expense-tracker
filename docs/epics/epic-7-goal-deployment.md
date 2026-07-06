# Epic 7: Goal Deployment & Protection

**Status:** Mixed / In Process  
**Depends On:** Epic 6 (for isolated project wallet allocations, top-ups, spend-down reporting, and project intersections)

## Goal

Establish strict lifecycle rules and safety guardrails for the moment a user actually *uses* protected money. This epic covers goal money that becomes spending, Fund Project goals that graduate into isolated projects, isolated project stash spending, and wallet protection breaches caused by spending from wallets that hold protected money.

The core principle is:

```text
Wallet reality first.
Protected-money intent second.
Budget pressure only when the intent says it should apply.
No ghost transfers.
```

## Current Reality Discovered

The backend already has meaningful Fund Project support:

- `FUND_PROJECT` exists as a goal intent.
- Fund Project goals can graduate through `POST /goals/{goal_id}/graduate`.
- Graduation creates an isolated project, releases the funded amount into project wallet allocations, and marks the origin goal as `GRADUATED`.
- Project summaries expose spend-down fields such as `released_funding`, `remaining_funding`, `funding_shortfall`, and `progress_direction`.

The frontend is behind the backend:

- The Savings frontend schema and labels know about `FUND_PROJECT`.
- The Savings page has a graduation modal for existing Fund Project goals.
- The goal creation wizard does **not** expose a Fund Project choice, so normal users cannot create Fund Project goals from the UI.
- Fund Project goal cards need a complete, user-visible action model: reserve money, unreserve money, create isolated project, show graduated read-only state, and route future funding to project top-ups after graduation.

Current UI gap diagram:

```text
Backend
FUND_PROJECT goal
    |
    v
POST /goals/{id}/graduate
    |
    v
Isolated Project with released stash
    |
    v
Spend-down reporting
    [mostly present]

Frontend
Create Goal Wizard
    |
    +-- Reserve
    +-- Planned Purchase
    +-- Pay Obligation
    |
    x-- Fund Project missing
```

## PRDs Included

1. [ ] **[G11 - Goal Payment Philosophy & Auto-Reimbursement Deprecation](../prd/g11-goal-payment-philosophy.md)**
   - Remove `_settle_goal_funding_to_payment_wallets` and any automatic wallet-to-wallet reimbursement logic.
   - Record the wallet that actually paid.
   - Explicitly release or consume the protected goal/project money that the user intended to use.
   - Apply the correct monthly-budget behavior by intent.
   - Preserve spending reports even when the expense does not hit the monthly budget.

2. [x] **[G7 - Projects and Goal Deployment](../prd/g7-projects-and-goal-deployment.md)**
   - Enforce `project.start_date <= expense_date <= project.target_end_date` for expense tagging.
   - Protect completed projects as immutable reports until explicit reopen.
   - Allow Fund Project goals to graduate before full funding.
   - Use actual released funding, not target amount, as the isolated project stash.
   - Show overlay projects as tick-up trackers and isolated projects as tick-down stashes.

## Goal Payment Philosophy

G11 is not just a goal-card feature. It is an accounting philosophy for all protected-money spending:

```text
User spends money
    |
    v
Record the real payment wallet(s)
    |
    v
Identify the protected-money intent
    |
    v
Release/consume the relevant protected money
    |
    v
Apply the correct monthly budget behavior
```

### Planned Purchase

Example: the user saved 12M UZS for a laptop in Cash, but pays from Debit.

```text
Before

Cash
  Laptop Goal protected: 12M

Debit
  Pays laptop at store: 12M
```

Bad old behavior:

```text
Cash --fake system reimbursement--> Debit
```

Correct behavior:

```text
Debit records the real laptop expense
Cash releases/consumes the Laptop Goal money
Monthly budget is not hit
No wallet transfer is invented
```

Reasoning: the monthly lifestyle budget should not be punished when the user already absorbed the financial impact during saving.

### Reserve Fund With Budget Toggle

Reserve funds are different because they often represent unexpected operating expenses: medical, emergency repair, family help, etc.

The phrase "or providing a toggle for Reserve funds" means:

```text
Reserve expense from wrong wallet
    |
    v
Record the real expense
    |
    v
Release matching reserve money
    |
    v
Ask whether this should hit the monthly budget
```

Recommended default:

```text
[x] Count this against my monthly budget
```

The user can turn it off for catastrophic or exceptional events where counting it against the normal monthly plan would create noisy budget pressure.

Example:

```text
Medical Reserve: 3M protected in Cash
User pays hospital bill: 3M from Debit

Default:
  Debit expense is recorded
  Cash reserve is released
  Medical category budget shows spending

User can opt out:
  Debit expense is recorded
  Cash reserve is released
  Monthly budget pressure is bypassed
  Spending report still shows the medical expense
```

Senior-engineer judgment: Reserve needs the toggle because it sits between two truths. It is real spending that users may want visible in monthly habits, but some emergencies are not useful as monthly-budget failures.

### Fund Project / Isolated Project

Fund Project is the bridge from saving mode to project execution mode.

```text
Fund Project Goal
    |
    v
Graduate
    |
    v
Isolated Project stash
    |
    v
Project spending draws down the stash
```

If the user spends for an isolated project from a wallet that did not fund the project, apply the same G11 philosophy.

Example:

```text
Cash
  Wedding Project stash: 4M protected

Debit
  User pays venue: 1M
```

Correct behavior:

```text
1. Record real expense from Debit.
2. Tag it to Wedding Project.
3. Reduce/release 1M from the Wedding Project stash.
4. Do not hit the monthly budget.
5. Do not create a fake Cash-to-Debit transfer.
```

Diagram:

```text
Before

Cash Wallet
  Wedding Project stash: 4M

Debit Wallet
  Free money: 2M

Payment
  Venue paid from Debit: -1M

After

Cash Wallet
  Wedding Project stash: 3M
  Released/free equivalent: 1M

Debit Wallet
  Real venue payment: -1M

Monthly budget
  Not hit
```

Senior-engineer judgment: isolated projects should behave like deployed protected money. The payment wallet records reality; the project stash records intent.

## EC-162: Wallet Protection Breaches

EC-162 should apply to protected goal money and protected isolated project money.

The protection breach question is:

```text
After this real wallet payment, does any wallet still have enough balance
to honor the protected money assigned inside it?
```

Example:

```text
Debit wallet balance: 1M
Debit protected for Laptop Goal: 1M
Debit free cash: 0

User pays Wedding Project venue from Debit: 1M
```

Even if the Wedding Project stash is released from Cash, Debit still has a local protection breach:

```text
Debit after payment: 0
Laptop Goal still claims: 1M

Shortfall: 1M
```

The app must ask the user how to resolve the breach. It cannot guess which protected promise should be reduced.

General flow:

```text
Save expense
    |
    v
Apply known intent first
    |
    v
Recompute protected coverage by wallet
    |
    +-- Covered -> save
    |
    +-- Breached -> resolution wizard
```

Resolution wizard examples:

```text
Single wallet, single protected item

Cash balance after expense: 2M
Protected in Cash: 5M
Shortfall: 3M

Prompt:
This expense will consume 3M protected for "Laptop Goal".

[Release Laptop funds and save]
[Cancel]
```

```text
Single wallet, multiple protected items

Cash shortfall: 3M

Protected items:
Phone Goal        1M
Laptop Goal       2M
Wedding Project   2M

Prompt:
Choose which protected money to release.

Phone Goal        [0      ]
Laptop Goal       [0      ]
Wedding Project   [0      ]

Remaining to resolve: 3M

[Save and release funds] disabled until remaining is 0
```

```text
Multiple wallets breached

Cash needs 2M resolved
Debit needs 1M resolved

Cash protected items:
Laptop Goal       [1M]
Vacation Goal     [1M]

Debit protected items:
Emergency Reserve [1M]

[Save and release funds]
```

Senior-engineer judgment: EC-162 is a ledger-trust feature, not a convenience feature. It prevents the UI from claiming protected money is safe when the wallet no longer backs it.

## EC-163: Goal Fulfillment Interceptor

EC-163 is intentionally delayed for now.

It remains a useful future UX layer:

```text
Normal expense typed by user
    |
    v
Looks like an existing goal/project fulfillment?
    |
    +-- Yes -> ask "Did you mean to use protected money?"
    |
    +-- No -> continue normal expense / EC-162 checks
```

But it should not block G11 or EC-162.

Reasoning:

- G11 fixes accounting truth for explicit protected-money actions.
- EC-162 fixes protection coverage when wallet reality breaks protected promises.
- EC-163 is a smart convenience layer for careless entry.

Senior-engineer judgment: build truth first, convenience second.

## Required UI Surfaces

Goal Payment Philosophy must be enforced in more than one place.

### Savings / Goals Page

Required because the user may start from the protected money object.

Surfaces:

- Create Fund Project goal in the goal creation wizard.
- Fund Project goal card action: create isolated project.
- Planned Purchase action: record purchase / already paid from wrong wallet.
- Reserve action: use reserve / already paid from wrong wallet with budget toggle.
- Graduated Fund Project goal state: read-only saving history with link to the isolated project.
- Future funding copy: after graduation, additions happen through project top-ups, not the old goal.

### Expenses Page / Quick Add / Session Drafts

Required because the user may start from the real-world receipt.

Surfaces:

- Normal expense must respect EC-162 protection breach checks.
- Project-linked isolated expenses must support off-wallet project spending.
- Expense sessions must run the same validation and release rules as quick single expenses.
- Budget-hit behavior must be explicit and consistent with the selected protected-money intent.

### Budgets / Projects Page

Required because isolated projects are managed there after graduation.

Surfaces:

- Isolated project detail/card must show remaining stash and shortfall.
- Project expense entry from the project context must support real payment wallet selection.
- Project top-up, allocate, and rebalance flows must remain the post-graduation funding path.
- Off-wallet project spending should explain the stash release clearly.

## Execution Rules

- Execute G11 before EC-163. Remove ghost transaction technical debt before adding fuzzy smart-interceptor flows.
- Treat EC-163 as deferred until explicit protected-money flows and EC-162 protection checks are stable.
- Make G11/EC-162 rules shared service behavior, not one-off UI behavior.
- Apply project date validation centrally so Quick Add, Session drafts, goal flows, and project flows share the same invariants.
- Preserve user-facing dates in the user's effective timezone.
- Verify backend behavior in Docker where possible, because this app is Docker-first.

## Done When

- Fund Project goals are discoverable and usable from the Savings UI.
- Fund Project goals can graduate from the UI into isolated projects.
- Graduated goals are read-only saving history and route future money additions to project top-ups.
- Off-wallet Planned Purchase, Reserve, and Fund Project/isolated project spending record wallet reality without ghost transfers.
- Reserve off-wallet spending provides a budget-hit toggle.
- Isolated project off-wallet spending releases project stash and does not hit monthly budget.
- EC-162 detects and resolves wallet protection breaches for both goal allocations and isolated project allocations.
- EC-163 remains explicitly deferred, with no hidden dependency on it for ledger correctness.
