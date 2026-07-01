# 0017. Debt Receivables and Deadline Decoupling

## Context

We encountered an architectural question regarding how "Receivables" (Debts where `debt_type == OWED`) interact with the Monthly Timeline, and how their deadlines should synchronize with the Expected Inflow engine. 

Specifically, we needed to address:
1. Should open Debts automatically project onto the calendar timeline?
2. How do we handle complex split repayments (e.g., a 1M debt paid in three installments)?
3. If a user creates an Expected Inflow for a Debt, should the `due_date` of the inflow be strictly bound to the `expected_return_date` of the Debt?

## Decision

We are explicitly codifying the "No Auto-Trust" rule for Receivables and enforcing strict Domain Decoupling between Debt Obligations and Cashflow Timelines.

### 1. The "No Auto-Trust" Rule for Receivables
Debts owed to the user will **never** automatically project into the Monthly Timeline. 
- **Liabilities (OWING):** Are strictly auto-projected to warn the user and protect them from overdrafting.
- **Receivables (OWED):** Are notoriously unreliable. Auto-projecting them would create a false sense of security in the budget. To place a Receivable on the timeline, the user must explicitly create an Expected Inflow, formally declaring: *"I actively expect this cash on this specific date."*

### 2. Handling Splits via the Two-Layer Architecture
We leverage the Two-Layer Architecture (ADR-0012) to handle repayment splits natively, rather than polluting the Debt model.
- A user creates **One Promise** (Layer 1) linked to the Debt for the full amount (e.g., 100k).
- The user creates **Multiple Schedules** (Layer 2) inside that Promise for each split (e.g., 30k on July 15, 30k on Aug 15, 40k on Sept 15).
- Receiving cash against any Schedule automatically drives down the parent Debt's remaining balance.

### 3. Strict Deadline Decoupling (Contract vs Reality)
We strictly forbid the synchronization of deadlines between a Debt and its Expected Inflows. They govern their own time independently.
- **The Debt (Macro Deadline):** Holds the `expected_return_date`. This represents the formal **Contractual Deadline** agreed upon with the counterparty.
- **The Expected Inflow (Micro Deadline):** Holds the `due_date`. This represents the **Tactical Reality** of when the cash is actually expected to hit the bank.

**The "July 10 vs July 20" Scenario:**
If a Debt is due on July 10, but the counterparty delays payment to July 20, the user adjusts the Expected Inflow `due_date` to July 20. 
- We do *not* mutate the Debt's original July 10 deadline, as that would rewrite history and erase the default. 
- The system correctly marks the Debt as `Overdue` on July 11, holding the counterparty accountable.
- The Monthly Timeline safely projects the cash arriving on July 20, protecting the user's budget mathematically.

## Consequences

- **Domain Purity:** The Debt system remains a strict ledger of Obligations, while the Expected Inflow system remains a fluid tool for Cashflow Manipulation.
- **Resilience:** By allowing date drift between the two systems, the application perfectly absorbs the unpredictable nature of human behavior without breaking.
- **UX Requirement:** We must ensure the UI proactively prompts users to link their open Receivables to Expected Inflows at the start of a month, rather than relying on auto-linking.
