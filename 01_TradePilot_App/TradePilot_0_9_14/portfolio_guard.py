from __future__ import annotations

import math

"""Portfolio-level concentration and investment limits for Paper AutoTrader."""

LIMITS = {
    "defensive": {"max_sector_pct": 0.25, "max_invested_pct": 0.70},
    "balanced": {"max_sector_pct": 0.30, "max_invested_pct": 0.80},
    "offensive": {"max_sector_pct": 0.35, "max_invested_pct": 0.85},
    "speculative": {"max_sector_pct": 0.40, "max_invested_pct": 0.85},
}


def _f(v, d=0.0):
    try:
        out = float(v)
        return out if math.isfinite(out) else float(d)
    except Exception:
        return float(d)


def evaluate_portfolio_guard(broker, candidate: dict | None, profile: str, planned_value: float = 0.0) -> dict:
    cfg = LIMITS.get(profile, LIMITS["balanced"])
    equity = max(0.0, _f(broker.equity()))
    invested = max(0.0, _f(broker.market_value()))
    planned = max(0.0, _f(planned_value))
    sector = str((candidate or {}).get("sektor") or (candidate or {}).get("sector") or "").strip()
    blocks: list[str] = []
    warnings: list[str] = []

    projected_invested_pct = ((invested + planned) / equity) if equity > 0 else 1.0
    if projected_invested_pct > cfg["max_invested_pct"] + 1e-9:
        blocks.append("MAX_PORTFOLIO_INVESTMENT")

    sector_value = 0.0
    if sector:
        for p in broker.positions.values():
            if str(p.get("sector", "")).strip().lower() == sector.lower():
                sector_value += _f(p.get("shares")) * _f(p.get("last_price", p.get("entry_price")))
        projected_sector_pct = ((sector_value + planned) / equity) if equity > 0 else 1.0
        if projected_sector_pct > cfg["max_sector_pct"] + 1e-9:
            blocks.append("MAX_SECTOR_EXPOSURE")
    else:
        projected_sector_pct = None
        warnings.append("SECTOR_UNKNOWN")

    return {
        "allowed": not blocks,
        "blocks": blocks,
        "warnings": warnings,
        "sector": sector or None,
        "sector_value": sector_value,
        "projected_sector_pct": projected_sector_pct,
        "projected_invested_pct": projected_invested_pct,
        "limits": cfg,
    }
