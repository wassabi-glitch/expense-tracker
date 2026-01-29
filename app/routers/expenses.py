
import csv
from datetime import date, datetime, timedelta
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.utils import check_budget_alerts
from .. import models, oauth2, schemas
from ..session import get_db

router = APIRouter(
    prefix="/expenses",  # This means you don't have to type "/expenses" in every route!
    tags=['Expenses']    # This groups them nicely in your /docs page
)


@router.post("/", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
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
    else:
        # Default: Newest first based on creation time
        expenses_query = expenses_query.order_by(
            models.Expense.created_at.desc())

    # 6. Pagination and Execution
    expenses = expenses_query.offset(skip).limit(limit).all()

    return expenses


@router.get("/this-month-stats", response_model=schemas.ExpenseStats)
def get_expense_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):

    today = date.today()
    current_month_start = today.replace(day=1)
    # 1. Base Stats (Monthly stats)
    stats_query = db.query(
        func.sum(models.Expense.amount).label("total"),
        func.avg(models.Expense.amount).label("average"),
        func.max(models.Expense.amount).label("max"),
        func.min(models.Expense.amount).label("min")
    ).filter(models.Expense.owner_id == current_user.id,
             models.Expense.date >= current_month_start)

    # 2. Setup date cutoff if 'days' is provided
    # cutoff_date = None
    # if days > 0:
    #     cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    #     # Apply filter to the global stats
    #     stats_query = stats_query.filter(
    #         models.Expense.date >= cutoff_date)

    # 3. Category Breakdown Query (The "Deep" Join)
    # Note: We put the date filter INSIDE the outerjoin condition
    # so that categories with 0 expenses still show up.
    category_breakdown_query = db.query(
        models.Budget.category,
        models.Budget.monthly_limit,
        func.coalesce(func.sum(models.Expense.amount), 0).label("total"),
        func.count(models.Expense.id).label("count")
    ).outerjoin(
        models.Expense,
        (models.Expense.category == models.Budget.category) &
        (models.Expense.owner_id == models.Budget.owner_id) &
        ((models.Expense.date >= current_month_start))
    ).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.is_active == True
    ).group_by(
        models.Budget.category,
        models.Budget.monthly_limit
    )

    # 4. Execute Queries
    stats = stats_query.first()
    category_breakdown = category_breakdown_query.all()

    # 5. Build the Enhanced Breakdown
    enhanced_breakdown = []

    # Unpacking order must match the db.query() columns exactly:
    # 1. category, 2. monthly_limit, 3. total, 4. count
    for category, monthly_limit, total, count in category_breakdown:
        category_name = category.value if hasattr(
            category, "value") else category

        percentage_used = (round(total / monthly_limit * 100, 2)
                           ) if monthly_limit > 0 else 0
        if percentage_used >= 100:
            budget_status = schemas.BudgetStatus.Over_limit
        elif percentage_used >= 90:
            budget_status = schemas.BudgetStatus.Critical
        else:
            budget_status = schemas.BudgetStatus.Healthy

        enhanced_breakdown.append({
            "category": category_name,
            "total": float(total),
            "count": int(count),
            "budget_limit": float(monthly_limit),
            "remaining": float(max(0, monthly_limit - total)),
            "percentage_used": round(percentage_used, 1),
            "is_over_budget": total > monthly_limit,
            "budget_status": budget_status,
        })

    # 6. Final Return (Indented correctly outside the for-loop)
    return {
        "total_expenses": stats.total or 0,
        "average_expenses": stats.average or 0,
        "max_expenses": stats.max or 0,
        "min_expenses": stats.min or 0,
        "category_breakdown": enhanced_breakdown
    }


@router.get("/export")
def export_csv_expense(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user),
                       category: Optional[str] = None,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None):

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

    expenses = expenses_query.all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["date", "title", "amount", "category", "description"])

    for exp in expenses:
        writer.writerow([
            exp.date,
            exp.title,
            exp.amount,
            exp.category.value if hasattr(
                exp.category, "value") else exp.category,
            exp.description or ""
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
def update_expense(id: int, expense: schemas.ExpenseUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
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
def delete_expense(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
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
