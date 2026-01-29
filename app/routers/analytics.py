from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import List

from app import schemas
from app.session import get_db
from .. import models, oauth2

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


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
        "total_spent_lifetime": stats.total_spent or 0,
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
    current_user: models.User = Depends(oauth2.get_current_user)
):
    today = date.today()
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide both start_date and end_date, or use days."
        )

    if start_date and end_date:
        if end_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be in the future."
            )
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be after end date."
            )
        if (end_date - start_date).days + 1 > 366:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range too large. Max allowed is 366 days."
            )
    else:
        if days > 366:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range too large. Max allowed is 366 days."
            )
        if days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be at least 1."
            )
        start_date = today - timedelta(days=days - 1)
        end_date = today

    # user_join_date = current_user.created_at.date()

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
            "amount": float(amount)
        })

    return filled_data
