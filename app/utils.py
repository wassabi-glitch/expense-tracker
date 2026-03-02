from datetime import date
import logging

from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

# Tell passlib to use bcrypt for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def check_budget_alerts(db: Session, budget: models.Budget):
    """
    Recalculate alert threshold memory for a single month-scoped budget row.

    This function mutates `budget.last_notified_threshold` only.
    It does NOT commit; caller should commit.
    """
    # Build exact month range [first_day, next_month_first_day)
    first_day = date(budget.budget_year, budget.budget_month, 1)
    if budget.budget_month == 12:
        next_month_first_day = date(budget.budget_year + 1, 1, 1)
    else:
        next_month_first_day = date(
            budget.budget_year, budget.budget_month + 1, 1)

    total_spent = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.owner_id == budget.owner_id,
        models.Expense.category == budget.category,
        models.Expense.date >= first_day,
        models.Expense.date < next_month_first_day,
    ).scalar() or 0

    if budget.monthly_limit <= 0:
        budget.last_notified_threshold = 0
        return

    percentage = (total_spent / budget.monthly_limit) * 100

    if percentage >= 100:
        budget.last_notified_threshold = 100
    elif percentage >= 90:
        budget.last_notified_threshold = 90
    elif percentage >= 50:
        budget.last_notified_threshold = 50
    else:
        budget.last_notified_threshold = 0
