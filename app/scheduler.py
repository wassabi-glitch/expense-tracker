import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:  # pyright: ignore[reportMissingImports]
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger  # pyright: ignore[reportMissingImports]
except Exception:  # pragma: no cover - optional local dependency
    AsyncIOScheduler = None
    IntervalTrigger = None

# pyrefly: ignore [missing-import]
from sqlalchemy.exc import ProgrammingError
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app import models
from app.services.recurring_occurrence_service import (
    create_pending_due_occurrence,
    notify_pending_confirmation_once,
)
from app.session import SessionLocal
from app.timezone import today_in_tz


logger = logging.getLogger(__name__)


def _user_local_today(template: models.RecurringExpense):
    timezone_name = getattr(template.owner, "timezone", None) or "UTC"
    try:
        user_timezone = ZoneInfo(timezone_name)
    except Exception:
        user_timezone = ZoneInfo("UTC")
    return today_in_tz(user_timezone)





def process_due_recurring_expenses(db: Session | None = None) -> None:
    """Materialize pending occurrences for due templates."""
    db_session = db or SessionLocal()
    try:
        try:
            template_ids = [
                row[0]
                for row in (
                    db_session.query(models.RecurringExpense.id)
                    .join(models.User, models.RecurringExpense.owner_id == models.User.id)
                    .filter(
                        models.RecurringExpense.status == models.RecurringStatus.ACTIVE,
                        models.RecurringExpense.archived_at.is_(None),
                        models.User.is_premium,
                    )
                    .all()
                )
            ]
        except ProgrammingError:
            logger.warning("Recurring tables are not ready; skipping due processing.")
            db_session.rollback()
            return

        processed = 0
        for template_id in template_ids:
            try:
                with db_session.begin_nested():
                    template = (
                        db_session.query(models.RecurringExpense)
                        .filter(
                            models.RecurringExpense.id == template_id,
                            models.RecurringExpense.status == models.RecurringStatus.ACTIVE,
                            models.RecurringExpense.archived_at.is_(None),
                        )
                        .with_for_update()
                        .first()
                    )
                    if template is None:
                        continue

                    local_today = _user_local_today(template)
                    if template.next_due_date > local_today:
                        continue

                    occurrence = create_pending_due_occurrence(
                        db_session,
                        template,
                        local_today=local_today,
                    )
                    notify_pending_confirmation_once(db_session, template, occurrence)
                    processed += 1
            except Exception as exc:
                logger.error("Recurring template %s failed: %s", template_id, exc)

        db_session.commit()
        if processed:
            logger.info("Recurring scheduler recorded %s occurrence(s).", processed)
    except Exception as exc:
        db_session.rollback()
        logger.error("Fatal recurring scheduler error: %s", exc)
    finally:
        if db is None:
            db_session.close()


def start_scheduler():
    if AsyncIOScheduler is None or IntervalTrigger is None:
        logger.warning("APScheduler is not installed. Recurring background scheduler is disabled.")
        return None

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        process_due_recurring_expenses,
        trigger=IntervalTrigger(hours=1),
        id="process_recurring_expenses",
        name="Hourly recurring occurrence check",
        replace_existing=True,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    logger.info("Recurring occurrence scheduler started.")
    return scheduler
