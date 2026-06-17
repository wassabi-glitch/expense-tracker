from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import tzinfo

from app import models, schemas, oauth2
from app.session import get_db
from app.scheduler import calculate_next_due_date, get_or_create_budget
from app.timezone import get_effective_user_timezone, today_in_tz
from app.redis_rate_limiter import consume_token_bucket
from app.services.wallet_service import WalletService
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
        retry_count=recurring.retry_count,
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
    recurring = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == recurring_id,
        models.RecurringExpense.owner_id == owner_id,
    ).first()
    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found",
        )
    return recurring


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

    if db.query(models.RecurringExpense).filter(models.RecurringExpense.owner_id == current_user.id).count() >= 50:
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

    # ── WALLET VALIDATION ──────────────────────────────────────────────
    # wallet_id is required in the schema — user must explicitly choose.
    # We just validate it exists, belongs to them, and is active.
    wallet = db.query(models.Wallet).filter(
        models.Wallet.id == expense.wallet_id,
        models.Wallet.owner_id == current_user.id,
    ).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="wallets.not_found",
        )
    if not wallet.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.wallet_archived",
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
        wallet_id=wallet.id,
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

    # ── IMMEDIATE EXPENSE CREATION ────────────────────────────────────
    # If start_date is today or already past, process catch-up payments
    if expense.start_date <= today:
        current_due = expense.start_date
        while current_due <= today:
            budget = get_or_create_budget(
                db, current_user.id, expense.category, current_due.year, current_due.month
            )
            
            # Record Transaction with Bouncer
            WalletService.record_transaction(
                db=db,
                owner_id=current_user.id,
                wallet_id=wallet.id,
                transaction_type=models.TransactionType.EXPENSE,
                amount_delta=-expense.amount,
                category=expense.category,
                title=expense.title,
                description=expense.description,
                budget_id=budget.id if budget else None,
                transaction_date=current_due,
                recurring_id=new_recurring.id,
                idempotency_key=f"recur_{new_recurring.id}_{current_due}"
            )

            old_due = current_due
            current_due = calculate_next_due_date(
                current_due, expense.frequency, new_recurring.original_due_day
            )

            # LOG: PAID event for catch-up
            db.add(models.RecurringEvent(
                recurring_expense_id=new_recurring.id,
                event_type=models.RecurringEventType.PAID,
                target_due_date=old_due,
                old_next_due_date=old_due,
                new_next_due_date=current_due,
                metadata_notes="Immediate catch-up payment on creation"
            ))

            # Hard break for ONE_TIME to avoid infinite loop (since next_due == current_due)
            if expense.frequency == models.RecurringFrequency.ONE_TIME:
                new_recurring.status = models.RecurringStatus.DISABLED
                break

        # current_due is now the first future date
        new_recurring.next_due_date = current_due

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
        models.RecurringExpense.owner_id == current_user.id
    ).order_by(models.RecurringExpense.created_at.desc()).all()

    return [_serialize_recurring_out(r, user_tz) for r in recurring_expenses]


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
    recurring_query = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    )
    recurring = recurring_query.first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    # If wallet_id is being updated, validate it
    update_data = updated_expense.model_dump(exclude_unset=True)
    if "wallet_id" in update_data and update_data["wallet_id"] is not None:
        wallet = db.query(models.Wallet).filter(
            models.Wallet.id == update_data["wallet_id"],
            models.Wallet.owner_id == current_user.id,
        ).first()
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="wallets.not_found",
            )
        if not wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recurring_expenses.wallet_archived",
            )

    recurring_query.update(update_data, synchronize_session=False)
    
    # LOG: UPDATED event (The Diary)
    db.add(models.RecurringEvent(
        recurring_expense_id=id,
        event_type=models.RecurringEventType.UPDATED,
        target_due_date=recurring.next_due_date,
        metadata_notes=f"Template rules updated: {', '.join(update_data.keys())}"
    ))

    db.commit()
    return _serialize_recurring_out(recurring_query.first(), user_tz)


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
    recurring_query = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    )
    recurring = recurring_query.first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    # When re-enabling (moving to ACTIVE), reset the retry count
    old_status = recurring.status
    update_vals = {"status": payload.status}
    if payload.status == models.RecurringStatus.ACTIVE:
        update_vals["retry_count"] = 0
    
    recurring_query.update(update_vals, synchronize_session=False)

    # LOG: Event based on the toggle direction
    event_type = models.RecurringEventType.RESUMED if payload.status == models.RecurringStatus.ACTIVE else models.RecurringEventType.UPDATED
    db.add(models.RecurringEvent(
        recurring_expense_id=id,
        event_type=event_type,
        target_due_date=recurring.next_due_date,
        metadata_notes=f"Status changed from {old_status.value} to {payload.status.value}"
    ))

    db.commit()
    return _serialize_recurring_out(recurring_query.first(), user_tz)


@router.patch("/{id}/skip", response_model=schemas.RecurringExpenseOut)
def skip_recurring_occurrence(
    id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Advance the next_due_date to the next occurrence without creating an expense.
    Guardrail: Only allow skipping if the bill is due or overdue to prevent infinite jumps.
    """
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    
    recurring = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    ).first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    # 1. Guardrail: Allow skipping only if within the current/next cycle boundary.
    # This lets users skip upcoming bills (plan ahead) but prevents "infinite skip" loops.
    today = today_in_tz(user_tz)
    skip_limit = calculate_next_due_date(today, recurring.frequency, recurring.original_due_day)
    
    if recurring.next_due_date > skip_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.cannot_skip_further"
        )

    # Identify which occurrence we are skipping
    target_date = recurring.failing_due_date or recurring.next_due_date
    old_due = recurring.next_due_date

    # 2. Advance the date using the shared logic in the scheduler.
    # We force DAILY to behave like FIXED to prevent time-drift.
    anchor = recurring.next_due_date if (
        recurring.cycle_behavior == models.CycleBehavior.FIXED or 
        recurring.frequency == models.RecurringFrequency.DAILY
    ) else today
    
    new_due_date = calculate_next_due_date(anchor, recurring.frequency, recurring.original_due_day)
    
    # 3. Update the template state
    recurring.next_due_date = new_due_date
    recurring.status = models.RecurringStatus.ACTIVE
    recurring.failing_due_date = None # Skipping heals a failing bill by jumping past it
    recurring.retry_count = 0
    recurring.last_retry_at = None
    
    # RETIREMENT: One-time templates disable themselves after skip
    if recurring.frequency == models.RecurringFrequency.ONE_TIME:
        recurring.status = models.RecurringStatus.DISABLED

    # For FLEXIBLE non-daily schedules, the anchor moves to today's day
    if recurring.cycle_behavior == models.CycleBehavior.FLEXIBLE and recurring.frequency != models.RecurringFrequency.DAILY:
        recurring.original_due_day = today.day
        
    # RETIREMENT: One-time templates disable themselves after success
    if recurring.frequency == models.RecurringFrequency.ONE_TIME:
        recurring.status = models.RecurringStatus.DISABLED

    # LOG: SKIPPED event (The Diary)
    db.add(models.RecurringEvent(
        recurring_expense_id=recurring.id,
        event_type=models.RecurringEventType.SKIPPED,
        target_due_date=target_date,
        old_next_due_date=old_due,
        new_next_due_date=new_due_date,
        metadata_notes=f"Skipped manually by user on {today}"
    ))

    db.commit()
    db.refresh(recurring)
    return _serialize_recurring_out(recurring, user_tz)


@router.post("/{id}/pay-now", response_model=schemas.RecurringExpenseOut)
def pay_now_recurring(
    id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Force create the expense immediately using the assigned wallet.
    Hardened with row locking and guardrails to prevent double-spending.
    """
    rate_headers = enforce_recurring_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    
    # 1. Fetch with Row Locking (with_for_update)
    # This prevents race conditions if the user (or scheduler) tries to touch this row 
    # at the exact same millisecond.
    recurring = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    ).with_for_update().first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    # 2. Guardrails: Is it actually payable right now?
    today = today_in_tz(user_tz)
    is_failed = recurring.failing_due_date is not None
    is_due_today = (recurring.status == models.RecurringStatus.ACTIVE and recurring.next_due_date <= today)

    if not (is_failed or is_due_today):
        # If it's ACTIVE and next_due_date is in the future, it's already paid!
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.already_paid_or_not_due"
        )

    # 3. Resolve and Validate Wallet
    wallet = None
    if recurring.wallet_id:
        wallet = db.query(models.Wallet).filter(
            models.Wallet.id == recurring.wallet_id,
            models.Wallet.owner_id == current_user.id
        ).first()
    else:
        # Fallback for old templates without wallet_id
        wallet = db.query(models.Wallet).filter(
            models.Wallet.owner_id == current_user.id,
            models.Wallet.is_default == True
        ).first()

    if not wallet or not wallet.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.wallet_unavailable"
        )

    # 4. Get/Create Budget
    budget = get_or_create_budget(
        db, current_user.id, recurring.category, today.year, today.month
    )
    if not budget:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.budget_required"
        )
    
    # Identify which occurrence we are paying
    target_date = recurring.failing_due_date or recurring.next_due_date

    # 5. Record the Transaction with Idempotency
    WalletService.record_transaction(
        db=db,
        owner_id=current_user.id,
        wallet_id=wallet.id,
        transaction_type=models.TransactionType.EXPENSE,
        amount_delta=-recurring.amount,
        category=recurring.category,
        title=recurring.title,
        description=recurring.description,
        budget_id=budget.id,
        transaction_date=target_date,
        recurring_id=recurring.id,
        idempotency_key=f"recur_{recurring.id}_{target_date}"
    )

    # 6. Success Logging (The Diary)
    old_due = recurring.next_due_date
    
    if recurring.failing_due_date:
        recurring.failing_due_date = None
        new_due = recurring.next_due_date
    else:
        # Advance the pointer
        anchor = recurring.next_due_date if recurring.cycle_behavior == models.CycleBehavior.FIXED else today
        recurring.next_due_date = calculate_next_due_date(anchor, recurring.frequency, recurring.original_due_day)
        new_due = recurring.next_due_date
        
        # For FLEXIBLE, update the anchor day
        if recurring.cycle_behavior == models.CycleBehavior.FLEXIBLE:
            recurring.original_due_day = today.day

    # Write to Diary
    db.add(models.RecurringEvent(
        recurring_expense_id=recurring.id,
        event_type=models.RecurringEventType.PAID,
        target_due_date=target_date,
        old_next_due_date=old_due,
        new_next_due_date=new_due,
        metadata_notes=f"Paid manually by user on {today}"
    ))

    # 7. Update Template State
    recurring.retry_count = 0
    recurring.last_retry_at = None

    db.commit()
    db.refresh(recurring)
    return _serialize_recurring_out(recurring, user_tz)


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
    
    recurring = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    ).first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    # 1. Validate the new wallet
    new_wallet = db.query(models.Wallet).filter(
        models.Wallet.id == payload.wallet_id,
        models.Wallet.owner_id == current_user.id
    ).first()

    if not new_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="wallets.not_found"
        )
    
    if not new_wallet.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recurring_expenses.wallet_archived"
        )

    old_wallet_id = recurring.wallet_id
    # 2. Update the wallet
    recurring.wallet_id = new_wallet.id

    # 3. Smart Reset: If it was failing, give it a fresh start
    recurring.retry_count = 0
    recurring.last_retry_at = None
    
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
    recurring_query = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.id == id,
        models.RecurringExpense.owner_id == current_user.id
    )
    recurring = recurring_query.first()

    if recurring is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="recurring_expenses.not_found"
        )

    recurring_query.delete(synchronize_session=False)
    db.commit()
