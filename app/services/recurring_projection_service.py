from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status

from app import models, schemas
from app.services.recurring_schedule_service import calculate_next_due_date


DEFAULT_HORIZONS: dict[models.RecurringFrequency, list[tuple[str, int]]] = {
    models.RecurringFrequency.ONE_TIME: [("occurrences", 1)],
    models.RecurringFrequency.DAILY: [
        ("days", 7),
        ("days", 14),
        ("months", 1),
        ("months", 3),
        ("months", 6),
        ("months", 12),
    ],
    models.RecurringFrequency.WEEKLY: [
        ("months", 1),
        ("months", 3),
        ("months", 6),
        ("months", 12),
    ],
    models.RecurringFrequency.BIWEEKLY: [
        ("months", 1),
        ("months", 3),
        ("months", 6),
        ("months", 12),
    ],
    models.RecurringFrequency.MONTHLY: [
        ("months", 3),
        ("months", 6),
        ("months", 12),
    ],
    models.RecurringFrequency.QUARTERLY: [
        ("months", 6),
        ("months", 12),
    ],
    models.RecurringFrequency.SEMI_ANNUALLY: [("months", 12)],
    models.RecurringFrequency.YEARLY: [("months", 12)],
}


ALLOWED_CUSTOM_UNITS: dict[models.RecurringFrequency, set[str]] = {
    models.RecurringFrequency.ONE_TIME: {"occurrences"},
    models.RecurringFrequency.DAILY: {"days", "weeks", "months", "years"},
    models.RecurringFrequency.WEEKLY: {"weeks", "months", "years"},
    models.RecurringFrequency.BIWEEKLY: {"weeks", "months", "years"},
    models.RecurringFrequency.MONTHLY: {"months", "years"},
    models.RecurringFrequency.QUARTERLY: {"quarters", "months", "years"},
    models.RecurringFrequency.SEMI_ANNUALLY: {"half_years", "months", "years"},
    models.RecurringFrequency.YEARLY: {"years", "months"},
}


MAX_HORIZON_BY_UNIT = {
    "occurrences": 1,
    "days": 1825,
    "weeks": 260,
    "months": 60,
    "quarters": 20,
    "half_years": 10,
    "years": 5,
}


def _add_months(value: date, months: int) -> date:
    total_months = value.year * 12 + (value.month - 1) + months
    year = total_months // 12
    month = (total_months % 12) + 1
    next_total_months = total_months + 1
    next_year = next_total_months // 12
    next_month = (next_total_months % 12) + 1
    last_day = date(next_year, next_month, 1) - timedelta(days=1)
    return date(year, month, min(value.day, last_day.day))


def _exclusive_horizon_end(anchor_date: date, unit: str, value: int) -> date:
    if unit == "days":
        return anchor_date + timedelta(days=value)
    if unit == "weeks":
        return anchor_date + timedelta(weeks=value)
    if unit == "months":
        return _add_months(anchor_date, value)
    if unit == "quarters":
        return _add_months(anchor_date, value * 3)
    if unit == "half_years":
        return _add_months(anchor_date, value * 6)
    if unit == "years":
        return _add_months(anchor_date, value * 12)
    if unit == "occurrences":
        return anchor_date
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring.projection_unit_invalid")


def _label(unit: str, value: int) -> str:
    singular = {
        "occurrences": "occurrence",
        "days": "day",
        "weeks": "week",
        "months": "month",
        "quarters": "quarter",
        "half_years": "half-year",
        "years": "year",
    }[unit]
    return f"{value} {singular if value == 1 else unit.replace('_', '-')}"


def validate_projection_horizons(
    frequency: models.RecurringFrequency,
    horizons: list[schemas.RecurringProjectionHorizonIn],
) -> list[dict[str, int | str]]:
    allowed_units = ALLOWED_CUSTOM_UNITS[frequency]
    normalized: list[dict[str, int | str]] = []
    seen: set[tuple[str, int]] = set()
    for horizon in horizons:
        unit = horizon.unit.value if hasattr(horizon.unit, "value") else str(horizon.unit)
        value = int(horizon.value)
        if unit not in allowed_units:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring.projection_unit_not_allowed")
        if value > MAX_HORIZON_BY_UNIT[unit]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring.projection_horizon_too_large")
        key = (unit, value)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"unit": unit, "value": value})
    return normalized


def _count_occurrences_before(
    recurring: models.RecurringExpense,
    exclusive_end: date,
) -> int:
    if recurring.frequency == models.RecurringFrequency.ONE_TIME:
        return 1 if recurring.next_due_date <= exclusive_end else 0

    current_due = recurring.next_due_date
    original_due_day = recurring.original_due_day or recurring.start_date.day
    count = 0
    guard = 0
    while current_due < exclusive_end:
        count += 1
        next_due = calculate_next_due_date(current_due, recurring.frequency, original_due_day)
        if next_due <= current_due:
            break
        current_due = next_due
        guard += 1
        if guard > 2000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring.projection_horizon_too_large")
    return count


def build_projection_rows(
    recurring: models.RecurringExpense,
    *,
    source: str,
    horizons: list[dict[str, int | str]],
    anchor_date: date,
) -> list[schemas.RecurringProjectionRowOut]:
    rows: list[schemas.RecurringProjectionRowOut] = []
    for horizon in horizons:
        unit = str(horizon["unit"])
        value = int(horizon["value"])
        if unit == "occurrences":
            occurrence_count = 1
            horizon_end = recurring.next_due_date
        else:
            exclusive_end = _exclusive_horizon_end(anchor_date, unit, value)
            occurrence_count = _count_occurrences_before(recurring, exclusive_end)
            horizon_end = exclusive_end - timedelta(days=1)
        rows.append(
            schemas.RecurringProjectionRowOut(
                source=source,
                unit=unit,
                value=value,
                label=_label(unit, value),
                horizon_start=anchor_date,
                horizon_end=horizon_end,
                occurrence_count=occurrence_count,
                total_amount=occurrence_count * int(recurring.amount or 0),
            )
        )
    return rows


def build_recurring_projection_output(
    recurring: models.RecurringExpense,
    *,
    anchor_date: date,
    ad_hoc_horizons: list[schemas.RecurringProjectionHorizonIn] | None = None,
) -> schemas.RecurringProjectionOut:
    custom_horizons = [
        schemas.RecurringProjectionHorizonIn(**item)
        for item in (recurring.custom_projection_horizons or [])
    ]
    default_horizons = [
        {"unit": unit, "value": value}
        for unit, value in DEFAULT_HORIZONS[recurring.frequency]
    ]
    custom = validate_projection_horizons(recurring.frequency, custom_horizons)
    ad_hoc = validate_projection_horizons(recurring.frequency, ad_hoc_horizons or [])
    return schemas.RecurringProjectionOut(
        recurring_id=int(recurring.id),
        anchor_date=anchor_date,
        default_projections=build_projection_rows(
            recurring,
            source="default",
            horizons=default_horizons,
            anchor_date=anchor_date,
        ),
        custom_projections=build_projection_rows(
            recurring,
            source="custom",
            horizons=custom,
            anchor_date=anchor_date,
        ),
        ad_hoc_projections=build_projection_rows(
            recurring,
            source="ad_hoc",
            horizons=ad_hoc,
            anchor_date=anchor_date,
        ),
    )
