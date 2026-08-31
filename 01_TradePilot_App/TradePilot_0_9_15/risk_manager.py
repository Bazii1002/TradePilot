from __future__ import annotations

"""TradePilot Risk Manager 0.9.10 — paper position sizing only.

The risk manager does not decide *whether* a stock is attractive. It only
calculates a safe paper position after the Strategy Engine has produced a
candidate. The frozen research score weights are not changed here.
"""

import math

RISK_LIMITS = {
    "defensive": {"position_pct": 0.05, "max_positions": 5, "cash_reserve_pct": 0.30},
    "balanced": {"position_pct": 0.075, "max_positions": 8, "cash_reserve_pct": 0.20},
    "offensive": {"position_pct": 0.09, "max_positions": 10, "cash_reserve_pct": 0.15},
    "speculative": {"position_pct": 0.06, "max_positions": 12, "cash_reserve_pct": 0.15},
}


def _finite(value, default: float | None = None) -> float | None:
    try:
        out = float(value)
        if not math.isfinite(out):
            return default
        return out
    except Exception:
        return default


def _valid_price_from_analysis(data: dict | None) -> float | None:
    """Return a finite positive price, falling back to the last valid Close."""
    data = data or {}
    price = _finite((data.get("trend") or {}).get("kurs"))
    if price is not None and price > 0:
        return price

    history = data.get("historie")
    try:
        close = history["Close"].dropna()
        # yfinance can occasionally leave an invalid placeholder row at the end.
        for value in reversed(close.tolist()):
            p = _finite(value)
            if p is not None and p > 0:
                return p
    except Exception:
        pass
    return None


def calculate_position(data: dict | None, profile: str, capital: float = 10000.0,
                       open_positions: int = 0, available_cash: float | None = None,
                       max_trade_value: float | None = None) -> dict:
    cfg = RISK_LIMITS.get(profile, RISK_LIMITS["balanced"])
    capital = max(0.0, _finite(capital, 0.0) or 0.0)
    cash = capital if available_cash is None else max(0.0, _finite(available_cash, 0.0) or 0.0)
    price = _valid_price_from_analysis(data)

    reserve = capital * cfg["cash_reserve_pct"]
    tradable_cash = max(0.0, cash - reserve)
    # Dynamic sizing is deliberately separate from the frozen analysis engine.
    # Stronger signals may use more of the profile budget; high volatility reduces it.
    company = _finite((data or {}).get("unternehmensscore"), 50.0) or 50.0
    entry = _finite((data or {}).get("einstieg_score"), 50.0) or 50.0
    trap = _finite((data or {}).get("trap_score"), 50.0) or 50.0
    strength = max(0.0, min(100.0, company * 0.45 + entry * 0.45 + (100.0 - trap) * 0.10))
    if strength >= 85:
        signal_multiplier = 1.00
    elif strength >= 75:
        signal_multiplier = 0.90
    elif strength >= 65:
        signal_multiplier = 0.78
    elif strength >= 55:
        signal_multiplier = 0.65
    else:
        signal_multiplier = 0.55

    volatility_pct = None
    volatility_multiplier = 1.0
    try:
        hist = (data or {}).get("historie")
        close = hist["Close"].dropna().tail(61)
        if len(close) >= 20:
            rets = close.pct_change().dropna()
            volatility_pct = float(rets.std() * (252 ** 0.5) * 100.0)
            if math.isfinite(volatility_pct):
                if volatility_pct >= 70:
                    volatility_multiplier = 0.55
                elif volatility_pct >= 50:
                    volatility_multiplier = 0.70
                elif volatility_pct >= 35:
                    volatility_multiplier = 0.85
    except Exception:
        volatility_pct = None
        volatility_multiplier = 1.0

    profile_budget = max(0.0, capital * cfg["position_pct"])
    target_position = profile_budget * signal_multiplier * volatility_multiplier
    hard_max_trade = _finite(max_trade_value)
    if hard_max_trade is not None and hard_max_trade > 0:
        target_position = min(target_position, hard_max_trade)
    position_cap = min(target_position, tradable_cash)
    max_positions = cfg["max_positions"]

    blocks: list[str] = []
    if open_positions >= max_positions:
        blocks.append("MAX_POSITIONS")
    if price is None or price <= 0:
        blocks.append("NO_PRICE")

    shares = 0
    planned_value = 0.0
    if price is not None and price > 0 and position_cap > 0:
        shares = int(math.floor((position_cap + 1e-9) / price))
        planned_value = shares * price

        # A whole-share paper account can otherwise block a perfectly affordable
        # $800 stock just because the target position is $750. Allow one share if
        # it still respects the global cash reserve and investment guard. The
        # portfolio guard remains responsible for portfolio/sector concentration.
        hard_cap_ok = hard_max_trade is None or hard_max_trade <= 0 or price <= hard_max_trade + 1e-9
        if shares < 1 and price <= tradable_cash + 1e-9 and hard_cap_ok:
            shares = 1
            planned_value = price

    if price is not None and price > 0 and shares < 1:
        blocks.append("CAPITAL_TOO_LOW")

    # Defensive final cash check: never plan to spend cash that is not available.
    if planned_value > cash + 1e-9:
        if "CAPITAL_TOO_LOW" not in blocks:
            blocks.append("CAPITAL_TOO_LOW")
        shares = 0
        planned_value = 0.0

    return {
        "capital": capital,
        "available_cash": cash,
        "reserve": reserve,
        "tradable_cash": tradable_cash,
        "profile_budget": profile_budget,
        "target_position": target_position,
        "position_cap": position_cap,
        "max_trade_value": hard_max_trade,
        "signal_strength": strength,
        "signal_multiplier": signal_multiplier,
        "volatility_pct": volatility_pct,
        "volatility_multiplier": volatility_multiplier,
        "position_pct": cfg["position_pct"],
        "max_positions": max_positions,
        "shares": shares,
        "planned_value": planned_value,
        "price": price,
        "blocks": list(dict.fromkeys(blocks)),
        "allowed": not blocks,
    }
