# 0015. Income Sources and Ledger Naming

## Context

We encountered two related architectural and UX issues in the Expected Inflows engine:
1. **The Source vs Title Conflict:** There was tension between forcing users to select an "Income Source" (which causes high data-entry friction) versus just using a text "Title" (which ruins data grouping and analytics). 
2. **The "Robot Title" Ledger Bug:** When a user received an Expected Inflow, the backend ignored their custom `Promise.title` (e.g., "Website Redesign Phase 1") and automatically generated a generic string for the General Ledger based on the source (e.g., "Client payment received" or "Refund"). This caused severe loss of context in the ledger.

## Decision

We are adopting the industry-standard **"Entity + Memo"** accounting pattern and enforcing strict title inheritance for the ledger.

### 1. The Hybrid "Entity + Memo" Pattern
We explicitly refuse to kill either the `IncomeSource` (Entity) or the `Promise.title` (Memo). We need both for a professional financial engine.
- **The Source (Analytics):** Represents the Entity (e.g., "Client X", "Upwork"). It remains a strict Foreign Key used for database grouping, lifetime analytics, and tax reporting.
- **The Title (Context):** Represents the specific contract/memo (e.g., "July Salary"). It remains the primary human-readable identifier.

**Required UX Refactors to eliminate friction:**
- The Source dropdown in forms must become a "Creatable Select". Users must be able to type a new client name and create the Source instantly in the background without leaving the form.
- We must introduce an "Income Sources Hub" page. Sources are useless without a place to view their analytics (Lifetime Expected, Lifetime Received, Outstanding Balance, Payment Reliability).

### 2. Strict Ledger Title Inheritance
The backend must never generate generic titles for user-driven Expected Inflows.
- **The Rule:** The `FinancialEvent.title` generated upon receiving a Schedule must exactly inherit the `ExpectedInflowPromise.title`. If the Promise is named "Test", the Ledger Event is named "Test".
- **Metadata Display:** The `IncomeSource` (e.g., "Client payment") is already attached to the transaction via the `EntityLedger`. The UI will display this as a secondary subtitle/badge under the main title, ensuring no context is lost without overwriting the user's explicit memo.

## Consequences

- **Analytics Integrity:** By retaining the `IncomeSource`, the system can generate accurate pie charts, YTD reports, and client profitability metrics.
- **Auditability:** By enforcing title inheritance, users can easily trace a cashflow event in the General Ledger directly back to the specific contract/project they named in the Expected Inflows tab.
- **Development Effort:** We must refactor `expected_inflow_service.py` (specifically `_post_earned`, `_post_receivable`, `_post_refund`, and `_post_asset_sale`) to pull `Promise.title`. We must also build the Creatable Select UI component and the new Income Sources Hub.
