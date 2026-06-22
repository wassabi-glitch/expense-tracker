# PRD: G30 - Advanced Recurring Occurrence Architecture

Labels: `ready-for-agent`

This PRD is the authoritative contract for the advanced recurring-expense architecture discovered while preparing Epic 2 Issue 4. Where the earlier recurring projection and floor documents conflict with this contract, G30 takes precedence for recurring templates, occurrences, confirmation, recording, and lifecycle-aware projection.

## Problem Statement

Sarflog currently treats a recurring template as both a future instruction and sufficient proof that an expense happened. When a template becomes due, the scheduler records the template amount against one required wallet without asking whether the expense occurred, whether the real amount changed, whether a different date or category applied, or whether multiple wallets funded it.

That behavior can make wallet and budget history diverge from real life. A utility template may expect 300,000 UZS from one card while the actual bill is 347,000 UZS paid partly by card and partly in cash. Sarflog currently has no durable due occurrence waiting for confirmation, no expected-versus-actual occurrence record, and no reliable financial-event link proving which posted expense fulfilled which scheduled occurrence.

The mutable template also cannot safely serve as historical truth. Updating its amount or category overwrites the current rule. Hard deletion destroys its recurring-event diary. Pausing and later resuming can cause missed dates to catch up unexpectedly. The legacy floor calculation sees only one `next_due_date`, so it undercounts daily or weekly occurrences and cannot preserve a full-month recommendation after fulfilled payments advance the template pointer.

Users need recurring expenses to remain convenient without allowing automation to invent financial truth. They need a choice between confirming each occurrence and explicitly opting into automatic recording. They also need monthly category-floor warnings and cost projections to use the same schedule interpretation while respecting edits, pauses, skips, archive cutoffs, actual amounts, user-local dates, and valid financial-event status.

## Solution

Separate recurring future intent from dated occurrence truth.

A Recurring Template defines the current rule for future occurrences: title, expected amount, category, cadence, cycle behavior, recording mode, and optional preferred wallet. A Recurring Occurrence represents one scheduled due date and its lifecycle. Future occurrences remain derived from the template until they become due or otherwise need durable workflow state. Due occurrences are materialized idempotently under a unique template-and-scheduled-date identity.

Each template supports two recording modes:

- **Confirm each occurrence:** When due, the scheduler creates or finds a pending occurrence and notifies the user. Wallets, budgets, and financial ledgers do not change until the user confirms the real expense.
- **Automatically record:** When due, the scheduler creates the occurrence and attempts to post the expected amount from the preferred wallet. This is an explicit user-selected recording assumption, not bank-confirmed payment.

Confirmation records the actual amount, actual occurrence date, and one or more wallet allocations. Actual amount may be lower or higher than the template expectation because the expected amount is planning data while the confirmation is financial truth. Wallet allocations must equal the actual amount. Zero is represented by skipping the occurrence, not by creating a zero-value expense. A lower actual amount closes the occurrence in the first release; partial recurring settlements are intentionally deferred.

The recurring workflow delegates real expense posting to the existing expense-posting domain service so multi-wallet balances, goal protection, credit and overdraft funding classification, category budgets, financial events, and ledgers remain governed by one accounting path. The recurring occurrence links to the resulting financial event and preserves its event-time expected amount and category snapshots.

Template edits apply only to the next unresolved and later occurrences. Archive replaces hard deletion: it stops unmaterialized future occurrences while preserving the template and occurrence history. Pause suppresses paused-period occurrences; resume advances to the next future schedule date and never silently catches up the paused period. Skip explicitly closes one occurrence without wallet movement.

One authoritative, range-bounded occurrence projector serves recurring detail cost projections and recurring category-floor warnings. The selected month is a user-local calendar month, not a rolling 30-day window. A full-month recurring recommendation is derived from valid fulfilled actual amounts, pending/outstanding expected amounts, and still-projected expected amounts. It never persists a floor record and never mutates the saved category budget.

## User Stories

1. As a recurring-expense user, I want a template to represent future intent rather than proof of payment, so that Sarflog does not invent financial history.
2. As a recurring-expense user, I want to choose how each template is recorded, so that predictable subscriptions and variable bills can behave differently.
3. As a cautious user, I want `Confirm each occurrence` available and preselected for new templates, so that wallet truth changes only after I verify reality.
4. As an automation-oriented user, I want to opt into `Automatically record`, so that fixed predictable expenses remain convenient.
5. As an existing user, I want existing templates to preserve their automatic behavior during migration, so that an upgrade does not silently stop established recording.
6. As a user creating a confirmation-mode template, I want the wallet to be optional, so that I am not forced to predict which wallet will pay a future bill.
7. As a confirmation-mode user, I want an optional preferred wallet used only as a form default, so that common payments remain quick without restricting reality.
8. As an automatic-mode user, I want one active preferred wallet required, so that the scheduler has an explicit recording destination.
9. As a recurring-expense user, I want a due occurrence to appear as `Needs confirmation`, so that I know Sarflog is waiting for real information.
10. As a recurring-expense user, I want a due notification created once, so that an hourly scheduler does not spam me.
11. As a recurring-expense user, I want a pending occurrence to leave wallets unchanged, so that reminders do not masquerade as spending.
12. As a recurring-expense user, I want to confirm the actual expense date, so that late or early real-world spending is recorded honestly.
13. As a recurring-expense user, I want to confirm an actual amount lower than expected, so that discounts and variable bills do not overstate spending.
14. As a recurring-expense user, I want to confirm an actual amount higher than expected, so that real spending is not rejected merely because the estimate was wrong.
15. As a recurring-expense user, I want a visible expected-versus-actual variance, so that unusual changes are understandable before confirmation.
16. As a recurring-expense user, I want higher or lower values warned about without being blocked, so that reality-first accounting wins over template assumptions.
17. As a recurring-expense user, I want zero-value outcomes represented as skipped, so that the ledger never contains fake zero expenses.
18. As a recurring-expense user, I want confirmation to support one wallet, so that ordinary payments stay simple.
19. As a recurring-expense user, I want confirmation to support several wallets, so that split card-and-cash payments match reality.
20. As a recurring-expense user, I want wallet allocations required to equal the actual amount, so that wallet ledgers reconcile with the confirmed expense.
21. As a recurring-expense user, I want archived or unavailable wallets rejected at confirmation time, so that invalid destinations cannot receive ledger entries.
22. As a goal user, I want recurring confirmation to obey wallet goal protection, so that confirmation cannot spend protected money through a weaker path.
23. As a credit or overdraft user, I want each wallet allocation classified using the normal owned-versus-borrowed outflow rules, so that survival usage remains correct.
24. As a recurring-expense user, I want confirmation, financial-event posting, wallet movements, budget effects, and occurrence fulfillment to commit atomically, so that partial failures cannot create contradictory truth.
25. As a recurring-expense user, I want confirmation retries to be idempotent, so that a network retry cannot duplicate the expense.
26. As a recurring-expense user, I want the confirmed occurrence linked to its financial event, so that I can trace the schedule to the real expense.
27. As a recurring-expense user, I want an occurrence to preserve its expected amount and category, so that later template edits do not rewrite what was expected at the time.
28. As a recurring-expense user, I want a one-off amount variance to leave future expectations unchanged by default, so that one unusual bill does not rewrite the template.
29. As a recurring-expense user, I want an explicit option to use the confirmed amount for future occurrences, so that permanent price changes can update the template intentionally.
30. As a recurring-expense user, I want changing the template amount to affect only unresolved and future occurrences, so that paid history keeps its real amount.
31. As a recurring-expense user, I want changing the template category to affect only unresolved and future occurrences, so that past expenses remain in their original categories.
32. As a recurring-expense user, I want title, description, or preferred-wallet edits not to alter historical occurrence facts, so that presentation changes do not rewrite history.
33. As a recurring-expense user, I want deleting a template to archive it, so that future occurrences stop without destroying audit history.
34. As a recurring-expense user, I want archiving before today's occurrence is fulfilled to stop that unresolved occurrence when I explicitly skip/cancel it, so that ordering is deterministic.
35. As a recurring-expense user, I want archiving after today's occurrence is fulfilled to retain that fulfilled amount, so that the month remains historically accurate.
36. As a recurring-expense user, I want pausing to suppress occurrences during the paused period, so that temporary service suspension does not create imaginary expenses.
37. As a recurring-expense user, I want resuming to schedule the next future occurrence without catch-up, so that a pause does not become a delayed spending ambush.
38. As a recurring-expense user, I want to skip one due occurrence without deleting the template, so that vacations, free months, and waived bills are represented honestly.
39. As a recurring-expense user, I want a failed automatic posting to remain visible as needing attention, so that the obligation does not silently disappear.
40. As a recurring-expense user, I want a voided linked financial event not to count as fulfilled, so that reversed expenses do not remain accepted as payment truth.
41. As a recurring-expense user, I want fixed schedules to preserve calendar anchoring, so that paying late does not drift rent or subscription dates.
42. As a recurring-expense user, I want flexible schedules to retain their approved shift behavior outside paused-period catch-up, so that genuinely flexible habits remain useful.
43. As a user with a day-31 schedule, I want February to use its last valid day and later months to return to the intended anchor, so that short months do not permanently drift the schedule.
44. As a user in Tashkent or another timezone, I want `today` and `current month` determined in my effective timezone, so that due dates do not move because the server is in UTC.
45. As a user who travels, I want interactive routes to honor the effective request timezone while background work uses my stored timezone, so that each execution context has a deterministic local date.
46. As a budget user, I want recurring warnings scoped to a selected calendar month, so that monthly budgeting is not mixed with a rolling 30-day window.
47. As a budget user, I want all valid fulfilled occurrences retained in the full-month recommendation, so that paying an occurrence does not make the month's suggested minimum shrink.
48. As a budget user, I want pending confirmation occurrences included at their expected amounts, so that unconfirmed due bills remain visible in planning.
49. As a budget user, I want confirmed occurrences included at their actual amounts, so that the recommendation adapts to reality.
50. As a budget user, I want future occurrences included at their current template expectations, so that the remainder of the month is planned.
51. As a budget user, I want skipped, cancelled, and paused-period occurrences excluded, so that obsolete plans do not inflate the recommendation.
52. As a budget user, I want an archived template's unfulfilled future occurrences removed, so that stopped services do not remain in the recommendation.
53. As a budget user, I want a failed-but-still-outstanding occurrence retained, so that posting trouble does not erase a real expected cost.
54. As a budget user, I want a recurring amount or category edit to split the month honestly between old fulfilled facts and new future expectations, so that warnings remain explainable.
55. As a budget user, I want recurring reasons grouped clearly by template while retaining occurrence counts and totals, so that a daily expense does not create an unreadable wall of warning rows.
56. As a budget user, I want a saved category limit to remain unchanged when the recurring recommendation changes, so that warnings never silently rewrite spending permission.
57. As a budget user, I want warning gap derived from the current limit and current recommendation, so that the yellow warning disappears or changes naturally after lifecycle actions.
58. As a recurring-detail user, I want cost projections calculated by the backend, so that web, mobile, tests, and future timeline work share schedule semantics.
59. As a recurring-detail user, I want frequency-appropriate default horizons, so that daily and yearly templates are not presented with misleading comparisons.
60. As a recurring-detail user, I want saved custom projection horizons to remain preference metadata, so that inspecting costs never changes money or schedules.
61. As a recurring-detail user, I want projection calls to be read-only, so that opening a projection cannot advance due dates or post expenses.
62. As a maintainer, I want one range-bounded occurrence projector, so that floors and recurring detail cannot disagree about dates.
63. As a maintainer, I want durable occurrences only when workflow or historical truth requires them, so that the database does not store an unnecessary infinite future calendar.
64. As a maintainer, I want one stable identity per template and scheduled date, so that scheduler retries cannot materialize duplicate occurrences.
65. As a maintainer, I want template and occurrence lifecycle commands to lock the relevant rows, so that confirmation, automatic posting, pause, edit, skip, and archive cannot race.
66. As a maintainer, I want recurring posting to reuse the ordinary expense-posting service, so that it does not become a competing ledger engine.
67. As a maintainer, I want routers and the scheduler to delegate to deep recurring modules, so that lifecycle rules are not scattered through HTTP and background orchestration.
68. As a tester, I want public-route and scheduler-boundary tests, so that observable financial behavior survives internal refactoring.
69. As a tester, I want confirmation rollback and idempotency tests, so that failures and retries cannot duplicate or partially post money.
70. As a future timeline maintainer, I want occurrence output reusable as dated recurring commitments, so that later timeline work does not reinterpret recurrence rules.

## Implementation Decisions

- G30 owns advanced recurring templates and occurrences only. Debts and payment plans remain separate bounded workflows and must not create, mirror, or depend on recurring templates.
- Use `Recurring Template`, `Recurring Occurrence`, and `Recurring Recording Mode` as canonical domain terms.
- Add a first-class recurring-occurrence persistence model. At minimum it stores owner, template, scheduled due date, expected amount and category snapshots, lifecycle status, optional actual amount and actual date, optional linked financial event, timestamps, and an optimistic/idempotent uniqueness rule for template plus scheduled due date.
- Keep future not-yet-due occurrence calendars derived. Do not pre-generate an indefinite schedule in the database.
- Support recording modes `CONFIRM_EACH` and `AUTO_RECORD`. New-template UI preselects confirmation. Existing templates migrate to automatic recording for behavioral compatibility.
- In confirmation mode, preferred wallet is optional and used only to prefill confirmation. In automatic mode, an active preferred wallet is required.
- Templates do not store multi-wallet allocation rules in G30. Confirmation may freely replace the preferred wallet and use one or more active owned wallets, while automatic recording uses exactly one configured wallet. Percentage splits, fallback ordering, and automatic multi-wallet allocation are deferred.
- The scheduler is a due-work coordinator. For confirmation mode it materializes one pending occurrence and one notification without wallet or budget mutation. For automatic mode it materializes and atomically attempts ordinary expense posting.
- Scheduler behavior must be idempotent and based on the user's stored timezone. Interactive lifecycle and confirmation routes use the effective request/user timezone.
- The hourly scheduler may discover due work every hour, but it creates at most one initial due notification per occurrence. An unresolved occurrence is a persistent work item and must not generate another notification merely because the scheduler ran again.
- Store notification-delivery state outside deletable notification presentation, such as an occurrence `initial_notified_at` fact or an equivalent protected deduplication key. Reading or deleting a notification never confirms, skips, or removes the underlying occurrence.
- When scheduler downtime materializes several overdue occurrences together, prefer one grouped notification for the newly discovered backlog rather than a burst of identical alerts. Each occurrence remains individually actionable in the recurring work queue.
- Repeated reminders are explicit snoozes, not automatic hourly nagging. A `Remind later` action records the requested next reminder time and permits one new reminder when that time arrives. Automatic daily reminder policy is deferred until user notification preferences exist.
- Confirmation accepts actual amount, actual occurrence date, and one or more wallet allocations. Allocation totals must exactly equal actual amount; wallet identifiers must be unique, owned, and active.
- A confirmation attempt rejected for wallet capacity, goal protection, allocation mismatch, or wallet lifecycle remains `PENDING_CONFIRMATION`; it is not a failed financial occurrence because no posting succeeded. The UI must permit reallocating, selecting another wallet, funding a wallet, retrying, or skipping.
- Actual amount may be lower or higher than expected within normal expense limits. Variance is explicit presentation, not an error. Zero uses the skip command.
- A lower confirmed amount fully fulfills the occurrence in G30. Partial recurring settlement and an outstanding remainder are out of scope.
- Confirmation may optionally request that the actual amount become the template's future expected amount. This is an explicit second effect in the same locked transaction; default behavior changes only the occurrence.
- Actual financial truth is posted through the existing expense-posting domain service. The recurring service coordinates and links the result but does not duplicate wallet, goal-protection, credit/overdraft, budget, project, or ledger rules.
- Confirmation and automatic posting are atomic with occurrence lifecycle change. A failed transaction leaves no partial wallet or budget effect and keeps the occurrence actionable.
- An automatic recording blocked by insufficient spend capacity, goal protection, or an unavailable wallet becomes an actionable automatic-posting failure. It does not partially post, silently choose another wallet, or retry every hour. The user may repair wallet funding, manually choose wallet allocations for this occurrence, retry, or skip; changing the template wallet requires separate explicit intent.
- Spend-capacity validation follows the existing wallet domain: cash and ordinary asset wallets cannot cross zero, overdraft-enabled asset wallets may use their approved overdraft floor, liability wallets may use approved credit capacity, and protected goal money remains unavailable. Technical failures may retry with idempotent backoff; business-rule failures wait for the user.
- Archive replaces hard deletion. Archive removes unmaterialized future pressure but preserves occurrence and financial-event links.
- Template amount/category edits apply from the next unresolved occurrence forward. Fulfilled occurrences preserve event-time snapshots and valid linked-event values.
- Pausing suppresses paused dates. Resuming computes the next future occurrence and never auto-catches-up the paused interval.
- Skipped and cancelled occurrences have no financial event and no floor contribution. Posting failures remain outstanding. A voided linked financial event cannot count as fulfilled and must surface as needing reconciliation.
- Preserve existing FIXED/FLEXIBLE cadence semantics where they do not conflict with explicit pause behavior. Preserve original calendar anchoring across short months.
- Extract one pure, range-bounded occurrence projector that accepts a template/schedule snapshot and `[range_start, range_end)` dates and returns deterministic projected occurrences without persistence.
- Refactor existing recurring projection rows to use the shared projector rather than maintaining a second count loop.
- Build full-month recurring warning contributions by deduplicating occurrence identity and combining valid fulfilled actuals, pending/outstanding expectations, and still-projected future expectations.
- Aggregate recurring warning presentation by template/category while retaining enough counts, dates, and amounts for explanation. Do not force the UI to render one yellow row for every daily occurrence.
- Category-floor warnings remain read-time derived values. They are never persisted, accepted, reserved, or automatically applied to category budgets.
- Current-month defaults use the effective user-local calendar month. Explicit year/month requests use deterministic calendar boundaries and timezone-aware validation.
- Saved custom projection horizons remain preference metadata and never alter templates, occurrences, due dates, wallets, budgets, expenses, or warnings.
- Add thin public commands for confirming, skipping, retrying/resolving a failed automatic occurrence, pausing/resuming, and archiving. Add occurrence list/detail reads suitable for pending and history UI.
- The UI exposes the recording-mode choice during template creation/edit, a `Needs confirmation` surface, expected-versus-actual information, wallet-allocation editing, skip/remind-later actions, variance warnings, and an explicit update-future-amount option.
- The canonical durable confirmation location is `Expenses > Recurring`, with a `Needs confirmation` section above the template list and pending/history tabs or equivalent filters. Confirmation must remain discoverable even after its notification is read or deleted.
- The global notification bell is a secondary entry point. A recurring-due notification carries occurrence/template identifiers and deep-links to the canonical confirmation surface, opening the same shared confirmation component.
- The existing Dashboard upcoming-recurring card is a compact tertiary surface. It may show a pending count and `Review` action, but it must not implement different confirmation math or a separate posting flow.
- Use one shared confirmation interaction: a desktop dialog and mobile bottom sheet backed by the same form state and command. Do not force an interrupting modal on login and do not place recurring confirmation in Budgets or Wallets.
- Existing legacy recurring-event history may be retained for audit and migrated only where facts can be proven. Migration must not invent financial-event links that the old posting path failed to persist.
- Template/occurrence services should be deep modules with narrow commands and queries. HTTP routes and scheduler jobs should primarily authenticate, validate transport data, invoke domain services, and commit or report results.

## Testing Decisions

- Prefer authenticated public API tests for template creation, recording-mode selection, occurrence reads, confirmation, skip, pause/resume, archive, projection rows, and month-summary warnings.
- Test the scheduler at its public job boundary with controlled local dates and persisted user timezones. Assert observable occurrences, notifications, financial events, wallet balances, and template pointers rather than helper calls.
- Reuse existing expense route/service behavior as prior art for multi-wallet allocation totals, duplicate-wallet rejection, wallet locking, goal protection, owned/borrowed funding classification, budget materialization, and atomic posting.
- Reuse existing recurring route tests as prior art for premium access, rate limits, frequency anchoring, skip/pay-now behavior, projection horizons, and user ownership.
- Add timezone boundary tests where UTC and the user's timezone fall on different dates or months.
- Add full-month projector cases for daily, weekly, biweekly, monthly day-31, quarterly, semiannual, yearly, one-time, fixed, and flexible schedules.
- Add lifecycle floor cases for fulfilled plus future, pending confirmation, actual under/over variance, amount edit, category edit, skip, pause/resume, archive before/after a due occurrence, posting failure, and voided linked events.
- Add a daily example proving that multiple month occurrences are counted rather than only `next_due_date`.
- Add split-category examples proving fulfilled old-category amounts and projected new-category amounts remain separate.
- Add atomic rollback tests where one wallet allocation, goal-protection check, budget operation, or occurrence update fails.
- Add a multi-wallet rollback case proving that if any allocation lacks valid spend capacity, every wallet, budget, financial event, and occurrence remains unchanged.
- Add idempotency and concurrency tests for scheduler-versus-confirm, scheduler-versus-archive, confirm retry, pause-versus-due processing, and update-versus-due processing.
- Add read-only tests proving projection and month-summary requests do not mutate templates, occurrences, due dates, wallets, budgets, financial events, notifications, or floor records.
- Add compatibility tests proving existing templates remain automatic after migration and new confirmation templates may omit a wallet.
- Add frontend interaction tests for recording-mode fields, pending confirmation, multi-wallet total mismatch, amount variance, skip, and update-future-amount intent.
- Run backend migrations and focused/full backend tests inside Docker. Run the frontend build and relevant frontend tests against the Docker-backed contract as required by the repository workflow.

## Out of Scope

- Linking, mirroring, or converting debts or payment plans into recurring templates.
- A unified debt/installment/recurring due-obligation inbox.
- Partial settlement of one ordinary recurring occurrence. A lower confirmed amount closes that occurrence in G30.
- Actual bank payment initiation, bank-feed verification, or claiming that automatic recording proves an external provider was paid.
- Automatic amount prediction from historical bills.
- Pre-generating or persisting an indefinite future occurrence calendar.
- Persisting category-floor calculations or automatically changing category budget limits.
- Issue 5 Budget Workspace rendering and repair actions beyond the recurring data contract it consumes.
- The future timeline and cash-flow simulator beyond exposing reusable recurring occurrence semantics.
- Redesigning debt, installment, expected-inflow, project, or goal lifecycle rules.
- Cross-currency wallet allocation or conversion changes beyond the capabilities of the existing expense-posting path.
- Template-level multi-wallet percentages, fixed splits, fallback wallets, and automatic reallocation.

## Further Notes

### Reference Scenario: Variable Multi-Wallet Utility Bill

The template expects 300,000 UZS on June 15 and uses confirmation mode. On the due date the scheduler creates one pending occurrence and notification without touching money. The user confirms that 347,000 UZS occurred on June 17, funded by 200,000 from a debit wallet and 147,000 in cash. One financial event and two wallet-ledger rows post atomically. The occurrence becomes fulfilled at 347,000 and the template remains 300,000 unless the user explicitly selects `Use this amount for future occurrences`.

### Reference Scenario: Mid-Month Archive

A 3,000 UZS daily template has fourteen valid fulfilled June occurrences and is archived after the June 14 occurrence. The June recurring recommendation retains 42,000 UZS of fulfilled truth and projects no later occurrences. If the saved category limit was previously raised to 90,000 UZS, it remains 90,000; only the derived recommendation and warning gap change.

### Reference Scenario: Mid-Month Amount And Category Edit

A daily template posts fourteen June occurrences at 3,000 UZS in Dining. Before June 15 it changes to 5,000 UZS in Work Expenses. June warnings retain 42,000 UZS under Dining and project 80,000 UZS under Work Expenses for June 15 through June 30. Neither history nor the saved budgets are rewritten.

### Reference Scenario: Pause Without Catch-Up

A daily template is fulfilled through June 10, paused for June 11 through June 20, and resumed for the next future schedule date. June contains ten fulfilled occurrences before the pause and ten expected occurrences from June 21 through June 30. The paused ten dates generate neither expenses nor warning contribution, and resume does not generate a burst of overdue charges.

### Publication Note

Published locally under `docs/prd/` as requested, with the `ready-for-agent` label. No external issue-tracker publication was requested for this G30 file.
