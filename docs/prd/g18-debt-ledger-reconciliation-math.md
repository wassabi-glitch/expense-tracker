# PRD: G18 - Debt Ledger Reconciliation Math

Labels: `ready-for-agent`

## Problem Statement

The Debt module suffers from two systemic mathematical bugs that cause the UI to display wildly incorrect financial summaries (often referred to as the "Phantom Payments" bug).

1. **The Reversal Blindspot (Backend):** The backend function `get_debt_total_charges` explicitly filters for `charge_delta > 0`. This means when a user reverses a charge, the negative ledger entry is completely ignored by the `SUM()` function. The total charges figure becomes permanently bloated.
2. **The Naive Frontend Math (Frontend):** Because the backend does not return a `total_paid` field, the frontend attempts to guess the paid amount using the formula: `Paid = (Initial + Charges) - Remaining`. This is deeply flawed. If a debt is forgiven, settled with an asset, or corrected downward, the remaining balance drops. The frontend formula misinterprets these non-cash ledger reductions as actual cash payments, lying to the user.

## Solution

Enforce the "Dumb UI, Smart Ledger" architectural principle. First, fix the backend charge sum to include negative reversals. Second, move the `total_paid` calculation entirely into the backend where the true ledger records (`DebtTransaction` or `PAYMENT` entry types) can be queried accurately. Finally, update the `DebtOut` schema to return this exact value, and strip the dangerous subtraction formula out of the frontend.

## User Stories

1. As a user, I want reversing a charge to actually subtract from the "Total Charges" metric, so that my debt summary is mathematically accurate.
2. As a user, I want forgiving or settling a debt to drop my remaining balance WITHOUT falsely increasing my "Paid/Cleared" metric, so that my cash history isn't artificially bloated.
3. As a developer, I want the backend to be the sole source of truth for all ledger aggregations, so that introducing new debt actions (like write-offs) doesn't break frontend math.
4. As a frontend maintainer, I want the API to provide the exact `total_paid` amount, so that the UI can simply display the value without doing complex accounting subtraction.

## Implementation Decisions

- **Fix `get_debt_total_charges`:** Remove the `models.DebtLedgerEntry.charge_delta > 0` filter in `app/services/debt_service.py` so that negative reversals naturally net against positive charges.
- **Create `get_debt_total_paid`:** Implement a new service function that queries the ledger for all `models.DebtLedgerEntryType.PAYMENT` entries (or directly sums `DebtTransaction` amounts) to accurately count real cash applied to the debt.
- **Schema Update:** Add `total_paid: int = 0` to the `DebtOut` schema in `app/schemas.py`.
- **Router Update:** Update `_build_debt_out` in `app/routers/debts.py` to accept and map `total_paid`.
- **Frontend Refactor:** Remove the naive `paidAmount = (initial + charges) - remaining` calculation from the Debt Details/Summary React components. Replace it with direct usage of the new `debt.total_paid` field from the API.

## Testing Decisions

- Assert that adding a 200k charge and then reversing it results in `total_charges == 0`.
- Assert that creating a debt and executing a "Forgive Balance" action results in `remaining_amount == 0` and `total_paid == 0`.
- Assert that executing a real 500k cash payment results in `total_paid == 500_000`.
- Existing debt action integration tests in `tests/` can serve as prior art, specifically ensuring the new `total_paid` key in the JSON response is verified.

## Out of Scope

- Changing how installments calculate payments (they have their own tracking).
- Adding new types of ledger entries (we are only fixing the aggregation queries for the existing ledger).

## Further Notes

This PRD resolves the Phantom Payments bug discovered during deep codebase inspection. It restores data integrity to the Debt module by ensuring the frontend never guesses ledger math, strictly enforcing the backend as the singular source of accounting truth. Published locally under `docs/prd/` with the `ready-for-agent` label.
