from datetime import date, timedelta, tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app import models, oauth2, schemas
from app.savings_balances import get_net_position, get_total_balance
from app.services.budget_service import get_budget_spent_amount, normal_monthly_budget_impact_filters
from app.session import get_db
from app.timezone import get_effective_user_timezone, today_in_tz

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

MIN_ANALYTICS_DATE = date(2020, 1, 1)


def _expense_signed_amount():
    return case(
        (
            and_(
                models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
                models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            ),
            models.EntityLedger.amount,
        ),
        (
            and_(
                models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
                models.FinancialEvent.event_type == models.TransactionType.REFUND,
            ),
            -models.EntityLedger.amount,
        ),
        else_=0,
    )


def _expense_base_query(db: Session, user_id: int):
    return (
        db.query(models.EntityLedger, models.FinancialEvent)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.EntityLedger.category.isnot(None),
        )
    )


def _income_total_for_range(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
) -> int:
    total = (
        db.query(func.coalesce(func.sum(models.WalletLedger.amount), 0))
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.event_type == models.TransactionType.INCOME,
            models.FinancialEvent.date >= start_date,
            models.FinancialEvent.date <= end_date,
        )
        .scalar()
        or 0
    )
    return int(total)


@router.get("/this-month-stats", response_model=schemas.ExpenseStats)
def get_this_month_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    current_month_start = today.replace(day=1)
    next_month_start = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
    signed_amount = _expense_signed_amount()

    stats = (
        db.query(
            func.coalesce(func.sum(signed_amount), 0).label("total"),
            func.coalesce(func.avg(signed_amount), 0).label("average"),
            func.coalesce(func.max(signed_amount), 0).label("max"),
            func.coalesce(func.min(signed_amount), 0).label("min"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.FinancialEvent.date >= current_month_start,
            models.FinancialEvent.date < next_month_start,
            models.EntityLedger.category.isnot(None),
            *normal_monthly_budget_impact_filters(),
        )
        .first()
    )

    breakdown_rows = (
        db.query(
            models.Budget.category,
            models.Budget.monthly_limit,
            func.coalesce(func.sum(signed_amount), 0).label("total"),
            func.count(models.EntityLedger.id).label("count"),
        )
        .outerjoin(models.EntityLedger, models.EntityLedger.budget_id == models.Budget.id)
        .outerjoin(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.Budget.owner_id == current_user.id,
            models.Budget.budget_year == today.year,
            models.Budget.budget_month == today.month,
        )
        .group_by(models.Budget.category, models.Budget.monthly_limit)
        .all()
    )

    enhanced_breakdown = []
    for category, monthly_limit, _total, count in breakdown_rows:
        category_name = category.value if hasattr(category, "value") else category
        limit_value = int(monthly_limit or 0)
        total_value = get_budget_spent_amount(
            db,
            current_user.id,
            category=category,
            start_date=current_month_start,
            end_date=next_month_start,
        )
        percentage_used = round((total_value / limit_value) * 100, 2) if limit_value > 0 else 0

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
                "total": total_value,
                "count": int(count or 0),
                "budget_limit": limit_value,
                "remaining": int(max(0, limit_value - total_value)),
                "percentage_used": round(percentage_used, 1),
                "is_over_budget": total_value > limit_value,
                "budget_status": budget_status,
            }
        )

    return {
        "total_expenses": int(stats.total or 0),
        "average_expenses": float(stats.average or 0),
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
    signed_amount = _expense_signed_amount()

    spent = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.FinancialEvent.date >= current_month_start,
            models.FinancialEvent.date <= today,
            models.EntityLedger.category.isnot(None),
            *normal_monthly_budget_impact_filters(),
        )
        .scalar()
        or 0
    )

    income = _income_total_for_range(db, current_user.id, current_month_start, today)
    spent_int = int(spent)
    remaining = income - spent_int
    overall_balance = get_total_balance(db, current_user.id)
    net_position = get_net_position(db, current_user.id)
    elapsed_days = max(today.day, 1)
    daily_average = round(spent_int / elapsed_days) if elapsed_days else 0

    return {
        "income": income,
        "spent": spent_int,
        "remaining": int(remaining),
        "daily_average": int(daily_average),
        "overall_balance": int(overall_balance),
        "net_position": int(net_position),
    }


@router.get("/history", response_model=schemas.AnalyticsHistory)
def get_historical_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    signed_amount = _expense_signed_amount()
    stats = (
        db.query(
            func.coalesce(func.sum(signed_amount), 0).label("total_spent"),
            func.coalesce(func.avg(signed_amount), 0).label("average_transaction"),
            func.count(models.EntityLedger.id).label("total_transactions"),
            func.min(models.FinancialEvent.date).label("first_expense_date"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.EntityLedger.category.isnot(None),
            *normal_monthly_budget_impact_filters(),
        )
        .first()
    )

    return {
        "total_spent_lifetime": int(stats.total_spent or 0),
        "average_transaction": float(round(stats.average_transaction or 0, 2)),
        "total_transaction": int(stats.total_transactions or 0),
        "member_since": stats.first_expense_date,
    }


def _resolve_trend_range(
    *,
    today: date,
    days: int,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="analytics.range_both_or_days_required",
        )

    if start_date and end_date:
        if start_date < MIN_ANALYTICS_DATE or end_date < MIN_ANALYTICS_DATE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.date_too_early")
        if end_date > today:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.end_date_in_future")
        if start_date > end_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.start_after_end")
        if (end_date - start_date).days + 1 > 366:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.range_too_large")
        return start_date, end_date

    if days > 366:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.range_too_large")
    if days < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.days_min_1")
    return today - timedelta(days=days - 1), today


def _daily_amounts(
    db: Session,
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    signed_amount = _expense_signed_amount()
    results = (
        db.query(
            models.FinancialEvent.date,
            func.coalesce(func.sum(signed_amount), 0).label("total"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.FinancialEvent.date >= start_date,
            models.FinancialEvent.date <= end_date,
            models.EntityLedger.category.isnot(None),
            *normal_monthly_budget_impact_filters(),
        )
        .group_by(models.FinancialEvent.date)
        .order_by(models.FinancialEvent.date.asc())
        .all()
    )

    spending_dict = {row.date: int(row.total or 0) for row in results}
    return [
        {
            "date": start_date + timedelta(days=i),
            "amount": spending_dict.get(start_date + timedelta(days=i), 0),
        }
        for i in range((end_date - start_date).days + 1)
    ]


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
    start_date, end_date = _resolve_trend_range(
        today=today,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )
    return _daily_amounts(db, current_user.id, start_date, end_date)


@router.get("/month-to-date-trend", response_model=List[schemas.DailyTrendItem])
def get_month_to_date_trend(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    start_date = today.replace(day=1)
    return _daily_amounts(db, current_user.id, start_date, today)


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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.date_too_early")
        if end_date > today:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.end_date_in_future")
        if start_date > end_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.start_after_end")
    else:
        if days < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.days_min_1")
        if days > 366:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="analytics.range_too_large")
        start_date = today - timedelta(days=days - 1)
        end_date = today

    signed_amount = _expense_signed_amount()
    results = (
        db.query(
            models.EntityLedger.category,
            func.coalesce(func.sum(signed_amount), 0).label("total"),
            func.count(models.EntityLedger.id).label("count"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.FinancialEvent.date >= start_date,
            models.FinancialEvent.date <= end_date,
            models.EntityLedger.category.isnot(None),
            *normal_monthly_budget_impact_filters(),
        )
        .group_by(models.EntityLedger.category)
        .order_by(func.coalesce(func.sum(signed_amount), 0).desc())
        .all()
    )

    return [
        {
            "category": row.category.value if hasattr(row.category, "value") else row.category,
            "total": int(row.total or 0),
            "count": int(row.count or 0),
        }
        for row in results
    ]
