# PRD: G37 - Strict Isolated Project Wallet Spend Caps

Labels: `ready-for-agent`

## Problem Statement

Isolated Projects lock real wallet money so major events like weddings, renovations, and PC builds cannot accidentally consume everyday budget money. The existing pooled-vault language correctly says wallets should not map directly to project categories, but it can be misread too broadly during expense posting: a user might pay an isolated project expense from a wallet that contributed nothing to the project, or spend more from one project wallet than that wallet contributed.

That behavior would weaken the quarantine model. If a wallet can pay project expenses without explicit project funding, the app stops protecting users from double-spending and becomes a loose tagging system instead of a strict zero-based project vault.

## Solution

Keep Isolated Projects strict. A project expense may only be paid from wallets that have active isolated project funding for that project, and each selected wallet may only pay up to its remaining project-funded amount.

The remaining project-funded amount for a wallet is:

```text
wallet_project_remaining =
  wallet_project_allocations
  + wallet_project_topups
  - project_expenses_paid_from_that_wallet
  + refunds_or_reversals_to_that_wallet
```

For the current Issue 4 scope, wallet project funding comes from existing isolated project wallet allocation rows. Future top-up work must feed the same remaining calculation rather than create a separate spending rule.

Project categories still classify project intent. They do not become wallet-specific buckets. The strict wallet cap is only a liquidity quarantine rule: a wallet cannot pay more isolated project spending than the amount it contributed to that isolated project.

## User Stories

1. As a project user, I want only wallets that funded an isolated project to be available for that project's expenses, so that unrelated money is not accidentally spent.
2. As a project user, I want each project wallet to be capped by its remaining contribution, so that one wallet cannot silently cover another wallet's project responsibility.
3. As a project user, I want project categories to remain separate from wallets, so that Food, Venue, and Transport classify intent without creating wallet-to-category mappings.
4. As a project user, I want a clear error when a wallet has no remaining project funding, so that I know I need to choose another project wallet or top up.
5. As a project user, I want a clear error when a project category would be exceeded, so that I know I need to rebalance internal project funding.
6. As a project user, I want refunds and voids to restore the relevant wallet's project remaining amount, so that corrected history does not permanently consume project funding.
7. As a project user, I want session-based expense finalization to follow the same strict wallet rules as single expense entry, so that receipt workflows cannot bypass the project vault.
8. As a project user, I want isolated project expenses to keep bypassing monthly budget rows, so that major event spending does not distort normal monthly budget limits.
9. As a project user, I want completed and archived projects to reject new spending, so that closed project history stays stable.
10. As a project user, I want expenses through the target end date to be accepted in my timezone, so that the final project day behaves as expected.
11. As a project user, I want expenses after the target end date to be blocked unless the project is extended or reopened, so that leftover-sweep timing remains trustworthy.
12. As a budget user, I want isolated project spending to still roll up into global category analytics, so that yearly category reporting remains useful.

## Implementation Decisions

- Strict wallet eligibility means the selected wallet is user-owned, active, linked to the isolated project by funding rows, and has positive remaining project-funded amount.
- Wallet spend caps are enforced per wallet allocation on expense posting. Multi-wallet expenses are allowed only when every selected wallet can cover its own allocated payment amount.
- A wallet that contributed `0` to an isolated project is not eligible for normal isolated project expense posting.
- A wallet that contributed `400K` and has no prior project spending may pay at most `400K` toward that project until future top-up support increases its project-funded amount.
- The pooled-vault rule still stands at the category layer: wallets do not fund individual project categories. A wallet cap does not mean Wallet A funds Food and Wallet B funds Venue.
- The total project remaining, parent category remaining, and optional micro-subcategory remaining checks all still apply in addition to the wallet cap.
- Isolated project expenses continue to bypass monthly budget materialization and monthly budget limit math.
- Refund and void/reversal ledger events must reduce isolated project spent totals and restore wallet project remaining through immutable ledger math.
- Stable backend error codes should distinguish wallet-cap failures from category, subcategory, lifecycle, and date failures.
- Future cascading top-ups must update the same wallet-project remaining calculation rather than introducing a second source of truth.

## Testing Decisions

- Backend tests should exercise expense posting through public HTTP endpoints, not private helper functions.
- Tests should cover a linked wallet paying within its remaining contribution, a zero-contribution wallet being blocked, and a linked wallet being blocked when it exceeds its remaining contribution.
- Tests should cover multi-wallet payment where each wallet pays within its own remaining contribution.
- Tests should cover a session draft finalize path so receipt/session workflows cannot bypass strict wallet caps.
- Tests should preserve timezone behavior by using `X-Timezone` headers and `user_timezone_today()` for user-facing dates.
- Tests should prove isolated project expenses do not require a monthly budget row.
- Existing project funding and category allocation tests are prior art for setup and expected response shapes.

## Out of Scope

- Off-project-wallet reimbursement flows are out of scope for Issue 4.
- Cascading top-ups and internal rebalancing are owned by Epic 6 Issue 5.
- Infinite nested subcategories are out of scope. Issue 4 only relies on parent category plus optional current project micro-subcategory behavior.
- External bank integration is out of scope.
- Changing historical ledger rows is out of scope.

## Further Notes

This PRD intentionally chooses a stricter v1 than a fully flexible pooled-vault interpretation. The product tradeoff is worthwhile: the model is easier to explain, safer for wallet quarantine, and less likely to corrupt the user's mental model of locked project money.
