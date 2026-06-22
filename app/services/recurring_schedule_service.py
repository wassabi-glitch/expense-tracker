from __future__ import annotations

from datetime import date, timedelta

from app import models


def calculate_next_due_date(
    current_due_date: date,
    frequency: models.RecurringFrequency,
    original_due_day: int | None = None,
) -> date:
    """Advance one recurrence while preserving the intended calendar anchor."""
    if frequency == models.RecurringFrequency.ONE_TIME:
        return current_due_date
    if frequency == models.RecurringFrequency.DAILY:
        return current_due_date + timedelta(days=1)
    if frequency == models.RecurringFrequency.WEEKLY:
        return current_due_date + timedelta(weeks=1)
    if frequency == models.RecurringFrequency.BIWEEKLY:
        return current_due_date + timedelta(weeks=2)

    month_steps = {
        models.RecurringFrequency.MONTHLY: 1,
        models.RecurringFrequency.QUARTERLY: 3,
        models.RecurringFrequency.SEMI_ANNUALLY: 6,
        models.RecurringFrequency.YEARLY: 12,
    }
    months_to_jump = month_steps.get(frequency)
    if months_to_jump is None:
        raise ValueError(f"Unsupported recurring frequency: {frequency}")

    target_day = original_due_day or current_due_date.day
    total_months = current_due_date.year * 12 + current_due_date.month - 1 + months_to_jump
    new_year, zero_based_month = divmod(total_months, 12)
    new_month = zero_based_month + 1

    following_year, following_zero_based_month = divmod(total_months + 1, 12)
    following_month = following_zero_based_month + 1
    last_day = date(following_year, following_month, 1) - timedelta(days=1)
    return date(new_year, new_month, min(target_day, last_day.day))


def first_due_after(
    template: models.RecurringExpense,
    local_date: date,
) -> date:
    """Return the first schedule date strictly after ``local_date``."""
    if template.frequency == models.RecurringFrequency.ONE_TIME:
        return template.next_due_date

    if template.cycle_behavior == models.CycleBehavior.FLEXIBLE:
        return calculate_next_due_date(
            local_date,
            template.frequency,
            local_date.day,
        )

    candidate = template.next_due_date
    while candidate <= local_date:
        next_candidate = calculate_next_due_date(
            candidate,
            template.frequency,
            template.original_due_day,
        )
        if next_candidate <= candidate:
            break
        candidate = next_candidate
    return candidate
