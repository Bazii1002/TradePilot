from __future__ import annotations

"""TradePilot Strategy Engine 0.9

Evaluates an existing TradePilot analysis. It does not place orders and it does
not modify the frozen research/analysis engine.
"""

PROFILES = {
    "defensive": {
        "label_de": "Defensiv", "label_en": "Defensive",
        "company": 80, "entry": 70, "trap_max": 20,
        "quality": 80, "development": 65, "valuation": 45, "trend": 55,
        "required_confirmations": 6,
    },
    "balanced": {
        "label_de": "Ausgewogen", "label_en": "Balanced",
        "company": 70, "entry": 65, "trap_max": 40,
        "quality": 70, "development": 55, "valuation": 40, "trend": 45,
        "required_confirmations": 5,
    },
    "offensive": {
        "label_de": "Offensiv", "label_en": "Offensive",
        "company": 60, "entry": 55, "trap_max": 55,
        "quality": 60, "development": 45, "valuation": 35, "trend": 35,
        "required_confirmations": 4,
    },
    "speculative": {
        "label_de": "Spekulativ", "label_en": "Speculative",
        "company": 50, "entry": 48, "trap_max": 70,
        "quality": 50, "development": 35, "valuation": 30, "trend": 25,
        "required_confirmations": 3,
    },
}


def profile_label(profile: str, language: str = "de") -> str:
    p = PROFILES.get(profile, PROFILES["balanced"])
    return p["label_en"] if language == "en" else p["label_de"]


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def evaluate_strategy(data: dict | None, profile: str = "balanced") -> dict:
    """Return a transparent strategy decision for a completed stock analysis.

    confidence is a confirmation score (0..100), not a probability of profit.
    """
    cfg = PROFILES.get(profile, PROFILES["balanced"])
    if not data:
        return {
            "decision": "NO_DATA", "confidence": 0, "checks": [],
            "passed": 0, "total": 0, "hard_blocks": [], "profile": profile,
        }

    company = _num(data.get("unternehmensscore"))
    entry = _num(data.get("einstieg_score"))
    trap = _num(data.get("trap_score"), 100)
    quality = _num(data.get("fundamental_score"))
    development = _num(data.get("entwicklungs_score"))
    valuation = _num(data.get("bewertungs_score"))
    trend = _num((data.get("trend") or {}).get("trend_score"))

    checks = [
        {"key": "company", "value": company, "target": cfg["company"], "mode": "min", "ok": company >= cfg["company"]},
        {"key": "entry", "value": entry, "target": cfg["entry"], "mode": "min", "ok": entry >= cfg["entry"]},
        {"key": "trap", "value": trap, "target": cfg["trap_max"], "mode": "max", "ok": trap < cfg["trap_max"]},
        {"key": "quality", "value": quality, "target": cfg["quality"], "mode": "min", "ok": quality >= cfg["quality"]},
        {"key": "development", "value": development, "target": cfg["development"], "mode": "min", "ok": development >= cfg["development"]},
        {"key": "valuation", "value": valuation, "target": cfg["valuation"], "mode": "min", "ok": valuation >= cfg["valuation"]},
        {"key": "trend", "value": trend, "target": cfg["trend"], "mode": "min", "ok": trend >= cfg["trend"]},
    ]

    passed = sum(1 for item in checks if item["ok"])
    total = len(checks)

    # Weighted confirmation degree. This is deliberately not called a win rate.
    weights = {"company": 1.4, "entry": 1.5, "trap": 1.5, "quality": 1.2, "development": 1.0, "valuation": 0.7, "trend": 0.7}
    weight_total = sum(weights.values())
    achieved = sum(weights[item["key"]] for item in checks if item["ok"])
    confidence = round(100 * achieved / weight_total)

    # Safety rails remain active in every profile. A speculative profile may
    # enter earlier, but it does not bypass extreme value-trap / company risk.
    hard_blocks = []
    if trap >= 80:
        hard_blocks.append("EXTREME_TRAP")
    if company < 35:
        hard_blocks.append("VERY_WEAK_COMPANY")
    if quality < 35:
        hard_blocks.append("VERY_LOW_QUALITY")

    core_ok = company >= cfg["company"] and entry >= cfg["entry"] and trap < cfg["trap_max"]
    enough = passed >= cfg["required_confirmations"]

    if hard_blocks:
        decision = "BLOCKED"
    elif core_ok and enough:
        decision = "READY"
    elif company >= max(40, cfg["company"] - 10) and trap < min(75, cfg["trap_max"] + 15):
        decision = "WAIT"
    else:
        decision = "REJECT"

    return {
        "decision": decision,
        "confidence": confidence,
        "checks": checks,
        "passed": passed,
        "total": total,
        "hard_blocks": hard_blocks,
        "profile": profile,
        "required_confirmations": cfg["required_confirmations"],
    }
