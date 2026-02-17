# Timezone Model

This project uses a split model:

1. **Source of truth (DB/backend timestamps): UTC**
2. **User-facing day logic (calendar/today): local business timezone**

## What Is Stored

- `created_at` fields:
  - Stored as timezone-aware timestamps (UTC-oriented).
  - Used for audit/history consistency across environments.

- `expenses.date`:
  - Stored as `DATE` (no time, no timezone).
  - Represents the user's intended calendar day for the expense.

## Why This Split

- UTC timestamps are stable and unambiguous for system events.
- Date-only business fields avoid accidental timezone shifts.
- UI/business rules can still follow local expectations (midnight rollover).

## Current Business Timezone

- `Asia/Tashkent` (Uzbekistan)

Used for:
- "today" boundaries in filters/validation
- preventing future dates based on local day
- analytics ranges that depend on current date

## Frontend Responsibility

- Convert UTC timestamps for display in user context.
- Use timezone-aware "today" values for date input limits.

## Backend Responsibility

- Keep secure/system timestamps in UTC.
- Apply business-day validations/ranges using configured business timezone.

## Practical Rule

- **Store timestamps in UTC.**
- **Store business dates as date-only values.**
- **Use local timezone only for presentation and day-boundary logic.**

