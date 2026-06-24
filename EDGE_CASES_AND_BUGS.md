# Edge Cases and Bugs

## EC-1: Budget Cards UI Confusion (Hidden Cash Backing)
**Issue:** The UI cards show "Free Money Now" (which is purely the wallet snapshot) but the system uses `cash_backing_total` behind the scenes (which includes cash already spent on budgets minus cash obligations). Because this step is hidden, the math shown to the user on the cards doesn't appear to add up (`Free Money + Expected Income - Budget Total != Plan Backing Remaining`).
**Resolution Strategy:** Replace "Free Money Now" with "Cash Backing" at the top level so the math is verifiable. Hide the details of how Cash Backing is calculated behind a "See details" waterfall.

## EC-2: Overdue Debts Ignored in Future Planning
**Issue:** `cash_obligation_reserve_total` only reserves money for debts due in the currently viewed month. If a debt due in June is left unpaid, it disappears from the July plan's obligations, incorrectly inflating the user's available backing for July.
**Resolution Strategy:** Update backend query to include all overdue debts (where `expected_return_date < today`), regardless of the month being viewed. Add UI nudges for users to either pay or reschedule overdue debts.

## EC-3: Plan Health vs. Actual Spending Disconnect
**Issue:** The "Plan Health" card (e.g., "Cash covered") only compares the total budget limits against available backing. It completely ignores whether the user has actually overspent their budgets via credit cards. This creates a psychological disconnect where the plan claims to be healthy while individual categories are heavily in the red.
**Resolution Strategy:** TBD (Requires UX decision on whether Plan Health should reflect execution reality or just the theoretical limits).

## EC-4: Integer Division Truncation in `valid_budget_spent`
**Issue:** When an expense is paid using multiple wallets (e.g., part cash, part credit) and splits across multiple budget categories, the backend calculates the cash portion for each budget leg using integer division. This truncates fractions and loses ~1-2 UZS per multi-wallet transaction, slightly understating the user's valid budget spent.
**Resolution Strategy:** Implement the "largest remainder method" (Hamilton method) to ensure exactly 100% of the cash spent is distributed across the legs without rounding loss.

## EC-5: Redundant `available_plan_backing` Field
**Issue:** The API returns both `backing_total` and `available_plan_backing` in the budget summary, but both fields contain the exact same value. This creates API clutter and a potential future maintenance trap.
**Resolution Strategy:** Deprecate/delete `available_plan_backing` and rely solely on `backing_total`.

## EC-6: Fragile `cash_obligation_reserve_total` Definition
**Issue:** The current logic for identifying cash obligations relies on `origin_kind = 'CASH_BORROWED'` or `product_kind = 'INFORMAL_DEBT'`. If a user takes out a formal bank loan but doesn't link it to a budget category, it won't trigger a category floor AND it won't hit cash obligations, causing the debt to vanish from all capacity tracking.
**Resolution Strategy:** Implement airtight, mutually exclusive liability tracking. A debt MUST either hit a category limit or a cash obligation. The rule should be: "Include all 'I Owe' debts that require cash settlement, EXCEPT those with a non-null `expense_category`."
