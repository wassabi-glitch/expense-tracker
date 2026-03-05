import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import timedelta
from zoneinfo import ZoneInfo

from app.session import SessionLocal
from app import models
from app.timezone import today_in_tz

logger = logging.getLogger(__name__)


def calculate_next_due_date(current_due_date, frequency: models.RecurringFrequency):
    if frequency == models.RecurringFrequency.DAILY:
        return current_due_date + timedelta(days=1)
    elif frequency == models.RecurringFrequency.WEEKLY:
        return current_due_date + timedelta(weeks=1)
    elif frequency == models.RecurringFrequency.MONTHLY:
        # Simple approximation: advance by 30 days
        # A more robust solution would advance to the exact same day next month
        next_month = current_due_date.replace(day=28) + timedelta(days=4)
        last_day_of_next_month = next_month - timedelta(days=next_month.day)
        try:
            return current_due_date.replace(year=next_month.year, month=next_month.month)
        except ValueError:
            # e.g., Jan 31 -> Feb 28
            return last_day_of_next_month
    elif frequency == models.RecurringFrequency.YEARLY:
        try:
            return current_due_date.replace(year=current_due_date.year + 1)
        except ValueError:
            # Feb 29 leap year handled gracefully
            return current_due_date + timedelta(days=365)

# Helper to get or create a budget for a given month/category
def get_or_create_budget(db: Session, owner_id: int, category: models.ExpenseCategory, year: int, month: int) -> models.Budget:
    """Return existing budget or create a new one.
    If a budget for the given month does not exist, attempt to copy the most recent previous month's budget.
    If none exists, create a budget with a monthly_limit of 0.
    """
    # Try exact month
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == year,
            models.Budget.budget_month == month,
        )
        .first()
    )
    if budget:
        return budget
    # Find most recent previous month budget
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    prev_budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == prev_year,
            models.Budget.budget_month == prev_month,
        )
        .first()
    )
    if prev_budget:
        new_budget = models.Budget(
            owner_id=owner_id,
            category=category,
            monthly_limit=prev_budget.monthly_limit,
            budget_year=year,
            budget_month=month,
        )
        db.add(new_budget)
        db.flush()
        return new_budget
    # No previous budget, create with zero limit
    new_budget = models.Budget(
        owner_id=owner_id,
        category=category,
        monthly_limit=0,
        budget_year=year,
        budget_month=month,
    )
    db.add(new_budget)
    db.flush()
    return new_budget


def process_due_recurring_expenses(db: Session = None):
    """Reads all active recurring expenses and creates them if due."""
    db_session = db or SessionLocal()
    try:
        # Load ALL active templates (we'll filter by per-user date below)
        all_templates = (
            db_session.query(models.RecurringExpense)
            .join(models.User, models.RecurringExpense.owner_id == models.User.id)
            .filter(
                models.RecurringExpense.is_active == True,   # noqa: E712
                models.User.is_premium == True,              # noqa: E712
            )
            .all()
        )

        if not all_templates:
            logger.info("No active recurring templates found.")
            return

        # Group templates by owner timezone and compute "today" per-user
        processed = 0
        for rec in all_templates:
            user_tz_str = getattr(rec.owner, "timezone", None) or "UTC"
            try:
                user_tz = ZoneInfo(user_tz_str)
            except Exception:
                user_tz = ZoneInfo("UTC")
            today_for_user = today_in_tz(user_tz)

            if rec.next_due_date > today_for_user:
                continue  # Not due yet in user's local timezone

            logger.info(f"Backfilling template {rec.id}: {rec.title} (freq={rec.frequency}, tz={user_tz_str}, today={today_for_user})")

            current_due = rec.next_due_date
            created = 0
            while current_due <= today_for_user:
                new_expense = models.Expense(
                    title=rec.title,
                    amount=rec.amount,
                    category=rec.category,
                    description=rec.description,
                    owner_id=rec.owner_id,
                    date=current_due,
                    budget_id=get_or_create_budget(
                        db_session,
                        rec.owner_id,
                        rec.category,
                        current_due.year,
                        current_due.month,
                    ).id,
                )
                db_session.add(new_expense)
                current_due = calculate_next_due_date(current_due, rec.frequency)
                created += 1

            rec.next_due_date = current_due
            logger.info(f"  → Created {created} expense(s); next_due_date={rec.next_due_date}")
            processed += 1

        db_session.commit()
        logger.info(f"Scheduler done: processed {processed} template(s).")

    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to process recurring expenses: {e}")
    finally:
        if db is None:
            db_session.close()



def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        process_due_recurring_expenses,
        trigger=IntervalTrigger(hours=1),
        id="process_recurring_expenses",
        name="Hourly check for recurring expenses",
        replace_existing=True,
        next_run_time=__import__("datetime").datetime.now(),  # Fire immediately on startup
    )
    scheduler.start()
    logger.info("APScheduler started: Recurring expenses check scheduled hourly (+ immediate first run).")
    return scheduler

