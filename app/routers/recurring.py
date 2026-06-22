from fastapi import APIRouter, Depends, HTTPException, status, Response
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from typing import List
from datetime import tzinfo

from app import models, schemas, oauth2
from app.session import get_db
from app.services.recurring_schedule_service import calculate_next_due_date
from app.timezone import get_effective_user_timezone, today_in_tz
from app.redis_rate_limiter import consume_token_bucket
from app.services.recurring_occurrence_service import (
    apply_template_rule_updates,
    archive_template,
    create_pending_due_occurrence,
    get_owned_template,
    set_template_active,
    validate_preferred_wallet,
    notify_pending_confirmation_once,
)
from app.services.recurring_projection_service import (
    build_recurring_projection_output,
    validate_projection_horizons,
)

RECURRING_WRITE_BUCKET_CAPACITY = 10
RECURRING_WRITE_REFILL_RATE = 10 / 60


def enforce_recurring_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="recurring_write",
        identifier=str(user_id),
        capacity=RECURRING_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=RECURRING_WRITE_REFILL_RATE,
    )
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="recurring_expenses.write_rate_limited",
            headers=headers,
        )
    return headers


def _serialize_recurring_out(
    recurring: models.RecurringExpense,
    user_tz: tzinfo,
) -> schemas.RecurringExpenseOut:
    days_until_due = (recurring.next_due_date - today_in_tz(user_tz)).days
    return schemas.RecurringExpenseOut(
        id=recurring.id,
        owner_id=recurring.owner_id,
        title=recurring.title,
        amount=recurring.amount,
        category=recurring.category,
        description=recurring.description,
        frequency=recurring.frequency,
        start_date=recurring.start_date,
        next_due_date=recurring.next_due_date,
        days_until_due=days_until_due,
        status=recurring.status,
        wallet_id=recurring.wallet_id,
        cycle_behavior=recurring.cycle_behavior,
        original_due_day=recurring.original_due_day,
        archived_at=recurring.archived_at,
        paused_at=recurring.paused_at,
        created_at=recurring.created_at,
        owner=recurring.owner,
    )


router = APIRouter(
    prefix="/recurring",
    tags=["Recurring Expenses"]
)


def get_current_premium_user(current_user: models.User = Depends(oauth2.get_current_user)):
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="recurring_expenses.premium_required"
        )
    return current_user


def _get_owned_recurring_or_404(
    db: Session,
    owner_id: int,
    recurring_id: int,
) -> models.RecurringExpense:
    return get_owned_template(db, owner_id, recurring_id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.RecurringExpenseOut)
def create_recurring_expense(
    expense: schemas.RecurringExpenseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Create a recurring expense template.

    Scenario table:
    ┌──────────────────────────────┬────────────────────────────────────────────────┐
    │ start_date                   │ Behaviour                                      │
    ├──────────────────────────────┼────────────────────────────────────────────────┤
    │ past/today (current month)   │ Create first real expense NOW, advance due date│
    │ future (this or next month)  │ Just save template; scheduler fires on due date│
    └──────────────────────────────┴────────────────────────────────────────────────┘
    """
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    active_template_count = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.owner_id == current_user.id,
        models.RecurringExpense.archived_at.is_(None),
    ).count()
    if active_template_count >= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.max_limit_reached"
        )

    today = today_in_tz(user_tz)
    first_of_month = today.replace(day=1)
    if expense.start_date < first_of_month:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.start_date_before_current_month",
        )

    wallet = validate_preferred_wallet(
        db,
        current_user.id,
        expense.wallet_id,
    )

    # ── CREATE THE TEMPLATE ───────────────────────────────────────────
    next_due_date = expense.start_date

    new_recurring = models.RecurringExpense(
        owner_id=current_user.id,
        title=expense.title,
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        frequency=expense.frequency,
        start_date=expense.start_date,
        next_due_date=next_due_date,
        wallet_id=wallet.id if wallet is not None else None,
        cycle_behavior=expense.cycle_behavior,
        status=models.RecurringStatus.ACTIVE,
        original_due_day=expense.start_date.day,
    )
    db.add(new_recurring)
    db.flush()  # Assigns new_recurring.id

    # LOG: CREATED event (The Diary)
    db.add(models.RecurringEvent(
        recurring_expense_id=new_recurring.id,
        event_type=models.RecurringEventType.CREATED,
        target_due_date=expense.start_date,
        new_next_due_date=next_due_date,
        metadata_notes=f"Template created with cycle {expense.cycle_behavior}"
    ))

    if expense.start_date <= today:
        occurrence = create_pending_due_occurrence(db, new_recurring, local_today=today)
        notify_pending_confirmation_once(db, new_recurring, occurrence)

    db.commit()
    db.refresh(new_recurring)
    return _serialize_recurring_out(new_recurring, user_tz)


@router.get("/", response_model=List[schemas.RecurringExpenseOut])
def get_recurring_expenses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    recurring_expenses = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.owner_id == current_user.id,
        models.RecurringExpense.archived_at.is_(None),
    ).order_by(models.RecurringExpense.created_at.desc()).all()

    return [_serialize_recurring_out(r, user_tz) for r in recurring_expenses]


@router.get("/occurrences", response_model=List[schemas.RecurringOccurrenceOut])
def list_recurring_occurrences(
    occurrence_status: models.RecurringOccurrenceStatus | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
):
    query = db.query(models.RecurringOccurrence).filter(
        models.RecurringOccurrence.owner_id == current_user.id,
    )
    if occurrence_status is not None:
        query = query.filter(models.RecurringOccurrence.status == occurrence_status)
    return query.order_by(
        models.RecurringOccurrence.scheduled_due_date.desc(),
        models.RecurringOccurrence.id.desc(),
    ).all()


@router.post("/occurrences/{id}/confirm", response_model=schemas.RecurringOccurrenceOut)
def confirm_occurrence(
    id: int,
    payload: schemas.RecurringOccurrenceConfirmIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    from app.services.recurring_occurrence_service import confirm_recurring_occurrence
    
    occurrence = confirm_recurring_occurrence(
        db=db,
        owner_id=current_user.id,
        occurrence_id=id,
        actual_amount=payload.actual_amount,
        actual_date=payload.actual_date,
        wallet_allocations=[alloc.model_dump() for alloc in payload.wallet_allocations],
        update_template_amount=payload.update_template_amount,
        local_today=today_in_tz(user_tz),
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.get("/{id}/events", response_model=List[schemas.RecurringEventOut])
def get_recurring_events(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Fetch the full lifecycle audit log (The Diary) for a specific template."""
    recurring = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    ).first()
    
    if not recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )
        
    return db.query(models.RecurringEvent).filter(
        models.RecurringEvent.recurring_expense_id == id
    ).order_by(models.RecurringEvent.created_at.asc()).all()


@router.get("/{id}/projections", response_model=schemas.RecurringProjectionOut)
def get_recurring_projections(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    recurring = _get_owned_recurring_or_404(db, current_user.id, id)
    return build_recurring_projection_output(
        recurring,
        anchor_date=today_in_tz(user_tz),
    )


@router.post("/{id}/projections/preview", response_model=schemas.RecurringProjectionOut)
def preview_recurring_projections(
    id: int,
    payload: schemas.RecurringProjectionHorizonListIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    recurring = _get_owned_recurring_or_404(db, current_user.id, id)
    return build_recurring_projection_output(
        recurring,
        anchor_date=today_in_tz(user_tz),
        ad_hoc_horizons=payload.horizons,
    )


@router.put("/{id}/projection-horizons", response_model=schemas.RecurringProjectionOut)
def save_recurring_projection_horizons(
    id: int,
    payload: schemas.RecurringProjectionHorizonListIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    recurring = _get_owned_recurring_or_404(db, current_user.id, id)
    horizons = validate_projection_horizons(recurring.frequency, payload.horizons)
    recurring.custom_projection_horizons = horizons
    db.commit()
    db.refresh(recurring)
    return build_recurring_projection_output(
        recurring,
        anchor_date=today_in_tz(user_tz),
    )


@router.put("/{id}", response_model=schemas.RecurringExpenseOut)
def update_recurring_expense(
    id: int,
    updated_expense: schemas.RecurringExpenseUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    recurring = get_owned_template(db, current_user.id, id, lock=True)
    update_data = updated_expense.model_dump(exclude_unset=True)
    next_wallet_id = update_data.get("wallet_id", recurring.wallet_id)
    validate_preferred_wallet(db, current_user.id, next_wallet_id)

    apply_template_rule_updates(db, recurring, update_data)
    
    # LOG: UPDATED event (The Diary)
    db.add(models.RecurringEvent(
        recurring_expense_id=id,
        event_type=models.RecurringEventType.UPDATED,
        target_due_date=recurring.next_due_date,
        metadata_notes=f"Template rules updated: {', '.join(update_data.keys())}"
    ))

    db.commit()
    db.refresh(recurring)
    return _serialize_recurring_out(recurring, user_tz)


@router.patch("/{id}/toggle", response_model=schemas.RecurringExpenseOut)
def toggle_recurring_status(
    id: int,
    payload: schemas.RecurringStatusToggle,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """Toggle the status between ACTIVE and DISABLED."""
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    recurring = get_owned_template(db, current_user.id, id, lock=True)
    old_status = recurring.status
    set_template_active(
        recurring,
        active=payload.status == models.RecurringStatus.ACTIVE,
        local_today=today_in_tz(user_tz),
    )

    # LOG: Event based on the toggle direction
    event_type = models.RecurringEventType.RESUMED if payload.status == models.RecurringStatus.ACTIVE else models.RecurringEventType.UPDATED
    db.add(models.RecurringEvent(
        recurring_expense_id=id,
        event_type=event_type,
        target_due_date=recurring.next_due_date,
        metadata_notes=f"Status changed from {old_status.value} to {payload.status.value}"
    ))

    db.commit()
    db.refresh(recurring)
    return _serialize_recurring_out(recurring, user_tz)


@router.post("/occurrences/{id}/skip", response_model=schemas.RecurringOccurrenceOut)
def skip_occurrence_endpoint(
    id: int,
    payload: schemas.RecurringOccurrenceSkipIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    from app.services.recurring_occurrence_service import skip_occurrence
    
    occurrence = skip_occurrence(
        db=db,
        owner_id=current_user.id,
        occurrence_id=id,
        actual_date=payload.actual_date,
        local_today=today_in_tz(user_tz),
    )
    db.commit()
    db.refresh(occurrence)
    return occurrence


@router.patch("/{id}/change-wallet", response_model=schemas.RecurringExpenseOut)
def change_recurring_wallet(
    id: int,
    payload: schemas.RecurringChangeWallet,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Swap the wallet for a recurring template. 
    If the template was failing (RETRYING/PAUSED), it automatically resets to ACTIVE.
    """
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    
    recurring = get_owned_template(db, current_user.id, id, lock=True)
    new_wallet = validate_preferred_wallet(
        db,
        current_user.id,
        payload.wallet_id,
    )
    assert new_wallet is not None

    old_wallet_id = recurring.wallet_id
    # 2. Update the wallet
    recurring.wallet_id = new_wallet.id
    
    # LOG: UPDATED event (The Diary)
    db.add(models.RecurringEvent(
        recurring_expense_id=id,
        event_type=models.RecurringEventType.UPDATED,
        target_due_date=recurring.next_due_date,
        metadata_notes=f"Wallet changed from {old_wallet_id} to {new_wallet.id}"
    ))

    db.commit()
    db.refresh(recurring)
    return _serialize_recurring_out(recurring, user_tz)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_expense(
    id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user)
):
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    recurring = get_owned_template(db, current_user.id, id, lock=True)
    archive_template(recurring)
    db.commit()
