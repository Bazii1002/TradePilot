from __future__ import annotations

"""TradePilot 0.9.10 paper Order Engine.

This module deliberately has no broker/network side effects. It validates quote
freshness/session state, calculates deterministic paper slippage, and performs
execution-time safety checks for pending paper orders.
"""

import math
from datetime import datetime, timezone

from portfolio_guard import evaluate_portfolio_guard
from risk_manager import RISK_LIMITS


DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_MAX_ORDER_AGE_HOURS = 96.0
DEFAULT_MAX_GAP_PCT = 3.0


def _f(value, default=0.0):
    try:
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except Exception:
        return float(default)


def quote_is_executable(quote: dict | None) -> tuple[bool, str]:
    quote = quote or {}
    price = _f(quote.get("price"), 0.0)
    if price <= 0:
        return False, "NO_PRICE"
    if not bool(quote.get("session_open", False)):
        return False, "MARKET_CLOSED"
    if not bool(quote.get("fresh", False)):
        return False, "STALE_QUOTE"
    return True, "OK"


def apply_slippage(price: float, side: str, slippage_bps: float = DEFAULT_SLIPPAGE_BPS) -> float:
    """Return a conservative deterministic paper fill.

    BUY fills slightly above the observed quote, SELL slightly below it.
    """
    price = max(0.0, _f(price, 0.0))
    bps = max(0.0, min(100.0, _f(slippage_bps, DEFAULT_SLIPPAGE_BPS)))
    direction = 1.0 if str(side).upper() == "BUY" else -1.0
    return price * (1.0 + direction * bps / 10000.0)


def order_age_hours(order: dict | None) -> float:
    try:
        created = datetime.fromisoformat(str((order or {}).get("created", "")).replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds() / 3600.0)
    except Exception:
        return 0.0


def validate_pending_execution(
    broker,
    order: dict,
    quote: dict,
    *,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    max_order_age_hours: float = DEFAULT_MAX_ORDER_AGE_HOURS,
    max_gap_pct: float = DEFAULT_MAX_GAP_PCT,
    max_trade_value: float | None = None,
) -> dict:
    """Re-check an order immediately before a paper fill.

    Pending BUY orders are revalidated against cash reserve, max positions,
    portfolio/sector concentration, order age and excessive quote gaps. Pending
    SELL orders only require the corresponding open position and a fresh quote.
    """
    executable, quote_reason = quote_is_executable(quote)
    side = str(order.get("side", "BUY")).upper()
    market_price = _f((quote or {}).get("price"), 0.0)
    fill_price = apply_slippage(market_price, side, slippage_bps)
    blocks: list[str] = []

    if not executable:
        blocks.append(quote_reason)

    age = order_age_hours(order)
    if age > max(1.0, _f(max_order_age_hours, DEFAULT_MAX_ORDER_AGE_HOURS)):
        blocks.append("ORDER_EXPIRED")

    symbol = str(order.get("symbol", "")).upper()
    if side == "BUY":
        if broker.has_position(symbol):
            blocks.append("POSITION_EXISTS")
        profile = str(order.get("profile") or "balanced")
        cfg = RISK_LIMITS.get(profile, RISK_LIMITS["balanced"])
        if broker.open_count() >= int(cfg["max_positions"]):
            blocks.append("MAX_POSITIONS")

        shares = max(0, int(order.get("shares", 0) or 0))
        planned_value = shares * fill_price
        if shares < 1 or planned_value <= 0:
            blocks.append("INVALID_ORDER")
        hard_trade_cap = _f(max_trade_value, 0.0)
        if hard_trade_cap > 0 and planned_value > hard_trade_cap + 1e-9:
            blocks.append("MAX_TRADE_VALUE")

        reference = _f(order.get("reference_price"), 0.0)
        if reference > 0 and market_price > 0:
            gap_pct = ((market_price / reference) - 1.0) * 100.0
            # Large gaps in either direction mean the old signal should be
            # re-analysed rather than blindly filled at the new market state.
            if abs(gap_pct) > max(0.25, _f(max_gap_pct, DEFAULT_MAX_GAP_PCT)):
                blocks.append("PRICE_GAP_TOO_LARGE")
        else:
            gap_pct = None

        equity = max(0.0, _f(broker.equity(), 0.0))
        reserve = equity * _f(cfg.get("cash_reserve_pct"), 0.0)
        if broker.cash - planned_value < reserve - 1e-9:
            blocks.append("CASH_RESERVE")
        if planned_value > broker.cash + 1e-9:
            blocks.append("NOT_ENOUGH_CASH")

        candidate = {"sector": order.get("sector", "")}
        portfolio = evaluate_portfolio_guard(broker, candidate, profile, planned_value)
        blocks.extend(list(portfolio.get("blocks", [])))
    else:
        gap_pct = None
        portfolio = None
        if not broker.has_position(symbol):
            blocks.append("NO_POSITION")

    # stable de-duplication while retaining deterministic order
    clean_blocks: list[str] = []
    for block in blocks:
        if block and block not in clean_blocks:
            clean_blocks.append(block)

    return {
        "allowed": not clean_blocks,
        "blocks": clean_blocks,
        "market_price": market_price,
        "fill_price": fill_price,
        "slippage_bps": max(0.0, _f(slippage_bps, DEFAULT_SLIPPAGE_BPS)),
        "age_hours": age,
        "gap_pct": gap_pct,
        "portfolio": portfolio,
    }
