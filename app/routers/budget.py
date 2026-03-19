from datetime import date, tzinfo
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
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
    # Compute spent grouped by budget_id once, then apply rollover projection in memory.
    spent_rows = (
        db.query(
            models.Expense.budget_id,
            func.coalesce(func.sum(models.Expense.amount), 0).label("spent"),
        )
        .join(models.Budget, models.Budget.id == models.Expense.budget_id)
        .filter(models.Budget.owner_id == current_user.id)
        .group_by(models.Expense.budget_id)
        .all()
    )
    spent_by_budget_id = {int(row.budget_id): int(row.spent or 0) for row in spent_rows}

    budgets = (
        db.query(models.Budget)
        .filter(models.Budget.owner_id == current_user.id)
        .order_by(
            models.Budget.category.asc(),
            models.Budget.budget_year.asc(),
            models.Budget.budget_month.asc(),
        )
        .all()
    )

    if not budgets:
        return []

    budgets_out: list[schemas.BudgetOut] = []
    by_category: dict[str, list[models.Budget]] = {}
    for budget in budgets:
        by_category.setdefault(str(budget.category), []).append(budget)

    is_rollover_enabled = bool(
        current_user.is_premium
        and current_user.profile is not None
        and current_user.profile.budget_rollover_enabled
    )

    for _category, items in by_category.items():
        # Items are already ordered by year/month asc from query.
        rollover_for_month = 0
        prev_year = None
        prev_month = None

        for budget in items:
            spent = int(spent_by_budget_id.get(int(budget.id), 0))
            base_limit = int(budget.monthly_limit or 0)

            if is_rollover_enabled and prev_year is not None and prev_month is not None:
                expected_next_year = prev_year + 1 if prev_month == 12 else prev_year
                expected_next_month = 1 if prev_month == 12 else prev_month + 1
                # If there is a gap in configured budget months, restart the rollover chain.
                if budget.budget_year != expected_next_year or budget.budget_month != expected_next_month:
                    rollover_for_month = 0
            else:
                rollover_for_month = 0

            effective_limit = base_limit + rollover_for_month

            budget_out = schemas.BudgetOut.model_validate(budget)
            budget_out.spent = spent
            budget_out.rollover_amount = rollover_for_month if is_rollover_enabled else 0
            budget_out.effective_monthly_limit = effective_limit if is_rollover_enabled else base_limit
            budgets_out.append(budget_out)

            unused_positive = max(effective_limit - spent, 0)
            rollover_for_month = unused_positive if is_rollover_enabled else 0
            prev_year = int(budget.budget_year)
            prev_month = int(budget.budget_month)

    budgets_out.sort(
        key=lambda b: (
            int(b.budget_year),
            int(b.budget_month),
            str(b.category),
        ),
        reverse=True,
    )
    return budgets_out


@router.get("/item", response_model=schemas.BudgetOut)
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


@router.patch("/item", response_model=schemas.BudgetOut)
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


@router.delete("/item", status_code=status.HTTP_204_NO_CONTENT)
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
