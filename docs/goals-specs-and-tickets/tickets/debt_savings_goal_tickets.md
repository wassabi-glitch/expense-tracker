# Tickets: Debt Savings Goal

Build Debt Savings goals for debts the user owes, including wallet reservations, real debt-payment attribution, completion, and reversal. Source spec: `../specs/debt_savings_goal_spec.md`.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

## Proposed Breakdown

1. **Establish Debt Savings Goal creation and eligibility**
   - Blocked by: None
   - What it delivers: users can create one active Debt Savings goal for an eligible open debt they owe.

2. **Reserve and unreserve Debt Savings money**
   - Blocked by: Ticket 1
   - What it delivers: users can protect and release exact wallet money for the linked debt without changing the debt balance.

3. **Prepare Debt Savings payment wallets**
   - Blocked by: Ticket 2
   - What it delivers: users can move real money and matching reservation before paying the creditor.

4. **Record a Debt Payment with goal and ordinary attribution**
   - Blocked by: Ticket 2
   - What it delivers: users can record the real creditor payment from any wallet combination and split each leg into goal-funded and ordinary money.

5. **Enforce full and partial goal capacity during payments**
   - Blocked by: Ticket 4
   - What it delivers: full-mode and partial-mode goal-funded limits are enforced without capping valid ordinary payment money.

6. **Complete Debt Savings goals and release leftover reservations**
   - Blocked by: Ticket 5
   - What it delivers: goals complete for target-paid, debt-closed, or finish-early reasons and release leftover reservations.

7. **Apply debt actions to linked goal state**
   - Blocked by: Ticket 1
   - What it delivers: debt charges, forgiveness, corrections, metadata edits, and archive attempts affect linked goals truthfully.

8. **Reverse Debt Payment and lifecycle bundles**
   - Blocked by: Tickets 6, 7
   - What it delivers: reversing linked debt actions restores debt, wallets, reservations, progress, releases, and goal status together.

9. **Harden Debt Savings reliability and acceptance coverage**
   - Blocked by: Ticket 8
   - What it delivers: regression coverage proves creation, reservation, payment, completion, debt changes, reversal, idempotency, and UI behavior.

## Ticket 1: Establish Debt Savings Goal Creation and Eligibility

**What to build:** Users can create one active Debt Savings goal for an open debt they owe, choosing either Save everything left or Save a smaller amount, without moving wallet money or changing the debt balance.

**Blocked by:** None - can start immediately.

- [ ] Open debts where the user owes money are eligible for Debt Savings goal creation.
- [ ] Incoming, closed, reversed, deleted, or non-positive debts are rejected.
- [ ] A second active Debt Savings goal for the same debt is rejected.
- [ ] Save everything left uses the live debt balance as its readiness target.
- [ ] Save a smaller amount validates the user-selected target against the current debt balance.
- [ ] Creating the goal creates no wallet movement, no reservation, and no debt-ledger balance change.

## Ticket 2: Reserve and Unreserve Debt Savings Money

**What to build:** Users can protect free money in specific wallets for a Debt Savings goal and later unreserve it while the goal is active, with wallet balances unchanged and goal metrics updated.

**Blocked by:** Ticket 1: Establish Debt Savings Goal Creation and Eligibility.

- [ ] Reserve Money protects only free wallet money that is not already protected for another goal or obligation.
- [ ] Reserve Money can allocate from one or multiple wallets without changing real wallet balances.
- [ ] Unreserve returns protected money to free money without changing the real wallet balance.
- [ ] Debt balance and paid-through-goal remain unchanged by reserve and unreserve actions.
- [ ] The goal card shows debt remaining, reserved now, and paid through this goal as separate values.
- [ ] Reserve and unreserve operations are atomic and idempotent.

## Ticket 3: Prepare Debt Savings Payment Wallets

**What to build:** Before paying a creditor, users can move real money and matching Debt Savings reservation from source wallets to the wallet expected to pay, without affecting the debt balance.

**Blocked by:** Ticket 2: Reserve and Unreserve Debt Savings Money.

- [ ] Prepare Payment transfers real money from reserve source wallets to destination payment wallets.
- [ ] Matching reservations relocate from source wallets to destination wallets in the same operation.
- [ ] Total reservation before and after preparation is unchanged.
- [ ] Debt balance and paid-through-goal remain unchanged.
- [ ] The destination wallet can later use the relocated reservation in Record Debt Payment.
- [ ] Prepare Payment cannot be used to invent a transfer after the creditor payment already occurred.

## Ticket 4: Record a Debt Payment With Goal and Ordinary Attribution

**What to build:** Users can record the real creditor payment from any wallet combination and attribute each payment leg between debt-savings-funded and ordinary money in a two-step preview and completion flow.

**Blocked by:** Ticket 2: Reserve and Unreserve Debt Savings Money.

- [ ] The wizard asks which wallets actually paid, the amount from each wallet, and how much from each leg uses Debt Savings.
- [ ] The user is never asked to choose Direct, OffWallet, or Mixed.
- [ ] Each payment leg enforces `goal-funded <= payment amount` and `goal-funded <= same wallet reservation`.
- [ ] Payment above a wallet's reservation is accepted when the excess is ordinary money and the wallet has spendable balance.
- [ ] The full payment reduces the debt exactly once.
- [ ] Only goal-funded amounts consume reservations and increase paid-through-goal.
- [ ] Step 2 preview and final completion use the same backend policy and show debt, wallet, reservation, and attribution changes.

## Ticket 5: Enforce Full and Partial Goal Capacity During Payments

**What to build:** Debt payment attribution respects the selected goal mode, including live full-mode readiness and partial-mode capacity, while still allowing real payments above the goal-funded portion.

**Blocked by:** Ticket 4: Record a Debt Payment With Goal and Ordinary Attribution.

- [ ] Save everything left caps goal-funded use by available reservations, payment amount, and current debt balance.
- [ ] Save a smaller amount caps only the goal-funded portion by remaining partial target capacity.
- [ ] A large debt payoff can include a small goal-funded portion and a larger ordinary portion.
- [ ] User-reduced smart defaults, including zero goal use, are honored.
- [ ] Payment total above the current debt balance is rejected.
- [ ] Stale preview state is rejected and forces the user to review updated values.

## Ticket 6: Complete Debt Savings Goals and Release Leftover Reservations

**What to build:** Debt Savings goals complete for the correct reason, release leftover reservations without moving real wallet balances, and allow a new goal when appropriate.

**Blocked by:** Ticket 5: Enforce Full and Partial Goal Capacity During Payments.

- [ ] Partial goals complete with `TARGET_PAID` when the effective target is paid through the goal.
- [ ] Any active linked goal completes with `DEBT_CLOSED` when the linked debt reaches zero.
- [ ] Partial goals can be finished early with `FINISHED_EARLY` and a stored achieved amount.
- [ ] Completion releases all remaining reservations to free money without changing wallet balances.
- [ ] Completed cards show the real completion reason instead of misleading 100 percent funded language.
- [ ] A new Debt Savings goal can be created for the same debt after the previous one completes, if the debt remains eligible.

## Ticket 7: Apply Debt Actions to Linked Goal State

**What to build:** Debt charges, forgiveness, balance corrections, metadata edits, and archive attempts interact with active Debt Savings goals according to debt truth, without pretending they are goal-funded payments.

**Blocked by:** Ticket 1: Establish Debt Savings Goal Creation and Eligibility.

- [ ] Charges increase the live readiness requirement for full-mode goals.
- [ ] Charges do not grow the original target for partial-mode goals.
- [ ] Forgiveness and balance corrections reduce debt without increasing paid-through-goal.
- [ ] Debt closure through forgiveness or correction completes the linked goal with `DEBT_CLOSED` and releases reservations.
- [ ] Debt metadata edits do not affect reservations, paid-through-goal, or goal status.
- [ ] Archiving an open debt with an active Debt Savings goal requires an explicit resolution flow.

## Ticket 8: Reverse Debt Payment and Lifecycle Bundles

**What to build:** Reversing debt actions restores every linked debt, wallet, reservation, progress, release, and goal-status effect as one causal bundle.

**Blocked by:**

- Ticket 6: Complete Debt Savings Goals and Release Leftover Reservations.
- Ticket 7: Apply Debt Actions to Linked Goal State.

- [ ] Reversing a goal-funded payment restores debt balance, payment wallet balances, consumed reservations, and paid-through-goal.
- [ ] Reversing a mixed payment restores ordinary wallet outflows as well as goal-funded reservation effects.
- [ ] If a payment caused completion, reversal reopens the goal and restores released reservations when feasible.
- [ ] Reversing forgiveness or correction also reverses linked goal completion and release when those effects were caused by the original event.
- [ ] Reversal is blocked when restoration would violate wallet balances, currency rules, or reservation constraints.
- [ ] Reversal appends or records inverse effects without destructive deletion of financial history.

## Ticket 9: Harden Debt Savings Reliability and Acceptance Coverage

**What to build:** Debt Savings behavior is covered by focused tests and reliability checks across creation, reservation, payment, completion, debt changes, reversal, idempotency, concurrency, and wallet-order independence.

**Blocked by:** Ticket 8: Reverse Debt Payment and Lifecycle Bundles.

- [ ] Backend tests cover creation eligibility, duplicate active goal rejection, and partial target validation.
- [ ] Backend tests cover reserve, unreserve, Prepare Payment, fully goal-funded payment, OffWallet ordinary payment, same-wallet excess payment, and mixed payment.
- [ ] Backend tests cover partial target cap on goal-funded amount but not total payment amount.
- [ ] Backend tests cover target-paid completion, debt-closed completion, finish-early completion, and leftover reservation release.
- [ ] Backend tests cover debt charge, forgiveness, correction, and reversal effects on linked goals.
- [ ] UI tests cover the two-step wizard, no technical mode selection, plain-language attribution, stale preview handling, and completed-card reason display.
- [ ] Idempotent retries do not duplicate payment, reservation, release, or reversal records.
