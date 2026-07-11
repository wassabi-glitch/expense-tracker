# Tickets: Ledger Identity & Cross-Domain Integration

Source spec: `docs/epicspart2-specs/spec-5-ledger-identity-and-integration.md`

These tickets implement Epic 5 from ADR 0015-0018. They make Money In ledger entries human-readable, preserve analytics source identity, formalize refund duality, bridge receivable Debts to Expected Inflows without auto-trust, and harden frontend source-picker schema handling.

Assumption: the Epicspart2 ledger foundation, Debt architecture, and Expected Inflow architecture are the active contracts. Work the frontier: any ticket whose blockers are complete can start.

## Proposed Breakdown

1. **Enforce Expected Inflow Entity + Memo ledger identity**
   - Blocked by: None
   - What it delivers: Expected Inflow receipts preserve the user's Promise title while keeping source context available for analytics and subtitles.

2. **Add creatable Income Source selection for Expected Inflows**
   - Blocked by: Ticket 1
   - What it delivers: users can create and select a new Income Source without leaving the expected inflow form.

3. **Add Income Sources Hub with lifetime analytics**
   - Blocked by: Tickets 1, 2
   - What it delivers: Income Sources become first-class reporting objects with expected, received, outstanding, and reliability metrics.

4. **Apply global Money In title inheritance**
   - Blocked by: Ticket 1
   - What it delivers: refunds, debt receipts, asset sales, and corrections stop using robotic primary titles.

5. **Preserve refund duality across wallet and category math**
   - Blocked by: Ticket 4
   - What it delivers: refunds remain visible as wallet inflows and category contra-expenses without polluting earned-income analytics.

6. **Harden Expected Inflow source-picker read models**
   - Blocked by: None
   - What it delivers: frontend source options unwrap feed payloads, use current lifecycle vocabulary, and avoid legacy status bugs.

7. **Prompt explicit receivable Debt to Expected Inflow planning**
   - Blocked by: Tickets 1, 6
   - What it delivers: open receivable Debts can be intentionally planned as Expected Inflows without automatic timeline projection.

8. **Support receivable split repayment schedules**
   - Blocked by: Ticket 7
   - What it delivers: one receivable Debt can be planned as one Promise with multiple repayment schedules, and received cash reduces the Debt.

9. **Decouple Debt contractual deadlines from Inflow due dates**
   - Blocked by: Tickets 7, 8
   - What it delivers: Debt overdue accountability and Expected Inflow cashflow planning remain independent even when real-life dates drift.

10. **Finish Epic 5 cross-domain regression coverage**
    - Blocked by: Tickets 2, 3, 5, 8, 9
    - What it delivers: all naming, refund, receivable, date, and frontend schema contracts are verified together.

## Ticket 1: Enforce Expected Inflow Entity + Memo Ledger Identity

**What to build:** Expected Inflow receipts should preserve the user's Promise title as the primary ledger title while keeping Income Source, receivable Debt, refund source, or asset context available as metadata/subtitle. From the user's perspective, the ledger should show the exact name they gave the expected money, not a generic source-generated phrase.

**Blocked by:** None - can start immediately.

- [x] Receiving an earned Expected Inflow posts Money In with title exactly equal to the Promise title.
- [x] Receiving a receivable Expected Inflow posts Money In with title exactly equal to the Promise title.
- [x] Receiving a refund Expected Inflow posts Money In with title exactly equal to the Promise title.
- [x] Receiving an asset-sale Expected Inflow posts Money In with title exactly equal to the Promise title.
- [x] Source, counterparty, original expense, and asset context remain available outside the primary title.
- [x] Ledger responses and UI surfaces can display source context as subtitle, badge, or detail metadata.
- [x] Backend posting rejects or avoids generic generated titles for user-driven Expected Inflow receipts.
- [x] Tests prove no source-kind receipt path uses generic titles such as client payment received, refund received, or asset sale received.
- [x] Tests prove source analytics still use source relationships rather than parsing the title.

## Ticket 2: Add Creatable Income Source Selection For Expected Inflows

**What to build:** The Expected Inflow form should let users create a new Income Source inline when entering earned expected money. From the user's perspective, they can type a new client, employer, platform, or income stream and continue creating the expected inflow without leaving the workflow.

**Blocked by:** Ticket 1: Enforce Expected Inflow Entity + Memo ledger identity.

- [x] Earned Expected Inflow source selection supports creating a new Income Source from the form.
- [x] Inline source creation uses the same validation as normal Income Source creation.
- [x] Duplicate source names are handled consistently with existing source rules.
- [x] After creation, the new source appears in the source options immediately.
- [x] After creation, the new source is selected for the in-progress Expected Inflow.
- [x] Expected Inflow creation still requires a user-authored title separate from the source name.
- [x] Failed source creation leaves the Expected Inflow draft intact.
- [x] Tests cover successful inline source creation and duplicate-name rejection.
- [x] Frontend tests prove the title field and source field remain separate concepts.

## Ticket 3: Add Income Sources Hub With Lifetime Analytics

**What to build:** Income Sources should have a first-class hub where users can understand each source over time. From the user's perspective, a source is not just a dropdown option; it becomes a place to see expected money, received money, outstanding balance, and reliability.

**Blocked by:**

- Ticket 1: Enforce Expected Inflow Entity + Memo ledger identity.
- Ticket 2: Add creatable Income Source selection for Expected Inflows.

- [x] Users can navigate to an Income Sources Hub or equivalent first-class source analytics view.
- [x] Each source shows lifetime expected amount from linked Expected Inflows.
- [x] Each source shows lifetime received amount from linked posted money.
- [x] Each source shows current outstanding expected amount.
- [x] Each source exposes a reliability-oriented metric or status derived from due/received behavior.
- [x] Source analytics use durable source links, not ledger-title parsing.
- [x] Inactive sources remain viewable when historical analytics exist.
- [x] Source detail supports scanning related expected inflows and posted received money.
- [x] Tests cover source totals for expected, received, outstanding, and inactive-source history.
- [x] Frontend tests cover the empty state, populated list, and source detail summary.

## Ticket 4: Apply Global Money In Title Inheritance

**What to build:** Money In transaction types should stop overwriting user meaning with robotic prefixes. From the user's perspective, refunds, debt receipts, asset sales, and corrections should read like human financial journal entries, with system type shown through badges and metadata.

**Blocked by:** Ticket 1: Enforce Expected Inflow Entity + Memo ledger identity.

- [x] Direct refund posting stores the original expense title as the refund event title.
- [x] Expected refund receipt posting preserves the Promise title as the refund Money In title.
- [x] Refund titles do not use "Refund", "Partial Refund", or "Refund for" as stored primary title.
- [x] Debt receipt posting uses the user's receipt note or memo as the primary Money In title.
- [x] Debt receipt counterparty appears as supporting context, not as the primary title.
- [x] Debt receipt flow collects or validates the note required to become the title.
- [x] Asset sale posting stores the asset title or linked Promise title without an "Asset Sale" prefix.
- [x] Balance corrections use the user's note as title when one exists.
- [x] Balance corrections use "Balance Adjustment" only when no user note exists.
- [x] Tests cover every Money In title rule and prevent the banned prefixes from returning.

## Ticket 5: Preserve Refund Duality Across Wallet And Category Math

**What to build:** Refunds should remain visible both as cash entering the wallet and as reductions to expense/category spending. From the user's perspective, a refund explains why wallet money increased and why true category spend went down.

**Blocked by:** Ticket 4: Apply global Money In title inheritance.

- [ ] Refunds appear in Money In or wallet inflow views because cash entered a wallet.
- [ ] Refunds appear in Expenses or category ledgers as contra-expenses.
- [ ] A partial refund reduces net category spend by the refunded amount.
- [ ] A full refund reduces net category spend for the original expense to zero where appropriate.
- [ ] Refund rows are visually identified through type badges or context instead of title prefixes.
- [ ] Earned-income totals exclude refunds.
- [ ] Money In totals can distinguish earned income from refunds, borrowed money, sales, and corrections.
- [ ] Budget/category summaries use net expense math after refunds.
- [ ] Tests prove wallet balance increases and category spend decreases for the same refund.
- [ ] Tests prove hiding refunds from either side would fail the regression suite.

## Ticket 6: Harden Expected Inflow Source-Picker Read Models

**What to build:** Expected Inflow source selection should use normalized read models for income sources, receivable Debts, refundable expenses, and assets. From the user's perspective, valid sources appear with real titles and invalid sources are excluded.

**Blocked by:** None - can start immediately.

- [ ] Earned source options include active Income Sources and stable labels.
- [ ] Receivable source options include open OWED Debts with remaining balance.
- [ ] Receivable source options do not depend on legacy ACTIVE status checks.
- [ ] Refund source options unwrap feed-oriented expense payloads before filtering.
- [ ] Refund source options inspect the inner expense transaction type.
- [ ] Refund source options exclude refund rows so refund-of-refund links cannot be created.
- [ ] Refund source options display real expense titles and dates rather than undefined placeholders.
- [ ] Asset-sale source options display saleable owned assets with stable labels.
- [ ] Expected Inflow dialogs use the shared source-picker read model instead of duplicating filtering logic.
- [ ] Frontend tests cover each source kind and fail on legacy status or wrapper-field regressions.

## Ticket 7: Prompt Explicit Receivable Debt To Expected Inflow Planning

**What to build:** Sarflog should invite users to plan receivable Debts as Expected Inflows, but never auto-trust them. From the user's perspective, money someone owes them stays an obligation until they explicitly decide it belongs on their cashflow plan.

**Blocked by:**

- Ticket 1: Enforce Expected Inflow Entity + Memo ledger identity.
- Ticket 6: Harden Expected Inflow source-picker read models.

- [ ] Open OWED Debts do not automatically appear as Expected Inflows.
- [ ] Open OWED Debts do not automatically project into Monthly Timeline cashflow.
- [ ] Users can start an Expected Inflow from an open receivable Debt.
- [ ] The prompt explains that adding the inflow means the user expects cash on a specific date.
- [ ] Prompting appears in a planning surface such as month start, cashflow review, or receivable detail.
- [ ] The created Expected Inflow links back to the receivable Debt.
- [ ] The created Expected Inflow has a user-authored title and tactical due date.
- [ ] The Debt remains open until real receipt, forgiveness, correction, or other Debt-domain action changes its balance.
- [ ] Tests prove no auto-projection happens before explicit user action.
- [ ] Tests prove explicit creation creates the Debt-linked Expected Inflow.

## Ticket 8: Support Receivable Split Repayment Schedules

**What to build:** One receivable Debt should be plannable as one Expected Inflow Promise with multiple repayment schedules. From the user's perspective, if someone will repay in parts, Sarflog can track each expected arrival without splitting the Debt into fake records.

**Blocked by:** Ticket 7: Prompt explicit receivable Debt to Expected Inflow planning.

- [ ] A Debt-linked Expected Inflow Promise can contain multiple schedules.
- [ ] The total scheduled amount cannot exceed the linked Promise/debt-planning amount.
- [ ] Users can split one receivable repayment into multiple due dates.
- [ ] Each schedule appears in the expected cashflow month that matches its due date.
- [ ] Receiving one schedule reduces the Expected Inflow outstanding amount.
- [ ] Receiving one schedule reduces the linked Debt remaining balance through the established receipt/payment behavior.
- [ ] Receiving multiple schedules reconciles to the total repayment amount.
- [ ] Reversing a receivable receipt restores Expected Inflow outstanding amount.
- [ ] Reversing a receivable receipt restores linked Debt remaining amount.
- [ ] Tests cover two-part and three-part repayment plans, partial receipt, full receipt, and receipt reversal.

## Ticket 9: Decouple Debt Contractual Deadlines From Inflow Due Dates

**What to build:** Debt deadline and Expected Inflow due date should remain independent. From the user's perspective, the app can show that someone missed the original deadline while still planning for the realistic cash arrival date.

**Blocked by:**

- Ticket 7: Prompt explicit receivable Debt to Expected Inflow planning.
- Ticket 8: Support receivable split repayment schedules.

- [ ] Debt expected return date is treated as the contractual deadline.
- [ ] Expected Inflow schedule due date is treated as the tactical cash arrival date.
- [ ] Updating a Debt expected return date does not mutate linked Expected Inflow schedule due dates.
- [ ] Rescheduling an Expected Inflow does not mutate the linked Debt expected return date.
- [ ] Debt overdue state derives from Debt deadline and user-local today.
- [ ] Expected Inflow monthly cashflow placement derives from schedule due date and user-local month.
- [ ] A late receivable can remain overdue while its Expected Inflow projects the new expected cash date.
- [ ] UI copy distinguishes contractual deadline from expected cash date where both are visible.
- [ ] Tests cover a missed-deadline scenario where the Debt is overdue and the inflow is scheduled in the future.
- [ ] Timezone-boundary tests prove both date concepts use the effective user timezone.

## Ticket 10: Finish Epic 5 Cross-Domain Regression Coverage

**What to build:** Finish the integration pass by proving that ledger identity, source analytics, refund duality, receivable planning, date decoupling, and frontend schema handling work together. From the developer's perspective, future changes should trip tests before they reintroduce robot titles or domain confusion.

**Blocked by:**

- Ticket 2: Add creatable Income Source selection for Expected Inflows.
- Ticket 3: Add Income Sources Hub with lifetime analytics.
- Ticket 5: Preserve refund duality across wallet and category math.
- Ticket 8: Support receivable split repayment schedules.
- Ticket 9: Decouple Debt contractual deadlines from Inflow due dates.

- [ ] Regression coverage exercises earned expected inflow, refund, receivable, asset sale, and correction Money In identity.
- [ ] Regression coverage proves source analytics still work when ledger titles are user-authored.
- [ ] Regression coverage proves refunds are excluded from earned-income analytics while included in wallet and category math.
- [ ] Regression coverage proves open receivable Debts require explicit Expected Inflow creation before cashflow projection.
- [ ] Regression coverage proves split receivable schedules and Debt balance reduction reconcile.
- [ ] Regression coverage proves Debt deadlines and Expected Inflow due dates are independent.
- [ ] Frontend regression coverage proves source pickers unwrap payloads and use current status vocabulary.
- [ ] User-facing date behavior in these flows uses the effective user timezone.
- [ ] Documentation reflects the final Epic 5 title, source, refund, receivable, and schema rules.
- [ ] Docker backend tests and frontend build/test commands are run or clearly documented if unavailable.
