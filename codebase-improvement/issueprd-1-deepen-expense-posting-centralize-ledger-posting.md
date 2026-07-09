# Issue Breakdown For PRD 1: Deepen Expense Posting And Centralize Ledger Posting

Parent PRD: `prd-1-deepen-expense-posting-centralize-ledger-posting.md`

Triage: ready-for-agent

## Proposed Breakdown For Approval

1. **Create the Financial Event Ledger seam through normal Expense Posting**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1, 11, 16, 17, 20, 21, 22, 25

2. **Route session draft finalization through Expense Posting**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 2, 13, 14, 15, 16, 18, 19, 20, 25

3. **Route Payment Plan expense posting through Expense Posting**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 4, 13, 14, 15, 16, 18, 19, 20, 23, 25

4. **Route Debt charge expense posting through Expense Posting**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 5, 6, 13, 15, 16, 18, 19, 20, 23, 25

5. **Move expense void and reversal mechanics behind Financial Event Ledger**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 11, 12, 18, 19, 21, 22, 25

6. **Route refund posting through Financial Event Ledger**
   - Type: AFK
   - Blocked by: 1, 5
   - User stories covered: 8, 11, 12, 18, 19, 21, 22, 24, 25

7. **Route earned income and expected inflow receipt posting through Financial Event Ledger**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 7, 9, 16, 18, 19, 21, 22, 24, 25

8. **Route wallet transfers and reconciliation adjustments through Financial Event Ledger**
   - Type: AFK
   - Blocked by: 1, 5
   - User stories covered: 10, 11, 12, 16, 18, 19, 21, 22, 25

Review questions before implementation:

- Does this granularity feel right, or should issue 7 be split into earned income, expected inflow receipts, and asset sales?
- Are Payment Plan and Debt charge posting correctly independent after the first seam issue?
- Should void/reversal work happen before session draft finalization, or is the current order acceptable?
- Are all slices correctly marked AFK?

---

## Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Introduce the Financial Event Ledger seam by migrating the existing normal expense posting path through it while preserving current user-visible behavior. The slice should keep normal expense creation demoable end to end: a user records an expense, Wallet balance changes, Wallet Ledger and Entity Ledger entries are written, Budget permission is linked, project and subcategory links survive, Budget-required failures remain structured, and user-local date validation remains intact.

This issue should establish the seam conservatively. The first adapter is normal Expense Posting. Do not migrate unrelated income, refund, transfer, Debt, or Payment Plan flows in this issue.

## Acceptance criteria

- [x] Normal expense creation still writes one posted Financial Event with the correct event type, title, description, date, and reference metadata.
- [x] Wallet Ledger entries still match caller-supplied wallet allocations, including owned and borrowed spend classification where applicable.
- [x] Entity Ledger entries still preserve category, Budget, subcategory, project, project subcategory, Debt, and Payment Plan links when supplied.
- [x] Budget-required failures still return the existing structured error used by the Global Budget Interceptor.
- [x] Future-date validation still uses the user's effective timezone.
- [x] Wallet protection and Wallet balance floor behavior remain unchanged.
- [x] Existing normal expense route tests pass.
- [x] New focused regression coverage proves the new seam preserves normal expense ledger behavior.

## Blocked by

None - can start immediately.

---

## Issue 2: Route Session Draft Finalization Through Expense Posting

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move session draft finalization onto the deepened Expense Posting seam. A finalized receipt/session should still produce one posted expense-shaped Financial Event, multiple Entity Ledger lines where needed, Wallet Ledger entries for the paid amount, Budget links, project and subcategory links, discount/original amount information, and split reimbursement Debts.

The completed slice should remove duplicated posting knowledge from session finalization while preserving the existing session draft workflow from the user's perspective.

## Acceptance criteria

- [x] Finalizing a valid session draft still creates the same user-visible posted expense event.
- [x] Multi-item sessions still create Entity Ledger lines with item labels, adjusted amounts, original amounts where discounted, categories, subcategories, project links, project subcategory links, and Budget links.
- [x] Wallet allocations still debit the selected Wallets exactly once.
- [x] Split reimbursement Debts and their Debt Ledger entries are still created when session splits are present.
- [x] Session draft status and finalized event linkage still update exactly once.
- [x] Budget-required, wallet-total mismatch, missing wallet, future-date, and split-total validation behavior remains unchanged.
- [x] Existing session draft route tests pass.
- [x] New regression coverage proves session finalization now exercises Expense Posting without asserting private helper call order.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 3: Route Payment Plan Expense Posting Through Expense Posting

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move Payment Plan expense-shaped posting onto Expense Posting. Payment Plans should continue owning schedule, status, waterfall, charge, allocation, and Payment Plan Ledger decisions, while Expense Posting owns the actual expense-shaped money event, Wallet Ledger entries, Entity Ledger category links, Budget permission, project links, and user-local date validation.

The completed slice should preserve the strict Payment Plan engine and the Global Budget Interceptor behavior for hidden charges and scheduled payments.

## Acceptance criteria

- [x] Recording a Payment Plan payment still creates the correct Payment Plan Ledger entries and updates schedule row status.
- [x] Expense-shaped Payment Plan payment events are posted through the Expense Posting seam.
- [x] Entity Ledger entries still preserve Payment Plan and payment-row links.
- [x] Wallet allocations still debit selected Wallets exactly once.
- [x] Budget-required failures still return the existing structured error when the category has no Budget permission.
- [x] Project, subcategory, and Budget limit validation behavior remains unchanged.
- [x] Existing Payment Plan payment, charge, write-off, and reversal tests pass where relevant to this slice.
- [x] New regression coverage proves a Payment Plan expense event has the same ledger links after migration.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 4: Route Debt Charge Expense Posting Through Expense Posting

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move Debt charge expense posting onto Expense Posting while keeping Debt-specific obligation math in the Debt modules. Debt should continue owning principal versus charge splits, Debt Ledger entries, Debt reconciliation, Dual Path rules, and receivable/payable direction. Expense Posting should own any expense-shaped charge event that affects Budget permission and category spend.

This slice should preserve the distinction between Debt and Payment Plan. It only shares the money posting seam.

## Acceptance criteria

- [x] Paying a Debt charge still creates the correct Debt Ledger entry and updates Debt balance.
- [x] Charge payments that are expense-shaped are posted through Expense Posting.
- [x] Entity Ledger entries still preserve Debt links and charge category impact.
- [x] Wallet allocations still affect Wallet balances exactly once.
- [x] Budget-required failures remain structured for Debt charge categories.
- [x] Goal protection behavior remains unchanged for outflowing Wallets.
- [x] Existing Debt payment and charge tests pass.
- [x] New regression coverage proves Debt charge expense posting preserves category spend and obligation ledger links.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 5: Move Expense Void And Reversal Mechanics Behind Financial Event Ledger

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move expense void and reversal mechanics behind the Financial Event Ledger seam. A user voiding a posted expense should still leave the original Financial Event in history, mark it voided, append a reversal Financial Event, write counter-balancing Wallet Ledger and Entity Ledger entries, and restore Wallet and Budget math without hard-deleting financial truth.

This slice should focus on expense void/reversal first. Other reversal paths can migrate later after this seam is proven.

## Acceptance criteria

- [x] Voiding a posted expense marks the original event voided instead of hard-deleting it.
- [x] Voiding a posted expense creates one reversal Financial Event with the correct status and reference metadata.
- [x] Reversal Wallet Ledger entries counter-balance the original Wallet Ledger entries.
- [x] Reversal Entity Ledger entries counter-balance the original Entity Ledger entries.
- [x] Wallet balances are restored by the reversal exactly once.
- [x] Budget spend and refund-visible expense math remain consistent after reversal.
- [x] Existing expense void/reversal tests pass.
- [x] New focused tests exercise the Financial Event Ledger reversal seam through user-visible behavior.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 6: Route Refund Posting Through Financial Event Ledger

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move refund posting through Financial Event Ledger so refund duality remains consistent. Refunds should still enter the Wallet as Money In while also acting as a contra-expense against the original category. The title inheritance rule must be preserved: refund events should not add robotic prefixes when the original title should carry the human-readable ledger identity.

This slice should cover refund posting paths that already create Financial Events directly. It should not change refund product behavior.

## Acceptance criteria

- [x] A refund still creates a posted refund Financial Event linked to the original expense.
- [x] Refund Wallet Ledger entries still increase the selected Wallets by the received amounts.
- [x] Refund Entity Ledger entries still reduce category spend as contra-expense behavior.
- [x] Refunds still preserve Budget, subcategory, project, project subcategory, and Debt links from the original expense where applicable.
- [x] Refund title behavior follows strict title inheritance and avoids robotic prefixes.
- [x] Refunds cannot exceed the refundable amount.
- [x] Existing refund and expected inflow refund tests pass.
- [x] New regression coverage proves refund duality survives the Financial Event Ledger migration.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting
- Issue 5: Move Expense Void And Reversal Mechanics Behind Financial Event Ledger

---

## Issue 7: Route Earned Income And Expected Inflow Receipt Posting Through Financial Event Ledger

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move earned income and expected inflow receipt posting through Financial Event Ledger while keeping Expected Inflows responsible for Promise, Schedule, cap, realization, write-off, reschedule, and lifecycle rules. The Financial Event Ledger should own the actual money event mechanics: Financial Event, Wallet Ledger, Entity Ledger, event links, and user-local effective dates.

This slice may include asset-sale receipts if they share the same income-shaped posting adapter without making the issue too large. If the implementation gets broad, split asset sales into a follow-up issue before editing.

## Acceptance criteria

- [x] Recording earned income still creates a posted income Financial Event and Wallet Ledger entries.
- [x] Receiving an expected inflow still updates realization and lifecycle state correctly.
- [x] Expected inflow Promise caps, Schedule status, and write-off behavior remain unchanged.
- [x] Receivable expected inflows still delegate Debt repayment logic rather than duplicating obligation math.
- [x] Income source links and expected inflow event links remain intact.
- [x] User-local received dates remain explicit and cannot fall back to server-local date defaults.
- [x] Existing income and expected inflow receipt tests pass.
- [x] New regression coverage proves receipt posting preserves Wallet, Entity Ledger, and expected inflow lifecycle behavior.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 8: Route Wallet Transfers And Reconciliation Adjustments Through Financial Event Ledger

## Parent

PRD 1: Deepen Expense Posting And Centralize Ledger Posting

## What to build

Move Wallet transfers and reconciliation adjustments through Financial Event Ledger so direct Wallet movement uses the same immutable event mechanics as other money truth. Transfers should remain balanced across two Wallet Ledger entries. Reconciliation adjustments should remain explicit correction events, not hidden balance mutation.

This slice should also remove server-local date defaults from transfer and adjustment posting. The caller must provide the user-local effective date for user-facing money movement.

## Acceptance criteria

- [x] Wallet transfers still create one posted transfer Financial Event.
- [x] Wallet transfers still write one negative Wallet Ledger entry and one positive Wallet Ledger entry with equal absolute amounts.
- [x] Wallet transfers still update both Wallet balances exactly once.
- [x] Reconciliation adjustments still create explicit adjustment Financial Events when the target balance differs from current balance.
- [x] Reconciliation adjustments still do nothing when the target balance already matches current balance.
- [x] Transfer and adjustment dates are explicit user-local dates.
- [x] Existing Wallet transfer and reconciliation tests pass.
- [x] New regression coverage proves no server-local date fallback remains in these money posting paths.

## Blocked by

- Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting
- Issue 5: Move Expense Void And Reversal Mechanics Behind Financial Event Ledger
