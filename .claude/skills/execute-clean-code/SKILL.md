---
name: execute-clean-code
description: Execute code changes with senior engineering discipline, clean modular design, low bug risk, and honest verification. Use when the user asks Codex to implement a feature, fix a bug, execute an issue, improve code quality, make the solution robust, follow industry standards, reduce bugs, keep the work modular, or proceed with best-practice engineering judgment.
---

# Execute Clean Code

## Overview

Use this skill to turn an implementation request into production-minded work: scoped, readable, modular, tested, and aligned with the existing codebase.

Clean execution means: understand the system first, choose the smallest correct design, implement in focused slices, protect data and user behavior, verify with the right commands, and report truthfully.

## Execution Workflow

1. Read the local rules first:
   - `AGENTS.md`, if present
   - issue/PRD/docs named by the user
   - nearby code, tests, schemas, migrations, and frontend API callers related to the task

2. Clarify the mission in one sentence:
   - What user or system behavior must change?
   - What behavior must stay unchanged?
   - What data, permission, timezone, migration, or compatibility rules matter?

3. Map the existing pattern before editing:
   - Use `rg` to find similar routes, services, components, tests, and helpers.
   - Prefer existing local patterns over new abstractions.
   - Identify the true boundary: model, schema, router, service, frontend API, UI, tests, docs.

4. Design the smallest clean solution:
   - Keep public behavior backward-compatible unless the task requires a breaking change.
   - Put business rules in the domain/service layer when the codebase already does that.
   - Keep routers/controllers thin: parse, authorize, call domain logic, return response.
   - Keep schemas/contracts explicit and aligned with models and frontend callers.
   - Add migrations only for real schema changes, and make them safe for existing data.
   - Extract helpers only when they remove meaningful duplication or clarify a real concept.

5. Implement in focused slices:
   - Make one coherent change at a time.
   - Preserve unrelated user changes.
   - Avoid broad refactors and style churn.
   - Use clear names that match the domain language.
   - Prefer explicit validation over implicit assumptions.
   - Handle negative paths: missing records, wrong owner, invalid state, duplicate action, stale data.
   - Keep frontend state, API calls, and UI rendering separated enough to remain understandable.

6. Protect correctness:
   - Add or update tests for the behavior being changed.
   - Cover at least the happy path and the highest-risk failure path.
   - Add regression tests for the bug that motivated the work.
   - Include permission/cross-user checks when data ownership is involved.
   - Include date/timezone boundary tests when user-facing dates are involved.
   - Include migration/backfill tests or manual migration verification when schema changes are involved.

7. Self-review before finalizing:
   - Correctness: Does this satisfy the requested behavior?
   - Scope: Did the change avoid unrelated refactors?
   - Modularity: Is logic in the right layer?
   - Data integrity: Are historical rows, ledgers, and relationships preserved?
   - Security: Are ownership, auth, and validation enforced server-side?
   - UX/API: Does the frontend match the backend contract?
   - Operations: Are migrations, Docker commands, and builds accounted for?
   - Maintainability: Would another engineer understand this in six months?

## Quality Bar

Aim for boring, explicit, reliable code.

Do:

- Reuse existing helpers, conventions, and naming.
- Keep functions and components focused on one job.
- Make state transitions obvious.
- Fail with clear errors where the user or caller can recover.
- Keep tests close to the changed behavior.
- Prefer deterministic logic over clever shortcuts.
- Report uncertainty and residual risk honestly.

Avoid:

- Clever abstractions before the duplication or complexity is real.
- Mixing unrelated concerns in one service/component.
- Silent fallbacks that hide bad data.
- Client-only validation for rules that must be enforced by the backend.
- Local test commands when the repo requires Docker verification.
- Claiming full verification when only focused checks ran.

## Project-Specific Defaults

For this repo, follow `AGENTS.md`:

- User-facing dates must be user-timezone aware.
- Backend tests, migrations, and frontend builds are Docker-first.
- `api`, `frontend`, `db`, and `redis` run in Docker Compose.
- Preserve ledger/history compatibility for financial data.

Common verification commands:

```bash
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic current
docker compose exec api pytest -q tests/test_budget.py tests/test_expenses.py
docker compose exec frontend npm run build
```

Choose focused commands based on the files changed. If schema changes are made, run migration commands before backend tests.

## Final Report Shape

End with:

```text
Implemented:
- <high-signal change>
- <high-signal change>

Verification:
- <command>: <passed/failed/not run>

Notes:
- <important unchanged behavior, residual risk, or follow-up>
```

Keep the final answer concise. Do not bury failed or skipped verification.
