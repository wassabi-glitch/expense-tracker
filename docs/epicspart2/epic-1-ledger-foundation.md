# Epic 1: Ledger Foundation & Chronological Integrity

**Status:** Not Started

## Goal
Establish the non-negotiable rules that govern when, how, and whether money can be recorded in the system. These four ADRs form the constitutional bedrock of Sarflog's financial engine. Every subsequent epic — debts, goals, inflows, projects — assumes these rules are already in force. No feature can be safely built until these boundaries exist.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0001 — Wallet Epoch: No Backdating Before Wallet Creation](../adr/0001-wallet-epoch-no-backdating.md)**
   - The single most fundamental data integrity boundary. A wallet's opening balance is a sealed snapshot — no transaction may be dated before the wallet's `created_at` date. Per-wallet, date-granularity enforcement.

2. [ ] **[ADR 0010 — Income Backdating & Wallet Epoch](../adr/0010-income-backdating-and-wallet-epoch.md)**
   - Closes the income-side loophole left by ADR 0001. No Income or Expected Inflow may be dated before the wallet epoch. Historical financial data lives outside the ledger.

3. [ ] **[ADR 0002 — Strict Logging & Reconciliation](../adr/0002-strict-logging-and-reconciliation.md)**
   - Defines *when* money can be recorded: today-only for normal flow, reconciliation for the past, 5-day grace window for month closing, and sealed months after day 6. Prevents infinite backdating drift that would corrupt the live budget.

4. [ ] **[ADR 0011 — Immutable Ledger Architecture](../adr/0011-immutable-ledger-architecture.md)**
   - Defines *how* money records change: never via hard deletes or amount mutations. All corrections go through the Void → Reversal append pattern. This is the engineering pattern every module must follow — without it, the reversal mechanics in later ADRs (0005, 0014, 0016) have no foundation.

## Why This Order
- ADR 0001 defines the epoch boundary. ADR 0010 extends it to income. Together they seal the "when can data enter the system" question.
- ADR 0002 layers the operational discipline (today-only, grace windows, sealed months) on top of those boundaries.
- ADR 0011 locks down the mutation model. Once this is in place, every future module knows: append-only, void-and-reverse, never overwrite.

## Execution Rules
- These are system-wide invariants, not feature-scoped work. Enforcement must be validated across all existing modules (expenses, income, wallets) before moving to Epic 2.
- Any legacy code that violates these rules (e.g., hard deletes, backdated inserts) must be caught and fixed as part of this epic.
