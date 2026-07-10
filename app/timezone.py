from datetime import datetime, date, timezone, tzinfo, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, Header

from config import settings
from app import oauth2, models


def _safe_zoneinfo(name: str | None) -> tzinfo:
    if name:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            pass

    try:
        return ZoneInfo(settings.default_timezone)
    except ZoneInfoNotFoundError:
        return timezone.utc


def resolve_effective_timezone(
    x_timezone: str | None = None,
    user_timezone: str | None = None,
) -> tzinfo:
    # Interactive precedence:
    # 1) Request header timezone (current device/session)
    # 2) Persisted user timezone (background-friendly preference)
    # 3) App default timezone
    # 4) UTC
    normalized_header = (x_timezone or "").strip() or None
    if normalized_header:
        return _safe_zoneinfo(normalized_header)
    normalized_user = (user_timezone or "").strip() or None
    if normalized_user:
        return _safe_zoneinfo(normalized_user)
    return _safe_zoneinfo(None)


def get_request_timezone(x_timezone: str | None = Header(default=None, alias="X-Timezone")) -> tzinfo:
    # Allow clients to send an IANA timezone like "Asia/Tashkent".
    # Missing/invalid values fall back to configured default timezone, then UTC.
    normalized = (x_timezone or "").strip() or None
    return _safe_zoneinfo(normalized)


def get_effective_user_timezone(
    current_user: models.User = Depends(oauth2.get_current_user),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
) -> tzinfo:
    return resolve_effective_timezone(
        x_timezone=x_timezone,
        user_timezone=getattr(current_user, "timezone", None),
    )


def today_in_tz(tz: tzinfo | None) -> date:
    if tz is None:
        return date.today()
    return datetime.now(tz).date()


def now_in_tz(tz: tzinfo | None) -> datetime:
    if tz is None:
        return datetime.now()
    return datetime.now(tz)


CLOSING_WINDOW_DAYS = 5


def validate_normal_logging_date(
    entry_date: date,
    today: date,
    *,
    future_detail: str,
    closed_detail: str,
) -> None:
    """Validate a date against the closed-period guardrails for normal logging.

    - Future dates (after *today*) are always rejected.
    - The current calendar month is always open.
    - The first ``CLOSING_WINDOW_DAYS`` days of a new month form a closing
      window: backdating to the previous month is allowed for cleanup.
    - After the closing window the previous month is sealed — missed
      activity must use a current correction, not backdating.

    Raises :class:`fastapi.HTTPException` (400) with *future_detail* or
    *closed_detail* as appropriate.
    """
    from fastapi import HTTPException, status as http_status

    if entry_date > today:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=future_detail,
        )

    month_start = today.replace(day=1)
    if entry_date >= month_start:
        return  # current month — always open

    # Closing window: days 1-5 of the new month allow backdating to
    # the previous month for cleanup.
    if today.day <= CLOSING_WINDOW_DAYS:
        previous_month = today.replace(day=1) - timedelta(days=1)
        if entry_date.year == previous_month.year and entry_date.month == previous_month.month:
            return  # within closing window for previous month

    raise HTTPException(
        status_code=http_status.HTTP_400_BAD_REQUEST,
        detail=closed_detail,
    )
