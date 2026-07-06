# PRD: G39 - Goal Settlement Mode Simplification

Labels: `ready-for-agent`

## Problem Statement

Sarflog's goal payment flow currently mixes three different ideas in one purchase wizard:

- the real wallet/card that paid the merchant
- whether protected goal money backed the purchase
- whether the goal was completed "outside reserved funds"

That creates confusing product language and unnecessary backend state. A user who paid with a card after fully saving for a sofa usually still feels that the sofa goal funded the purchase. The card was only the payment instrument. Calling that purchase "outside goal funds" is psychologically blurry and can make users choose the wrong path.

The current `PAID_OUTSIDE_GOAL_FUNDS` settlement mode is also weak as an expense concept. If a company, family member, or gift paid for the item, no money left the user's wallet, so Sarflog should not record a user expense. If the user bought the item with their own money but does not want the goal involved, that is a normal expense plus a separate decision to unreserve/archive the goal, not a special goal settlement.

`GoalCompletionMode` adds another layer of confusion. Once outside-goal settlement is removed from active product behavior, the completion-mode enum no longer carries a distinct user-facing truth. Goal lifecycle status remains enough for the current product model.

## Solution

Simplify active goal settlement to two modes:

- `DIRECT`: the purchase/use was paid from the wallet(s) already funding the goal.
- `GOAL_BACKED_OFF_WALLET_PAYMENT`: the real payment came from another wallet/card, but protected goal money still backs and is consumed for the purchase/use.

Remove `PAID_OUTSIDE_GOAL_FUNDS` from the active settlement model and remove `GoalCompletionMode` from active backend/frontend contracts.

For Planned Purchase goals, "Record purchase" means the purchase is goal-backed. If the user paid from another wallet/card, Sarflog records that real payment wallet, consumes the matching protected goal funding, creates no fake wallet transfer, bypasses monthly budget pressure, and still includes the expense in spending reports.

For Reserve goals, off-wallet use remains valid because a reserve can cover an emergency even when the real payment came from a debit card or another wallet. The reserve's protected amount is reduced/consumed. Reserve use defaults to monthly-budget visibility, with a bypass toggle for exceptional or catastrophic cases. Spending reports still include the expense.

If a goal becomes unnecessary because the item was gifted, employer-paid, family-paid, or the user changed their mind, Sarflog should not create a fake expense. For now, users can use existing unreserve/archive/delete behavior. New closure reasons and new "achieved externally" workflows are intentionally out of scope.

## User Stories

1. As a Planned Purchase user, I want "Record purchase" to mean I am using my saved goal money, so that the goal flow matches why I saved the money.
2. As a Planned Purchase user, I want to select the wallet/card that actually paid the merchant, so that my wallet history matches real life.
3. As a Planned Purchase user who paid with a different card, I want the purchase to still count as goal-backed, so that the saved goal money is consumed for the thing I saved for.
4. As a Planned Purchase user, I do not want Sarflog to create an automatic reimbursement transfer, so that my ledger does not show money movement I never performed.
5. As a Planned Purchase user, I want the purchase to bypass monthly budget pressure, so that a pre-saved planned purchase does not look like ordinary lifestyle overspending.
6. As a Planned Purchase user, I still want the expense to appear in spending reports, so that reports answer where my money went.
7. As a Planned Purchase user who received the item as a gift or employer benefit, I do not want Sarflog to record a personal expense, so that the app does not invent money leaving my wallet.
8. As a Planned Purchase user who no longer needs the goal, I want existing unreserve/archive behavior to remain available, so that I can release the money without a new complicated closure workflow.
9. As a Reserve user, I want to pay from any real wallet/card and consume reserve money, so that the reserve can cover emergencies even when the protected cash was not the payment instrument.
10. As a Reserve user, I want ordinary reserve use to hit the monthly budget by default, so that normal medical, repair, or household spending remains visible.
11. As a Reserve user, I want a clear bypass toggle for catastrophic or non-routine use, so that one exceptional event does not distort normal monthly budget pressure.
12. As a Reserve user, I want spending reports to include reserve-funded expenses whether or not they hit the monthly budget, so that reports remain complete.
13. As a user, I want the UI to avoid words like "outside goal funds" and "reimbursement" when no reimbursement transfer occurs, so that the app does not teach me misleading accounting.
14. As a user, I want only two goal settlement concepts, so that the purchase flow does not ask me to reason about backend enums.
15. As a user, I want gift/company/family-paid cases to be treated as no personal expense, so that Sarflog stays wallet-reality-first.
16. As a developer, I want the backend settlement enum to represent only active settlement behavior, so that impossible or abandoned product states cannot leak through the API.
17. As a developer, I want `GoalCompletionMode` removed from active schemas and storage, so that goal lifecycle truth is not split across redundant fields.
18. As a tester, I want API and UI tests proving the deprecated outside-funds path is gone, so that the simplified model cannot regress silently.

## Implementation Decisions

- Rename the old reimbursement-style settlement to `GOAL_BACKED_OFF_WALLET_PAYMENT`.
- Keep only `DIRECT` and `GOAL_BACKED_OFF_WALLET_PAYMENT` as valid active goal settlement modes.
- Remove `PAID_OUTSIDE_GOAL_FUNDS` from backend validation, frontend schema validation, and user-facing flows.
- Remove `GoalCompletionMode` from active API payloads, API responses, frontend schemas, and persisted goal state after a safe migration.
- Keep `GoalStatus` as the goal lifecycle source of truth. Planned Purchase goals can still become `COMPLETED`; Reserve goals remain `ACTIVE` or `ARCHIVED`; Fund Project goals remain governed by graduation rules.
- Planned Purchase "Record purchase" must require enough unreleased goal funding to back the purchase amount. If the user buys before the goal is funded and does not want to use goal money, they should record a normal expense outside the goal flow.
- Planned Purchase same-wallet purchases use `DIRECT`.
- Planned Purchase purchases paid from another real wallet/card use `GOAL_BACKED_OFF_WALLET_PAYMENT`.
- Goal-backed off-wallet Planned Purchase spending consumes the protected goal funding, records the real payment wallet, creates no wallet-to-wallet transfer, bypasses monthly budget pressure, and remains visible in spending reports.
- Reserve same-wallet use uses `DIRECT`.
- Reserve off-wallet use uses `GOAL_BACKED_OFF_WALLET_PAYMENT`.
- Reserve off-wallet use consumes protected reserve funding, records the real payment wallet, creates no wallet-to-wallet transfer, defaults to monthly-budget pressure, and supports the existing budget-bypass toggle for exceptional cases.
- Multi-wallet payment rows should remain supported where the existing expense payment model already supports them.
- Gifts, employer-paid purchases, family-paid purchases, and other cases where no user wallet loses money are not expenses in this PRD.
- New closure reasons such as "achieved externally" or "no longer needed" are not introduced in this PRD.
- Existing unreserve, archive, and delete behavior remains the lightweight way to clear a goal that is no longer needed.
- Existing data created under the removed outside-funds mode must not block migration. Posted financial events and goal ledger history should be preserved, while no new outside-funds records can be created.
- This PRD supersedes the `ACHIEVED_OUTSIDE_RESERVED_FUNDS` and `PAID_OUTSIDE_GOAL_FUNDS` parts of G11 for active implementation. G11's rejection of automatic reimbursement transfers remains valid.

## Testing Decisions

- Good tests should verify public behavior through API routes, frontend flows, budget summaries, spending reports, and wallet/goal read models rather than internal helper calls.
- Add backend tests proving only `DIRECT` and `GOAL_BACKED_OFF_WALLET_PAYMENT` are valid active settlement modes.
- Add backend tests proving deprecated `PAID_OUTSIDE_GOAL_FUNDS` and `completion_mode` payloads are rejected or ignored according to the migration-compatible API decision.
- Add backend tests proving Planned Purchase off-wallet payment records the real payment wallet, consumes goal funding, creates no wallet transfer, bypasses monthly budget pressure, and remains visible in spending reports.
- Add backend tests proving Planned Purchase goal-backed purchase requires sufficient unreleased goal funding.
- Add backend tests proving gift/company/family-paid cases are not represented by the goal purchase route.
- Add backend tests proving Reserve off-wallet use consumes reserve funding, records the real payment wallet, defaults to budget pressure, supports budget bypass, and remains visible in spending reports.
- Add backend migration tests or migration smoke coverage proving existing rows with old completion-mode values do not break upgrade.
- Add frontend tests proving the Record Purchase UI presents goal-backed choices only, uses copy that avoids "outside goal funds" and "reimbursement", and sends the new settlement mode.
- Add frontend tests proving no `completion_mode` is sent from the goal purchase/use flows.
- Add frontend tests proving Reserve budget toggle behavior and stale-query refresh still work.
- Docker-backed backend tests and frontend build remain the verification source for the completed slice.

## Out of Scope

- New goal closure reasons.
- A new "achieved externally" workflow.
- Automatic archive/delete when a gift, company, or family member provides the item.
- Recording gifts or employer-provided items as personal expenses.
- Smart detection that converts normal expenses into goal fulfillment.
- Isolated project off-wallet spending, which remains covered by Epic 7 Issue 5.
- Retroactive semantic cleanup of historical user decisions beyond what is required for schema migration safety.
- Redesigning the full goal lifecycle matrix beyond removing the redundant completion mode.

## Further Notes

The practical product rule is:

```text
Goal purchase/use flow = user money left a real wallet and protected goal money backed that spending.

Gift/company/family paid = no user expense.

Bought with user money but not goal-backed = normal expense flow, then optionally unreserve/archive the goal.
```

The recommended user-facing copy for the second settlement mode is:

```text
I paid from another wallet/card, but use goal money
```

The recommended enum name is:

```text
GOAL_BACKED_OFF_WALLET_PAYMENT
```

This keeps the ledger reality-first while reducing user choice friction.
