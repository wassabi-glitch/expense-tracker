# Epic 7 Issues: Goal Deployment & Protection

Parent: [Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md)  
Publish label: `ready-for-agent`  
Epic prerequisite: Epic 6 isolated project wallet allocations, project top-ups, isolated spend-down reporting, and project expense posting foundations

## Scope Note

The G7 backend project-date and graduation work is already tracked in [G7 - Projects and Goal Deployment Issues](../g7-projects-and-goal-deployment-issues.md). This file focuses on the remaining Epic 7 work discovered while reviewing the combined goal deployment epic:

- Fund Project goal UI discoverability and action gaps.
- G11 Goal Payment Philosophy implementation.
- Off-wallet protected-money spending for goals and isolated projects.
- EC-162 wallet protection breach detection and resolution.
- EC-163 smart interceptor explicitly deferred until ledger-correct flows are stable.

---

## Issue 1: Expose Fund Project Goals in the Savings UI

**Type:** AFK

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md), [G7 - Projects and Goal Deployment](../../prd/g7-projects-and-goal-deployment.md)

### What to build

Make Fund Project goals discoverable and understandable from the Savings page. A user should be able to choose "Fund a project" from the goal creation wizard, create a `FUND_PROJECT` goal through the existing backend contract, reserve and unreserve money against it, and see goal-card copy that explains this is a saving-phase project fund rather than a one-shot purchase or reserve.

This slice closes the current UI hole where the backend supports `FUND_PROJECT` but the wizard only exposes Reserve, Planned Purchase, and Pay Obligation.

### Acceptance criteria

- [x] The goal creation wizard offers a Fund Project choice with project-oriented copy.
- [x] Creating a Fund Project goal sends `intent: FUND_PROJECT` to the existing goal creation API.
- [x] Fund Project goals render with a distinct label, description, progress state, and saving-phase language.
- [x] Fund Project goals allow normal saving-phase funding actions while active: reserve money and unreserve money.
- [x] Fund Project goals do not show Planned Purchase, Reserve, or Pay Obligation actions that do not apply.
- [x] Fund Project goals cannot be completed from the UI; the terminal success path is graduation into a project.
- [x] Empty, loading, error, mobile, and desktop states remain stable in the Savings page.
- [x] Backend behavior tests remain green for Fund Project creation and lifecycle guards.
- [x] Frontend tests cover the new wizard choice, create payload, card label/action visibility, and disabled invalid actions.
- [x] Docker frontend build passes.

### Blocked by

None - can start immediately.

---

## Issue 2: Graduate Fund Project Goals from the UI into Isolated Projects

**Type:** AFK

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md), [G7 - Projects and Goal Deployment](../../prd/g7-projects-and-goal-deployment.md)

### What to build

Complete the user-facing graduation baton pass. A user with an active Fund Project goal should be able to click a clear "Create project" or "Start project" action, confirm that the currently reserved money becomes the isolated project stash, and land in the Budgets/Projects surface with the new isolated project highlighted.

After graduation, the origin goal should become read-only saving history. Future additions should route to isolated project top-ups, not to goal funding.

### Acceptance criteria

- [x] Active Fund Project cards expose a primary project-graduation action when the backend can graduate the goal.
- [x] The graduation confirmation explains that reserved goal money becomes isolated project stash.
- [x] Graduation sends `is_isolated: true`, project title, start date, and target end date using the user's local date helpers.
- [x] Successful graduation navigates to the Budgets/Projects surface and highlights or opens the created project.
- [x] The origin goal card shows a graduated/read-only state with a link or route to the project.
- [x] Graduated goals block reserve, unreserve, consume, purchase, and completion actions in the UI.
- [x] Copy explains that future funding belongs in project top-ups.
- [x] API errors such as not Fund Project, archived, already graduated, project already exists, or premium required render as localized actionable messages.
- [x] Backend tests remain green for partial graduation, owner scoping, rollback, and no double funding.
- [x] Frontend tests cover graduation modal, API payload, success navigation, read-only graduated state, and stale-query refresh.
- [x] Docker frontend build passes.

### Blocked by

- Issue 1: Expose Fund Project Goals in the Savings UI

---

## Issue 3: Remove Goal Auto-Reimbursements and Fix the Budget Bypass Contract

**Type:** AFK

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md), [G11 - Goal Payment Philosophy & Auto-Reimbursement Deprecation](../../prd/g11-goal-payment-philosophy.md)

### What to build

Remove the old auto-reimbursement philosophy from backend goal payment flows. The app must never invent wallet-to-wallet transfers to make off-wallet protected-money purchases look tidy. Instead, protected-money flows should record the wallet that actually paid, release or consume protected funding explicitly, and pass a working budget-hit/bypass flag to expense posting.

This slice establishes the shared accounting contract that later UI flows call.

### Acceptance criteria

- [x] Automatic reimbursement/settlement helper logic is removed or made unreachable from active goal payment flows.
- [x] Off-wallet goal payment flows create zero wallet-to-wallet transfer ledger entries unless the user explicitly performs a transfer.
- [x] `post_expense_event` or the active expense posting seam honors `enforce_monthly_budget_limits=False`.
- [x] Planned Purchase off-wallet completion can record an expense without hitting monthly budget aggregates.
- [x] Reserve and isolated-project flows can choose whether monthly budget aggregates are hit according to intent-specific rules.
- [x] Spending reports still include expenses even when those expenses bypass monthly budget pressure.
- [x] Ledger/history copy distinguishes "paid from wallet" from "released protected money".
- [x] Backend tests prove no ghost transfers, budget bypass correctness, wallet reality preservation, and reporting visibility.
- [x] Docker backend tests pass for goal payment and expense posting slices.

### Blocked by

None - can start immediately.

---

## Issue 4: Build Explicit Off-Wallet Goal Payment Flows for Planned Purchases and Reserves

**Type:** AFK

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md), [G11 - Goal Payment Philosophy & Auto-Reimbursement Deprecation](../../prd/g11-goal-payment-philosophy.md)

### What to build

Add user-facing "already paid from wrong wallet" flows for goal spending. A user who paid for a Planned Purchase or Reserve need from a wallet that did not fund the goal should be able to record the real payment wallet, release matching protected money, and apply the correct monthly-budget behavior.

For Reserve goals, the UI must expose the budget toggle because reserve spending may be ordinary visibility-worthy spending or catastrophic/non-routine spending.

### Acceptance criteria

- [ ] Planned Purchase goals expose an off-wallet completion path distinct from same-wallet goal-funded purchase.
- [ ] Planned Purchase off-wallet completion records the real payment wallet and does not hit the monthly budget.
- [ ] Reserve goals expose an off-wallet use path that records the real payment wallet.
- [ ] Reserve off-wallet use defaults to hitting the monthly budget for visibility.
- [ ] Reserve off-wallet use includes a clear toggle to bypass monthly budget pressure for exceptional/catastrophic cases.
- [ ] The toggle affects budget aggregates but never hides the expense from spending reports.
- [ ] The UI explains that protected money is being released and no wallet transfer is being created.
- [ ] Multi-wallet payment rows are supported where the existing expense payment model supports them.
- [ ] API and UI errors preserve wallet reality and do not leave partial goal releases behind.
- [ ] Backend tests cover Planned Purchase off-wallet, Reserve default budget-hit, Reserve budget-bypass, multi-wallet payment, and transaction rollback.
- [ ] Frontend tests cover both flows, the Reserve toggle, payloads, disabled states, localized errors, and stale-query refresh.
- [ ] Docker backend tests and frontend build pass.

### Blocked by

- Issue 3: Remove Goal Auto-Reimbursements and Fix the Budget Bypass Contract

---

## Issue 5: Apply Goal Payment Philosophy to Isolated Project Off-Wallet Spending

**Type:** HITL

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md), [G11 - Goal Payment Philosophy & Auto-Reimbursement Deprecation](../../prd/g11-goal-payment-philosophy.md), [G7 - Projects and Goal Deployment](../../prd/g7-projects-and-goal-deployment.md)

### What to build

Support the isolated-project version of "already paid from wrong wallet." A user should be able to record an isolated project expense from the wallet that actually paid, even when that wallet did not fund the project. The system should reduce/release the equivalent isolated project stash, bypass monthly budget pressure because isolated projects are already deployed protected money, and avoid fake wallet transfers.

Human review is useful before implementation because multi-wallet project stashes need a clear release-selection UX: when a project stash is funded by several wallets, the user may need to choose which project funding source is released.

### Acceptance criteria

- [ ] Product decision is documented for how to release project stash when multiple wallets fund the isolated project.
- [ ] Isolated project expense entry can mark a payment as project-stash-funded even when paid from a non-funding wallet.
- [ ] The expense records the real payment wallet allocation.
- [ ] The project stash decreases by the equivalent amount through explicit project funding release/consumption records.
- [ ] Monthly budget aggregates are not hit for isolated project off-wallet spending.
- [ ] Spending reports still include the expense.
- [ ] No wallet-to-wallet transfer is generated.
- [ ] Project remaining funding, funding shortfall, category availability, and free-money pressure update consistently after save.
- [ ] The UI explains the difference between real payment wallet and project stash release.
- [ ] Backend tests cover same-wallet project spending, off-wallet project spending, multi-wallet project funding release choice, overspend/shortfall, and rollback.
- [ ] Frontend tests cover project-context expense entry, wrong-wallet explanation, release choice if required, payloads, errors, and cache refresh.
- [ ] Docker backend tests and frontend build pass.

### Blocked by

- Issue 3: Remove Goal Auto-Reimbursements and Fix the Budget Bypass Contract
- Issue 2: Graduate Fund Project Goals from the UI into Isolated Projects

---

## Issue 6: Detect and Resolve EC-162 Protection Breaches for Goals and Isolated Projects

**Type:** HITL

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md)

### What to build

Implement EC-162 as a shared protection-coverage rule. After a real wallet payment is applied and any known goal/project intent is handled, the system should detect whether the paying wallet still has enough balance to back protected goal allocations and isolated project wallet allocations. If not, the user must explicitly choose which protected promises to release or reduce.

Human review is useful because the resolution wizard is product-sensitive: it determines how users sacrifice goal or project commitments when wallet reality breaks protection coverage.

### Acceptance criteria

- [ ] The backend can compute protected coverage per wallet after goals and isolated project allocations are considered.
- [ ] Protection breach detection includes protected goal money and protected isolated project wallet allocations.
- [ ] Detection runs after known protected-money intent is applied, so intentional goal/project spending is not double-counted as an unresolved breach.
- [ ] The API exposes a stable preview shape for single-wallet/single-item, single-wallet/multi-item, and multi-wallet/multi-item breaches.
- [ ] The resolution payload requires the user to allocate the full shortfall before final save.
- [ ] Resolution can release/reduce selected protected goal and isolated project allocations without inventing wallet transfers.
- [ ] The save is transactional: expense, releases, and protection resolution all commit together or not at all.
- [ ] Stable error codes distinguish unresolved breach, invalid release amount, ownership mismatch, stale protected amounts, and insufficient resolution.
- [ ] Backend tests cover single goal breach, multiple goal breach, project allocation breach, mixed goal/project breach, multi-wallet breach, stale preview, and rollback.
- [ ] Docker backend tests pass.

### Blocked by

- Issue 3: Remove Goal Auto-Reimbursements and Fix the Budget Bypass Contract
- Issue 5: Apply Goal Payment Philosophy to Isolated Project Off-Wallet Spending

---

## Issue 7: Wire EC-162 Resolution into Expense, Session, Goal, and Project UI Surfaces

**Type:** AFK

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md)

### What to build

Expose EC-162 protection breach prevention and resolution wherever users can create wallet-impacting expenses. The user should see an inline warning before save when an amount will dip into protected money, then a resolution modal on save when the backend reports that protected goal/project money no longer fits inside the paying wallets.

This is the UI half of the EC-162 shared backend contract.

### Acceptance criteria

- [ ] Quick Add shows an inline warning when selected wallet/payment rows exceed free cash after protected money.
- [ ] Expense sessions show the same warning and final-save resolution behavior.
- [ ] Goal off-wallet flows show EC-162 only for collateral wallet breaches after the known goal intent is applied.
- [ ] Isolated project expense flows show EC-162 only for collateral wallet breaches after the known project-stash intent is applied.
- [ ] The resolution modal supports single protected item, multiple protected items, and multiple breached wallets.
- [ ] The modal uses goal/project language clearly: release goal funds, release project stash, or cancel.
- [ ] Save remains disabled until the user resolves the full shortfall.
- [ ] Cancelling preserves the user's draft inputs without committing ledger changes.
- [ ] Successful resolution refreshes wallets, goals, projects, budgets, and expense lists.
- [ ] Frontend tests cover warning calculation, modal states, multi-item inputs, disabled save, cancel preservation, success refresh, and localized errors.
- [ ] Docker frontend build passes.

### Blocked by

- Issue 6: Detect and Resolve EC-162 Protection Breaches for Goals and Isolated Projects

---

## Deferred Candidate: EC-163 Goal Fulfillment Interceptor

**Type:** HITL / Deferred

### Parent

[Epic 7 - Goal Deployment & Protection](../../epics/epic-7-goal-deployment.md)

### What to build

Do not implement EC-163 in this execution pass. Keep it as a future UX convenience layer after explicit G11 flows and EC-162 protection resolution are stable.

The future version may detect when a normal expense looks like a goal or project fulfillment and ask whether the user meant to use protected money. Until then, explicit goal/project actions plus EC-162 are the source of truth.

### Acceptance criteria

- [ ] EC-163 remains documented as deferred and is not required for G11 or EC-162 correctness.
- [ ] Current issues do not depend on fuzzy title/category/amount matching.
- [ ] Any future implementation proposal distinguishes smart detection from ledger truth.
- [ ] No hidden automatic conversion of normal expenses into goal/project fulfillment is introduced in this pass.

### Blocked by

- Issue 4: Build Explicit Off-Wallet Goal Payment Flows for Planned Purchases and Reserves
- Issue 7: Wire EC-162 Resolution into Expense, Session, Goal, and Project UI Surfaces
