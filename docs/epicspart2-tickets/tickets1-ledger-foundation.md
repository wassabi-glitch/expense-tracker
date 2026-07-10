# Tickets: Ledger Foundation & Chronological Integrity

Source spec: `docs/epicspart2-specs/spec-1-ledger-foundation.md`

These tickets build the minimum immutable-ledger foundation before deeper Epicspart2 execution. Work the frontier: any ticket whose blockers are complete can start. The intended first implementation path is narrow: establish shared reversal behavior, enforce chronological boundaries, then convert standalone income as the proof slice.

## Proposed Breakdown

1. **Standardize posted financial-event void and reversal behavior**
   - Blocked by: None
   - What it delivers: one trustworthy way to void posted money without erasing ledger history.

2. **Enforce wallet epoch boundaries for wallet-touching money flows**
   - Blocked by: None
   - What it delivers: no money movement can be dated before the relevant wallet exists.

3. **Enforce user-timezone normal logging boundaries**
   - Blocked by: Ticket 2
   - What it delivers: normal expense/income logging respects the user's local today and routes past activity toward reconciliation.

4. **Convert standalone income delete to void and reversal**
   - Blocked by: Tickets 1, 2, 3
   - What it delivers: deleting posted income preserves the original financial fact and appends a reversing fact.

5. **Convert standalone income financial edits to correction reposts**
   - Blocked by: Ticket 4
   - What it delivers: changing posted income amount, date, wallet, or source preserves the original and records the corrected financial truth.

6. **Add closed-period correction guardrails for normal money entry**
   - Blocked by: Ticket 3
   - What it delivers: closed months stay sealed and missed closed-period activity becomes a current correction path.

7. **Add immutable-ledger regression guardrails for new obligation work**
   - Blocked by: Tickets 1, 4, 5
   - What it delivers: debt and payment-plan Epicspart2 work has a clear no-hard-delete, no-rewrite contract before new behavior is added.

8. **Add wallet projection verification around reversals and corrections**
   - Blocked by: Tickets 1, 4, 5
   - What it delivers: current wallet balances can be trusted after create, void, reversal, and corrected repost flows.

9. **Document the Epicspart2 money-history definition of done**
   - Blocked by: Tickets 1, 2, 3, 4, 5, 6, 7, 8
   - What it delivers: future Epicspart2 tickets have an explicit standard for ledger immutability, chronology, and test coverage.

## Ticket 1: Standardize Posted Financial-Event Void And Reversal Behavior

**What to build:** A shared, reusable way to void posted financial events without hard-deleting them. From the user's perspective, deleting posted money should keep the original record, add a clear reversal, and leave current balances correct.

**Blocked by:** None - can start immediately.

- [x] A posted financial event can be voided through one shared application-level behavior.
- [x] Voiding preserves the original event instead of deleting it.
- [x] Voiding appends a reversal event with counter-balancing wallet and entity ledger effects.
- [x] The original and reversal events are linked so the audit trail is explainable.
- [x] A second void attempt on the same posted event is rejected or made idempotent with clear behavior.
- [x] Metadata-only fields remain editable without creating a reversal.
- [x] Existing expense delete behavior continues to work through or consistently with the shared reversal behavior.
- [x] Tests prove the original event remains queryable after voiding.
- [x] Tests prove wallet math returns to the expected balance after reversal.

## Ticket 2: Enforce Wallet Epoch Boundaries For Wallet-Touching Money Flows

**What to build:** Per-wallet epoch validation for money movement. From the user's perspective, Sarflog should refuse to record expenses, income, transfers, settlements, or adjustments before the wallet's tracked financial truth begins.

**Blocked by:** None - can start immediately.

- [x] A wallet's creation date acts as the earliest allowed date for money movement touching that wallet.
- [x] Same-day activity on the wallet creation date is allowed.
- [x] The rule is per wallet, not global per user.
- [x] Cash wallets and credit wallets follow the same epoch principle.
- [x] Multi-wallet money movements validate every touched wallet.
- [x] Transfers validate both source and destination wallet epochs.
- [x] Reconciliation adjustments cannot be dated before the target wallet epoch.
- [x] User-facing errors explain that the requested date is before the wallet's tracking start.

- [x] Tests cover at least one accepted same-day case and one rejected pre-epoch case.

## Ticket 3: Enforce User-Timezone Normal Logging Boundaries

**What to build:** User-local date validation for normal money logging. From the user's perspective, "today" should mean their local today, and missed past activity should not be casually entered through normal add flows.

**Blocked by:** Ticket 2: Enforce wallet epoch boundaries for wallet-touching money flows.

- [x] Normal expense logging uses the user's effective timezone for today's date.
- [x] Normal income logging uses the user's effective timezone for today's date.
- [x] Future-dated normal expense and income entries are rejected according to the user's local date.
- [x] Past-dated normal expense and income entries are rejected or routed to the reconciliation path according to the product rule.
- [x] Existing request timezone behavior is preserved.
- [x] Tests cover a timezone boundary where server date and user date could differ.
- [x] Tests use the project's timezone helpers rather than server-local dates.
- [x] Error messages distinguish future-date rejection from past-date/reconciliation guidance.

## Ticket 4: Convert Standalone Income Delete To Void And Reversal

**What to build:** Deleting posted standalone income should use the immutable ledger pattern. From the user's perspective, removing an income entry should correct the wallet balance while keeping a durable record of what was originally logged and why it was reversed.

**Blocked by:**

- Ticket 1: Standardize posted financial-event void and reversal behavior.
- Ticket 2: Enforce wallet epoch boundaries for wallet-touching money flows.
- Ticket 3: Enforce user-timezone normal logging boundaries.

- [x] Deleting posted standalone income no longer hard-deletes the posted financial event.
- [x] Deleting posted standalone income appends a reversal event.
- [x] The original income event is marked voided.
- [x] Wallet ledger effects are counter-balanced exactly once.
- [x] Entity/source ledger history remains explainable after delete.
- [x] Deleting already-voided income is rejected or idempotent with clear behavior.
- [x] Debt or expected-inflow links affected by the income reversal remain consistent.
- [x] Tests prove the original income event remains queryable.
- [x] Tests prove the wallet balance after income delete matches the balance before the income was created.

## Ticket 5: Convert Standalone Income Financial Edits To Correction Reposts

**What to build:** Financial edits to posted standalone income should become a correction flow. From the user's perspective, changing amount, wallet allocation, date, or source should produce a corrected current result without pretending the original entry never existed.

**Blocked by:** Ticket 4: Convert standalone income delete to void and reversal.

- [x] Metadata-only income edits remain possible without reversal.
- [x] Editing income amount voids/reverses the original financial event and posts a corrected event.
- [x] Editing income wallet allocation voids/reverses the original financial event and posts a corrected event.
- [x] Editing income source voids/reverses the original financial event and posts a corrected event.
- [x] Editing income date voids/reverses the original financial event and posts a corrected event if the corrected date is allowed.
- [x] Corrected reposts preserve user-visible title/note behavior.
- [x] Corrected reposts respect wallet epoch and user-timezone date boundaries.
- [x] Corrected reposts keep wallet balances mathematically exact.
- [x] Tests prove old ledger legs are not rewritten in place.
- [x] Tests prove the response still returns the corrected current income entry shape expected by the UI.

## Ticket 6: Add Closed-Period Correction Guardrails For Normal Money Entry

**What to build:** Month closing behavior for normal money entry. From the user's perspective, recent cleanup is possible inside the grace window, but old closed-month history is sealed and missed activity becomes a current correction.

**Blocked by:** Ticket 3: Enforce user-timezone normal logging boundaries.

- [x] The current month remains open for allowed normal and reconciliation behavior.
- [x] The closing window allows cleanup according to the accepted grace-window rule.
- [x] Closed months reject direct backdated normal money entry.
- [x] Missed activity for a closed month is represented as a current correction rather than a rewrite of the closed period.
- [x] Current corrections include enough context for the user to understand what past period they refer to.
- [x] User-facing dates use the effective user timezone.
- [x] Tests cover open month, closing window, and closed-period behavior.
- [x] Tests prove closed-period corrections affect the current allowed period instead of the sealed historical period.

## Ticket 7: Add Immutable-Ledger Regression Guardrails For New Obligation Work

**What to build:** Guardrails that keep new debt and payment-plan Epicspart2 work aligned with the ledger foundation. From the user's perspective, obligations should not become a separate system that erases payment or correction history.

**Blocked by:**

- Ticket 1: Standardize posted financial-event void and reversal behavior.
- Ticket 4: Convert standalone income delete to void and reversal.
- Ticket 5: Convert standalone income financial edits to correction reposts.

- [x] New debt/payment-plan money-changing flows are expected to append ledger facts rather than hard-delete posted financial history.
- [x] New debt/payment-plan correction flows are expected to use reversal or adjustment rows rather than rewriting prior rows in place.
- [x] Payment-plan and debt current-state fields are treated as projections where money history exists.
- [x] At least one debt or payment-plan regression test proves posted financial events remain available after an undo/reversal-style action.
- [x] Tests distinguish immutable money facts from mutable metadata or planning intent.
- [x] The guardrails do not force budgets, recurring templates, or drafts into the global financial ledger.
- [x] The behavior is documented clearly enough for subsequent Epicspart2 implementation tickets to follow.

## Ticket 8: Add Wallet Projection Verification Around Reversals And Corrections

**What to build:** Confidence checks for wallet balances after ledger operations. From the user's perspective, the displayed wallet balance should remain trustworthy after create, void, reversal, and corrected repost flows.

**Blocked by:**

- Ticket 1: Standardize posted financial-event void and reversal behavior.
- Ticket 4: Convert standalone income delete to void and reversal.
- Ticket 5: Convert standalone income financial edits to correction reposts.

- [ ] Wallet balance after a normal posted money event matches the expected projection.
- [ ] Wallet balance after void/reversal matches the expected projection.
- [ ] Wallet balance after income corrected repost matches the expected projection.
- [ ] Multi-wallet operations are included in the projection verification.
- [ ] Projection checks account for the wallet opening snapshot or equivalent starting point.
- [ ] Tests prove reversals do not double-apply wallet effects.
- [ ] Tests prove corrected reposts do not leave stale wallet effects from the original event.
- [ ] Failures produce useful debugging information for event and wallet ledger mismatch.

## Ticket 9: Document The Epicspart2 Money-History Definition Of Done

**What to build:** A short implementation standard for future Epicspart2 work. From the developer's perspective, every new money-history feature should know how to handle epoch boundaries, user-timezone dates, immutable corrections, projections, and tests before code starts.

**Blocked by:**

- Ticket 1: Standardize posted financial-event void and reversal behavior.
- Ticket 2: Enforce wallet epoch boundaries for wallet-touching money flows.
- Ticket 3: Enforce user-timezone normal logging boundaries.
- Ticket 4: Convert standalone income delete to void and reversal.
- Ticket 5: Convert standalone income financial edits to correction reposts.
- Ticket 6: Add closed-period correction guardrails for normal money entry.
- Ticket 7: Add immutable-ledger regression guardrails for new obligation work.
- Ticket 8: Add wallet projection verification around reversals and corrections.

- [ ] The standard explains when a feature must use append-only financial history.
- [ ] The standard explains when mutable metadata is still acceptable.
- [ ] The standard explains how wallet epoch and user-timezone date validation should be applied.
- [ ] The standard explains how void, reversal, corrected repost, and current correction differ.
- [ ] The standard explains that budgets, recurring templates, and drafts are not automatically global financial ledger events.
- [ ] The standard includes a testing checklist for money-history features.
- [ ] The standard is written in project domain language so future specs and tickets can reference it.
