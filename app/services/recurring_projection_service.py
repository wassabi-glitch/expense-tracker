from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import select

from app import models, schemas
from app.services.recurring_schedule_service import calculate_next_due_date


@dataclass
class ProjectedOccurrence:
    category: models.ExpenseCategory
    amount: int
    source_id: int
    title: str
    due_date: date
    is_materialized: bool


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


def project_occurrences_for_range(
    db: Session,
    template: models.RecurringExpense,
    start_date: date,
    end_date: date,
) -> list[ProjectedOccurrence]:
    results: list[ProjectedOccurrence] = []
    
    occurrences = db.scalars(
        select(models.RecurringOccurrence)
        .where(models.RecurringOccurrence.template_id == template.id)
        .where(models.RecurringOccurrence.scheduled_due_date >= start_date)
        .where(models.RecurringOccurrence.scheduled_due_date <= end_date)
    ).all()
    
    for occ in occurrences:
        if occ.status in (models.RecurringOccurrenceStatus.SKIPPED, models.RecurringOccurrenceStatus.CANCELLED):
            continue
            
        amount = occ.expected_amount
        if occ.status == models.RecurringOccurrenceStatus.FULFILLED and occ.actual_amount is not None:
            amount = occ.actual_amount
            
        results.append(ProjectedOccurrence(
            category=occ.expected_category,
            amount=amount,
            source_id=template.id,
            title=template.title,
            due_date=occ.scheduled_due_date,
            is_materialized=True,
        ))
        
    curr_date = template.next_due_date
    original_due_day = template.original_due_day or template.start_date.day
    
    guard = 0
    while curr_date and curr_date <= end_date:
        if curr_date >= start_date:
            results.append(ProjectedOccurrence(
                category=template.category,
                amount=template.amount,
                source_id=template.id,
                title=template.title,
                due_date=curr_date,
                is_materialized=False,
            ))
            
        if template.frequency == models.RecurringFrequency.ONE_TIME:
            break
            
        next_due = calculate_next_due_date(curr_date, template.frequency, original_due_day)
        if next_due <= curr_date:
            break
        curr_date = next_due
        
        guard += 1
        if guard > 2000:
            break
            
    results.sort(key=lambda x: x.due_date)
    return results


def build_projection_rows(
    db: Session,
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
            safe_end = anchor_date + timedelta(days=365*5)
            projected = project_occurrences_for_range(db, recurring, anchor_date, safe_end)
            if projected:
                first_occ = projected[0]
                horizon_end = first_occ.due_date
                occurrence_count = 1
                total_amount = first_occ.amount
            else:
                horizon_end = recurring.next_due_date
                occurrence_count = 0
                total_amount = 0
        else:
            exclusive_end = _exclusive_horizon_end(anchor_date, unit, value)
            horizon_end = exclusive_end - timedelta(days=1)
            projected = project_occurrences_for_range(db, recurring, anchor_date, horizon_end)
            occurrence_count = len(projected)
            total_amount = sum(p.amount for p in projected)
            
        rows.append(
            schemas.RecurringProjectionRowOut(
                source=source,
                unit=unit,
                value=value,
                label=_label(unit, value),
                horizon_start=anchor_date,
                horizon_end=horizon_end,
                occurrence_count=occurrence_count,
                total_amount=total_amount,
            )
        )
    return rows


def build_recurring_projection_output(
    db: Session,
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
            db,
            recurring,
            source="default",
            horizons=default_horizons,
            anchor_date=anchor_date,
        ),
        custom_projections=build_projection_rows(
            db,
            recurring,
            source="custom",
            horizons=custom,
            anchor_date=anchor_date,
        ),
        ad_hoc_projections=build_projection_rows(
            db,
            recurring,
            source="ad_hoc",
            horizons=ad_hoc,
            anchor_date=anchor_date,
        ),
    )
