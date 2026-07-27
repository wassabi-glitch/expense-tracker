# Tickets: Planned Purchase Goal

Build terminal Planned Purchase settlement so users record the real final checkout, Sarflog derives Direct, OffWallet, or Mixed behavior, and the goal closes without hidden transfers. Source spec: `../specs/planned_purchase_goal_spec.md`.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

## Proposed Breakdown

1. **Establish Planned Purchase funding and settlement policy**
   - Blocked by: None
   - What it delivers: an authoritative backend policy can preview and validate Direct, OffWallet, and Mixed final purchase settlement.

2. **Record a Direct Planned Purchase**
   - Blocked by: Ticket 1
   - What it delivers: users can complete a purchase paid from funding wallets and release unused protection.

3. **Record OffWallet and Mixed Planned Purchases**
   - Blocked by: Ticket 2
   - What it delivers: users can complete purchases paid from non-funding wallets or mixed wallet sources without hidden transfers.

4. **Build the two-step Record Purchase wizard**
   - Blocked by: Ticket 3
   - What it delivers: users record actual payment wallets and review backend-derived consequences before completion.

5. **Add Planned Purchase Prepare Payment**
   - Blocked by: Ticket 1
   - What it delivers: users can explicitly move real money and matching protection before checkout.

6. **Persist Planned Purchase audit bundles and idempotency**
   - Blocked by: Ticket 4
   - What it delivers: completion is auditable, idempotent, and stores source facts for recalculation.

7. **Reverse Planned Purchase completion**
   - Blocked by: Ticket 6
   - What it delivers: a completed purchase can be reversed as one linked bundle when exact restoration is safe.

8. **Harden Planned Purchase acceptance coverage**
   - Blocked by: Ticket 7
   - What it delivers: tests prove classification, validation, settlement, Prepare Payment, audit, reversal, idempotency, concurrency, and UI behavior.

## Ticket 1: Establish Planned Purchase Funding and Settlement Policy

**What to build:** Planned Purchase goals have an authoritative settlement policy that can derive mode, validate totals and per-wallet limits, and produce a preview without mutating state.

**Blocked by:** None - can start immediately.

- [ ] The policy constructs funding, payment, Direct, and OffWallet sets from current allocations and payment legs.
- [ ] The policy derives exactly one mode: Direct, OffWallet, or Mixed.
- [ ] Settlement requires positive existing funding and a positive final purchase payment.
- [ ] Total payment above total funded amount is rejected.
- [ ] A funding wallet cannot pay more than its own current goal allocation.
- [ ] Every payment wallet must have enough spendable balance after preserving other protected money.
- [ ] Preview output includes final purchase amount, derived mode, wallet outflows, protection releases, unused amount, and validation errors.

## Ticket 2: Record a Direct Planned Purchase

**What to build:** Users can complete a Planned Purchase paid only from wallets that hold the goal money, including multi-wallet Direct payments and unused protection release.

**Blocked by:** Ticket 1: Establish Planned Purchase Funding and Settlement Policy.

- [ ] Record Purchase accepts one or more payment wallets that all funded the goal.
- [ ] Each Direct payment wallet is capped by its own current goal allocation.
- [ ] Funding wallets that do not pay remain valid and have their protection released on completion.
- [ ] Only actual payment wallets lose real balance.
- [ ] All current goal protection becomes zero after successful completion.
- [ ] The goal status changes from `ACTIVE` to `COMPLETED`.
- [ ] The unused amount equals total funding minus total payment.

## Ticket 3: Record OffWallet and Mixed Planned Purchases

**What to build:** Users can complete a Planned Purchase when checkout uses non-funding wallets or a mix of funding and non-funding wallets, with no artificial source pairing or hidden transfers.

**Blocked by:** Ticket 2: Record a Direct Planned Purchase.

- [ ] OffWallet settlement is accepted when no payment wallet funded the goal.
- [ ] Mixed settlement is accepted when at least one funding wallet and at least one non-funding wallet pay.
- [ ] OffWallet payment wallets lose real balance and funding-wallet real balances remain unchanged.
- [ ] Mixed payment wallets lose only the amounts they actually paid.
- [ ] Direct portions are attributed to specific funding wallets, while OffWallet portions are tracked only against aggregate funded capacity.
- [ ] The system does not invent funding-wallet to payment-wallet mappings.
- [ ] No automatic real transfer or rebalancing is created.

## Ticket 4: Build the Two-Step Record Purchase Wizard

**What to build:** The frontend gives users one Record Purchase flow that asks which wallets actually paid and shows an authoritative review before completion.

**Blocked by:** Ticket 3: Record OffWallet and Mixed Planned Purchases.

- [ ] Step 1 asks for purchase date, payment wallets, payment amounts, and optional merchant/category/note data.
- [ ] The UI never asks the user to choose Direct, OffWallet, or Mixed.
- [ ] Payment rows show wallet balance, amount protected for this goal, valid row maximum, and amount paid.
- [ ] Step 2 is populated from backend preview data, not independently calculated frontend settlement logic.
- [ ] Review copy groups consequences in plain language for goal-money wallets, other wallets, and unused money released.
- [ ] Completion revalidates current state and blocks stale previews with a useful message.

## Ticket 5: Add Planned Purchase Prepare Payment

**What to build:** Before checkout, users can explicitly move real money and matching goal protection to the wallet expected to pay, without completing the purchase or creating reimbursement semantics.

**Blocked by:** Ticket 1: Establish Planned Purchase Funding and Settlement Policy.

- [ ] Prepare Payment transfers real balance from source wallet to destination wallet.
- [ ] Matching goal protection relocates from source wallet to destination wallet.
- [ ] Total goal funding remains unchanged.
- [ ] The goal remains active and no purchase is created.
- [ ] The destination wallet can later participate as a Direct payment wallet.
- [ ] Prepare Payment cannot be automatically invented after the purchase occurred.

## Ticket 6: Persist Planned Purchase Audit Bundles and Idempotency

**What to build:** Completion stores one auditable bundle that ties together the purchase, wallet outflows, allocation releases, derived mode, goal completion, and idempotency behavior.

**Blocked by:** Ticket 4: Build the Two-Step Record Purchase Wizard.

- [ ] The bundle stores total funded before settlement, total payment, Direct paid, OffWallet paid, unused amount, and derived mode.
- [ ] The bundle stores payment wallet IDs and amounts, funding wallet IDs and allocations before settlement, and wallet balances before and after.
- [ ] Payment legs and allocation events remain the source of truth; mode is derived data.
- [ ] Completion uses an idempotency key and retrying the same request returns the existing bundle.
- [ ] Goal, funding allocations, and payment wallets are locked or version-checked before commit.
- [ ] Any validation failure leaves all wallet, goal, purchase, and audit state unchanged.

## Ticket 7: Reverse Planned Purchase Completion

**What to build:** A completed Planned Purchase can be reversed as one linked bundle when exact restoration is safe.

**Blocked by:** Ticket 6: Persist Planned Purchase Audit Bundles and Idempotency.

- [ ] Reversal restores each payment wallet by the amount it paid.
- [ ] Reversal restores the original per-wallet goal allocations.
- [ ] Reversal changes the goal from `COMPLETED` back to `ACTIVE`.
- [ ] Reversal removes or voids the active purchase completion record and links to the original bundle.
- [ ] Budget/category effects are restored when they were part of the completion bundle.
- [ ] Reversal is blocked when released money has since been spent or protected in a way that prevents truthful restoration.
- [ ] Reversal is atomic and idempotent.

## Ticket 8: Harden Planned Purchase Acceptance Coverage

**What to build:** Planned Purchase settlement is covered across classification, validation, settlement, Prepare Payment, audit, reversal, idempotency, concurrency, and UI behavior.

**Blocked by:** Ticket 7: Reverse Planned Purchase Completion.

- [ ] Tests cover Direct, OffWallet, Mixed, duplicate wallet row aggregation, zero-row ignoring, and row-order independence.
- [ ] Tests reject payment above total funding, Direct wallet payment above local allocation, insufficient spendable balance, zero payment, negative amount, completed goal, stale preview, and currency failure.
- [ ] Tests verify only payment wallets lose real balance and all goal protection becomes zero after completion.
- [ ] Tests verify unused amount and global free-money change equal total funding minus total payment.
- [ ] Tests cover Prepare Payment conservation and no hidden post-purchase transfer.
- [ ] Tests cover purchase bundle contents, mode recalculation from source data, duplicate Complete behavior, and full rollback on failure.
- [ ] UI tests verify the wizard avoids technical mode selection and renders backend preview consequences.
