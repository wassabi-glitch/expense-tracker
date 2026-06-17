# PRD: G0 - Budget Language Cleanup

Labels: `ready-for-agent`

Implementation status: Completed. References to `Underfunded` / `underfunded`
in this PRD describe the retired pre-G0 vocabulary and are kept as legacy
problem context, not current product language.

## Problem Statement

Sarflog previously used the budget plan-health term `Underfunded` in backend status values, frontend copy, tests, and documentation. That term conflicts with the product philosophy that budgets are monthly spending permissions, not cash envelopes.

When users see `Underfunded`, they can reasonably believe they need to physically move money into a budget. The real issue is different: their planned budget promises exceed the available backing from wallet reality and expected inflows. The product language should make that mismatch clear without implying envelope budgeting.

## Solution

Replace budget plan-health language that says or encodes `Underfunded` with language that reflects over-committed planning.

The primary user-facing status should be `Over-Planned`. Supporting copy may use `Exceeds Free Cash` or `Unbacked` when the specific context benefits from sharper wording.

The system should continue to detect the same plan-health condition for now. This PRD changes naming and copy only; it does not change budget backing math.

## User Stories

1. As a Sarflog user, I want budget health language to say `Over-Planned`, so that I understand my plan promises exceed my backing.
2. As a Sarflog user, I want budget warnings to avoid `Underfunded`, so that I do not think budgets are cash envelopes.
3. As a Sarflog user, I want the budget dashboard to explain plan risk in wallet-reality language, so that I know the issue is planning pressure.
4. As a Sarflog user, I want plan-health hints to tell me what action to take, so that I can reduce limits or add expected income.
5. As a Sarflog user, I want budget copy to distinguish expected income from current cash, so that I understand whether I am waiting on income or over-planned.
6. As a Sarflog user, I want budget status labels to be consistent across pages, so that I do not see different names for the same problem.
7. As a Sarflog user, I want error and warning copy to avoid envelope-budget language, so that Sarflog’s mental model stays clear.
8. As a Sarflog user, I want budget status to remain stable after this wording cleanup, so that only language changes and behavior does not surprise me.
9. As a Sarflog user, I want existing budget guardrails to keep working, so that impossible plan increases still get blocked.
10. As a Sarflog user, I want the budget summary to show shortfall information with clearer wording, so that I can repair the plan.
11. As a Sarflog user, I want translated budget status copy to match the new meaning, so that the app remains coherent in every supported language.
12. As a developer, I want backend budget status vocabulary to stop exposing `underfunded`, so that future work builds on the correct domain language.
13. As a developer, I want tests to assert `Over-Planned` semantics, so that the old language does not return accidentally.
14. As a developer, I want the implementation to be a narrow rename/copy cleanup, so that later budget math changes remain separate.
15. As a developer, I want no migration unless persisted data actually needs it, so that a copy-only change does not create unnecessary database risk.
16. As a product maintainer, I want old planning docs to be marked or updated where they conflict, so that future agents do not reintroduce `Underfunded`.
17. As a product maintainer, I want `Waiting on income` to stay distinct from `Over-Planned`, so that the two statuses keep different meanings.
18. As a tester, I want budget summary tests to cover the renamed status, so that backend responses and frontend assumptions stay aligned.
19. As a tester, I want UI copy checks to cover the plan-repair callout, so that the most visible surface uses the new wording.
20. As a future agent, I want the G0 scope to be precise, so that I do not accidentally implement G3 budget backing math during copy cleanup.

## Implementation Decisions

- Rename the budget plan-health state currently represented as `underfunded` to an over-planning term.
- Prefer `over_planned` as the machine-readable value for the backend and frontend contract.
- Prefer `Over-Planned` as the primary visible label.
- Allow `Exceeds Free Cash` or `Unbacked` only as supporting copy when the context is specifically about cash/backing.
- Preserve existing plan-health behavior for this PRD; the backing math changes belong to the later core budget backing work.
- Preserve `Waiting on income` as a separate status for plans that are short on current cash but covered by expected inflows.
- Update frontend budget status metadata so the fallback branch does not silently treat every unknown status as the over-planned state.
- Update budget plan-repair callouts so they describe exceeded backing, not lack of envelope funding.
- Update translations for every supported language.
- Update tests that assert the old machine-readable value or old wording.
- Update planning documentation where the old term appears as settled product language.
- Do not rename unrelated category-level statuses such as warning, high risk, or over limit.
- Do not change expense-save behavior, budget create/update blocking behavior, expected-income lifecycle behavior, or budget backing formulas in this PRD.

## Testing Decisions

- Test at the highest existing seam: budget month summary responses and budget plan-capacity responses.
- Update existing backend budget tests that currently expect the old status value to expect the new status value.
- Add or update assertions that distinguish `Waiting on income` from `Over-Planned`.
- Verify existing guardrail behavior still blocks plan increases that exceed backing.
- Verify existing reduction behavior still allows repairing an over-planned budget.
- Verify frontend plan-status copy maps the new machine-readable status to the intended visible label and hint.
- Verify supported translation files include the new copy keys or updated values.
- Avoid implementation-detail tests around enum internals unless they are the public serialized contract.

## Out of Scope

- Reworking budget backing math.
- Implementing `valid_budget_spent`.
- Changing how expected inflows are calculated.
- Adding receivables, liquidity loans, or debt-funded plan flags.
- Changing expense save blocking rules.
- Changing subcategory limit architecture.
- Changing project budget behavior.
- Changing debt or payment-plan workflows.
- Adding new dashboard intelligence.

## Further Notes

This PRD is intentionally small. It prepares the language foundation for later budget math work by removing a misleading term before deeper planning behavior changes begin.

The issue-tracker publish step is pending because no issue-tracker tool or CLI is available in the current environment. When publishing manually, use the title `G0 - Budget Language Cleanup` and apply the `ready-for-agent` label.
