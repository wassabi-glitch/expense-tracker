from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app import models
from app.services.expense_posting_service import post_expense_event
from app.services.recurring_schedule_service import calculate_next_due_date, first_due_after

UNRESOLVED_OCCURRENCE_STATUSES = (
    models.RecurringOccurrenceStatus.PENDING_CONFIRMATION,
)

def notify_pending_confirmation_once(
    db: Session,
    template: models.RecurringExpense,
    occurrence: models.RecurringOccurrence,
) -> None:
    if occurrence.initial_notified_at is not None:
        return
    occurrence.initial_notified_at = datetime.now(timezone.utc)
    db.add(
        models.Notification(
            owner_id=template.owner_id,
            type=models.NotificationType.RECURRING_DUE.value,
            title="Recurring expense due",
            message=(
                f"Your recurring expense '{template.title}' "
                f"({int(template.amount):,} UZS) is due for confirmation."
            ),
            priority=models.NotificationPriority.MEDIUM.value,
            is_read=False,
            extra_data={
                "template_id": int(template.id),
                "occurrence_id": int(occurrence.id),
            },
        )
    )

def get_owned_template(
    db: Session,
    owner_id: int,
    template_id: int,
    *,
    lock: bool = False,
    include_archived: bool = False,
) -> models.RecurringExpense:
    query = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == template_id,
        models.RecurringExpense.owner_id == owner_id,
    )
    if not include_archived:
        query = query.filter(models.RecurringExpense.archived_at.is_(None))
    if lock:
        query = query.with_for_update()
    template = query.first()
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found",
        )
    return template

def validate_preferred_wallet(
    db: Session,
    owner_id: int,
    wallet_id: int | None,
) -> models.Wallet | None:
    if wallet_id is None:
        return None

    wallet = db.query(models.Wallet).filter(
        models.Wallet.id == wallet_id,
        models.Wallet.owner_id == owner_id,
    ).first()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    if not wallet.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.wallet_archived",
        )
    return wallet

def apply_template_rule_updates(
    db: Session,
    template: models.RecurringExpense,
    changes: dict[str, object],
) -> None:
    """Apply mutable template rules without rewriting fulfilled history."""
    snapshot_fields = {
        "title": "expected_title",
        "amount": "expected_amount",
        "category": "expected_category",
    }
    occurrence_changes = {
        occurrence_field: changes[template_field]
        for template_field, occurrence_field in snapshot_fields.items()
        if template_field in changes
    }
    if occurrence_changes:
        unresolved = (
            db.query(models.RecurringOccurrence)
            .filter(
                models.RecurringOccurrence.template_id == template.id,
                models.RecurringOccurrence.status.in_(UNRESOLVED_OCCURRENCE_STATUSES),
            )
            .with_for_update()
            .all()
        )
        for occurrence in unresolved:
            for field, value in occurrence_changes.items():
                setattr(occurrence, field, value)

    for field, value in changes.items():
        setattr(template, field, value)

def materialize_occurrence(
    db: Session,
    template: models.RecurringExpense,
    scheduled_due_date: date,
    *,
    initial_status: models.RecurringOccurrenceStatus,
) -> tuple[models.RecurringOccurrence, bool]:
    existing = db.query(models.RecurringOccurrence).filter(
        models.RecurringOccurrence.template_id == template.id,
        models.RecurringOccurrence.scheduled_due_date == scheduled_due_date,
    ).first()
    if existing is not None:
        return existing, False

    occurrence = models.RecurringOccurrence(
        owner_id=template.owner_id,
        template_id=template.id,
        scheduled_due_date=scheduled_due_date,
        expected_title=template.title,
        expected_amount=int(template.amount),
        expected_category=template.category,
        status=initial_status,
    )
    try:
        with db.begin_nested():
            db.add(occurrence)
            db.flush()
    except IntegrityError:
        occurrence = db.query(models.RecurringOccurrence).filter(
            models.RecurringOccurrence.template_id == template.id,
            models.RecurringOccurrence.scheduled_due_date == scheduled_due_date,
        ).one()
        return occurrence, False
    return occurrence, True

def advance_template_on_generation(
    template: models.RecurringExpense,
    scheduled_due_date: date,
) -> date:
    """Advances the template to the strictly next cycle based purely on the due date."""
    if template.frequency == models.RecurringFrequency.ONE_TIME:
        template.status = models.RecurringStatus.DISABLED
        return scheduled_due_date

    next_due = calculate_next_due_date(
        scheduled_due_date,
        template.frequency,
        template.original_due_day,
    )
    template.next_due_date = next_due
    return next_due

def _apply_flexible_max_math(
    template: models.RecurringExpense,
    actual_date: date,
) -> date:
    """Applies MAX(current_next_due_date, actual_date + frequency) for FLEXIBLE templates."""
    if (
        template.cycle_behavior != models.CycleBehavior.FLEXIBLE
        or template.frequency == models.RecurringFrequency.ONE_TIME
    ):
        return template.next_due_date

    proposed_next_due = calculate_next_due_date(
        actual_date,
        template.frequency,
        actual_date.day,
    )
    if proposed_next_due > template.next_due_date:
        template.next_due_date = proposed_next_due
        if template.frequency != models.RecurringFrequency.DAILY:
            template.original_due_day = actual_date.day
            
    return template.next_due_date


def create_pending_due_occurrence(
    db: Session,
    template: models.RecurringExpense,
    *,
    local_today: date,
) -> models.RecurringOccurrence:
    due_date = template.next_due_date
    occurrence, created = materialize_occurrence(
        db,
        template,
        due_date,
        initial_status=models.RecurringOccurrenceStatus.PENDING_CONFIRMATION,
    )
    if created:
        next_due = advance_template_on_generation(template, due_date)
        db.add(
            models.RecurringEvent(
                recurring_expense_id=template.id,
                event_type=models.RecurringEventType.UPDATED,
                target_due_date=due_date,
                old_next_due_date=due_date,
                new_next_due_date=next_due,
                metadata_notes="Occurrence generated, template strictly advanced",
            )
        )
    return occurrence


def set_template_active(
    template: models.RecurringExpense,
    *,
    active: bool,
    local_today: date,
) -> None:
    if template.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="recurring_expenses.archived_locked",
        )
    if active:
        template.next_due_date = first_due_after(template, local_today)
        template.status = models.RecurringStatus.ACTIVE
        template.paused_at = None
        return

    template.status = models.RecurringStatus.DISABLED
    template.paused_at = datetime.now(timezone.utc)

def archive_template(template: models.RecurringExpense) -> None:
    template.archived_at = datetime.now(timezone.utc)
    template.status = models.RecurringStatus.DISABLED
    template.paused_at = None

def confirm_recurring_occurrence(
    db: Session,
    owner_id: int,
    occurrence_id: int,
    *,
    actual_amount: int,
    actual_date: date,
    wallet_allocations: list[dict],
    update_template_amount: bool = False,
    local_today: date,
) -> models.RecurringOccurrence:
    occurrence = (
        db.query(models.RecurringOccurrence)
        .join(models.RecurringExpense)
        .filter(
            models.RecurringOccurrence.id == occurrence_id,
            models.RecurringOccurrence.owner_id == owner_id,
        )
        .with_for_update()
        .first()
    )
    if not occurrence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recurring_expenses.occurrence_not_found")

    if occurrence.status not in UNRESOLVED_OCCURRENCE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="recurring_expenses.occurrence_already_resolved")

    template = occurrence.template

    if actual_date > local_today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.future_date_not_allowed")

    try:
        with db.begin_nested():
            posted = post_expense_event(
                db,
                owner_id,
                title=occurrence.expected_title,
                amount=actual_amount,
                category=occurrence.expected_category,
                expense_date=actual_date,
                description=template.description,
                wallet_allocations=wallet_allocations,
                reference_type="recurring_occurrence",
                local_today=local_today,
            )
    except Exception:
        raise

    occurrence.status = models.RecurringOccurrenceStatus.FULFILLED
    occurrence.actual_amount = actual_amount
    occurrence.actual_date = actual_date
    occurrence.linked_financial_event_id = posted.event.id
    occurrence.failure_code = None

    if update_template_amount:
        template.amount = actual_amount

    old_next_due = template.next_due_date
    new_next_due = _apply_flexible_max_math(template, actual_date)

    db.add(
        models.RecurringEvent(
            recurring_expense_id=template.id,
            event_type=models.RecurringEventType.PAID,
            target_due_date=occurrence.scheduled_due_date,
            old_next_due_date=old_next_due,
            new_next_due_date=new_next_due,
            metadata_notes="Confirmed. Math applied.",
        )
    )
    return occurrence

def skip_occurrence(
    db: Session,
    owner_id: int,
    occurrence_id: int,
    *,
    actual_date: date,
    local_today: date,
) -> models.RecurringOccurrence:
    occurrence = (
        db.query(models.RecurringOccurrence)
        .join(models.RecurringExpense)
        .filter(
            models.RecurringOccurrence.id == occurrence_id,
            models.RecurringOccurrence.owner_id == owner_id,
        )
        .with_for_update()
        .first()
    )
    if not occurrence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recurring_expenses.occurrence_not_found")

    if occurrence.status not in UNRESOLVED_OCCURRENCE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="recurring_expenses.occurrence_already_resolved")

    if actual_date > local_today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.future_date_not_allowed")

    template = occurrence.template

    occurrence.status = models.RecurringOccurrenceStatus.SKIPPED
    occurrence.actual_date = actual_date
    occurrence.failure_code = None

    old_next_due = template.next_due_date
    new_next_due = _apply_flexible_max_math(template, actual_date)

    db.add(
        models.RecurringEvent(
            recurring_expense_id=template.id,
            event_type=models.RecurringEventType.SKIPPED,
            target_due_date=occurrence.scheduled_due_date,
            old_next_due_date=old_next_due,
            new_next_due_date=new_next_due,
            metadata_notes=f"Skipped manually by user on {actual_date}.",
        )
    )
    return occurrence
