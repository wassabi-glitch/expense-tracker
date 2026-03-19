from datetime import date
import logging

from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def _calculate_spent(db: Session, owner_id: int, category: models.ExpenseCategory, budget_year: int, budget_month: int) -> int:
    first_day = date(budget_year, budget_month, 1)
    if budget_month == 12:
        next_month_first_day = date(budget_year + 1, 1, 1)
    else:
        next_month_first_day = date(budget_year, budget_month + 1, 1)

    total_spent = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.owner_id == owner_id,
        models.Expense.category == category,
        models.Expense.date >= first_day,
        models.Expense.date < next_month_first_day,
    ).scalar() or 0
    return int(total_spent)


def check_budget_alerts(db: Session, budget: models.Budget):
    """
    Recalculate alert threshold memory for a single month-scoped budget row.
    Creates notifications when new thresholds are crossed.

    This function mutates `budget.last_notified_threshold` only.
    It does NOT commit; caller should commit.
    """
    from app.routers.notifications import create_budget_notification

    if budget.monthly_limit <= 0:
        budget.last_notified_threshold = 0
        return

    spent = _calculate_spent(db, budget.owner_id, budget.category, budget.budget_year, budget.budget_month)
    percentage = (spent / budget.monthly_limit) * 100

    new_threshold = 0
    if percentage >= 100:
        new_threshold = 100
    elif percentage >= 90:
        new_threshold = 90
    elif percentage >= 70:
        new_threshold = 70
    elif percentage >= 50:
        new_threshold = 50

    should_notify = new_threshold > (getattr(budget, 'last_notified_threshold', 0) or 0)

    if should_notify and new_threshold > 0:
        notification = create_budget_notification(
            db=db,
            budget=budget,
            threshold=new_threshold,
            spent=spent,
            limit=budget.monthly_limit,
        )
        if notification:
            db.add(notification)
            logger.info(f"Budget alert notification created for user {budget.owner_id}, category {budget.category}, threshold {new_threshold}")

    budget.last_notified_threshold = new_threshold
