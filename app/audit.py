"""Thin audit helper — records redacted security events.

Usage in any route:
    from app.audit import log_security_event
    log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.SUCCESS,
                       request=request, user_id=user.id)

Rules (from auth-round-5 spec):
    • Never log passwords, raw tokens, or secrets.
    • Only store user_id, action, status, IP, user-agent, and safe metadata.
"""
import logging

from app.models import SecurityAction, SecurityEvent, SecurityStatus  # noqa: F401 — re-exported for convenience

logger = logging.getLogger(__name__)


def log_security_event(
    db,
    *,
    action: SecurityAction,
    status: SecurityStatus,
    request=None,
    user_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Insert one row into security_events. Commits immediately."""
    ip_address = None
    user_agent = None
    if request is not None:
        ip_address = request.headers.get(
            "X-Forwarded-For",
            request.client.host if request.client else None,
        )
        user_agent = (request.headers.get("User-Agent") or "")[:512] or None

    db.add(SecurityEvent(
        user_id=user_id,
        action=action,
        status=status,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_=metadata,
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record security event %s/%s for user %s",
                         action, status, user_id)
