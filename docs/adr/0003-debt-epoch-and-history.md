# Debt Epoch & The Dual Path Rule

Dealing with financial obligations that existed *before* a user started tracking their money is a classic trap that breaks ledger integrity. If a user tries to log a 1,000,000 UZS loan from two years ago, attempting to retroactively attach that money to a wallet destroys the wallet's mathematically sound opening snapshot.

**Decision:**
Sarflog enforces a strict "Dual Path" model for creating debts, treating the past and the present entirely differently.

1. **Path 1: New Transaction (Active Reality)**
   - **Trigger:** The user is borrowing or lending money *today* (or recently).
   - **Mechanism:** Must be tied to a Wallet. Uses `origin = CASH_BORROWED` or `CASH_LENT`.
   - **Rules:** The transaction triggers real money movement in the wallet ledger. Because it touches a wallet, it is strictly bound by the Wallet Epoch rule (cannot be dated before the wallet) and the standard Logging/Reconciliation rules (today-only for normal flow).

2. **Path 2: Pre-Existing Balance (The Snapshot)**
   - **Trigger:** The user already owed (or was owed) this money *before* they started tracking.
   - **Mechanism:** Completely disconnected from Wallets. Uses `origin = IMPORTED_BALANCE`. 
   - **Rules:** The user is asked *only* for the remaining balance as of today. The system does not care about the original principal or past payments. Because there is zero wallet impact, the `date` (origination date) is treated purely as reference metadata and **can safely be set to the historical past** to satisfy user psychology, without breaking any system math.

**Why:**
This mathematically decouples the obligation ledger from the wallet ledger for historical dead data. It guarantees that a user's opening wallet snapshot remains untainted, while still allowing them to accurately track their true net worth and active obligations from Day 1.
