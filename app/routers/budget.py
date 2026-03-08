from datetime import date, tzinfo
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import List

from .. import oauth2
from .. import models, schemas
from ..session import get_db
from app.redis_rate_limiter import consume_token_bucket
from app.timezone import get_effective_user_timezone, today_in_tz


router = APIRouter(
    prefix="/budgets",
    tags=["Budgets"]
)

BUDGET_WRITE_BUCKET_CAPACITY = 10
# ~0.1667 tokens/sec => 10 write ops/min sustained
BUDGET_WRITE_REFILL_RATE = 10 / 60


def enforce_budget_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="budgets_write",
        identifier=str(user_id),
        capacity=BUDGET_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=BUDGET_WRITE_REFILL_RATE,
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
            detail="budgets.write_rate_limited",
            headers=headers,
        )
    return headers


def validate_budget_month_window(
    budget_year: int,
    budget_month: int,
    user_tz: tzinfo,
) -> None:
    candidate = date(budget_year, budget_month, 1)
    min_allowed = date(schemas.MIN_BUDGET_YEAR, 1, 1)
    today_local = today_in_tz(user_tz)
    max_allowed = date(
        today_local.year + schemas.MAX_BUDGET_YEARS_AHEAD,
        today_local.month,
        1,
    )

    if candidate < min_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budgets.month_too_early",
        )

    if candidate > max_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budgets.month_too_far_in_future",
        )


@router.post("/", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: schemas.BudgetCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_budget_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    validate_budget_month_window(
        budget_year=budget.budget_year,
        budget_month=budget.budget_month,
        user_tz=user_tz,
    )

    existing_budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == budget.category,
        models.Budget.budget_year == budget.budget_year,
        models.Budget.budget_month == budget.budget_month,
    ).first()

    if existing_budget:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="budgets.already_exists",
        )

    new_budget = models.Budget(
        **budget.model_dump(),
        owner_id=current_user.id,
        owner=current_user,
    )

    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget


@router.get("/", response_model=List[schemas.BudgetOut])
def get_budgets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    from sqlalchemy import func
    
    # We join Budget and Expense on budget_id. 
    # This computes total expenses linked to each budget.
    results = (
        db.query(
            models.Budget,
            func.coalesce(func.sum(models.Expense.amount), 0).label("spent")
        )
        .outerjoin(
            models.Expense,
            (models.Budget.id == models.Expense.budget_id)
        )
        .filter(models.Budget.owner_id == current_user.id)
        .group_by(models.Budget.id)
        .order_by(
            models.Budget.budget_year.desc(),
            models.Budget.budget_month.desc(),
            models.Budget.category.asc(),
        )
        .all()
    )
    
    budgets_out = []
    for b, spent in results:
        # We need to explicitly set spent because models.Budget doesn't have it natively
        b_out = schemas.BudgetOut.model_validate(b)
        b_out.spent = int(spent)
        budgets_out.append(b_out)
        
    return budgets_out


@router.get("/{budget_year}/{budget_month}/{category}", response_model=schemas.BudgetOut)
def get_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == category,
        models.Budget.budget_year == budget_year,
        models.Budget.budget_month == budget_month,
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="budgets.not_found",
        )

    return budget


@router.patch("/{budget_year}/{budget_month}/{category}", response_model=schemas.BudgetOut)
def update_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    budget_update: schemas.BudgetUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_budget_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == category,
        models.Budget.budget_year == budget_year,
        models.Budget.budget_month == budget_month,
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="budgets.not_found",
        )

    budget.monthly_limit = budget_update.monthly_limit

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_year}/{budget_month}/{category}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_budget_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == category,
        models.Budget.budget_year == budget_year,
        models.Budget.budget_month == budget_month,
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="budgets.not_found",
        )

    first_day = date(budget_year, budget_month, 1)
    if budget_month == 12:
        next_month_first_day = date(budget_year + 1, 1, 1)
    else:
        next_month_first_day = date(budget_year, budget_month + 1, 1)

    has_dependent_expense = db.query(models.Expense.id).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.category == category,
        models.Expense.date >= first_day,
        models.Expense.date < next_month_first_day,
    ).first()

    if has_dependent_expense:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="budgets.has_linked_expenses",
        )

    db.delete(budget)
    db.commit()
    return
