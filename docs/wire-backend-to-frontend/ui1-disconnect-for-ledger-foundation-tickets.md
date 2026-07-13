# Tickets: UI1 Ledger Foundation Disconnects

Source spec: `docs/wire-backend-to-frontend/ui1-disconnect-for-ledger-foundation.md`

These tickets wire the Ledger Foundation rules through the UI-facing posted-money paths found in the UI1 audit. Work the frontier: any ticket whose blockers are complete can start. The intended first implementation path is narrow: preserve structured wallet-epoch errors, then close the backend validation holes flow by flow, then add cross-flow regression guardrails.

## Proposed Breakdown

1. **Surface wallet epoch errors end-to-end**
   - Blocked by: None
   - What it delivers: users see clear wallet tracking-start errors instead of internal codes when any UI flow hits the epoch boundary.

2. **Enforce wallet epochs on Expected Inflow receipts**
   - Blocked by: Ticket 1
   - What it delivers: receiving expected money into wallets validates every destination wallet before posting money.

3. **Seal session expense finalization boundaries**
   - Blocked by: Ticket 1
   - What it delivers: receipt/session finalization follows the same date and wallet-epoch rules as normal expense creation.

4. **Enforce wallet epochs on Debt wallet movements**
   - Blocked by: Ticket 1
   - What it delivers: debt initial wallet movements and debt payments cannot post before any touched wallet's tracking start.

5. **Enforce wallet epochs on Payment Plan wallet movements**
   - Blocked by: Ticket 1
   - What it delivers: payment-plan setup, disbursement, and payment wallet movements obey wallet tracking-start dates.

6. **Add cross-flow Ledger Foundation guardrails**
   - Blocked by: Tickets 2, 3, 4, 5
   - What it delivers: the audited posted-money paths have shared regression coverage for epoch boundaries, user timezone dates, and wallet projection integrity.

## Ticket 1: Surface Wallet Epoch Errors End-To-End

**What to build:** A shared frontend error path for wallet tracking-start failures. From the user's perspective, any flow that tries to post money before a wallet's tracking start should explain which wallet caused the failure, which date was requested, and what earliest date is allowed.

**Blocked by:** None - can start immediately.

- [x] Structured wallet epoch errors preserve the backend detail object through the API client.
- [x] Wallet epoch errors render user-facing copy instead of an internal error code.
- [x] The message names the affected wallet when backend detail includes the wallet name.
- [x] The message includes the requested date and the wallet tracking-start date when backend detail includes them.
- [x] The message distinguishes wallet tracking-start failures from future-date failures.
- [x] The message distinguishes wallet tracking-start failures from closed-period failures.
- [x] The same translation path works for expenses, income, transfers, reconciliation, Expected Inflows, Debt, and Payment Plans.
- [x] Existing structured goal-protection and budget-required errors continue to render correctly.
- [x] Frontend tests cover a structured wallet epoch error with wallet name, requested date, and tracking-start date.

## Ticket 2: Enforce Wallet Epochs On Expected Inflow Receipts

**What to build:** Expected Inflow realization should validate every destination wallet before posting receipt money. From the user's perspective, planned income, receivables, refunds, and asset sales cannot become posted wallet history before the destination wallet exists.

**Blocked by:** Ticket 1: Surface wallet epoch errors end-to-end.

- [x] Realizing an Expected Inflow rejects a received date before any destination wallet's tracking start.
- [x] Same-day receipt on the destination wallet's tracking start is accepted.
- [x] Multi-wallet receipts validate every destination wallet.
- [x] Multi-wallet receipts reject the whole command if any destination wallet is invalid.
- [x] Rejected earned-income receipts create no Financial Event, Wallet Ledger, Entity Ledger, realization, allocation, or wallet balance change.
- [x] Rejected receivable receipts create no Debt payment, Debt Ledger, Financial Event, realization, allocation, or wallet balance change.
- [x] Rejected refund receipts create no refund event, realization, allocation, or wallet balance change.
- [x] Rejected asset-sale receipts create no sale event, asset closure, realization, allocation, or wallet balance change.
- [x] The receive dialog surfaces the shared wallet epoch error clearly.
- [x] Tests use explicit user timezone headers and project timezone helpers.

## Ticket 3: Seal Session Expense Finalization Boundaries

**What to build:** Finalizing a receipt/session draft should follow the same date and wallet-epoch rules as normal expense creation. From the user's perspective, receipt sessions are convenient, but they do not bypass closed-period or wallet tracking-start rules.

**Blocked by:** Ticket 1: Surface wallet epoch errors end-to-end.

- [x] Finalizing a session expense rejects future dates using the user's effective timezone.
- [x] Finalizing a session expense rejects sealed closed-period dates with current-correction guidance.
- [x] Finalizing a session expense accepts valid current-month dates.
- [x] Finalizing a session expense accepts allowed grace-window cleanup dates.
- [x] Finalizing validates every wallet allocation against the finalized expense date.
- [x] Rejected finalization leaves the draft editable.
- [x] Rejected finalization creates no posted Financial Event, Wallet Ledger, Entity Ledger, split Debt, or wallet balance change.
- [x] The session composer displays localized future-date, closed-period, and wallet epoch errors.
- [x] Accepted session finalization still updates budgets, wallet balances, splits, and ledger projections correctly.
- [x] Tests use project timezone helpers rather than server-local dates.

## Ticket 4: Enforce Wallet Epochs On Debt Wallet Movements

**What to build:** Debt flows that move wallet money should validate the transaction date against every touched wallet before recording debt history or wallet effects. From the user's perspective, obligations follow the same wallet tracking-start rule as ordinary money movement.

**Blocked by:** Ticket 1: Surface wallet epoch errors end-to-end.

- [x] Debt creation with initial wallet movement rejects dates before the touched wallet's tracking start.
- [x] Debt creation with initial multi-wallet movement rejects if any touched wallet is pre-epoch.
- [x] Debt payment rejects payment dates before any payment wallet's tracking start.
- [x] Same-day debt initial wallet movement remains accepted.
- [x] Same-day debt payment remains accepted.
- [x] Rejected debt creation creates no Financial Event, Wallet Ledger, Debt Ledger, Debt Transaction, allocation, or wallet balance change.
- [x] Rejected debt payment creates no Financial Event, Wallet Ledger, Debt Ledger, Debt Transaction, allocation, or wallet balance change.
- [x] Metadata-only debt edits remain mutable where they do not change posted money.
- [x] Debt UI flows surface the shared wallet epoch error.
- [x] Tests cover both informal and formal debt paths where wallet money moves.

## Ticket 5: Enforce Wallet Epochs On Payment Plan Wallet Movements

**What to build:** Payment Plan flows that move wallet money should validate the transaction date against every touched wallet before recording plan history or wallet effects. From the user's perspective, setup, disbursement, and payment activity cannot rewrite pre-wallet history.

**Blocked by:** Ticket 1: Surface wallet epoch errors end-to-end.

- [ ] Payment Plan setup with wallet movement rejects dates before any touched wallet's tracking start.
- [ ] Loan or disbursement wallet movement rejects dates before the disbursement wallet's tracking start.
- [ ] Payment Plan payment rejects paid dates before any payment wallet's tracking start.
- [ ] Split wallet allocations reject the whole command if any touched wallet is pre-epoch.
- [ ] Same-day setup activity remains accepted.
- [ ] Same-day disbursement activity remains accepted.
- [ ] Same-day payment activity remains accepted.
- [ ] Rejected commands create no Financial Event, Wallet Ledger, Payment Plan Ledger, payment allocation, row mutation, or wallet balance change.
- [ ] Planning-only schedule edits remain outside wallet epoch validation unless they post wallet money.
- [ ] Payment Plan UI flows surface the shared wallet epoch error.

## Ticket 6: Add Cross-Flow Ledger Foundation Guardrails

**What to build:** A regression guardrail matrix for all audited UI-facing posted-money paths. From the user's perspective, every way of posting money now obeys the same chronology rules and preserves wallet balance trust.

**Blocked by:**

- Ticket 2: Enforce wallet epochs on Expected Inflow receipts.
- Ticket 3: Seal session expense finalization boundaries.
- Ticket 4: Enforce wallet epochs on Debt wallet movements.
- Ticket 5: Enforce wallet epochs on Payment Plan wallet movements.

- [ ] A route/service test matrix covers expense creation.
- [ ] A route/service test matrix covers income creation and correction reposts.
- [ ] A route/service test matrix covers transfers.
- [ ] A route/service test matrix covers reconciliation.
- [ ] A route/service test matrix covers Expected Inflow receipt realization.
- [ ] A route/service test matrix covers session expense finalization.
- [ ] A route/service test matrix covers Debt wallet movement.
- [ ] A route/service test matrix covers Payment Plan wallet movement.
- [ ] Each covered flow has at least one accepted same-day epoch case.
- [ ] Each covered flow has at least one rejected pre-epoch case.
- [ ] Rejected flows prove no partial posted-money rows or wallet balance changes are committed.
- [ ] Accepted flows prove wallet projection remains valid after posting.
- [ ] Tests use user timezone helpers and explicit timezone headers where date boundaries matter.
- [ ] The guardrail documents which planning-only, metadata-only, template, and draft flows intentionally stay out of the global Financial Event ledger.
