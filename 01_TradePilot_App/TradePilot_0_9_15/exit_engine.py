from __future__ import annotations

import math
from datetime import datetime, timezone

EXIT_RULES = {
    "defensive": {"stop_loss": -8.0, "take_profit": 18.0, "trailing": 7.0, "max_days": 90, "trap_exit": 55, "company_exit": 45},
    "balanced": {"stop_loss": -10.0, "take_profit": 22.0, "trailing": 9.0, "max_days": 120, "trap_exit": 65, "company_exit": 40},
    "offensive": {"stop_loss": -12.0, "take_profit": 28.0, "trailing": 11.0, "max_days": 150, "trap_exit": 75, "company_exit": 35},
    "speculative": {"stop_loss": -15.0, "take_profit": 35.0, "trailing": 13.0, "max_days": 180, "trap_exit": 80, "company_exit": 35},
}


def _f(value, default=0.0):
    try:
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except Exception:
        return float(default)


def _days(opened: str | None) -> int:
    try:
        dt = datetime.fromisoformat(str(opened).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return 0


def evaluate_exit(position: dict, analysis: dict | None = None, profile: str | None = None) -> dict:
    profile = profile or position.get("profile", "balanced")
    cfg = EXIT_RULES.get(profile, EXIT_RULES["balanced"])
    entry = _f(position.get("entry_price"))
    price = _f(position.get("last_price", entry))
    high = max(entry, _f(position.get("high_price", price)))
    perf = ((price / entry) - 1) * 100 if entry > 0 else 0.0
    from_high = ((price / high) - 1) * 100 if high > 0 else 0.0
    days = _days(position.get("opened"))

    reasons = []
    if perf <= cfg["stop_loss"]:
        reasons.append("STOP_LOSS")
    if perf >= cfg["take_profit"]:
        reasons.append("TAKE_PROFIT")
    # Trailing stop becomes active after at least +6% profit, avoiding immediate noise.
    if high >= entry * 1.06 and from_high <= -cfg["trailing"]:
        reasons.append("TRAILING_STOP")
    if days >= cfg["max_days"]:
        reasons.append("MAX_HOLDING_TIME")

    if analysis:
        trap = _f(analysis.get("trap_score"), 100)
        company = _f(analysis.get("unternehmensscore"))
        if trap >= cfg["trap_exit"]:
            reasons.append("TRAP_DETERIORATION")
        if company < cfg["company_exit"]:
            reasons.append("COMPANY_DETERIORATION")

    return {
        "exit": bool(reasons),
        "reason": reasons[0] if reasons else None,
        "reasons": reasons,
        "performance_pct": perf,
        "drawdown_from_high_pct": from_high,
        "days": days,
        "rules": cfg,
    }
