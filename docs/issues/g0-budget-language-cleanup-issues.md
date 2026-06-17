# Issues: G0 - Budget Language Cleanup

Parent PRD: `docs/prd/g0-budget-language-cleanup.md`

Publish label: `ready-for-agent`

Implementation status: Completed. References to `Underfunded` / `underfunded`
in this issue file describe the retired pre-G0 vocabulary or the cleanup task
itself, not current product language.

## Proposed Breakdown

1. **Expose Over-Planned budget status end-to-end**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-15, 17-20

2. **Retire stale Underfunded planning language in docs**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 16, 20

## Issue 1: Expose Over-Planned Budget Status End-to-End

## What to build

Rename the budget plan-health state currently exposed as `underfunded` so the backend, frontend, translations, and tests use over-planning language instead. The completed slice should preserve the existing plan-health behavior while making the public budget status contract and visible UI copy say `Over-Planned` rather than `Underfunded`.

This slice must keep `Waiting on income` distinct from `Over-Planned`. It must not change budget backing math, budget create/update guardrails, expected-income lifecycle behavior, or expense-save behavior.

## Acceptance criteria

- [x] Budget month summary responses expose an over-planning machine-readable status instead of `underfunded`.
- [x] Existing budget tests that currently assert the old status value assert the new over-planning value.
- [x] Tests still prove plan increases that exceed backing are blocked.
- [x] Tests still prove reducing limits can repair the over-planned budget.
- [x] Frontend budget plan-status logic recognizes the new status explicitly.
- [x] Frontend fallback behavior does not silently treat every unknown status as over-planned.
- [x] Visible budget plan-health label says `Over-Planned`.
- [x] Visible plan-repair copy explains exceeded backing/planning pressure without envelope-budget language.
- [x] `Waiting on income` UI and behavior remain distinct.
- [x] English, Russian, and Uzbek translation files contain the updated status label and hint.
- [x] No budget backing math changes are included.

## Blocked by

None - can start immediately.

## Suggested Verification

- Docker is the normal project runtime: API, database, frontend, and Redis run through Docker Compose.
- Run backend tests through the API container, for example: `docker-compose exec api pytest -q tests/test_budget.py`
- Run frontend build/checks through the frontend container when available, or use the project’s Docker/frontend workflow if the container is already running.

## Issue 2: Retire Stale Underfunded Planning Language In Docs

## What to build

Update settled planning/product documentation so future work no longer treats `Underfunded` as the correct budget plan-health language. Keep historical edge-case source material intact where it is useful for provenance, but make current guidance point agents toward `Over-Planned`, `Exceeds Free Cash`, or `Unbacked`.

This slice should be done after the app contract is renamed so docs can match the implemented vocabulary.

## Acceptance criteria

- [x] Current planning docs no longer present `Underfunded` as the intended budget health term.
- [x] Any remaining `Underfunded` mentions are clearly historical/provenance-only or deliberately deferred.
- [x] `docs/EC_IMPLEMENTATION_PLAN.md` G0 status can be updated only after Issue 1 and this issue are complete.
- [x] No code behavior is changed in this documentation-only slice.

## Blocked by

- Issue 1: Expose Over-Planned Budget Status End-to-End

## Suggested Verification

- Docker is the normal project runtime, but this documentation-only slice can be verified with a repo text search.
- Search current docs for `Underfunded`, `underfunded`, and `UNDERFUNDED`.
- Confirm remaining matches are either historical edge-case text or intentional references to old behavior.
