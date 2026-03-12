from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, tzinfo
from typing import List

from app import schemas
from app.session import get_db
from app.timezone import get_effective_user_timezone, today_in_tz
from .. import models, oauth2

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

MIN_ANALYTICS_DATE = date(2020, 1, 1)


@router.get("/this-month-stats", response_model=schemas.ExpenseStats)
def get_this_month_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    current_month_start = today.replace(day=1)

    stats_query = db.query(
        func.sum(models.Expense.amount).label("total"),
        func.avg(models.Expense.amount).label("average"),
        func.max(models.Expense.amount).label("max"),
        func.min(models.Expense.amount).label("min"),
    ).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.date >= current_month_start,
    )

    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    category_breakdown_query = db.query(
        models.Budget.category,
        models.Budget.monthly_limit,
        func.coalesce(func.sum(models.Expense.amount), 0).label("total"),
        func.count(models.Expense.id).label("count"),
    ).outerjoin(
        models.Expense,
        (models.Expense.budget_id == models.Budget.id)
        & (models.Expense.owner_id == current_user.id)
        & (models.Expense.date >= current_month_start)
        & (models.Expense.date < next_month_start),
    ).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.budget_year == today.year,
        models.Budget.budget_month == today.month,
    ).group_by(
        models.Budget.category,
        models.Budget.monthly_limit,
    )

    stats = stats_query.first()
    category_breakdown = category_breakdown_query.all()

    enhanced_breakdown = []
    for category, monthly_limit, total, count in category_breakdown:
        category_name = category.value if hasattr(
            category, "value") else category
        percentage_used = round((total / monthly_limit)
                                * 100, 2) if monthly_limit > 0 else 0

        if percentage_used >= 100:
            budget_status = schemas.BudgetStatus.Over_limit
        elif percentage_used >= 90:
            budget_status = schemas.BudgetStatus.High_risk
        elif percentage_used >= 70:
            budget_status = schemas.BudgetStatus.Warning
        else:
            budget_status = schemas.BudgetStatus.On_track

        enhanced_breakdown.append(
            {
                "category": category_name,
                "total": int(total),
                "count": int(count),
                "budget_limit": int(monthly_limit),
                "remaining": int(max(0, monthly_limit - total)),
                "percentage_used": round(percentage_used, 1),
                "is_over_budget": total > monthly_limit,
                "budget_status": budget_status,
            }
        )

    return {
        "total_expenses": int(stats.total or 0),
        "average_expenses": stats.average or 0,
        "max_expenses": int(stats.max or 0),
        "min_expenses": int(stats.min or 0),
        "category_breakdown": enhanced_breakdown,
    }


@router.get("/dashboard-summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    current_month_start = today.replace(day=1)

    spent = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0))
        .filter(
            models.Expense.owner_id == current_user.id,
            models.Expense.date >= current_month_start,
            models.Expense.date <= today,
        )
        .scalar()
    ) or 0

    month_income_total, _month_income_count = (
        db.query(
            func.coalesce(func.sum(models.IncomeEntry.amount), 0),
            func.count(models.IncomeEntry.id),
        )
        .filter(
            models.IncomeEntry.owner_id == current_user.id,
            models.IncomeEntry.date >= current_month_start,
            models.IncomeEntry.date <= today,
        )
        .first()
    )
    income = int(month_income_total or 0)
    spent_int = int(spent)
    remaining = income - spent_int

    overall_income_total = (
        db.query(func.coalesce(func.sum(models.IncomeEntry.amount), 0))
        .filter(models.IncomeEntry.owner_id == current_user.id)
        .scalar()
    ) or 0
    overall_spent_total = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0))
        .filter(models.Expense.owner_id == current_user.id)
        .scalar()
    ) or 0
    initial_balance = int(getattr(current_user.profile, "initial_balance", 0) or 0)
    overall_balance = initial_balance + int(overall_income_total) - int(overall_spent_total)

    elapsed_days = max(today.day, 1)
    daily_average = round(spent_int / elapsed_days) if elapsed_days else 0

    return {
        "income": income,
        "spent": spent_int,
        "remaining": int(remaining),
        "daily_average": int(daily_average),
        "overall_balance": int(overall_balance),
    }


@router.get("/history", response_model=schemas.AnalyticsHistory)
def get_historical_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    stats = db.query(
        func.sum(models.Expense.amount).label("total_spent"),
        func.avg(models.Expense.amount).label("average_transaction"),
        func.count(models.Expense.id).label("total_transactions"),
        func.min(models.Expense.date).label("first_expense_date")
    ).filter(
        models.Expense.owner_id == current_user.id
    ).first()

    return {
        "total_spent_lifetime": int(stats.total_spent or 0),
        "average_transaction": round(stats.average_transaction or 0),
        "total_transaction": stats.total_transactions or 0,
        "member_since": stats.first_expense_date
    }


@router.get("/daily-trend", response_model=List[schemas.DailyTrendItem])
def get_daily_trend(
    days: int = 30,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="analytics.range_both_or_days_required"
        )

    if start_date and end_date:
        if start_date < MIN_ANALYTICS_DATE or end_date < MIN_ANALYTICS_DATE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.date_too_early"
            )
        if end_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.end_date_in_future"
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.start_after_end"
            )
        if (end_date - start_date).days + 1 > 366:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.range_too_large"
            )
    else:
        if days > 366:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.range_too_large"
            )
        if days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.days_min_1"
            )
        start_date = today - timedelta(days=days - 1)
        end_date = today

    first_expense = db.query(func.min(models.Expense.date)).filter(
        models.Expense.owner_id == current_user.id
    ).scalar()

    if first_expense:
        user_start_date = min(current_user.created_at.date(), first_expense)
    else:
        user_start_date = current_user.created_at.date()

    if start_date < user_start_date:
        start_date = user_start_date

    results = db.query(
        models.Expense.date,
        func.sum(models.Expense.amount).label("total")
    ).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.date >= start_date,
        models.Expense.date <= end_date,
    ).group_by(
        models.Expense.date
    ).order_by(
        models.Expense.date.asc()
    ).all()

    spending_dict = {row.date: row.total for row in results}
    filled_data = []

    actual_days_count = (end_date - start_date).days + 1

    for i in range(actual_days_count):
        current_date = start_date + timedelta(days=i)
        amount = spending_dict.get(current_date, 0)

        filled_data.append({
            "date": current_date,
            "amount": int(amount)
        })

    return filled_data


@router.get("/month-to-date-trend", response_model=List[schemas.DailyTrendItem])
def get_month_to_date_trend(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    month_start = today.replace(day=1)

    first_expense = db.query(func.min(models.Expense.date)).filter(
        models.Expense.owner_id == current_user.id
    ).scalar()

    if first_expense:
        user_start_date = min(current_user.created_at.date(), first_expense)
    else:
        user_start_date = current_user.created_at.date()

    start_date = max(month_start, user_start_date)
    end_date = today

    results = db.query(
        models.Expense.date,
        func.sum(models.Expense.amount).label("total")
    ).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.date >= start_date,
        models.Expense.date <= end_date,
    ).group_by(
        models.Expense.date
    ).order_by(
        models.Expense.date.asc()
    ).all()

    spending_dict = {row.date: row.total for row in results}
    filled_data = []
    actual_days_count = (end_date - start_date).days + 1

    for i in range(actual_days_count):
        current_date = start_date + timedelta(days=i)
        amount = spending_dict.get(current_date, 0)
        filled_data.append({
            "date": current_date,
            "amount": int(amount)
        })

    return filled_data


@router.get("/category-breakdown", response_model=List[schemas.CategoryBreakdownItem])
def get_category_breakdown(
    days: int = 30,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)

    if (start_date is None) ^ (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="analytics.range_both_required",
        )

    if start_date and end_date:
        if start_date < MIN_ANALYTICS_DATE or end_date < MIN_ANALYTICS_DATE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.date_too_early",
            )
        if end_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.end_date_in_future",
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.start_after_end",
            )
    elif days is not None:
        if days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.days_min_1",
            )
        if days > 366:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="analytics.range_too_large",
            )
        start_date = today - timedelta(days=days - 1)
        end_date = today

    query = db.query(
        models.Expense.category,
        func.coalesce(func.sum(models.Expense.amount), 0).label("total"),
        func.count(models.Expense.id).label("count"),
    ).filter(
        models.Expense.owner_id == current_user.id
    )

    if start_date:
        query = query.filter(models.Expense.date >= start_date)
    if end_date:
        query = query.filter(models.Expense.date <= end_date)

    results = query.group_by(
        models.Expense.category
    ).order_by(
        func.sum(models.Expense.amount).desc()
    ).all()

    return [
        {
            "category": row.category.value if hasattr(row.category, "value") else row.category,
            "total": int(row.total or 0),
            "count": int(row.count or 0),
        }
        for row in results
    ]
