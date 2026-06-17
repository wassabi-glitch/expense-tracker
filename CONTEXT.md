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

**Financial Event**:
The overarching wrapper representing a single user action (like making a purchase or transferring money). It contains no currency context or amounts itself.
_Avoid_: Transaction, Expense (when referring to the wrapper)

**Ledger Entry**:
The individual value movement line item (e.g., `WalletLedger`, `EntityLedger`, `DebtLedgerEntry`) that holds the actual amount, original currency context, and exchange rate back to the base currency.
_Avoid_: Event amount, Transaction line

**Budget**:
A monthly spending permission limit, not a physical wallet-backed envelope.
_Use_: Spending permission, Plan backing, Borrowing pressure, Red state, Repair action, Subcategory lane, Project overlay
_Avoid_: Envelope balance, Budget cash, Move budget money, Fund the category, Credit-backed budget
