# PRD: G9 - Budget Explainability and Credit Survival

Labels: `ready-for-agent`

Source ECs: EC-127, EC-131, EC-132, EC-135, EC-145, plus budget and credit-card philosophy clarified in conversation on 2026-06-15.

## Problem Statement

Sarflog has a strong budget philosophy, but the product now exposes several places where users can no longer explain the numbers they see.

The clearest case is the Budgets page: a user can see `Free Money Now`, `Monthly Budget Total`, `Budget Room After Plan`, and `Plan Health`, but not the bridge math that explains how those values relate. After adding a current-month deferred expense debt, the page can become `Over-Planned` without showing whether the cause was valid budget spent, a cash obligation reserve, a category floor, expected income, goal protection, or a credit-card/liability effect.

The same confusion appears around credit cards. Sarflog correctly says credit limits are not budget room, but the current product language is too blunt around positive credit-card balances. In real life, a credit-card account can have a positive credit balance, usually from overpayment, refunds, rewards, or issuer credits. That positive balance is owned value, while the credit limit remains borrowed capacity. The app needs to model this distinction instead of treating every credit wallet as fully excluded from owned money.

Finally, users with no cash and only borrowed capacity need a controlled way to record survival spending without pretending the normal monthly budget is healthy. The survival layer should cover both credit-card borrowing and debit/prepaid overdraft borrowing. Credit Survival Mode should therefore evolve into Borrowing Survival Mode: intentional borrowing is visible and capped, but it never converts credit limits or overdraft limits into normal budget backing.

## Solution

Add a G9 product layer that makes budget plan health explainable and models credit-card balances by financial substance.

The Budgets page should show an explicit plan backing explanation:

```text
 Free money now
+ Already valid budget spending
- Cash obligation reserves
+ Expected income remaining
= Available plan backing

Available plan backing
- Monthly budget total
= Budget room after plan
```

Current-month category-linked obligations should appear as category floors when their future payment is categorized consumption. Cash-only obligations should appear as global cash reserves. The UI must show which bucket caused the pressure.

Credit-card wallets should be split by balance sign:

```text
positive credit-card balance = owned value
zero credit-card balance     = neutral
negative credit-card balance = liability
credit limit                 = borrowing capacity only
```

Normal credit-card spending should continue to hit monthly category budgets immediately. If the spending uses positive credit balance, it is normal owned-money spending. If it crosses below zero, only the borrowed portion counts toward borrowing pressure and Credit Survival Mode.

Credit Survival Mode should be a separate risk overlay. The product term may remain `Credit Survival Mode` in UI if desired, but the domain model should treat it as borrowed-spending survival because the same rule applies to credit cards and overdraft-enabled debit/prepaid wallets:

```text
Normal budget layer:
  Is this spending permission backed by owned money or expected earned income?

Borrowing Survival layer:
  If I must borrow, what maximum damage am I allowing this month?
```

Credit Survival Mode / Borrowing Survival Mode must never mark the normal plan as healthy. It only makes controlled borrowing visible.

Keep the current signed wallet ledger convention:

```text
current_balance > 0  = user owns value
current_balance = 0  = neutral
current_balance < 0  = user owes / liability exposure
```

For credit wallets:

```text
current_balance = -500,000  means user owes bank/card issuer 500,000
current_balance = +500,000  means bank/card issuer owes user a 500,000 credit balance
```

For debit/prepaid wallets with overdraft:

```text
current_balance = +300,000  means user owns 300,000
current_balance = -200,000  means user has used 200,000 overdraft
```

Do not change the existing UI sign display for credit cards in this PRD. The user explicitly decided the current wallet UI is acceptable. G9 should preserve the internal sign convention and focus behavior changes on budget backing, goal eligibility, debt projection, and survival-mode math.

## User Stories

1. As a budget user, I want the Budgets page to explain why my plan is covered, tight, waiting on income, or over-planned, so that I can trust the plan health status.
2. As a budget user, I want to see `Available Plan Backing` broken into its parts, so that I can reconcile the cards without doing hidden math.
3. As a budget user, I want `Valid Budget Spent` explained, so that normal in-limit spending does not look like a bug when it is added back into backing.
4. As a budget user, I want cash obligation reserves shown separately, so that debt pressure is not hidden inside a mysterious negative budget room number.
5. As a budget user, I want category floors shown by category, so that required Dining, Groceries, Transport, or Utilities spending is visible in the right life area.
6. As a budget user, I want the `Over-Planned` banner to name the causes, so that I know whether to reduce limits, add expected income, handle debt pressure, or review goals.
7. As a budget user, I want the third analytics card, `Monthly Budget Total`, to be clearly described as total spending permission, so that I do not confuse it with spendable money.
8. As a budget user, I want `Free Money Now` to remain separate from budget permission, so that wallet reality stays distinct from planning limits.
9. As a budget user, I want `Budget Room After Plan` to show the result after active limits and obligations, so that a negative number is understandable.
10. As a debt user, I want a personal deferred expense with a category and current-month due date to create category pressure, so that the budget category shows the minimum needed limit.
11. As a debt user, I want cash-only debts to remain global reserve pressure, so that raw payback obligations do not fake category spending.
12. As a debt user, I want the UI to distinguish `Dining Out floor: 200,000` from `Cash debt reserve: 200,000`, so that I understand the accounting route.
13. As a recurring-expense user, I want recurring items due this month to appear as category floors, so that required subscriptions or bills are visible before I plan discretionary spending.
14. As a planner, I want Smart Auto-Fill to respect category floors, so that required current-month obligations are not accidentally under-planned.
15. As a credit-card user, I want purchases on credit cards to hit the real category budget immediately, so that Dining paid by credit still counts as Dining.
16. As a credit-card user, I want credit-card repayment to be a wallet transfer, so that the original purchase is not counted twice.
17. As a credit-card user, I want credit limits excluded from budget backing, so that borrowed capacity does not become fake wealth.
18. As a credit-card user, I want a positive credit-card balance to count as owned value, so that overpaid or credited card money can support plans until it is used.
19. As a credit-card user, I want only the positive part of a credit wallet to fund goals, so that goal funding never uses the credit limit.
20. As a goal user, I want positive credit-card balance protection to work like other wallet protection, so that goal money on that wallet cannot be silently spent as normal free money.
21. As a goal user, I want negative credit and credit limits blocked from goal funding, so that goals remain protected real money.
22. As a user with only a cash wallet and a credit-card wallet, I want Sarflog to model the card by real balance, so that my simple real-world setup is not forced into fake categories.
23. As a user who receives refunds or overpays a credit card, I want the resulting positive balance to be visible as owned value, so that the app matches what the issuer owes me.
24. As a user who receives salary or transfers into an account I call a card, I want Sarflog to model the financial substance, so that prepaid, debit, and positive credit-balance cases are handled correctly.
25. As a user with no cash and only credit capacity, I want to set a Credit Survival cap, so that I can control emergency borrowing without pretending I have normal budget backing.
26. As a Credit Survival user, I want borrowed spending to count against both the real spending category and the survival cap, so that behavior and risk are both visible.
27. As a Credit Survival user, I want the normal plan to remain `Over-Planned` or unbacked when I borrow without cash, so that the app does not tell me the plan is healthy.
28. As a Credit Survival user, I want the borrowed portion of a split positive-to-negative card transaction to be calculated, so that only the true borrowed amount hits the survival cap.
29. As a Credit Survival user, I want survival spending to show payoff pressure, so that future cash can be directed toward repayment deliberately.
30. As a wallet user, I want credit-card cash advances, transfers, repayments, and normal purchases to have distinct transaction semantics, so that reports do not confuse payment rails with consumption.
31. As an overdraft debit user, I want overdraft spending to count against both the real category and the survival cap, so that debit overdraft risk is visible like credit-card risk.
32. As an overdraft debit user, I want only the below-zero portion of a debit/prepaid wallet outflow to count as borrowed survival usage, so that owned money used before overdraft is not mislabeled as borrowing.
33. As an overdraft debit user, I want overdraft limit excluded from budget backing, so that access to overdraft does not create fake monthly permission.
34. As an overdraft debit user, I want a negative overdraft wallet to appear as a wallet-backed obligation, so that I can cover it through wallet transfer rather than recording a fake debt-table payment.
35. As a wallet user, I want Sarflog to keep one signed balance rule across credit, debit, prepaid, and cash wallets, so that backend math stays predictable.
36. As a credit-card user, I want Sarflog to preserve the meaning that negative credit balance means I owe and positive credit balance means the issuer owes me, so that reconciliation and debt projection remain correct.
37. As a product user, I want the current credit-card UI sign display preserved unless a separate UI redesign is approved, so that this PRD does not change a screen I already consider good.
38. As a maintainer, I want budget plan summary, wallet availability, goal funding, and borrowing pressure to share one signed-balance rule, so that frontend and backend do not drift.
39. As a maintainer, I want budget explainability fields returned by the backend, so that the frontend does not reverse-engineer plan math.
40. As a maintainer, I want category floors and cash reserves to include source details, so that UI copy can explain debts and recurring items without fragile guessing.
41. As a tester, I want API tests for positive credit balances, so that credit limits never sneak into free money while positive balances are included.
42. As a tester, I want end-to-end budget tests for the deferred-expense debt case, so that the UI and backend explain `Over-Planned` consistently.
43. As a tester, I want Credit Survival / Borrowing Survival tests to prove that borrowed spending can be allowed while normal plan health remains honest.

## Implementation Decisions

- Preserve the core philosophy: wallets are reality, goals are protected real money, budgets are monthly spending permission, expected income is planning support, and credit is payment capacity plus possible borrowing.
- Keep credit-card purchases as normal category spending when the expense has normal monthly budget impact.
- Keep credit-card repayment as a wallet transfer with no second category budget hit.
- Never include credit limit, overdraft limit, or negative credit balance in budget backing.
- Include the positive balance of a credit wallet in owned money calculations, because a positive credit balance is value owed back to the user.
- Treat positive credit-card balance as eligible for normal expense payment, budget backing, and goal funding up to the positive unprotected amount.
- Treat goal protection on a positive credit wallet the same as goal protection on cash, debit, savings, or prepaid wallets.
- Keep credit capacity itself ineligible for goal funding. A goal may not be funded by a credit limit, negative credit balance, or overdraft capacity.
- Define the owned part of a credit wallet as `max(current_balance, 0)`. Define the liability part as `max(-current_balance, 0)`.
- For a purchase from a positive credit wallet that crosses below zero, split the financial meaning: the positive portion is owned-money spending, and the below-zero portion is borrowed spending.
- Add Credit Survival Mode as a separate risk overlay, not a replacement for monthly plan status.
- Credit Survival Mode may remain the user-facing name, but the backend concept should be borrowed-spending survival so overdraft debit/prepaid wallets can participate.
- Credit Survival Mode should have a user-defined monthly borrowed-spending cap.
- Credit Survival Mode usage should increase only by the borrowed portion of normal spending, not by spending covered by positive credit balance.
- A Credit Survival cap does not increase `Free Money Now`, `Available Plan Backing`, `Budget Room After Plan`, or normal budget create/update capacity.
- Normal budget health can remain `Over-Planned`, `Waiting on income`, or unbacked while Credit Survival usage is within cap.
- Include overdraft-enabled debit/prepaid wallets in survival usage when an outflow pushes or keeps the wallet below zero.
- For overdraft wallets, survival usage should count only the below-zero borrowed portion of the outflow.
- Overdraft limit must never increase budget backing, free money, goal availability, or normal budget create/update capacity.
- Negative overdraft balances should remain wallet-backed obligations projected into the obligations/debts UI, settled by wallet transfer.
- Preserve the existing signed `current_balance` convention across the database and backend services: positive means owned value, negative means owed/liability exposure, zero means neutral.
- Preserve the current credit-card UI sign display in this PRD. Do not redesign wallet card balance signs as part of G9.
- If an expense is a normal monthly expense, it should hit the category budget whether paid by cash, debit, prepaid, positive credit balance, or borrowed credit.
- If an expense is goal-funded or isolated-project-funded, preserve existing budget exclusion rules. Payment by credit must not create a generic bypass.
- If a credit-card transaction is a cash advance or transfer-out rather than consumption, model it as a transfer/advance/liability operation, not as a normal category expense unless a real fee or consumption event exists.
- Classify current-month debts by repayment accounting route, not only by debt label.
- A payable deferred expense with an expense category should become a category floor if the future payment represents categorized consumption.
- A raw cash-borrowed or cash-only informal debt should become a cash obligation reserve, not a category floor.
- The existing personal deferred expense flow should be reviewed because `product_kind: INFORMAL_DEBT` plus an expense category can currently push it into global cash reserve behavior even when product semantics say category floor.
- Extend month summary with explicit explainability fields for available plan backing, including free money now, valid budget spent, cash obligation reserves, expected income remaining, monthly effective limit total, and shortfall.
- Extend category floor output with source details sufficient for UI copy, such as recurring item, deferred expense, installment, debt name, due date, and amount.
- Extend cash reserve output with source details sufficient for UI copy, such as cash debt name, due date, and amount.
- Keep the Budgets page top cards, but add an explainability surface below or inside the plan-health card that names the specific causes.
- Avoid envelope language. Use `spending permission`, `plan backing`, `category floor`, `cash reserve`, `borrowed spending`, and `Credit Survival cap`.
- Do not silently auto-create or auto-increase budgets when a category floor appears. Smart Auto-Fill may propose or apply floors only through an explicit planner action.
- Backend remains source of truth for budget math. Frontend should render returned fields and avoid duplicating plan formulas.

## Testing Decisions

- Use `/budgets/month-summary` as the highest seam for plan explainability behavior.
- Use wallet and goal funding API seams to verify positive credit balance availability.
- Use expense creation seams to verify credit-card spending hits categories and borrowed portions create borrowing pressure.
- Use debt creation seams to verify category-linked deferred expenses become category floors and cash-only debts become reserves.
- Add tests where a normal in-limit expense keeps plan health stable through valid budget spent.
- Add tests where a current-month deferred Dining Out debt creates a Dining Out floor and shows floor shortfall when no Dining budget exists.
- Add tests where a cash-borrowed debt creates cash reserve pressure and explains `Over-Planned` without creating category spend.
- Add tests where a credit wallet with positive balance contributes to `owned_money_now` and `free_money_now`.
- Add tests where a credit wallet with negative balance does not reduce free money directly and does not add backing.
- Add tests where credit limit does not affect budget backing.
- Add tests where protected goal money on a positive credit balance reduces `free_money_now`.
- Add tests where goal funding from negative credit or credit limit is rejected.
- Add tests where a credit-card purchase from positive balance does not create Credit Survival usage.
- Add tests where a credit-card purchase crossing from positive to negative creates Credit Survival usage only for the borrowed part.
- Add tests where a debit/prepaid wallet outflow crossing from positive to negative creates survival usage only for the overdraft portion.
- Add tests where a debit/prepaid wallet already below zero creates survival usage for the full additional outflow.
- Add tests where overdraft limit does not affect budget backing, goal availability, or budget create/update capacity.
- Add tests where a negative overdraft wallet is projected as a wallet-backed obligation and settled by wallet transfer.
- Add tests where Credit Survival cap being available does not allow normal budget create/update validation to exceed real backing.
- Add frontend or browser smoke tests for the Budgets page explanation surface: warning, save, red state, debt floor/reserve explanation, and one repair/planner path where available.
- Tests should assert observable behavior and response contracts, not private helper implementation details.
- Existing budget tests, expense tests, wallet transfer tests, and goal availability tests are the prior art.

## Out of Scope

- Replacing the whole budget system with envelope budgeting.
- Treating credit limits as budget room.
- Treating overdraft limits as free money.
- Redesigning the existing wallet card sign display for credit cards.
- Changing the database sign convention for credit wallets, overdraft wallets, or wallet ledger rows.
- Auto-funding goals from expected income.
- Auto-paying debts from expected income.
- Full credit-card statement closing date, grace period, minimum payment, and interest engine.
- Automatic direct-deposit integrations.
- Bank sync or open banking.
- Region-specific legal compliance beyond modeling the product semantics safely.
- Multicurrency changes.
- Reworking G8 expense repair behavior.
- Cross-parent subcategory reallocation.
- Automatically creating category budgets without explicit user action.
- Full lending, cash advance, and fee workflow redesign, except where transaction semantics are needed to avoid category confusion.

## Further Notes

This PRD intentionally clarifies several misunderstandings that appeared during product review:

- `Monthly Budget Total` is not cash. It is total active spending permission for the month.
- `Free Money Now` is not the whole backing formula. Valid already-spent budgeted money and obligation reserves explain why plan status can differ from the raw free-money number.
- `Budget Room After Plan` can be negative because obligations or floors reduced backing, not because the UI randomly changed the budget total.
- A deferred expense with a category is usually category pressure, not a generic cash reserve.
- Credit-card spending should count against monthly categories, because category answers what life area was consumed.
- Credit Survival Mode can overlap with monthly budget spending, because it answers a different question: how much borrowed damage is being allowed.
- Credit Survival Mode should conceptually include overdraft debit/prepaid spending too, because the shared domain concept is borrowed spending.
- A positive credit-card balance is not the same as a credit limit. The positive balance is owned value; the credit limit is borrowing capacity.
- Goal money should not normally live on credit-card credit balances, but if the card truly has a positive owned balance, Sarflog can protect that value the same way it protects other owned wallet money.
- The internal sign convention is correct and should stay: positive `current_balance` means owned value, negative `current_balance` means user owes. Credit-card UI presentation may invert or relabel signs for familiarity, but that is a display choice and is not part of this PRD.

Real-world grounding:

- U.S. Regulation Z recognizes credit-card credit balances. When a credit balance above one dollar exists, the creditor must credit it to the account and refund it on request within the regulatory timing rules. See 12 CFR 1026.11: https://www.ecfr.gov/current/title-12/chapter-X/part-1026/subpart-B/section-1026.11
- U.S. Regulation E recognizes overdraft services as paying transactions when an account has insufficient or unavailable funds, and it defines opt-in treatment for ATM and one-time debit card overdrafts. See 12 CFR 1005.17: https://www.ecfr.gov/current/title-12/chapter-X/part-1005/subpart-A/section-1005.17
- The product should not depend on whether users call a card "credit" or "debit" in casual language. Sarflog should model financial substance: owned positive balance, protected goal value, negative liability, and borrowing capacity.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
