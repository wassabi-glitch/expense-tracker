import logging
try:  # pyright: ignore[reportMissingImports]
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    # pyright: ignore[reportMissingImports]
    from apscheduler.triggers.interval import IntervalTrigger
except Exception:  # pragma: no cover - optional local dependency
    AsyncIOScheduler = None
    IntervalTrigger = None
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from app.session import SessionLocal
from app import models
from app.timezone import today_in_tz
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)
AUTO_CREATED_BUDGET_DEFAULT_LIMIT = 50_000


def calculate_next_due_date(current_due_date, frequency: models.RecurringFrequency, original_due_day: int = None):
    """
    Calculates the next due date based on the current due date and frequency.
    Handles anchor day logic for all monthly/yearly variants to avoid date drift.
    """
    if frequency == models.RecurringFrequency.ONE_TIME:
        return current_due_date

    if frequency == models.RecurringFrequency.DAILY:
        return current_due_date + timedelta(days=1)
    
    if frequency == models.RecurringFrequency.WEEKLY:
        return current_due_date + timedelta(weeks=1)
        
    if frequency == models.RecurringFrequency.BIWEEKLY:
        return current_due_date + timedelta(weeks=2)
    
    # Month-based jumps
    if frequency in (
        models.RecurringFrequency.MONTHLY, 
        models.RecurringFrequency.QUARTERLY, 
        models.RecurringFrequency.SEMI_ANNUALLY,
        models.RecurringFrequency.YEARLY
    ):
        months_to_jump = 1
        if frequency == models.RecurringFrequency.QUARTERLY:
            months_to_jump = 3
        elif frequency == models.RecurringFrequency.SEMI_ANNUALLY:
            months_to_jump = 6
        elif frequency == models.RecurringFrequency.YEARLY:
            months_to_jump = 12
            
        target_day = original_due_day or current_due_date.day
        
        # Calculate new month and year safely
        total_months = current_due_date.year * 12 + (current_due_date.month - 1) + months_to_jump
        new_year = total_months // 12
        new_month = (total_months % 12) + 1
        
        # Find last day of new month to prevent invalid dates (e.g. Feb 31)
        nm_total_months = total_months + 1
        nm_year = nm_total_months // 12
        nm_month = (nm_total_months % 12) + 1
        last_day_new_month = date(nm_year, nm_month, 1) - timedelta(days=1)
        
        final_day = min(target_day, last_day_new_month.day)
        return date(new_year, new_month, final_day)

    return current_due_date # Fallback

# Helper to get or create a budget for a given month/category


def get_or_create_budget(db: Session, owner_id: int, category: models.ExpenseCategory, year: int, month: int) -> models.Budget:
    """Return existing month budget, previous-month copy, or fallback default."""
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
            auto_created=True,
        )
        db.add(new_budget)
        db.flush()
        return new_budget

    new_budget = models.Budget(
        owner_id=owner_id,
        category=category,
        monthly_limit=AUTO_CREATED_BUDGET_DEFAULT_LIMIT,
        budget_year=year,
        budget_month=month,
        auto_created=True,
    )
    db.add(new_budget)
    db.flush()
    return new_budget


def process_due_recurring_expenses(db: Session = None):
    """
    Reads all ACTIVE recurring expenses and creates them if due.
    Failed templates remain ACTIVE and use retry_count / failing_due_date for retry handling.
    """
    db_session = db or SessionLocal()
    try:
        # 1. Load templates that are currently in a runnable state.
        # The current enum only supports ACTIVE and DISABLED.
        try:
            runnable_templates = (
                db_session.query(models.RecurringExpense)
                .join(models.User, models.RecurringExpense.owner_id == models.User.id)
                .filter(
                    models.RecurringExpense.status == models.RecurringStatus.ACTIVE,
                    models.User.is_premium,
                )
                .all()
            )
        except ProgrammingError:
            logger.warning("recurring_expenses table not ready — skipping.")
            db_session.rollback()
            return

        if not runnable_templates:
            return

        processed = 0
        for rec in runnable_templates:
            # --- ISOLATION: Process each template in a savepoint ---
            # If one template crashes, we don't want to stop the whole scheduler.
            try:
                with db_session.begin_nested():
                    # Calculate "Today" in user's local time
                    user_tz_str = getattr(rec.owner, "timezone", None) or "UTC"
                    try:
                        user_tz = ZoneInfo(user_tz_str)
                    except Exception:
                        user_tz = ZoneInfo("UTC")
                    today_for_user = today_in_tz(user_tz)

                    # Only process if actually due
                    if rec.next_due_date > today_for_user:
                        continue

                    # --- WALLET RESOLUTION ---
                    wallet = None
                    if rec.wallet_id:
                        # User PICKED a wallet — be strict. 
                        # Only use this specific wallet, and only if it's active.
                        wallet = db_session.query(models.Wallet).filter(
                            models.Wallet.id == rec.wallet_id,
                            models.Wallet.owner_id == rec.owner_id,
                            models.Wallet.is_active
                        ).first()
                        
                        if not wallet:
                            # The wallet was either deleted (shouldn't happen with our FKs) 
                            # or ARCHIVED. We do NOT fall back here. We fail so the 
                            # user is notified to pick a new wallet.
                            raise ValueError("assigned_wallet_archived_or_missing")
                    else:
                        # LEGACY FALLBACK: Only for templates created before wallet_id existed.
                        wallet = db_session.query(models.Wallet).filter(
                            models.Wallet.owner_id == rec.owner_id,
                            models.Wallet.is_default,
                            models.Wallet.is_active
                        ).first()
                        if not wallet:
                            # If no default, try any active wallet for legacy support
                            wallet = db_session.query(models.Wallet).filter(
                                models.Wallet.owner_id == rec.owner_id,
                                models.Wallet.is_active
                            ).first()

                    # --- EXECUTION ---
                    try:
                        if not wallet:
                            raise ValueError("No active wallet available")

                        # Determine which occurrence we are processing
                        target_date = rec.failing_due_date or rec.next_due_date
                        
                        budget = get_or_create_budget(
                            db_session,
                            rec.owner_id,
                            rec.category,
                            target_date.year,
                            target_date.month,
                        )

                        # Attempt the transaction with our Idempotency Bouncer
                        WalletService.record_transaction(
                            db=db_session,
                            owner_id=rec.owner_id,
                            wallet_id=wallet.id,
                            transaction_type=models.TransactionType.EXPENSE,
                            amount_delta=-rec.amount,
                            category=rec.category,
                            title=rec.title,
                            description=rec.description,
                            budget_id=budget.id,
                            transaction_date=target_date,
                            recurring_id=rec.id,
                            idempotency_key=f"recur_{rec.id}_{target_date}"
                        )

                        # SUCCESS LOGGING (The Diary)
                        old_due = rec.next_due_date
                        
                        if rec.failing_due_date:
                            rec.failing_due_date = None
                            new_due = rec.next_due_date
                        else:
                            anchor = rec.next_due_date if rec.cycle_behavior == models.CycleBehavior.FIXED else today_for_user
                            rec.next_due_date = calculate_next_due_date(anchor, rec.frequency, rec.original_due_day)
                            new_due = rec.next_due_date
                            
                            if rec.cycle_behavior == models.CycleBehavior.FLEXIBLE:
                                rec.original_due_day = today_for_user.day
                            
                            # RETIREMENT: One-time templates disable themselves after success
                            if rec.frequency == models.RecurringFrequency.ONE_TIME:
                                rec.status = models.RecurringStatus.DISABLED
                                logger.info(f"One-time template {rec.id} ({rec.title}) completed. AUTO-DISABLING.")

                        # Write to Diary
                        db_session.add(models.RecurringEvent(
                            recurring_expense_id=rec.id,
                            event_type=models.RecurringEventType.PAID,
                            target_due_date=target_date,
                            old_next_due_date=old_due,
                            new_next_due_date=new_due,
                            metadata_notes=f"Processed by scheduler on {today_for_user}"
                        ))

                        rec.retry_count = 0
                        rec.last_retry_at = None
                        processed += 1
                        logger.info(f"Successfully processed recurring {rec.id} ({rec.title})")

                    except Exception as failure:
                        # FAILURE: Dunning/Retry Logic
                        target_date = rec.failing_due_date or rec.next_due_date
                        rec.failing_due_date = target_date
                        rec.retry_count += 1
                        
                        if rec.retry_count >= 72:
                            rec.status = models.RecurringStatus.DISABLED
                            logger.error(f"Template {rec.id} ({rec.title}) has reached max retries. DISABLING.")
                        
                        db_session.add(models.RecurringEvent(
                            recurring_expense_id=rec.id,
                            event_type=models.RecurringEventType.FAILED,
                            target_due_date=target_date,
                            metadata_notes=f"Attempt failed: {str(failure)}"
                        ))

                        should_notify = False
                        if rec.last_retry_at is None:
                            should_notify = True
                        else:
                            if rec.last_retry_at.date() < today_for_user:
                                should_notify = True
                        
                        rec.last_retry_at = today_for_user
                        
                        if should_notify:
                            new_notif = models.Notification(
                                owner_id=rec.owner_id,
                                type=models.NotificationType.RECURRING_FAILED,
                                title="Recurring Payment Failed",
                                message=f"Could not process '{rec.title}' ({rec.amount:,.0f} UZS). Reason: {str(failure)}",
                                is_read=False
                            )
                            db_session.add(new_notif)
                            logger.warning(f"Notification sent for failing template {rec.id}: {failure}")

            except Exception as e:
                # This catches database-level errors during the savepoint
                logger.error(f"Critical failure processing template {rec.id}: {e}")
                continue # Move to the next template

        db_session.commit()
        if processed > 0:
            logger.info(f"Scheduler run complete: {processed} expenses created.")

    except Exception as e:
        db_session.rollback()
        logger.error(f"Fatal scheduler error: {e}")
    finally:
        if db is None:
            db_session.close()


def start_scheduler():
    if AsyncIOScheduler is None or IntervalTrigger is None:
        logger.warning(
            "APScheduler is not installed. Recurring background scheduler is disabled."
        )
        return None

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        process_due_recurring_expenses,
        trigger=IntervalTrigger(hours=1),
        id="process_recurring_expenses",
        name="Hourly check for recurring expenses",
        replace_existing=True,
        # Fire immediately on startup
        next_run_time=__import__("datetime").datetime.now(),
    )
    scheduler.start()
    logger.info(
        "APScheduler started: Recurring expenses check scheduled hourly (+ immediate first run).")
    return scheduler
