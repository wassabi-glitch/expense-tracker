from datetime import datetime, date, timezone, tzinfo
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
