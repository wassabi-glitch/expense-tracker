from datetime import datetime, date, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Header

from config import settings


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


def get_request_timezone(x_timezone: str | None = Header(default=None, alias="X-Timezone")) -> tzinfo | None:
    # Allow clients to send an IANA timezone like "Asia/Tashkent".
    # Missing header keeps legacy server-local behavior.
    # Invalid values safely fall back to configured default, then UTC.
    normalized = (x_timezone or "").strip()
    if not normalized:
        return None
    return _safe_zoneinfo(normalized)


def today_in_tz(tz: tzinfo | None) -> date:
    if tz is None:
        return date.today()
    return datetime.now(tz).date()


def now_in_tz(tz: tzinfo | None) -> datetime:
    if tz is None:
        return datetime.now()
    return datetime.now(tz)
