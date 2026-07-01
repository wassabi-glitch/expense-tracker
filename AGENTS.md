# AGENTS.md

## Project Operating Rules

This is Sarflog / ExpenseTracker, a money-tracking app. Date math, ledger history, migrations, and Docker verification are high-risk areas. Follow these rules unless the user explicitly says otherwise.

## Timezone Rules

All user-facing dates must be computed in the user's timezone.

The backend timezone source of truth is `app/timezone.py`:

- Use `get_effective_user_timezone` in FastAPI routes when the current user is available.
- Use `today_in_tz(user_tz)` for "today" in product behavior.
- Use `now_in_tz(user_tz)` when a local user-aware datetime is needed.
- Use `resolve_effective_timezone(...)` for service/background flows that need to resolve from a stored user timezone.
- The request timezone comes from the `X-Timezone` header first, then the user's persisted timezone, then `settings.default_timezone`, then UTC.

Do not use `date.today()` or naive `datetime.now()` for user-visible business rules such as:

- expense dates
- budget month selection
- recurring due dates
- debt/payment due dates
- goal progress dates
- income/expected inflow dates
- project effective dates
- "future date" validation
- analytics ranges

UTC is still appropriate for technical/audit timestamps such as token expiry, `created_at`, `updated_at`, `archived_at`, `voided_at`, and security events. Prefer timezone-aware UTC: `datetime.now(timezone.utc)`.

## Frontend Date Rules

The frontend already sends the browser timezone automatically.

- `frontend/src/lib/api/client.js` attaches `X-Timezone` to API requests using `getBrowserTimeZone()`.
- `frontend/src/lib/date.js` provides `getBrowserTimeZone()` and `toISODateInTimeZone()`.
- Use `toISODateInTimeZone()` when creating today's `YYYY-MM-DD` value for forms, filters, max dates, and client-side validation.
- Avoid ad hoc `new Date()` date-only parsing when it could shift the day across timezones.
- Use existing display helpers in `frontend/src/lib/format.js`, especially `formatDisplayDate`, `formatDisplayDateTime`, and `formatMonthYear`.

## Test Timezone Rules

Tests should preserve user-timezone behavior.

- Use `tests/helpers.py`.
- `TEST_TIMEZONE` is `Asia/Tashkent`.
- `create_user_and_token(...)` returns headers with `X-Timezone`.
- Use `user_timezone_today()` instead of `date.today()` when test data depends on the user's current local date.

If a test specifically checks timezone boundaries, make the timezone explicit in headers, for example `X-Timezone: Asia/Tashkent` or `X-Timezone: UTC`.

## Docker Rules

This project is Docker-first.

The main Compose services are:

- `api`: FastAPI backend
- `frontend`: React/Vite build served by Nginx
- `db`: Postgres
- `redis`: Redis

Run migrations, backend tests, and frontend builds inside Docker unless the user explicitly asks for local execution.

Common commands:

```bash
docker compose ps
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic current
docker compose exec api pytest -q tests/test_budget.py tests/test_expenses.py
docker compose exec frontend npm run build