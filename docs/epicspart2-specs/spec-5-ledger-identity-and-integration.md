# Spec 5: Ledger Identity & Cross-Domain Integration

Source epic: Epic 5 Ledger Identity & Cross-Domain Integration

Source decisions: ADR 0015, ADR 0016, ADR 0017, ADR 0018

## Problem Statement

Sarflog's core money engines are becoming more powerful: immutable ledger history, Debt and Payment Plan obligations, and Expected Inflow Promise/Schedule tracking. Epic 5 is the integration layer that makes those engines feel like one trustworthy financial product instead of separate features that happen to share a database.

The user-facing problems are practical:

- A user can carefully name an expected payment "Website Redesign Phase 1", but the ledger can still show a generic title such as client payment received.
- Refunds can look like generic income even though they are actually money returning against an expense category.
- Debt receivables can be confused with expected cashflow, even though money someone owes the user is not the same as money the user trusts will arrive this month.
- Contractual debt deadlines and real-world cash arrival dates can drift apart, and the app must not hide that drift by mutating one domain from another.
- Frontend source pickers can silently break when backend response shapes or status vocabulary evolve.
- Income Sources are useful for analytics, but selecting or creating them can feel like friction if the user has to leave the form.

The deeper product risk is trust. A money app earns trust when every screen tells the same story: what the user called the money, who it came from, whether it was actual income or a refund, why it affected a wallet, and how it relates to debts, budgets, and expected cashflow.

If Epic 5 is not completed, Sarflog may still calculate many balances correctly, but the financial journal will feel inconsistent. Users will see robotic labels, duplicated-looking refunds, missing receivable prompts, and dropdown bugs that make valid records unavailable. That weakens auditability and makes the app harder to reason about as the domain grows.

## Solution

Implement the Epic 5 integration contract from ADR 0015-0018.

From the user's perspective, Sarflog should behave like this:

- The title the user wrote remains the primary ledger title.
- The source, counterparty, original expense, or asset appears as supporting context, not as a replacement for the user's memo.
- Earned expected inflows use both an Income Source for analytics and a Title for the human-readable contract or memo.
- Users can create a new Income Source directly while creating an expected inflow.
- Income Sources have their own hub where users can see lifetime expected, received, outstanding, and reliability metrics.
- Refunds appear in Money In because cash entered the wallet.
- Refunds also appear in Expenses and category math because they reduce true spending.
- Refunds do not pretend to be ordinary income.
- Money owed to the user does not automatically become trusted monthly cashflow.
- The user explicitly creates an Expected Inflow when they believe a receivable debt will arrive on a date.
- Debt contractual deadline and Expected Inflow tactical due date remain independent.
- Expected Inflow source pickers show the right debts, expenses, assets, and income sources even when backend payloads are wrapped or status names have changed.

From the engineering perspective, the solution is an integration and cleanup pass:

- Adopt the Entity + Memo pattern for expected inflows.
- Preserve strict foreign-key sources for analytics while preserving user-authored titles for ledger readability.
- Apply strict title inheritance across Money In transaction types.
- Make refund duality explicit in wallet, expense, category, budget, and analytics behavior.
- Bridge receivable Debts to Expected Inflows through explicit user action, not automatic projection.
- Decouple Debt deadlines from Expected Inflow due dates.
- Standardize frontend read models so components unwrap polymorphic payloads before filtering and stop hardcoding legacy status strings.

The highest-level testing seam should be cross-domain route behavior around Expected Inflow creation/receipt, Debt receivable linking, refund posting, asset sale posting, and Money In/Expense list responses. Focused service-level tests are appropriate for ledger-title generation and refund/category math. Frontend tests should cover the Expected Inflow source picker, creatable source creation, and schema/status guardrails.

## User Stories

1. As a user, I want my expected inflow title to become the ledger title when money arrives, so that the ledger keeps the wording I chose.
2. As a user, I want "Client X" and "July Salary" to be stored as different concepts, so that analytics can group by client while my ledger remains readable.
3. As a freelancer, I want to create a new client source while entering an expected payment, so that I do not have to leave the form.
4. As a user, I want the expected inflow form to remember both source and title, so that future reports and the ledger both make sense.
5. As a user, I want Income Sources to have their own hub, so that sources are more than dropdown values.
6. As a user, I want to see lifetime expected amount by source, so that I know how much work or income was planned from that source.
7. As a user, I want to see lifetime received amount by source, so that I know how much cash actually arrived from that source.
8. As a user, I want to see outstanding expected money by source, so that I can follow up on unpaid clients or income streams.
9. As a user, I want to see payment reliability by source, so that I can tell which clients or payers are predictable.
10. As a user, I want source names to appear as supporting context under ledger titles, so that I can scan both memo and source.
11. As a user, I do not want generic titles like client payment received to overwrite my memo, so that I can recognize old transactions later.
12. As a user, I want refund ledger rows to keep the original expense title, so that a returned grocery purchase still reads like groceries.
13. As a user, I do not want refund titles prefixed with "Refund for", so that the title stays clean and the refund badge carries the type.
14. As a user, I want partial and full refunds to follow the same title rule, so that refund rows are consistent.
15. As a user, I want refunds visible in Money In, so that wallet cash increases are explainable.
16. As a user, I want refunds visible in Expenses, so that category spending reflects the true net amount.
17. As a user, I want a grocery refund to reduce grocery spending, so that my grocery budget does not stay overstated.
18. As a user, I do not want refunds counted as earned income, so that income analytics remain honest.
19. As a user, I want Money In filters to distinguish income, refunds, borrowed money, sales, and corrections, so that different cash arrivals do not blur together.
20. As a user, I want a debt receipt to use the note I wrote as the ledger title, so that the payment story is human-readable.
21. As a user, I want the counterparty name on a debt receipt to appear as metadata, so that it does not erase my payment note.
22. As a user, I want asset-sale money to use the asset or promise title, so that sale proceeds are traceable to the thing sold.
23. As a user, I do not want asset-sale titles prefixed with "Asset Sale", so that the tab and badge provide the type without polluting the title.
24. As a user, I want balance corrections to use my note when I provide one, so that reconciliation events are understandable.
25. As a user, I accept "Balance Adjustment" only when I did not write a note, so that system naming is limited to true fallback cases.
26. As a user who lent money, I want that receivable Debt to remain an obligation record, so that it does not automatically become trusted cashflow.
27. As a user, I want Sarflog to ask whether I expect an open receivable this month, so that I can choose what belongs on the timeline.
28. As a user, I want to create an Expected Inflow from an open receivable Debt, so that likely repayment can be planned.
29. As a user, I do not want every open receivable Debt on my cashflow timeline, so that unreliable repayments do not create false confidence.
30. As a user, I want one receivable Debt to support multiple expected repayment schedules, so that split repayments are modeled naturally.
31. As a user, I want receiving one repayment schedule to reduce the linked Debt balance, so that the Debt and Expected Inflow stay connected through real cash.
32. As a user, I want the Debt deadline to remain the original agreement date, so that lateness is visible.
33. As a user, I want the Expected Inflow due date to represent when I now expect cash, so that cash planning stays realistic.
34. As a user, I want changing an Expected Inflow due date to leave the Debt deadline alone, so that tactical planning does not rewrite the contract.
35. As a user, I want changing the Debt deadline to leave the Expected Inflow due date alone, so that contract edits do not silently move my cashflow plan.
36. As a user, I want a debt due July 10 to stay overdue on July 11 even if I now expect payment July 20, so that accountability and planning remain separate.
37. As a user, I want dropdowns to show valid open receivable Debts, so that I can link money owed to me.
38. As a user, I want refund source dropdowns to show original expenses, not refund rows, so that I cannot create refund-of-refund chains.
39. As a user, I want expense titles in refund dropdowns to be real titles, not undefined placeholders, so that source selection is usable.
40. As a developer, I want frontend source pickers to unwrap feed payloads before filtering, so that backend response wrappers do not break UI logic.
41. As a developer, I want source pickers to use current lifecycle vocabulary, so that old hardcoded statuses do not return.
42. As a developer, I want Money In title rules tested across expected inflows, refunds, debt receipts, asset sales, and corrections, so that robot titles do not creep back.
43. As a developer, I want refund duality tested through wallet and category math, so that future cleanup does not hide refunds from one side of the accounting story.
44. As a developer, I want receivable Debt to Expected Inflow linking tested end to end, so that the two domains remain connected without auto-trust.
45. As a developer, I want source analytics to come from durable source links, so that reports do not depend on parsing ledger titles.
46. As a developer, I want cross-domain integration tests to use the user's effective timezone for due dates and monthly prompts, so that cashflow planning matches the user's day.
47. As a developer, I want UI badges and subtitles to carry system type and entity context, so that the primary title can stay user-owned.
48. As a developer, I want this epic to finish with shared guardrails, so that future Money In features inherit the same identity and schema rules.

## Implementation Decisions

- Treat ADR 0015, ADR 0016, ADR 0017, and ADR 0018 as the canonical Epic 5 execution set.
- Epic 5 depends on the Epic 4 Expected Inflow Promise/Schedule model and the Epic 2 Debt receivable model.
- Do not rebuild Expected Inflows, Debt, or immutable ledger history from scratch during this epic.
- The main job of this epic is cross-domain identity, naming, integration behavior, and frontend read-model hardening.
- Use the Entity + Memo pattern for earned expected inflows.
- Income Source is the entity. It is used for grouping, analytics, lifetime metrics, and source-level reporting.
- Expected Inflow title is the memo. It is the user's human-readable name for the specific agreement, payment, invoice, project, salary period, or expected cash event.
- Keep Income Source as a strict relationship for earned expected inflows.
- Do not replace Income Source with free-text title-only behavior.
- Do not replace user-authored titles with source names during ledger posting.
- FinancialEvent title generated from an Expected Inflow receipt must exactly inherit the parent Promise title.
- The source label, counterparty, asset, or original expense should appear in metadata, subtitle, badge, relationship fields, or detail surfaces.
- Backend posting logic must not generate generic Money In titles for user-driven expected inflows.
- UI may suggest a default title during creation, but once the user submits a title, the ledger must preserve it.
- Expected Inflow creation should make source selection low-friction through a creatable select.
- Creating an Income Source inline should use the same source validation and duplicate-name behavior as normal source creation.
- Inline source creation should update the source option list and select the new source without forcing a page refresh.
- Income Sources need a dedicated hub or equivalent first-class view.
- The Income Sources Hub should expose lifetime expected, lifetime received, outstanding balance, and reliability-oriented metrics.
- Source analytics should use durable source relationships, not title parsing.
- Global Money In ledger title inheritance applies to refunds, debt receipts, asset sales, and corrections.
- Refund FinancialEvent title must inherit the original expense title, or the Promise title when the refund arrives through Expected Inflows.
- Refund titles must not include prefixes such as "Refund", "Partial Refund", or "Refund for".
- The UI should communicate refund type through transaction type, badges, amount direction, and source context.
- Debt receipt title must come from the user's note or memo collected for that receipt.
- Counterparty name must not overwrite a debt receipt title.
- Debt receipt UI should collect a clear note when the note will become the ledger title.
- Asset sale title must use the asset title or linked Promise title exactly.
- Asset sale titles must not include an "Asset Sale" prefix.
- Balance correction titles should use the user's note when one exists.
- "Balance Adjustment" is allowed only as a fallback when the user gave no correction note.
- Refunds are contra-expenses, not ordinary income.
- Refunds must appear in Money In because wallet cash entered.
- Refunds must also appear in expense/category ledgers because true category spend decreased.
- Hiding refunds from either wallet inflow or expense/category accounting is incorrect.
- Income analytics must distinguish earned income from refunds, borrowed money, asset sales, and corrections.
- Receivable Debts must not automatically project into the Monthly Timeline or Expected Inflow cashflow.
- Payable obligations may continue using warning/projection behavior from their own domain where applicable.
- Users must explicitly create an Expected Inflow when they trust a receivable Debt enough to plan around it.
- The UI should proactively prompt users to link open receivable Debts to Expected Inflows at useful planning moments, such as month start or cashflow review.
- A receivable Debt can be linked to one Expected Inflow Promise.
- Split repayments use one Promise with multiple Schedules, not multiple shadow Debts.
- Receiving a schedule linked to a receivable Debt should reduce the Debt's remaining balance through the established debt payment/receipt behavior.
- Receipt reversal should restore the relevant expected inflow and debt math while preserving ledger history.
- Debt expected return date is the contractual deadline.
- Expected Inflow schedule due date is the tactical cash arrival date.
- Updating one date must not mutate the other.
- Debt overdue state should continue to derive from the Debt deadline and user-local today.
- Expected Inflow cashflow placement should continue to derive from schedule due date and user-local month.
- Frontend source-selection code should consume a normalized read model for earned sources, receivables, refunds, and assets.
- Feed-oriented endpoint responses must be unwrapped before filtering or display.
- Refund source selection must inspect the inner expense transaction type, not a guessed outer wrapper field.
- Receivable source selection must use current Debt lifecycle vocabulary and remaining amount, not legacy status strings.
- Frontend components should not duplicate fragile source filtering logic when a shared source-picker helper exists.
- New source-picker tests should become guardrails for ADR 0018 behavior.
- Any remaining hardcoded legacy status checks in Epic 5 flows should be removed or isolated behind current-domain helpers.
- User-facing "today", monthly planning, overdue labels, and date validation must use the effective user timezone.
- The final public behavior should make it unnecessary for users to understand internal ledger, source, Promise, Schedule, Debt, or feed-wrapper implementation details.

## Testing Decisions

- Tests should assert external behavior and financial invariants rather than private helper implementation.
- The preferred backend seam is route-level behavior for Expected Inflow creation, receipt, reversal, Debt receivable linking, refund posting, asset sale posting, and Money In/Expense list responses.
- Service-level tests are appropriate for dense ledger-title mapping and source analytics aggregation when route tests would be noisy.
- Frontend tests should cover the Expected Inflow source picker read model and user-visible form behavior.
- Expected Inflow receipt tests should prove the posted ledger title exactly equals the Promise title for earned income, receivables, refunds, and asset-sale source kinds where applicable.
- Expected Inflow tests should prove source/counterparty/asset/original-expense context remains visible outside the title.
- Income Source tests should prove inline creation validates duplicate names, creates the source, selects it, and can immediately create an expected inflow.
- Income Sources Hub tests should prove lifetime expected, lifetime received, outstanding, and reliability metrics are computed from source-linked records.
- Refund posting tests should prove refund titles inherit the original expense title.
- Refund posting tests should prove prefixes such as "Refund", "Partial Refund", and "Refund for" are not used as the stored title.
- Refund duality tests should prove refund events increase wallet balance and reduce category spend.
- Budget/category tests should prove a partially refunded expense reports net category spend.
- Income analytics tests should prove refunds do not inflate earned-income totals.
- Debt receipt tests should prove the user note becomes the Money In title and the counterparty remains metadata.
- Debt receipt tests should prove missing or empty note behavior follows the product contract and never silently uses counterparty as the primary title.
- Asset sale tests should prove the asset or Promise title is preserved without "Asset Sale" prefixes.
- Correction tests should prove user notes are preserved and "Balance Adjustment" is only a no-note fallback.
- Receivable Debt tests should prove open OWED debts do not automatically appear as expected inflow timeline cash.
- Receivable prompt tests should prove users can explicitly create an Expected Inflow from an open receivable.
- Split repayment tests should prove one Promise can contain multiple schedules for the same receivable Debt.
- Receipt tests should prove receiving linked receivable schedules reduces the parent Debt balance.
- Reversal tests should prove reversing receivable receipts restores Expected Inflow and Debt math without erasing history.
- Deadline decoupling tests should prove changing an Expected Inflow due date does not change Debt expected return date.
- Deadline decoupling tests should prove changing a Debt expected return date does not move existing Expected Inflow schedules.
- Timezone tests should prove Debt overdue and Expected Inflow monthly placement use the user's effective timezone.
- Frontend source-picker tests should prove receivable options require open OWED Debts with remaining balance.
- Frontend source-picker tests should prove refund options unwrap feed payloads and exclude refund rows.
- Frontend source-picker tests should prove asset-sale options use owned/saleable assets and show human titles.
- Frontend guardrail tests should fail if code regresses to hardcoded legacy status inclusion or outer-wrapper expense filtering.
- Existing expected inflow, debt, refund ledger, income, wallet projection, immutable ledger, budget, and frontend source-picker tests are prior art.
- Docker should be the default verification environment for backend tests and frontend builds when executing these tickets.

## Out of Scope

- Rebuilding the full Expected Inflow Promise/Schedule architecture from Epic 4.
- Rebuilding the full Debt and Payment Plan architecture from Epic 2.
- Automatic bank import, invoice import, OCR, statement matching, or reconciliation automation.
- Automatic trust scoring that projects receivables without user confirmation.
- Full tax reporting, invoice aging reports, or formal accounts-receivable accounting beyond source metrics.
- Full asset lifecycle redesign beyond preserving asset-sale ledger identity.
- Multi-currency source analytics.
- Legal contract management for receivable Debt deadlines.
- A generic frontend schema-codegen system.
- Rewriting all project status vocabulary outside the Epic 5 source-picker and Money In integration surfaces.
- Redesigning all analytics dashboards outside the Income Sources Hub and refund/income separation needed by this epic.
- Production-grade migration guarantees for obsolete development-only robot titles.

## Further Notes

Epic 5 is small in schema ambition but large in trust impact.

The mental model should stay simple:

- Title says what the user called this money.
- Source says who or what it belongs to for analytics.
- Badge says what kind of money movement it is.
- Metadata says which debt, expense, asset, wallet, or source is linked.
- Refund says cash came back and spending went down.
- Debt deadline says what was promised.
- Expected Inflow due date says when cash is now expected.

Some ADR 0018-style frontend guardrails and Epic 4 expected-inflow structures already exist in the codebase. This spec should verify and complete the contract rather than assume every line must be built from zero.

Do not fix ledger readability by deleting analytics structure. Do not fix analytics by overwriting human titles. The whole point of this epic is keeping both.
