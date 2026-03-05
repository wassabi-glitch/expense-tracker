from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

from zoneinfo import ZoneInfo

from app import models, schemas, oauth2
from app.session import get_db
from app.scheduler import calculate_next_due_date, get_or_create_budget
from app.timezone import today_in_tz
from app.redis_rate_limiter import consume_token_bucket

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


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.RecurringExpenseOut)
def create_recurring_expense(
    expense: schemas.RecurringExpenseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user)
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

    today = today_in_tz(ZoneInfo("Asia/Tashkent"))

    # Initial next_due_date = start_date; may be advanced below if we create now
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
    )
    db.add(new_recurring)
    db.flush()  # Assigns new_recurring.id without committing yet

    # If start_date is today or already past (but still current month per schema),
    # create ALL missed occurrences up to today instead of waiting for the scheduler.
    if expense.start_date <= today:
        current_due = expense.start_date
        while current_due <= today:
            budget = get_or_create_budget(
                db,
                current_user.id,
                expense.category,
                current_due.year,
                current_due.month,
            )
            db.add(models.Expense(
                owner_id=current_user.id,
                title=expense.title,
                amount=expense.amount,
                category=expense.category,
                description=expense.description,
                date=current_due,
                budget_id=budget.id,
            ))
            current_due = calculate_next_due_date(current_due, expense.frequency)

        # current_due is now the first future date — that's our next_due_date
        new_recurring.next_due_date = current_due

    db.commit()
    db.refresh(new_recurring)
    return new_recurring


@router.get("/", response_model=List[schemas.RecurringExpenseOut])
def get_recurring_expenses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user)
):
    recurring_expenses = db.query(models.RecurringExpense).filter(
        models.RecurringExpense.owner_id == current_user.id
    ).order_by(models.RecurringExpense.created_at.desc()).all()
    
    return recurring_expenses


@router.put("/{id}", response_model=schemas.RecurringExpenseOut)
def update_recurring_expense(
    id: int,
    updated_expense: schemas.RecurringExpenseUpdate,
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

    # Only update the fields that were actually sent (PATCH semantics)
    update_data = updated_expense.model_dump(exclude_unset=True)
    recurring_query.update(update_data, synchronize_session=False)
    db.commit()
    return recurring_query.first()


@router.patch("/{id}/active", response_model=schemas.RecurringExpenseOut)
def toggle_recurring_active(
    id: int,
    payload: schemas.RecurringActiveToggle,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_premium_user)
):
    """Toggle the is_active flag for a recurring expense template."""
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

    recurring_query.update({"is_active": payload.is_active}, synchronize_session=False)
    db.commit()
    return recurring_query.first()


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
