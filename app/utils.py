from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
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


def check_budget_alerts(db: Session, user_id: int, category: str):
    budget = db.query(models.Budget).filter(
        models.Budget.owner_id == user_id,
        models.Budget.category == category
    ).first()

    if not budget:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No budget set for category: {category}.Please set a budget before adding expenses in this category.")

    db.refresh(budget)
    now = datetime.now(timezone.utc)
   # 1. Handle Monthly Reset (and initial setup)
    if now.month != budget.last_notified_month or now.year != budget.last_notified_year:
        budget.last_notified_threshold = 0
        budget.last_notified_month = now.month  # <--- SYNC THIS NOW
        budget.last_notified_year = now.year   # <--- SYNC THIS NOW
        db.commit()
        db.refresh(budget)
    # 2. Calculate current month's total
    first_day = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    total_spent = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.owner_id == user_id,
        models.Expense.category == category,
        models.Expense.date >= first_day
    ).scalar() or 0

    percentage = (total_spent / budget.monthly_limit) * 100

    logger.debug(
        "Current percentage: %s, last threshold: %s",
        percentage,
        budget.last_notified_threshold,
    )

    # 3. Check Thresholds
    if percentage >= 100:
        if budget.last_notified_threshold < 100:
            logger.warning("Budget reached 100%% for category %s", category)
            budget.last_notified_threshold = 100
            db.commit()

    elif percentage >= 90:
        if budget.last_notified_threshold < 90:
            logger.warning("Budget reached 90%% for category %s", category)
            budget.last_notified_threshold = 90
            db.commit()
        elif budget.last_notified_threshold > 90:
            # Drop-down logic: If we were at 100 and deleted an expense to hit 95
            budget.last_notified_threshold = 90
            db.commit()

    elif percentage >= 50:
        if budget.last_notified_threshold < 50:
            logger.info("Budget reached 50%% for category %s", category)
            budget.last_notified_threshold = 50
            db.commit()
        elif budget.last_notified_threshold > 50:
            # Drop-down logic: If we were at 90 and deleted an expense to hit 60
            budget.last_notified_threshold = 50
            db.commit()

    else:
        # Below 50%
        if budget.last_notified_threshold != 0:
            logger.debug("Threshold reset to 0 for category %s", category)
            budget.last_notified_threshold = 0
            db.commit()

    db.commit()
