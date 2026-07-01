# Sarflog Domain Glossary

The core vocabulary and bounded context for the Sarflog personal finance tracking application.

## Core Philosophy: Reality-First Permission Budgeting

Sarflog is a **ledger-first, cash-aware spending-permission system**. It is a truth-first budgeting system for real spending, protected goals, and repairable plans.

- **Wallets are reality**: They record actual money and payment capacity (credit, overdraft).
- **Budgets are permission**: They define monthly spending permission, checked against plan backing.
- **Goals are protected real money**: They reserve physical cash so it cannot be spent.
- **Expected income is planning support**: It influences plan health but is not treated as current cash.
- **Credit is payment capacity**: It is not wealth or budget backing.

The core principle is **save truth first, repair plan second**. If an expense occurs, it is saved as ledger truth even if it breaks the budget (goes red). The app then offers honest repair (reallocate, increase limit, or leave red) without falsifying history.

## Mental Model

1. **Reality Layer**: Wallets / Cards / Cash (Actual balances)
2. **Free Money Now**: Owned positive cash - Protected goals
3. **Plan Backing**: Free money now + Valid expected income
4. **Budget Permission**: Category monthly limits + Subcategory lanes
5. **Plan Status**: Cash covered / Waiting on income / Over-Planned

## Core Domain

**Wallet Epoch**:
The per-wallet temporal boundary established at wallet creation. The initial balance is a sealed snapshot of reality at that moment — the net result of all prior financial activity. No transaction (expense, inflow, transfer) may be dated before a wallet's epoch because that money movement is already reflected in the opening balance. For credit wallets, the snapshot is the outstanding balance owed.
_Avoid_: Start date, Onboarding date, First transaction date

**Debt**:
An open-ended obligation with a running balance and no strict repayment schedule (e.g., informal IOUs, a running tab). It is completely decoupled from Payment Plans.
_Avoid_: Liability, Loan, Installment

**Payment Plan**:
A closed-end obligation governed by a strict schedule of fixed payments over a set duration (e.g., Car Loan, Store Installment). It maintains its own independent ledger and is never linked to a Debt.
_Avoid_: Scheduled Debt, Recurring payment

**Financial Event**:
The overarching wrapper representing a single user action (like making a purchase or transferring money). It contains no currency context or amounts itself.
_Avoid_: Transaction, Expense (when referring to the wrapper)

**Ledger Entry**:
The individual value movement line item (e.g., `WalletLedger`, `EntityLedger`, `DebtLedgerEntry`) that holds the actual amount, original currency context, and exchange rate back to the base currency.
_Avoid_: Event amount, Transaction line

**Reconciliation Flow**:
The controlled process for recording missed past events or fixing wallet balance drift. Unlike normal logging (which is restricted to today), this flow forces the user to resolve the gap between the app's ledger and reality. It can generate exact past-dated records, category-approximate records, or Unknown/Untracked adjustments.
_Avoid_: Adjust balance, Retroactive add

**Closed Period**:
A budget month that has passed its 5-day reconciliation grace window (or was manually closed by the user). Once closed, its historical ledger cannot be rewritten with new past-dated entries.
_Avoid_: Locked month, Archived month

**Current Correction**:
An entry made in an open period (today) to account for a missed event from a Closed Period. This ensures the wallet balance is fixed without silently rewriting sealed historical reports.
_Avoid_: Late entry, Backdated expense

**Budget**:
A monthly spending permission limit, not a physical wallet-backed envelope.
_Use_: Spending permission, Plan backing, Borrowing pressure, Red state, Repair action, Subcategory lane, Project overlay
_Avoid_: Envelope balance, Budget cash, Move budget money, Fund the category, Credit-backed budget

**Category Floor Warning**:
A derived, non-binding suggested minimum for a budget category in one selected calendar month. It represents the full-month total of relevant categorized obligations, including amounts already fulfilled and amounts still due, without reserving money or changing the category limit.
_Avoid_: Mandatory floor, Floor record, Next-30-days floor, Remaining-obligations floor

**Recurring Template**:
The user's current instruction for generating future repeating expenses. Editing, pausing, or archiving it changes future intent but does not rewrite fulfilled occurrences.
_Avoid_: Recurring payment history, Recurring floor

**Recurring Occurrence**:
One dated realization or disposition of a recurring template, such as fulfilled, failed, skipped, or cancelled. Its historical amount and category remain those that applied to that occurrence even if the template later changes.
_Avoid_: Current template state, Projection row

**Recurring Recording Mode**:
The user's chosen rule for turning a due recurring occurrence into financial truth: either ask for confirmation of the real expense or automatically record the expected expense. The recording mode does not change the recurrence schedule itself.
_Use_: Confirm each occurrence, Automatically record
_Avoid_: Automatically pay, Scheduler payment

**Goal vs Project**:
A `FUND_PROJECT` goal is strictly an "incubator" for the saving phase. It digitally locks money over time. A Project represents the execution and spending phase (e.g., buying materials for the remodel).
_Avoid_: Saving inside a Project, Spending directly from a Goal

**Goal Graduation**:
The one-way lifecycle event where a `FUND_PROJECT` goal is closed (status becomes `GRADUATED`), and its locked funds are released into a Project. Once graduated, the Goal is dead. If the user needs more money for the kitchen later, they allocate funds directly into the Project, not the Goal.
_Avoid_: Reopening a graduated goal, Funding a graduated goal

**Historical Start Date**:
Purely decorative UI metadata (often from imported history) used for gamification, nudges, and progress bars. It generates no ledger entries and must never influence core system math, preserving the Wallet Epoch boundary.
_Avoid_: Goal Start Date, Debt Origination Date (when used for math)
