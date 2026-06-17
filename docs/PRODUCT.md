# Sarflog Product Model

This document captures the current product philosophy behind Sarflog.

It is meant to answer one question:

```text
What is Sarflog trying to help the user understand about their money?
```

The short answer:

```text
Sarflog separates real money, protected commitments, monthly spending limits,
future income, borrowed payment capacity, and project-based missions.
```

The core product line:

```text
Wallets = reality
Goals = protected real money
Budgets = monthly spending limits
Expected income = future planning support, not money today
Credit/overdraft = payment capacity through borrowing, not budget room
Projects = scoped missions for grouped spending
```

---

## 1. Master Mental Model

```text
                                    SARFLOG
                                      |
                                      v
        +-----------------------------+-----------------------------+
        |                                                           |
        v                                                           v
  REAL MONEY NOW                                             FUTURE CONTEXT
        |                                                           |
        |                                                           |
        v                                                           v
+-------------------+                                  +----------------------+
|      WALLETS      |                                  |   EXPECTED INCOME    |
+-------------------+                                  +----------------------+
| Cash              |                                  | Salary expected      |
| Debit             |                                  | Freelance expected   |
| Savings           |                                  | Other expected money |
| Preloaded         |                                  +----------------------+
| Credit            |                                             |
| Overdraft debit   |                                             |
+-------------------+                                             |
        |                                                         |
        |                                                         |
        v                                                         v
  +-------------+                                      +----------------------+
  | OWNED MONEY |                                      | PLANNING SUPPORT     |
  +-------------+                                      +----------------------+
  | Positive    |                                      | Not spendable today  |
  | balances    |                                      | Not guaranteed       |
  +-------------+                                      | Not auto-allocated   |
        |                                             +----------------------+
        |
        v
+-------------------------+
| FREE MONEY NOW          |
+-------------------------+
| Owned wallet money      |
| minus protected goals   |
+-------------------------+
        |
        +-----------------------------+
        |                             |
        v                             v
+---------------------+       +----------------------+
| GOALS               |       | MONTHLY BUDGETS      |
+---------------------+       +----------------------+
| Protected money     |       | Spending permission  |
| Wallet-backed       |       | Category limits      |
| Hard protection     |       | Soft planning        |
+---------------------+       +----------------------+
        |                             |
        |                             |
        v                             v
+---------------------+       +----------------------+
| Goal actions        |       | Budget usage         |
+---------------------+       +----------------------+
| Reserve money       |       | Normal expenses hit  |
| Prepare payment     |       | monthly categories   |
| Pay obligation      |       |                      |
| Record purchase     |       | Goal-funded spending |
| Fund project        |       | is excluded from     |
| Use reserve         |       | normal budget limits |
+---------------------+       +----------------------+
        |
        v
+----------------------+
| PROJECTS             |
+----------------------+
| Overlay project      |
| Isolated project     |
| Goal-funded project  |
+----------------------+
```

---

## 2. The Three Reality Questions

Sarflog should help the user answer three different questions without mixing them.

```text
1. Can I pay?
   -> Wallets, credit cards, overdrafts

2. Should I spend?
   -> Budgets, subcategories, budget room, cushion

3. What future commitment does this affect?
   -> Goals, debts, payment plans, projects
```

Example:

```text
Ali has:

Debit balance:              1,000,000 UZS
Credit card limit:         10,000,000 UZS
Food budget remaining:      2,000,000 UZS

Ali buys groceries:           500,000 UZS
Paid with: credit card
```

Sarflog should say:

```text
Can Ali pay?       Yes, the credit card allows it.
Should he spend?   Food budget still has room.
What changed?      He increased borrowed balance by 500,000 UZS.
```

Sarflog should not say:

```text
Credit limit increased Ali's budget room.
```

That would be wrong. Credit helps complete payment. It does not make the plan healthier.

---

## 3. Budgets Are Limits, Not Money

The budget philosophy:

```text
Budgets = monthly spending limits
Budgets are not wallet-backed
Budgets are not envelope money
Budgets do not reserve cash
Budgets do not create spendable money
```

Example:

```text
Ali creates June budgets:

Food:             3,000,000 UZS
Transport:        1,000,000 UZS
Dining:           1,000,000 UZS
Utilities:          800,000 UZS
Entertainment:      700,000 UZS

Total budgets:    6,500,000 UZS
```

This means:

```text
Ali is allowing himself to spend up to 6,500,000 UZS across these categories.
```

It does not mean:

```text
Sarflog moved 6,500,000 UZS into budget envelopes.
```

It does not mean:

```text
Ali has 6,500,000 UZS available in wallets.
```

Budget creation is planning. Wallet balance is reality.

---

## 4. Free Money Now

Free money now is the amount of owned wallet money not protected by goals.

```text
Free money now =
owned wallet balances
- protected goal money
```

Example:

```text
Debit wallet:            7,000,000 UZS
Cash wallet:             1,000,000 UZS
Savings wallet:          4,000,000 UZS

Total owned money:      12,000,000 UZS

Goal-protected money:
Emergency reserve:       2,000,000 UZS
Laptop goal:             3,000,000 UZS

Protected total:         5,000,000 UZS

Free money now:          7,000,000 UZS
```

Only the 7,000,000 UZS is freely available for normal spending.

The protected 5,000,000 UZS still sits in wallets, but Sarflog treats it as committed.

---

## 5. Budget Room

Budget room is a planning health check.

Senior simplified model:

```text
Budget room =
free money now
+ expected income for the month
- known promises
- desired cushion
```

Known promises may include:

```text
Debt payments due
Payment plan installments due
Required bills
Explicit scheduled goal contributions, if supported later
```

Important:

```text
Expected income is not allocated.
Expected income is not spendable today.
Expected income only helps classify whether the monthly plan can work.
```

Example:

```text
Free money now:             1,000,000 UZS
Expected salary:            9,000,000 UZS
Debt payment due:           2,000,000 UZS
Desired cushion:            1,000,000 UZS

Planning capacity:
1,000,000 + 9,000,000 - 2,000,000 - 1,000,000
= 7,000,000 UZS
```

If Ali creates 7,000,000 UZS of budgets, Sarflog says:

```text
This plan works if expected income arrives.
```

Sarflog should not say:

```text
You can spend 7,000,000 UZS today.
```

Today Ali has only 1,000,000 UZS free.

---

## 6. Budget Statuses

Sarflog should classify budget health instead of pretending all plans are equal.

```text
+----------------------+-----------------------------------------------+
| Status               | Meaning                                       |
+----------------------+-----------------------------------------------+
| Covered with cushion | Budgets fit current free money and leave room |
| Covered, no cushion  | Budgets fit current free money but are tight  |
| Waiting on income    | Budgets need expected income to work          |
| Over-Planned         | Budgets exceed free money + expected income   |
| Borrowing pressure   | Spending is within budget but paid by debt    |
+----------------------+-----------------------------------------------+
```

Example A:

```text
Free money now:          8,000,000 UZS
Budgets total:           6,000,000 UZS
Cushion:                 2,000,000 UZS

Status: Covered with cushion
```

Example B:

```text
Free money now:          8,000,000 UZS
Budgets total:           8,000,000 UZS
Cushion:                         0 UZS

Status: Covered, no cushion
```

This is allowed, but Sarflog should warn:

```text
Your plan uses all free money. You are covered, but you have no cushion.
```

Example C:

```text
Free money now:          1,000,000 UZS
Expected income:         9,000,000 UZS
Budgets total:           7,000,000 UZS

Status: Waiting on income
```

Example D:

```text
Free money now:          1,000,000 UZS
Expected income:         9,000,000 UZS
Debt due:                3,000,000 UZS
Budgets total:          10,000,000 UZS

Planning capacity:
1,000,000 + 9,000,000 - 3,000,000
= 7,000,000 UZS

Status: Over-Planned by 3,000,000 UZS
```

---

## 7. Expected Income: Classification, Not Allocation

This is the key simplification.

Do not ask:

```text
Which exact part of salary belongs to Food?
Which exact part belongs to Goals?
Which exact part belongs to Debts?
```

That becomes too complex too early.

Instead, Sarflog should ask:

```text
Does the monthly plan fit current free money?
If not, does it fit after expected income and known promises?
```

Expected income should not auto-fund goals.

Expected income should not auto-pay debts.

Expected income should not automatically become budget cash.

Expected income should only support planning status.

Example:

```text
Expected salary:         10,000,000 UZS
Laptop goal wants:        2,000,000 UZS this month
Debt due:                 3,000,000 UZS
Budgets total:            6,000,000 UZS
```

If there is no explicit scheduled goal contribution feature yet, do not subtract the laptop goal automatically.

Sarflog may show:

```text
Your laptop goal may need 2,000,000 UZS this month to stay on track.
```

But it should not silently reduce budget room until the product supports explicit goal contribution commitments.

The clean rule:

```text
Only explicit commitments reduce planning capacity.
```

---

## 8. Rollover

Rollover is unused spending permission carried forward.

Rollover is not new money.

```text
Previous budget limit
- previous spending
= unused budget room
```

Example:

```text
May Food budget:          3,000,000 UZS
May Food spending:        2,200,000 UZS
Unused May room:            800,000 UZS

June Food base budget:    3,000,000 UZS
June rollover:              800,000 UZS
June effective room:      3,800,000 UZS
```

This is okay only as a planning permission.

Sarflog must still reality-check it against wallets and commitments.

Bad interpretation:

```text
You did not spend 800,000 UZS in May, so 800,000 UZS magically exists.
```

Correct interpretation:

```text
You carried 800,000 UZS of unused Food permission into June.
This permission is only healthy if your real free money still supports it.
```

Example:

```text
May unused Food room:       800,000 UZS
But Ali used that money to fund a Laptop goal.
```

June can still show the rollover history, but the budget health may say:

```text
This rollover is not fully covered by current free money.
```

---

## 9. Credit Cards And Budgets

Credit cards are payment methods and liability accounts.

Credit limit is not budget room.

```text
Credit card spending hits the budget immediately.
Credit card repayment does not hit the budget again.
Interest and fees hit Bank Fees & Interest.
Credit limit does not increase monthly planning capacity.
```

Example:

```text
Debit wallet:             5,000,000 UZS
Credit card limit:       10,000,000 UZS
Food budget:              2,000,000 UZS
```

Ali buys groceries:

```text
Amount:                     400,000 UZS
Paid with: credit card
```

Result:

```text
Food budget used:           400,000 / 2,000,000 UZS
Credit card liability:      400,000 UZS owed
Debit wallet:             5,000,000 UZS unchanged
```

Later Ali repays the card from debit:

```text
Debit wallet:            -400,000 UZS
Credit liability:        -400,000 UZS
Food budget:                    no new impact
```

Why no budget impact on repayment?

Because the grocery spending already hit the Food budget when the purchase happened.

If repayment hit Food again, Sarflog would double-count the same real-world spending.

Bad model:

```text
Credit card limit:       10,000,000 UZS
Therefore budgets can increase by 10,000,000 UZS.
```

Correct model:

```text
Credit can allow payment.
Credit does not make the monthly plan healthier.
```

---

## 10. Overdraft Debit Cards And Budgets

Overdraft is borrowed payment capacity attached to a debit wallet.

It is not free money.

It is not budget room.

Example:

```text
Debit balance:              300,000 UZS
Overdraft limit:          1,000,000 UZS
Transport budget:           700,000 UZS
```

Ali spends:

```text
Taxi:                       500,000 UZS
Paid from debit wallet
```

Result:

```text
Debit balance:             -200,000 UZS
Transport budget used:      500,000 / 700,000 UZS
```

Sarflog should say:

```text
Transport budget is still within limit.
But the wallet went into overdraft.
```

Budget health and wallet health are different.

The expense may be behaviorally okay but financially risky.

---

## 11. Monthly Budget Subcategories

Subcategories are smaller lanes inside one monthly category budget.

```text
Parent category = source of monthly spending permission
Subcategory = optional split of that permission
```

Example:

```text
Food budget:              3,000,000 UZS

Subcategories:
Groceries:                1,800,000 UZS
Restaurants:                700,000 UZS
Coffee/snacks:              300,000 UZS
Unassigned Food room:       200,000 UZS
```

Rules:

```text
Subcategory limits must not exceed parent category limit.
Expenses with subcategory hit both parent and subcategory.
Expenses without subcategory hit parent and unassigned room.
Subcategory leftover is not real money.
Subcategory leftover cannot fund goals.
Subcategories should not become envelopes.
```

Example:

```text
Food budget:              3,000,000 UZS
Restaurants limit:          700,000 UZS

Ali spends restaurants:      900,000 UZS
```

Sarflog can say:

```text
Restaurants is over by 200,000 UZS.
Food overall may still be okay if there is unassigned room.
```

Possible user actions:

```text
Move room from Groceries to Restaurants
Increase Food budget
Record anyway with warning
Change category/subcategory if it was classified wrong
```

Deletion rule:

```text
If a subcategory has historical expenses, do not hard-delete it.
Deactivate/archive it so history remains understandable.
```

---

## 12. Goals

Goals protect real money.

```text
Goal allocation does not move money by itself.
It labels existing wallet money as protected.
```

Goal intents:

```text
Reserve money     -> flexible protection for future unknown use
Planned purchase  -> save for a specific purchase
Pay obligation    -> save for a debt or payment plan payment
Fund project      -> save for a larger scoped mission
```

Core rule:

```text
Goal money should not be silently spent as normal free money.
```

Normal expenses should not consume goal money unless the user explicitly goes through a goal workflow:

```text
Use reserve
Record purchase
Make debt payment
Release to project
```

---

## 13. Projects

Projects group spending around a scoped mission.

There are two project types:

```text
+------------------+-----------------------------------------------+
| Project type     | Meaning                                       |
+------------------+-----------------------------------------------+
| Overlay project  | A reporting/planning lens over monthly budget |
| Isolated project | A separate project budget world               |
+------------------+-----------------------------------------------+
```

### Overlay Project

Overlay projects live inside monthly budgets.

Use them for:

```text
School season
Ramadan meals
Business trip
Birthday month
Short seasonal campaign
```

Example:

```text
Monthly Transport budget:       1,000,000 UZS
Already spent Transport:          400,000 UZS

Overlay project:
Tashkent work trip
Transport project limit:          600,000 UZS maximum
```

Why 600,000 UZS?

Because the project is not isolated. It shares the monthly Transport budget.

Rules:

```text
Overlay project expenses hit monthly budgets.
Overlay project should reuse monthly categories/subcategories.
Overlay project category limits should fit current monthly category room.
Overlay project should not create project-only subcategories.
```

### Isolated Project

Isolated projects have their own project budget world.

Use them for:

```text
Wedding
Home renovation
Medical event
Vacation
Car repair
Laptop setup
Moving house
```

Example:

```text
Project: Home renovation
Total project limit:       30,000,000 UZS

Project categories:
Materials:                 18,000,000 UZS
Labor:                      8,000,000 UZS
Transport:                  2,000,000 UZS
Unexpected:                 2,000,000 UZS
```

Rules:

```text
Isolated project expenses do not consume normal monthly budgets.
Isolated projects can have project-specific subcategories.
Isolated project limits are scoped to the project period, not one month.
If linked to a Fund Project goal, released goal funding can become a hard project spending cap.
```

---

## 14. Fund Project Goal

A Fund Project goal saves protected wallet money for a project.

Lifecycle:

```text
1. User creates Fund Project goal
2. User reserves wallet money into the goal
3. Goal graduates into a project or links to a project
4. User releases some protected goal money to the project
5. Project expenses spend against released project funding
```

ASCII flow:

```text
+------------------+
| Fund Project Goal|
+------------------+
        |
        | reserve wallet money
        v
+--------------------------+
| Protected goal funding   |
| Still physically in      |
| real wallets             |
+--------------------------+
        |
        | graduate/link
        v
+--------------------------+
| Project                  |
| Prefer isolated project  |
| for goal-funded work     |
+--------------------------+
        |
        | release funding
        v
+--------------------------+
| Released project funding |
| Committed to project     |
+--------------------------+
        |
        | project expense
        v
+--------------------------+
| Spending recorded        |
| Wallet decreases         |
| Project spent increases  |
+--------------------------+
```

Example:

```text
Ali creates:
Goal: Home renovation fund
Target: 30,000,000 UZS

He reserves:
12,000,000 UZS

He graduates to:
Project: Home renovation
Project total limit: 30,000,000 UZS

He releases:
10,000,000 UZS to project
```

Project state:

```text
Planned project limit:      30,000,000 UZS
Released funding:           10,000,000 UZS
Spent:                               0 UZS
Remaining released funding: 10,000,000 UZS
Unfunded project need:      20,000,000 UZS
```

If Ali spends 8,000,000 UZS on materials:

```text
Project spent:               8,000,000 UZS
Remaining released funding:  2,000,000 UZS
```

If he wants to spend another 5,000,000 UZS:

Sarflog should require one of:

```text
Release more goal funding
Reduce/change the expense
Explicitly record unfunded project spending with warning, if supported
```

Senior rule:

```text
Fund Project should usually create or link to an isolated project.
```

Why?

Because Fund Project goals are wallet-backed commitments, while overlay projects are monthly-budget reporting lenses.

Mixing those too casually causes confusion.

---

## 15. Goal-Funded Spending Vs Normal Budget Spending

Normal expense:

```text
Hits wallet
Hits monthly budget
May hit project if selected
```

Goal-funded planned purchase:

```text
Hits wallet
Consumes goal funding
Does not consume normal monthly budget limit
Still keeps category data for analytics
```

Reserve use:

```text
Hits wallet
Consumes reserve goal funding
Does not make the reserve goal "failed"
May create refill need
```

Debt goal payment:

```text
Hits wallet
Consumes Pay Obligation goal funding
Reduces debt/payment plan
Does not become normal category spending
```

Project goal release:

```text
Does not physically move wallet money by itself
Marks protected goal money as committed to project
Project spending later hits wallet and project budget
```

---

## 16. Product Invariants

These rules protect the product from becoming conceptually muddy.

```text
1. Budget limits are not wallet balances.
2. Expected income is not spendable today.
3. Credit limit is not budget room.
4. Overdraft limit is not free money.
5. Goal allocations protect real wallet money.
6. Goal allocations do not move money unless a transfer happens.
7. Goal-funded spending should not double-hit normal monthly budgets.
8. Credit card repayment should not double-hit budgets.
9. Project total limit is a spending cap, not money.
10. Released project funding is a commitment, not a wallet transfer.
11. Overlay project expenses hit monthly budgets.
12. Isolated project expenses do not hit monthly budgets.
13. Subcategory limits must fit inside parent category limits.
14. Subcategory leftover is unused permission, not cash.
15. Rollover is carried permission, not newly created money.
```

---

## 17. Failure Modes To Avoid

### Failure: Treating Credit As Budget Room

Bad:

```text
Free money now:       2,000,000 UZS
Credit limit:        20,000,000 UZS
Budget room:         22,000,000 UZS
```

Correct:

```text
Free money now:       2,000,000 UZS
Credit limit:        payment capacity only
Budget room:         based on owned money + expected income - promises
```

### Failure: Double-Counting Credit Card Repayment

Bad:

```text
Restaurant purchase on credit hits Dining.
Credit card repayment also hits Dining.
```

Correct:

```text
Purchase hits Dining.
Repayment settles liability only.
```

### Failure: Treating Rollover As Cash

Bad:

```text
Unused May Food budget automatically becomes cash in June.
```

Correct:

```text
Unused May Food budget becomes extra June permission, then Sarflog checks whether real free money can support it.
```

### Failure: Auto-Allocating Expected Salary

Bad:

```text
Expected salary is silently split between budgets, goals, debts, and projects.
```

Correct:

```text
Expected salary helps classify plan realism.
Only explicit commitments reduce planning capacity.
```

### Failure: Making Subcategories Envelopes

Bad:

```text
Coffee leftover can be moved into a goal as if it were real money.
```

Correct:

```text
Coffee leftover is unused budget permission.
Only wallet money can fund a goal.
```

### Failure: Project Double Counting

Bad:

```text
Wedding project expense hits isolated Wedding budget and monthly Family budget.
```

Correct:

```text
Isolated Wedding expense hits project budget only.
Overlay project expense hits monthly budget.
```

---

## 18. UI Language Principles

Use human language that reflects the product model.

Prefer:

```text
Free money now
Protected money
Budget room
Waiting on income
No cushion
Paid with credit
Went into overdraft
Move room from another category
Released to project
Used from reserve
```

Avoid:

```text
Allocate salary to budget buckets
Transfer budget money
Move budget cash
Credit-backed budget
Envelope balance
Database terms
Ledger terms
```

Good budget warning:

```text
Your plan is covered, but it uses all free money. There is no cushion.
```

Good expected income warning:

```text
This plan works if expected income arrives.
```

Good credit warning:

```text
This spending is within budget, but it was paid with borrowed money.
```

Good rollover warning:

```text
You carried unused room from last month. Sarflog still checks whether your real money can support it.
```

---

## 19. One-Screen Product Summary

```text
                            SARFLOG FINANCIAL TRUTH

 +-------------------+      +-------------------+      +-------------------+
 | Wallet reality    |      | Protected future  |      | Monthly behavior  |
 +-------------------+      +-------------------+      +-------------------+
 | Cash              |      | Reserve goals     |      | Category budgets  |
 | Debit             | ---> | Purchase goals    | ---> | Subcategories     |
 | Savings           |      | Debt goals        |      | Rollover room     |
 | Credit liability  |      | Project goals     |      | Reallocation      |
 | Overdraft risk    |      +-------------------+      +-------------------+
 +-------------------+                |                         |
          |                           |                         |
          v                           v                         v
 +-------------------+      +-------------------+      +-------------------+
 | Free money now    |      | Commitments       |      | Budget status    |
 +-------------------+      +-------------------+      +-------------------+
 | Owned money       |      | Debts due         |      | Covered          |
 | minus goal money  |      | Installments due  |      | No cushion       |
 +-------------------+      | Project releases  |      | Waiting income   |
                            +-------------------+      | Over-Planned     |
                                                       +-------------------+
          |                           |                         |
          +---------------------------+-------------------------+
                                      |
                                      v
                         +---------------------------+
                         | What Sarflog tells user   |
                         +---------------------------+
                         | Can you pay?              |
                         | Should you spend?         |
                         | What does this delay/risk?|
                         | Is your plan realistic?   |
                         +---------------------------+
```

---

## 20. Current Senior Recommendation

For the next implementation stage, keep the model simple:

```text
Do not allocate expected income.
Do not treat credit as budget room.
Do not let rollover pretend to be cash.
Do not turn subcategories into envelopes.
Do not mix isolated and overlay project rules.
```

Build the first Budget Philosophy layer as:

```text
1. Calculate free money now.
2. Calculate expected income for the month.
3. Subtract known promises.
4. Compare against monthly budgets.
5. Show clear status:
   - Covered with cushion
   - Covered, no cushion
   - Waiting on income
   - Over-Planned
   - Borrowing pressure
```

This gives Sarflog a strong financial truth layer without making the system too complex too early.
