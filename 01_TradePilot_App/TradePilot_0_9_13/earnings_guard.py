from __future__ import annotations

"""Best-effort upcoming-earnings guard for the AutoTrader."""

from datetime import datetime, timezone

PROFILE_WINDOWS = {
    "defensive": {"block_days": 7, "warn_days": 14},
    "balanced": {"block_days": 4, "warn_days": 10},
    "offensive": {"block_days": 2, "warn_days": 7},
    "speculative": {"block_days": 0, "warn_days": 3},
}


def _as_datetime(value):
    if value is None:
        return None
    try:
        if hasattr(value, "to_pydatetime"):
            value = value.to_pydatetime()
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def get_earnings_info(symbol: str) -> dict:
    out = {"symbol": symbol, "next_earnings": None, "days": None, "status": "UNKNOWN", "error": None}
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        dates = []

        try:
            ed = ticker.get_earnings_dates(limit=8)
            if ed is not None and not ed.empty:
                for idx in ed.index:
                    dt = _as_datetime(idx)
                    if dt:
                        dates.append(dt)
        except Exception:
            pass

        if not dates:
            try:
                cal = ticker.calendar
                if isinstance(cal, dict):
                    raw = cal.get("Earnings Date") or cal.get("EarningsDate")
                    if isinstance(raw, (list, tuple)):
                        dates.extend(dt for dt in (_as_datetime(x) for x in raw) if dt)
                    else:
                        dt = _as_datetime(raw)
                        if dt:
                            dates.append(dt)
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        future = sorted(dt for dt in dates if dt >= now)
        if not future:
            out["status"] = "NO_DATE"
            return out
        nxt = future[0]
        days = max(0, (nxt.date() - now.date()).days)
        out.update({"next_earnings": nxt.isoformat(timespec="minutes"), "days": days, "status": "KNOWN"})
        return out
    except Exception as exc:
        out["error"] = str(exc)
        return out


def earnings_profile_filter(info: dict | None, profile: str) -> dict:
    cfg = PROFILE_WINDOWS.get(profile, PROFILE_WINDOWS["balanced"])
    status = (info or {}).get("status", "UNKNOWN")
    days = (info or {}).get("days")
    block = False
    warning = None

    if status == "KNOWN" and days is not None:
        try:
            days = int(days)
            if cfg["block_days"] > 0 and days <= cfg["block_days"]:
                block = True
                warning = "EARNINGS_TOO_CLOSE"
            elif days <= cfg["warn_days"]:
                warning = "EARNINGS_SOON"
        except Exception:
            warning = "EARNINGS_DATA_UNKNOWN"
    elif status == "UNKNOWN":
        warning = "EARNINGS_DATA_UNKNOWN"
    return {"block": block, "warning": warning, "days": days, "status": status}
