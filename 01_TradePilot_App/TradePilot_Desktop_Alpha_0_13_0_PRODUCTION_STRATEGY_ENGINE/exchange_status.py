from __future__ import annotations

"""Local exchange-session status for TradePilot 0.9.10.

The module uses regular cash-market sessions plus the most important full-day
holidays. It is intended for UI/status and paper-trading safeguards, not as an
official exchange calendar. Fresh provider timestamps remain the decisive
execution guard in the Order Engine.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


EXCHANGES = {
    "NYSE": {"name": "NYSE", "tz": "America/New_York", "open": time(9, 30), "close": time(16, 0), "calendar": "US"},
    "NASDAQ": {"name": "NASDAQ", "tz": "America/New_York", "open": time(9, 30), "close": time(16, 0), "calendar": "US"},
    "XETRA": {"name": "XETRA", "tz": "Europe/Berlin", "open": time(9, 0), "close": time(17, 30), "calendar": "DE"},
    "VIE": {"name": "WIEN", "tz": "Europe/Vienna", "open": time(9, 0), "close": time(17, 30), "calendar": "AT"},
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed_fixed(year: int, month: int, day: int) -> date:
    d = date(year, month, day)
    if d.weekday() == 5:  # Saturday -> Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def _easter_sunday(year: int) -> date:
    # Anonymous Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _us_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    return {
        _observed_fixed(year, 1, 1),
        _nth_weekday(year, 1, 0, 3),       # MLK Day
        _nth_weekday(year, 2, 0, 3),       # Presidents Day
        easter - timedelta(days=2),         # Good Friday
        _last_weekday(year, 5, 0),         # Memorial Day
        _observed_fixed(year, 6, 19),       # Juneteenth
        _observed_fixed(year, 7, 4),        # Independence Day
        _nth_weekday(year, 9, 0, 1),       # Labor Day
        _nth_weekday(year, 11, 3, 4),      # Thanksgiving
        _observed_fixed(year, 12, 25),      # Christmas
    }


def _de_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 12, 24),
        date(year, 12, 25),
        date(year, 12, 26),
        date(year, 12, 31),
    }


def _at_holidays(year: int) -> set[date]:
    easter = _easter_sunday(year)
    # Conservative major closure calendar for the Vienna cash market UI.
    return {
        date(year, 1, 1), date(year, 1, 6),
        easter - timedelta(days=2), easter + timedelta(days=1),
        date(year, 5, 1), date(year, 12, 24), date(year, 12, 25),
        date(year, 12, 26), date(year, 12, 31),
    }


def _holiday(calendar: str, d: date) -> bool:
    if calendar == "US":
        return d in _us_holidays(d.year)
    if calendar == "DE":
        return d in _de_holidays(d.year)
    if calendar == "AT":
        return d in _at_holidays(d.year)
    return False


def _trading_day(cfg: dict, d: date) -> bool:
    return d.weekday() < 5 and not _holiday(str(cfg.get("calendar", "")), d)


def _session_for_day(cfg: dict, d: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(cfg["tz"])
    return (
        datetime.combine(d, cfg["open"], tzinfo=tz),
        datetime.combine(d, cfg["close"], tzinfo=tz),
    )


def _next_open(cfg: dict, local_now: datetime) -> datetime:
    d = local_now.date()
    for offset in range(0, 370):
        day = d + timedelta(days=offset)
        if not _trading_day(cfg, day):
            continue
        op, _ = _session_for_day(cfg, day)
        if op > local_now:
            return op
    return local_now + timedelta(days=1)


def get_exchange_status(code: str, now_utc: datetime | None = None) -> dict:
    code = str(code).upper()
    cfg = EXCHANGES[code]
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    local_now = now_utc.astimezone(ZoneInfo(cfg["tz"]))
    trading_day = _trading_day(cfg, local_now.date())
    op, cl = _session_for_day(cfg, local_now.date())
    is_open = bool(trading_day and op <= local_now < cl)
    if is_open:
        event = "CLOSE"
        target = cl
    else:
        event = "OPEN"
        target = _next_open(cfg, local_now)
    seconds = max(0, int((target - local_now).total_seconds()))
    return {
        "code": code,
        "name": cfg["name"],
        "is_open": is_open,
        "event": event,
        "seconds": seconds,
        "local_time": local_now.isoformat(timespec="seconds"),
        "target_time": target.isoformat(timespec="seconds"),
        "regular_hours": f"{cfg['open'].strftime('%H:%M')}–{cfg['close'].strftime('%H:%M')}",
        "timezone": cfg["tz"],
        "trading_day": trading_day,
    }


def is_exchange_open(code: str, now_utc: datetime | None = None) -> bool:
    try:
        return bool(get_exchange_status(code, now_utc).get("is_open"))
    except Exception:
        return False


def format_countdown(seconds: int, lang: str = "de") -> str:
    seconds = max(0, int(seconds or 0))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if lang == "en":
        if days:
            return f"{days}d {hours}h"
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    if days:
        return f"{days} T. {hours} Std."
    if hours:
        return f"{hours} Std. {minutes} Min."
    return f"{minutes} Min."


def all_exchange_statuses(now_utc: datetime | None = None) -> list[dict]:
    return [get_exchange_status(code, now_utc) for code in ("NYSE", "NASDAQ", "XETRA", "VIE")]
