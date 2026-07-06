---
name: audit-user-timezone-dates
description: Audit backend and frontend code for user-facing date/time bugs where logic ignores the user's timezone. Use when the user asks to find timezone/date bugs, check date.today()/datetime.now()/new Date() usage, verify X-Timezone handling, or produce a clear report with real-life examples and concrete fixes for date behavior across the system.
---

# Audit User Timezone Dates

## Overview

Find places where the app may treat "today", month boundaries, due dates, or calendar dates as server time or browser/UTC accident instead of the user's intended local date.

The mission is practical: a user in Tashkent, New York, or Tokyo should see expenses, budgets, recurring items, debts, goals, and analytics land on the day/month they actually experienced.

## Audit Workflow

1. Read project rules first:
   - `AGENTS.md`, if present
   - backend timezone helpers, usually `app/timezone.py`
   - frontend date helpers, usually `frontend/src/lib/date.js` and `frontend/src/lib/format.js`
   - API client timezone handling, usually `frontend/src/lib/api/client.js`
   - test helpers, usually `tests/helpers.py`

2. Search backend date creation and timezone handling:

```bash
rg -n "date\.today\(|datetime\.now\(|datetime\.utcnow\(|utcnow\(|today\(|now\(" app tests -g "*.py"
rg -n "get_effective_user_timezone|resolve_effective_timezone|get_request_timezone|today_in_tz|now_in_tz|X-Timezone|timezone" app tests -g "*.py"
```

3. Search frontend date creation and display:

```bash
rg -n "new Date\(|Date\.now\(|toISOString\(|toLocaleDateString|getTimezoneOffset|Intl\.DateTimeFormat|toISODateInTimeZone|getBrowserTimeZone|formatDisplayDate|formatMonthYear" frontend/src -g "*.js" -g "*.jsx" -g "*.ts" -g "*.tsx"
rg -n "X-Timezone|timeZone|timezone" frontend/src app tests
```

4. Inspect each hit in nearby context. Do not classify by search result alone.

5. Report findings before fixing unless the user explicitly asked for implementation.

## Classification Rules

Treat as likely bugs when date logic affects user-facing calendar behavior and does not use the user's timezone:

- default expense/income/debt/goal/project dates
- "future date" validation
- recurring due date generation
- budget month selection
- analytics date ranges
- monthly limits, rollover, or month-scoped calculations
- date-only frontend form defaults and max values
- date-only display that can shift a day because a `YYYY-MM-DD` string was parsed as an instant

Treat as usually acceptable:

- audit timestamps such as `created_at`, `updated_at`, `archived_at`, `voided_at`
- token expiry and security timestamps using `datetime.now(timezone.utc)`
- absolute timestamp display, where `new Date(isoTimestamp)` intentionally converts an instant to local display time
- tests that intentionally pin time or monkeypatch timezone helpers

Still inspect "acceptable" hits. A UTC timestamp is fine for "when did the server record this?", but not for "what day does this count for the user?"

## Fix Patterns

Backend route pattern:

```python
from datetime import tzinfo
from fastapi import Depends
from app.timezone import get_effective_user_timezone, today_in_tz

def create_item(..., user_tz: tzinfo = Depends(get_effective_user_timezone)):
    local_today = today_in_tz(user_tz)
```

Backend service pattern:

- Prefer passing `today`, `user_tz`, or a specific effective date into services.
- Avoid hidden `date.today()` inside services that make user-facing decisions.
- For background jobs, resolve from the stored user timezone with `resolve_effective_timezone(...)`.

Frontend pattern:

- Use `toISODateInTimeZone()` for today's `YYYY-MM-DD` in forms, filters, and validation.
- Keep the API client's `X-Timezone` header intact.
- Treat date-only values as calendar dates, not instants.
- Avoid `new Date("YYYY-MM-DD")` for date-only display or comparisons.
- Prefer splitting `YYYY-MM-DD` into year/month/day or fixing/using a shared helper.
- Use `new Date(isoTimestamp)` for real timestamps, not date-only strings.

Test pattern:

- Use the repo's timezone-aware test helper, such as `user_timezone_today()`.
- Include `X-Timezone` headers when testing authenticated user flows.
- Add boundary tests around midnight when the bug depends on UTC versus local date.

## Report Shape

Order findings by practical risk. For each issue, include:

```text
Finding: <short title>
Location: <file:line>
Risk: <High/Medium/Low>
What is wrong:
<plain explanation>

Real-life example:
<simple example, such as a Tashkent user logging an expense after midnight and the app putting it in yesterday's budget>

Suggested fix:
<specific code-level fix or pattern>

Test to add:
<focused regression test>
```

Also include:

- `Looks safe / intentionally UTC`: list important hits that were reviewed and judged safe.
- `Systemic fix`: name any shared helper that should be fixed if many call sites depend on it.
- `Verification`: list Docker commands to run after changes.

## Verification Commands

Use Docker-first verification when this repo is running in Compose:

```bash
docker compose exec api python -m alembic current
docker compose exec api pytest -q tests/test_budget.py tests/test_expenses.py
docker compose exec frontend npm run build
```

If a fix changes schema, create/apply a migration first:

```bash
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic current
```

Never claim a command passed unless it was actually run.
