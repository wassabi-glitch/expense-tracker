import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from config import settings


VERIFY_EMAIL_TOKEN_TTL_HOURS = 48


def hash_email_verification_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_verify_email_link(raw_token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/verify-email?token={raw_token}"


def issue_email_verification_token(
    db: Session,
    user: models.User,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_email_verification_token(raw_token)

    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_(None),
    ).update(
        {models.EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )

    db.add(
        models.EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=VERIFY_EMAIL_TOKEN_TTL_HOURS),
        )
    )
    db.commit()
    return raw_token
