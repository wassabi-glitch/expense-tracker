from datetime import date
import logging
from pathlib import Path
# pyrefly: ignore [missing-import]
import httpx

# pyrefly: ignore [missing-import]
from passlib.context import CryptContext
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app import models
from app.services.budget_service import get_budget_spent_amount

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def verify_turnstile_token(token: str, client_ip: str, secret_key: str) -> bool:
    """Verifies a Cloudflare Turnstile token."""
    if not token:
        return False
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": secret_key,
                    "response": token,
                    "remoteip": client_ip,
                }
            )
            res.raise_for_status()
            data = res.json()
            if not data.get("success"):
                logger.warning(f"CAPTCHA verification failed for {client_ip}: {data}")
                return False
            return True
    except httpx.RequestError as exc:
        logger.error(f"Error contacting Cloudflare Turnstile: {exc}")
        return False


_disposable_domains: set[str] | None = None

def is_disposable_email(email: str) -> bool:
    """Checks if an email domain is in the disposable email blocklist."""
    global _disposable_domains
    if _disposable_domains is None:
        blocklist_path = Path(__file__).parent / "resources" / "disposable_email_blocklist.txt"
        try:
            with blocklist_path.open("r", encoding="utf-8") as f:
                _disposable_domains = {line.strip().lower() for line in f if line.strip() and not line.startswith("//")}
            logger.info(f"Loaded {len(_disposable_domains)} disposable email domains.")
        except Exception as e:
            logger.error(f"Failed to load disposable email blocklist: {e}")
            _disposable_domains = set()

    try:
        domain = email.split("@")[1].lower()
        return domain in _disposable_domains
    except IndexError:
        return False


def _calculate_spent(db: Session, owner_id: int, category: models.ExpenseCategory, budget_year: int, budget_month: int) -> int:
    first_day = date(budget_year, budget_month, 1)
    if budget_month == 12:
        next_month_first_day = date(budget_year + 1, 1, 1)
    else:
        next_month_first_day = date(budget_year, budget_month + 1, 1)

    return get_budget_spent_amount(
        db,
        owner_id,
        category=category,
        start_date=first_day,
        end_date=next_month_first_day,
    )


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
