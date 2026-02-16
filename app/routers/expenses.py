
import csv
from datetime import date, datetime, timedelta
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.redis_rate_limiter import consume_token_bucket
from app.utils import check_budget_alerts
from .. import models, oauth2, schemas
from ..session import get_db

router = APIRouter(
    prefix="/expenses",  # This means you don't have to type "/expenses" in every route!
    tags=['Expenses']    # This groups them nicely in your /docs page
)

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_csv_cell(value: str) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(CSV_FORMULA_PREFIXES):
        return f"'{text}"
    return text


EXPENSE_WRITE_BUCKET_CAPACITY = 10
EXPENSE_WRITE_REFILL_RATE = 10 / 60  # ~0.1667 tokens/sec => 10 write ops/min sustained


def enforce_expense_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="expenses_write",
        identifier=str(user_id),
        capacity=EXPENSE_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=EXPENSE_WRITE_REFILL_RATE,
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
            detail="Too many expense write requests. Please try again later.",
            headers=headers,
        )
    return headers


@router.post("/", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: schemas.ExpenseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == expense.category,
        models.Budget.is_active == True
    ).first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"you cannot create an expense for {expense.category.value}.Please create a budget first for {expense.category.value} category"
        )

    new_expense = models.Expense(
        **expense.model_dump(), owner_id=current_user.id, owner=current_user)

    db.add(new_expense)
    db.commit()
    check_budget_alerts(db, current_user.id, new_expense.category.value)
    db.refresh(new_expense)
    return new_expense


@router.get("/", response_model=List[schemas.ExpenseOut])
def get_expenses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = None,
    sort: str = "newest",
    category: Optional[str] = None,
    time_range: Optional[str] = None,  # past_week, past_month, last_3_months
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    # Base query with Eager Loading for performance
    expenses_query = db.query(models.Expense).options(
        joinedload(models.Expense.owner)
    ).filter(models.Expense.owner_id == current_user.id)

    # 1. Handle Pre-defined Time Range Filters
    today = datetime.now()
    if time_range == "past_week":
        start_date = (today - timedelta(days=7)).date()
    elif time_range == "past_month":
        start_date = (today - timedelta(days=30)).date()
    elif time_range == "last_3_months":
        start_date = (today - timedelta(days=90)).date()

    # 2. Apply Date Filters (Used by both time_range and custom dates)
    if start_date:
        expenses_query = expenses_query.filter(
            models.Expense.date >= start_date)
    if end_date:
        expenses_query = expenses_query.filter(models.Expense.date <= end_date)

    # 3. Category Filter
    if category:
        expenses_query = expenses_query.filter(
            models.Expense.category == category)

    # 4. Search Filter (Case-insensitive)
    if search:
        expenses_query = expenses_query.filter(
            func.lower(models.Expense.title).contains(search.lower())
        )

    # 5. Sorting Logic
    if sort == "expensive":
        expenses_query = expenses_query.order_by(models.Expense.amount.desc())
    elif sort == "cheapest":
        expenses_query = expenses_query.order_by(models.Expense.amount.asc())
    elif sort == "oldest":
        expenses_query = expenses_query.order_by(
            models.Expense.date.asc(),
            models.Expense.created_at.asc(),
        )
    else:
        # Default: Newest first by expense date, then creation time for stable ordering
        expenses_query = expenses_query.order_by(
            models.Expense.date.desc(),
            models.Expense.created_at.desc())

    # 6. Pagination and Execution
    expenses = expenses_query.offset(skip).limit(limit).all()

    return expenses


@router.get("/export")
def export_csv_expense(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user),
                       category: Optional[str] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None,
                       sort: str = "newest"):

    expenses_query = db.query(models.Expense).options(
        joinedload(models.Expense.owner)
    ).filter(models.Expense.owner_id == current_user.id)

    if start_date:
        expenses_query = expenses_query.filter(
            models.Expense.date >= start_date)
    if end_date:
        expenses_query = expenses_query.filter(models.Expense.date <= end_date)

    if category:
        expenses_query = expenses_query.filter(
            models.Expense.category == category)

    if sort == "oldest":
        expenses_query = expenses_query.order_by(
            models.Expense.date.asc(),
            models.Expense.created_at.asc(),
        )
    elif sort == "newest":
        expenses_query = expenses_query.order_by(
            models.Expense.date.desc(),
            models.Expense.created_at.desc(),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort. Use 'newest' or 'oldest'."
        )

    expenses = expenses_query.all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["date", "title", "amount", "category", "description"])

    for exp in expenses:
        writer.writerow([
            exp.date,
            sanitize_csv_cell(exp.title),
            exp.amount,
            exp.category.value if hasattr(
                exp.category, "value") else exp.category,
            sanitize_csv_cell(exp.description)
        ])

    output.seek(0)

    headers = {"Content-Disposition": "attachment; filename=expenses.csv"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)


@router.get("/{id}", response_model=schemas.ExpenseOut)
def get_expense(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    # expense = db.query(models.Expense).filter(
    #     models.Expense.id == id and models.Expense.owner_id == current_user.id).first()

    expense = db.query(models.Expense).filter(models.Expense.id == id).first()

    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Expense with id:{id} not found ")
    if expense.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Not authorized to perform requested action")

    return expense


@router.put("/{id}", response_model=schemas.ExpenseOut)
def update_expense(
    id: int,
    expense: schemas.ExpenseUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    # Find the expense
    db_expense_query = db.query(models.Expense).filter(
        models.Expense.id == id)
    db_expense = db_expense_query.first()

    if not db_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Expense with id:{id} not found")

    if db_expense.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Not authorized to perform requested action")
        # Update the expense
    db_expense_query.update(expense.model_dump(
        exclude_unset=True), synchronize_session=False)
    db.commit()

    check_budget_alerts(db, current_user.id, expense.category.value)
    db.commit()

    db.refresh(db_expense)
    return db_expense


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    # Find the expense
    db_expense_query = db.query(models.Expense).filter(
        models.Expense.id == id)

    db_expense = db_expense_query.first()

    if not db_expense:
        raise HTTPException(
            status_code=404, detail=f"Expense with id:{id} not found")

    if db_expense.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Not authorized to perform requested action")

    db.delete(db_expense)
    db.commit()
    check_budget_alerts(db, current_user.id, db_expense.category.value)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
