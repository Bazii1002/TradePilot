from __future__ import annotations

import math
from collections import defaultdict

from exit_engine import EXIT_RULES
from portfolio_guard import LIMITS as PORTFOLIO_LIMITS
from risk_manager import RISK_LIMITS, calculate_position
from portfolio_guard import evaluate_portfolio_guard


def _f(value, default=0.0):
    try:
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except Exception:
        return float(default)


def performance_metrics(broker) -> dict:
    initial = max(0.01, _f(broker.state.get("initial_cash"), 10000.0))
    equity = _f(broker.equity())
    total_pnl = equity - initial
    total_return_pct = total_pnl / initial * 100.0
    sells = [t for t in broker.trades if str(t.get("side", "")).upper() == "SELL"]
    pnls = [_f(t.get("pnl")) for t in sells]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 1e-12 else (float("inf") if gross_win > 0 else 0.0)

    hist = list(broker.state.get("equity_history") or [])
    values = [_f(x.get("equity")) for x in hist if _f(x.get("equity")) > 0]
    max_dd = 0.0
    peak = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            dd = (value / peak - 1.0) * 100.0
            max_dd = min(max_dd, dd)

    today = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).date()
    prior_equity = None
    first_today = None
    for point in hist:
        try:
            dt = __import__("datetime").datetime.fromisoformat(str(point.get("time", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=__import__("datetime").timezone.utc)
            if dt.astimezone(__import__("datetime").timezone.utc).date() < today:
                prior_equity = _f(point.get("equity"))
            elif dt.astimezone(__import__("datetime").timezone.utc).date() == today and first_today is None:
                first_today = _f(point.get("equity"))
        except Exception:
            pass
    day_base = prior_equity if prior_equity and prior_equity > 0 else (first_today if first_today and first_today > 0 else equity)
    day_pnl = equity - day_base
    day_return_pct = day_pnl / day_base * 100.0 if day_base > 0 else 0.0

    return {
        "initial": initial,
        "equity": equity,
        "cash": _f(broker.cash),
        "market_value": _f(broker.market_value()),
        "unrealized": _f(broker.unrealized_pnl()),
        "realized": _f(broker.realized_pnl()),
        "total_pnl": total_pnl,
        "return_pct": total_return_pct,
        "day_pnl": day_pnl,
        "day_return_pct": day_return_pct,
        "closed_trades": len(sells),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(sells) * 100.0) if sells else 0.0,
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (sum(losses) / len(losses)) if losses else 0.0,
        "best_trade": max(pnls) if pnls else 0.0,
        "worst_trade": min(pnls) if pnls else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_dd,
        "history": hist,
    }


def sector_exposure(broker) -> list[dict]:
    equity = max(0.01, _f(broker.equity()))
    totals = defaultdict(float)
    for p in broker.positions.values():
        sector = str(p.get("sector") or "Unbekannt")
        totals[sector] += _f(p.get("shares")) * _f(p.get("last_price", p.get("entry_price")))
    return [
        {"sector": sector, "value": value, "pct": value / equity * 100.0}
        for sector, value in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]


def risk_overview(broker, profile: str, max_trade_value: float | None = None) -> dict:
    r = RISK_LIMITS.get(profile, RISK_LIMITS["balanced"])
    p = PORTFOLIO_LIMITS.get(profile, PORTFOLIO_LIMITS["balanced"])
    equity = max(0.01, _f(broker.equity()))
    invested = _f(broker.market_value())
    pending = sum(_f(o.get("shares")) * _f(o.get("reference_price")) for o in broker.pending_orders("BUY"))
    max_trade = max(0.0, _f(max_trade_value, 0.0))
    profile_trade = equity * _f(r.get("position_pct"))
    effective_trade = min(profile_trade, max_trade) if max_trade > 0 else profile_trade
    return {
        "profile": profile,
        "equity": equity,
        "invested": invested,
        "pending": pending,
        "invested_pct": invested / equity * 100.0,
        "committed_pct": (invested + pending) / equity * 100.0,
        "cash_pct": _f(broker.cash) / equity * 100.0,
        "position_count": broker.open_count(),
        "pending_count": broker.pending_count(),
        "position_pct_limit": _f(r.get("position_pct")) * 100.0,
        "effective_trade_limit": effective_trade,
        "absolute_trade_limit": max_trade,
        "max_positions": int(r.get("max_positions", 0)),
        "cash_reserve_pct": _f(r.get("cash_reserve_pct")) * 100.0,
        "max_sector_pct": _f(p.get("max_sector_pct")) * 100.0,
        "max_invested_pct": _f(p.get("max_invested_pct")) * 100.0,
    }


def position_rows(broker) -> list[dict]:
    equity = max(0.01, _f(broker.equity()))
    rows = []
    for symbol, pos in broker.positions.items():
        entry = _f(pos.get("entry_price"))
        last = _f(pos.get("last_price", entry))
        high = max(entry, _f(pos.get("high_price", last)))
        shares = int(pos.get("shares", 0) or 0)
        value = shares * last
        pnl = shares * (last - entry)
        pnl_pct = ((last / entry) - 1.0) * 100.0 if entry > 0 else 0.0
        profile = str(pos.get("profile") or "balanced")
        rules = EXIT_RULES.get(profile, EXIT_RULES["balanced"])
        stop = entry * (1.0 + _f(rules.get("stop_loss")) / 100.0) if entry > 0 else 0.0
        take = entry * (1.0 + _f(rules.get("take_profit")) / 100.0) if entry > 0 else 0.0
        trailing = high * (1.0 - _f(rules.get("trailing")) / 100.0) if high >= entry * 1.06 and entry > 0 else None
        dist_stop = ((last / stop) - 1.0) * 100.0 if stop > 0 else 999.0
        if last <= stop:
            risk = "EXIT"
        elif dist_stop <= 2.0:
            risk = "HIGH"
        elif pnl_pct < 0:
            risk = "WATCH"
        else:
            risk = "OK"
        rows.append({
            "symbol": symbol,
            "name": pos.get("name", symbol),
            "sector": pos.get("sector") or "—",
            "shares": shares,
            "entry": entry,
            "last": last,
            "high": high,
            "value": value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "portfolio_pct": value / equity * 100.0,
            "stop": stop,
            "take": take,
            "trailing": trailing,
            "profile": profile,
            "risk": risk,
        })
    return sorted(rows, key=lambda x: x["value"], reverse=True)


def candidate_position_plan(data: dict | None, broker, profile: str, max_trade_value: float | None = None) -> dict:
    if not data:
        return {"available": False}
    risk = calculate_position(
        data, profile, broker.equity(), broker.open_count(), broker.cash,
        max_trade_value=max_trade_value,
    )
    guard = evaluate_portfolio_guard(broker, data, profile, risk.get("planned_value", 0.0))
    blocks = list(dict.fromkeys(list(risk.get("blocks", [])) + list(guard.get("blocks", []))))
    return {
        "available": True,
        "symbol": data.get("symbol", ""),
        "name": data.get("name", data.get("symbol", "")),
        "risk": risk,
        "guard": guard,
        "blocks": blocks,
        "allowed": not blocks,
    }
