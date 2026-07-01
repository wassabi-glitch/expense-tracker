# ADR 0008: Goal Intent Status Matrix and Overdue Rejection

## Status
Accepted

## Context
Goals in Sarflog represent "protected real money" physically locked in a wallet. However, users save money for different reasons: infinite emergency funds, one-time purchases, debt settlements, and project incubators. 

Because the nature of these goals differs drastically, applying a universal set of statuses and target dates to all goals creates mathematical paradoxes. For example, an emergency fund is a perpetual sinking fund; it can never mathematically be "Overdue", nor is it ever truly "Completed" just because it hits its target capacity.

Furthermore, we must strictly enforce the "Golden Rule of State Management": If a status is purely a function of time (e.g., `OVERDUE = today > due_date`), it must be derived on the fly, not stored in the database, to prevent "Midnight Cron Job" synchronization failures.

## Decision

We establish a strict mapping of allowed statuses, target date behaviors, and UI badge rules for each `GoalIntent`. The database schema `GoalStatus` remains constrained to explicit User Intents: `ACTIVE`, `COMPLETED`, `GRADUATED`, and `ARCHIVED`.

### The Goal Intent Matrix

| Intent | Target Date | Valid DB Statuses | "Overdue" Handling |
|---|---|---|---|
| **`RESERVE`**<br>(Emergency/Sinking Fund) | **Disabled / Hidden** | `ACTIVE`, `ARCHIVED` | **Impossible**. A perpetual fund has no deadline. Hitting the target amount does not change its status to Completed. |
| **`PLANNED_PURCHASE`**<br>(Buy a Laptop) | **Optional** | `ACTIVE`, `COMPLETED`, `ARCHIVED` | **UI Badge Only**. If the target date passes, the DB status remains `ACTIVE`. The UI may display a soft "Past Target Date" warning. |
| **`FUND_PROJECT`**<br>(Kitchen Remodel Incubator) | **Optional** | `ACTIVE`, `GRADUATED`, `ARCHIVED` | **UI Badge Only**. It remains `ACTIVE` until manually graduated to a Project or archived. It can never be `COMPLETED` directly. |
| **`PAY_OBLIGATION`**<br>(Save for Mom's Loan) | **Mandatory**<br>*(Inherited from Debt)* | `ACTIVE`, `COMPLETED`, `ARCHIVED` | **Handled by Debt Engine**. The Goal itself is never overdue. If the target date passes, the linked *Debt* triggers the overdue logic. |

## Consequences
1. **No Database `OVERDUE`:** The `GoalStatus` enum explicitly omits `OVERDUE`. The system will never mathematically punish a user for failing to save fast enough. A goal is just a box of money.
2. **Intent-Driven UI:** The frontend must dynamically toggle the visibility of the `target_date` input and adapt the "Close Goal" button options (Complete vs Graduate) based on the selected `GoalIntent`.
3. **Data Integrity:** By restricting database statuses to explicit Human Actions (Archiving, Completing, Graduating) rather than Time (Overdue), the Goal ledger remains perpetually sound without requiring background reconciliation scripts.
