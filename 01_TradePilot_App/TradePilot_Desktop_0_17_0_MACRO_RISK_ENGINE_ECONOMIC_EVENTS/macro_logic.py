from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

ECONOMIC_CALENDAR_URL = "https://xoomar.com/api/markets/calendar"
EVENT_PAUSE_MINUTES = 30
POST_EVENT_OBSERVE_MINUTES = 20
CACHE_MAX_MINUTES = 20

LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "UNKNOWN": 3}

# TradePilot's own normalization layer. Source labels are hints, not authority.
EVENT_RULES = [
    (("fed interest rate", "fed rate", "fomc rate", "federal funds rate", "interest rate decision"), "CRITICAL", "higher_is_risk_off"),
    (("cpi", "consumer price index", "core inflation"), "CRITICAL", "higher_is_risk_off"),
    (("nonfarm payroll", "non farm payroll", "nfp"), "CRITICAL", "context_dependent"),
    (("ecb interest rate", "ecb rate", "ecb monetary policy"), "CRITICAL", "higher_is_risk_off"),
    (("pce", "personal consumption expenditure", "core pce"), "HIGH", "higher_is_risk_off"),
    (("unemployment rate", "jobless rate"), "HIGH", "higher_is_risk_on"),
    (("gdp", "gross domestic product"), "HIGH", "higher_is_risk_on"),
    (("ism manufacturing", "ism services", "ism pmi"), "HIGH", "higher_is_risk_on"),
    (("retail sales",), "MEDIUM", "higher_is_risk_on"),
    (("consumer confidence", "michigan sentiment", "consumer sentiment"), "MEDIUM", "higher_is_risk_on"),
]

MARKET_TICKERS = {
    "NASDAQ": "^IXIC",
    "S&P 500": "^GSPC",
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "OIL": "CL=F",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            x = float(value)
            return x if math.isfinite(x) else None
        except Exception:
            return None
    s = str(value).strip().replace("\u2212", "-")
    if not s or s.lower() in {"n/a", "na", "none", "-", "—"}:
        return None
    # Preserve decimal semantics; remove unit suffixes and thousands separators conservatively.
    mult = 1.0
    if s.endswith("K"):
        mult, s = 1_000.0, s[:-1]
    elif s.endswith("M"):
        mult, s = 1_000_000.0, s[:-1]
    elif s.endswith("B"):
        mult, s = 1_000_000_000.0, s[:-1]
    s = s.replace("%", "").replace("$", "").replace("€", "").strip()
    if s.count(",") == 1 and "." not in s:
        left, right = s.split(",")
        if len(right) <= 3:
            s = left + "." + right
        else:
            s = left + right
    else:
        s = s.replace(",", "")
    try:
        x = float(s) * mult
        return x if math.isfinite(x) else None
    except Exception:
        return None


def classify_event(name: str, source_importance: str = "") -> tuple[str, str]:
    low = (name or "").lower()
    for names, relevance, semantic in EVENT_RULES:
        if any(token in low for token in names):
            return relevance, semantic
    src = (source_importance or "").strip().lower()
    if src in {"critical", "3", "high"}:
        return "HIGH", "context_dependent"
    if src in {"medium", "2", "moderate"}:
        return "MEDIUM", "context_dependent"
    return "LOW", "context_dependent"


def economic_surprise(event: dict) -> dict:
    actual = _number(event.get("actual"))
    forecast = _number(event.get("forecast"))
    previous = _number(event.get("previous"))
    semantic = event.get("semantic") or "context_dependent"
    if actual is None or forecast is None:
        return {"available": False, "raw": None, "direction": "UNKNOWN", "text": "Actual/Forecast noch nicht vollständig"}
    raw = actual - forecast
    eps = max(abs(forecast) * 0.001, 1e-9)
    if abs(raw) <= eps:
        direction = "NEUTRAL"
    elif semantic == "higher_is_risk_off":
        direction = "NEGATIVE" if raw > 0 else "POSITIVE"
    elif semantic == "higher_is_risk_on":
        direction = "POSITIVE" if raw > 0 else "NEGATIVE"
    else:
        # Context dependent may never make trading more aggressive by itself.
        direction = "CAUTION"
    sign = "+" if raw > 0 else ""
    return {
        "available": True,
        "raw": round(raw, 6),
        "direction": direction,
        "previous": previous,
        "text": f"Actual vs Forecast: {sign}{raw:g} · {direction}",
    }


def market_regime_from_moves(moves: dict[str, float | None]) -> dict:
    # Positive score = risk-on. Missing inputs reduce confidence and can never create RISK-ON.
    required = ["NASDAQ", "S&P 500", "VIX", "US10Y"]
    present = sum(moves.get(k) is not None for k in required)
    score = 0.0
    n = moves.get("NASDAQ")
    sp = moves.get("S&P 500")
    vix = moves.get("VIX")
    y10 = moves.get("US10Y")  # basis-point move
    oil = moves.get("OIL")
    if n is not None: score += max(-2, min(2, n / 0.5))
    if sp is not None: score += max(-2, min(2, sp / 0.4))
    if vix is not None: score += max(-2, min(2, -vix / 4.0))
    if y10 is not None: score += max(-1.5, min(1.5, -y10 / 6.0))
    if oil is not None and oil > 2.0: score -= min(1.0, oil / 5.0)
    confidence = int(round(100 * present / len(required)))
    if present < 3:
        return {"regime": "NEUTRAL", "score": round(score, 2), "confidence": confidence, "complete": False}
    if score >= 2.0:
        regime = "RISK-ON"
    elif score <= -2.0:
        regime = "RISK-OFF"
    else:
        regime = "NEUTRAL"
    return {"regime": regime, "score": round(score, 2), "confidence": confidence, "complete": present == len(required)}


def normalize_event(raw: dict) -> dict | None:
    scheduled = raw.get("scheduledAt") or raw.get("scheduled_at") or raw.get("date") or raw.get("Date")
    dt = _parse_dt(scheduled)
    if not dt:
        return None
    name = raw.get("eventName") or raw.get("event_name") or raw.get("name") or raw.get("Event") or "-"
    importance = raw.get("importance") or raw.get("impact") or raw.get("Importance") or "-"
    relevance, semantic = classify_event(str(name), str(importance))
    country = raw.get("country") or raw.get("Country") or raw.get("currency") or raw.get("Currency") or "—"
    event = {
        "event_name": str(name),
        "country": str(country),
        "importance_source": str(importance),
        "relevance": relevance,
        "semantic": semantic,
        "scheduled_at": dt.isoformat(),
        "source": str(raw.get("source") or raw.get("Source") or "Economic Calendar"),
        "forecast": raw.get("forecast") if raw.get("forecast") is not None else raw.get("Forecast"),
        "previous": raw.get("previous") if raw.get("previous") is not None else raw.get("Previous"),
        "actual": raw.get("actual") if raw.get("actual") is not None else raw.get("Actual"),
    }
    event["surprise"] = economic_surprise(event)
    return event


def compute_macro_snapshot(events: list[dict], market: dict | None = None, now: datetime | None = None, data_ok: bool = True) -> dict:
    now = now or _now_utc()
    market = market or {"moves": {}, "regime": "NEUTRAL", "confidence": 0, "complete": False}
    upcoming = []
    recent = []
    for e in events:
        dt = _parse_dt(e.get("scheduled_at"))
        if not dt:
            continue
        mins = (dt - now).total_seconds() / 60.0
        item = dict(e)
        item["minutes_to_event"] = round(mins, 1)
        if mins >= 0:
            upcoming.append(item)
        elif mins >= -POST_EVENT_OBSERVE_MINUTES:
            recent.append(item)
    upcoming.sort(key=lambda e: e["minutes_to_event"])
    recent.sort(key=lambda e: e["minutes_to_event"], reverse=True)

    risk = "LOW"
    reasons: list[str] = []
    blocked = False
    multiplier = 1.0

    if not data_ok:
        risk, blocked, multiplier = "HIGH", True, 0.0
        reasons.append("Makro-/Kalenderdaten fehlen oder sind unsicher → fail-closed")
    else:
        for e in upcoming:
            rel = e.get("relevance", "LOW")
            mins = float(e.get("minutes_to_event", 999999))
            if rel == "CRITICAL" and mins <= EVENT_PAUSE_MINUTES:
                risk, blocked, multiplier = "CRITICAL", True, 0.0
                reasons.append(f"{e['event_name']} in {max(0, int(round(mins)))} Min. → neue Trades pausiert")
                break
            if rel == "HIGH" and mins <= EVENT_PAUSE_MINUTES and LEVEL_ORDER[risk] < LEVEL_ORDER["HIGH"]:
                risk, multiplier = "HIGH", 0.5
                reasons.append(f"HIGH Event {e['event_name']} steht kurz bevor")
            elif rel in {"CRITICAL", "HIGH"} and mins <= 360 and LEVEL_ORDER[risk] < LEVEL_ORDER["MEDIUM"]:
                risk, multiplier = "MEDIUM", 0.5
                reasons.append(f"Wichtiges Event {e['event_name']} in weniger als 6 Std.")

        # Released events: negative surprises + market confirmation can raise risk.
        for e in recent:
            surprise = e.get("surprise") or economic_surprise(e)
            if surprise.get("direction") == "NEGATIVE":
                if market.get("regime") == "RISK-OFF":
                    risk = "CRITICAL" if e.get("relevance") == "CRITICAL" else "HIGH"
                    blocked, multiplier = True, 0.0
                    reasons.append(f"{e['event_name']}: negative Überraschung + Markt bestätigt RISK-OFF")
                elif LEVEL_ORDER[risk] < LEVEL_ORDER["HIGH"]:
                    risk, multiplier = "HIGH", min(multiplier, 0.5)
                    reasons.append(f"{e['event_name']}: negative Economic Surprise")
            elif surprise.get("direction") in {"UNKNOWN", "CAUTION"} and e.get("relevance") in {"HIGH", "CRITICAL"}:
                if LEVEL_ORDER[risk] < LEVEL_ORDER["MEDIUM"]:
                    risk, multiplier = "MEDIUM", min(multiplier, 0.5)
                    reasons.append(f"{e['event_name']}: Ergebnis noch nicht eindeutig")

        if market.get("regime") == "RISK-OFF":
            if LEVEL_ORDER[risk] < LEVEL_ORDER["HIGH"]:
                risk = "HIGH"
            multiplier = min(multiplier, 0.5)
            reasons.append("Marktreaktion: RISK-OFF")
        # Fail-closed market completeness: incomplete reaction cannot create Risk-On or increase size.
        if not market.get("complete", False):
            if market.get("regime") == "RISK-ON":
                market = dict(market); market["regime"] = "NEUTRAL"
            multiplier = min(multiplier, 1.0)

    regime = market.get("regime", "NEUTRAL")
    if risk in {"HIGH", "CRITICAL"} and regime == "RISK-ON":
        regime = "NEUTRAL"
    if not reasons:
        reasons.append("Keine unmittelbar kritische Makrobelastung erkannt")
    next_event = upcoming[0] if upcoming else None
    return {
        "risk": risk,
        "regime": regime,
        "confidence": int(market.get("confidence", 0)),
        "allow_new_trade": not blocked,
        "position_multiplier": multiplier,
        "reason": " · ".join(reasons),
        "next_event": next_event,
        "upcoming": upcoming,
        "recent": recent,
        "market": market,
        "data_ok": data_ok,
    }
