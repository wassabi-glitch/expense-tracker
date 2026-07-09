# 0022. Freeze Isolated Projects and Fund Project Until Core Philosophy Stabilizes

Date: 2026-07-07

## Status

Accepted

## Context

Sarflog currently has a partially implemented Isolated Project concept:

- wallet-backed project funding allocations
- project-local category and micro-subcategory allocations
- monthly-budget bypass behavior for isolated project spending
- Fund Project goals that can graduate into isolated projects
- top-up, rebalance, spend-down, wrap-up, and protection-breach ideas

This is not a small project feature. It is a second money engine inside the app.

The current middle state creates philosophy risk because Isolated Projects touch core surfaces that are still evolving:

- wallet balances and wallet protection
- Free Money Now
- monthly budgets
- overlay projects
- goals and goal fulfillment
- expense entry and session drafts
- reports and analytics
- project completion and wrap-up
- EC-162 protected-money breach resolution

The clearest unresolved conflict is the split between:

```text
Wallets fund the isolated project stash.
Categories spend from the pooled stash.
The payment wallet records real-world payment.
```

That model can be made correct, but only if isolated project stash consumption is modeled as a first-class ledger concept. Otherwise the system can claim that project funding has been spent down while the wallet protection layer still lacks a clear record of which project backing was consumed or released.

## Decision

Freeze Isolated Projects and Fund Project work until Sarflog's core app philosophy is stable.

The freeze applies to:

- direct Isolated Project creation and expansion
- Fund Project goal creation and graduation UX
- isolated project wallet-backed stash mechanics
- isolated project category and micro-subcategory expansion
- isolated project top-ups, rebalancing, wrap-up, and sweep flows
- isolated project off-wallet spending and stash release decisions
- EC-162 project-protection breach resolution
- any new work that depends on Isolated Projects as a core money primitive

The freeze does not require immediately deleting existing code. Existing code may remain if it does not block or distort core app work.

During the freeze, new product and implementation work should prioritize the stable core:

```text
Wallets
Monthly Budgets
Overlay Projects
Goals that do not require project graduation
Expenses and session drafts
Debts and payment plans
Income and expected inflows
Reports and analytics
```

## Freeze Rules

Until this ADR is superseded:

- Do not start new Isolated Project or Fund Project implementation slices.
- Do not make unrelated core features depend on Isolated Project behavior.
- Do not deepen isolated stash mechanics, top-ups, release-selection, or sweep behavior.
- Do not implement project-backed EC-162 resolution.
- Do not treat older Isolated Project PRDs or issue files marked `ready-for-agent` as active execution targets.
- If existing isolated code causes confusion in the UI, prefer hiding or labeling it as experimental/deferred over extending it.

## Revisit Criteria

After the core app is stable, revisit Isolated Projects with one explicit product decision:

```text
Option A: Remove Isolated Projects and Fund Project.
```

Sarflog remains a cleaner system built around wallets, monthly budgets, overlay projects, goals, expenses, debts, and reports.

```text
Option B: Promote Isolated Projects into a first-class protected-stash ledger.
```

If kept, the model must include complete ledger truth for:

- wallet funding/backing
- project category allocation
- real payment wallet
- project stash consumption/release
- multi-wallet release selection
- budget bypass behavior
- reports that distinguish payment wallet from backing wallet
- protection breach resolution after known project intent is applied

The feature should only be unfrozen if it can be explained clearly and implemented without corrupting wallet, budget, free-money, and reporting rules.

## Consequences

- The current product surface avoids being pulled into unresolved isolated-project edge cases.
- Core app philosophy can settle before Sarflog commits to a second money engine.
- Some existing isolated-project code and docs remain present but are no longer treated as active roadmap work.
- Future agents must not continue Isolated Project or Fund Project work merely because older issue files describe it.
- The eventual decision may be either deletion or a deeper first-class subsystem; the current half-state is explicitly not the target architecture.
