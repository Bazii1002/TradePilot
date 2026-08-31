from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _f(value, default=0.0):
    try:
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except Exception:
        return float(default)


class PaperBroker:
    """Persistent local paper account. No real orders are sent anywhere.

    0.9.9 adds an explicit paper-order lifecycle. Signals can create pending
    orders while the market is closed; positions exist only after an order has
    been filled using a fresh regular-session quote.
    """

    def __init__(self, path: Path, initial_cash: float = 10000.0, currency: str = "USD"):
        self.path = Path(path)
        self.initial_cash = max(100.0, _f(initial_cash, 10000.0))
        self.currency = currency or "USD"
        self.state = self._load()

    def _blank(self) -> dict:
        now = _now()
        return {
            "version": 3,
            "currency": self.currency,
            "initial_cash": self.initial_cash,
            "cash": self.initial_cash,
            "positions": {},
            "orders": [],
            "trades": [],
            "equity_history": [{"time": now, "equity": self.initial_cash, "cash": self.initial_cash, "market_value": 0.0, "unrealized": 0.0, "realized": 0.0, "reason": "RESET"}],
            "updated": now,
        }

    def _load(self) -> dict:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    raw.setdefault("currency", self.currency)
                    raw.setdefault("initial_cash", self.initial_cash)
                    raw.setdefault("cash", raw.get("initial_cash", self.initial_cash))
                    raw.setdefault("positions", {})
                    raw.setdefault("orders", [])
                    raw.setdefault("trades", [])
                    raw.setdefault("equity_history", [])
                    raw["version"] = max(3, int(raw.get("version", 1) or 1))
                    return raw
        except Exception:
            pass
        return self._blank()

    def save(self) -> None:
        self.state["updated"] = _now()
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def reset(self, initial_cash: float | None = None) -> None:
        if initial_cash is not None:
            self.initial_cash = max(100.0, _f(initial_cash, self.initial_cash))
        self.state = self._blank()
        self.save()

    @property
    def cash(self) -> float:
        return _f(self.state.get("cash"))

    @property
    def positions(self) -> dict[str, dict]:
        return self.state.setdefault("positions", {})

    @property
    def orders(self) -> list[dict]:
        return self.state.setdefault("orders", [])

    @property
    def trades(self) -> list[dict]:
        return self.state.setdefault("trades", [])

    def has_position(self, symbol: str) -> bool:
        return str(symbol).upper() in self.positions

    def open_count(self) -> int:
        return len(self.positions)

    def pending_orders(self, side: str | None = None) -> list[dict]:
        out = [x for x in self.orders if str(x.get("status", "")).upper() == "PENDING"]
        if side:
            side = str(side).upper()
            out = [x for x in out if str(x.get("side", "")).upper() == side]
        return out

    def pending_count(self) -> int:
        return len(self.pending_orders())

    def has_pending_order(self, symbol: str, side: str | None = None) -> bool:
        symbol = str(symbol).upper()
        for order in self.pending_orders(side):
            if str(order.get("symbol", "")).upper() == symbol:
                return True
        return False

    def market_value(self) -> float:
        return sum(_f(p.get("shares")) * _f(p.get("last_price", p.get("entry_price"))) for p in self.positions.values())

    def equity(self) -> float:
        return self.cash + self.market_value()

    def unrealized_pnl(self) -> float:
        total = 0.0
        for p in self.positions.values():
            shares = _f(p.get("shares"))
            total += shares * (_f(p.get("last_price", p.get("entry_price"))) - _f(p.get("entry_price")))
        return total

    def realized_pnl(self) -> float:
        return sum(_f(t.get("pnl")) for t in self.trades if t.get("side") == "SELL")

    def update_price(self, symbol: str, price: float, quote_time: str | None = None,
                     quote_source: str | None = None, quote_fresh: bool | None = None) -> None:
        symbol = str(symbol).upper()
        if symbol not in self.positions:
            return
        price = _f(price)
        if price <= 0:
            return
        p = self.positions[symbol]
        p["last_price"] = price
        p["high_price"] = max(_f(p.get("high_price", p.get("entry_price"))), price)
        p["updated"] = _now()
        if quote_time is not None:
            p["quote_time"] = quote_time
        if quote_source is not None:
            p["quote_source"] = quote_source
        if quote_fresh is not None:
            p["quote_fresh"] = bool(quote_fresh)
        self.save()


    def record_equity_snapshot(self, reason: str = "REFRESH", min_interval_seconds: int = 30) -> None:
        """Store a compact local equity-curve point for performance monitoring."""
        now = datetime.now(timezone.utc)
        hist = self.state.setdefault("equity_history", [])
        point = {
            "time": now.isoformat(timespec="seconds"),
            "equity": self.equity(),
            "cash": self.cash,
            "market_value": self.market_value(),
            "unrealized": self.unrealized_pnl(),
            "realized": self.realized_pnl(),
            "reason": str(reason or "REFRESH"),
        }
        if hist:
            try:
                last = datetime.fromisoformat(str(hist[-1].get("time", "")).replace("Z", "+00:00"))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                age = (now - last.astimezone(timezone.utc)).total_seconds()
                if age < max(0, int(min_interval_seconds)):
                    hist[-1] = point
                    self.save()
                    return
            except Exception:
                pass
        hist.append(point)
        # Keep roughly a year of minute-level points without unbounded growth.
        if len(hist) > 25000:
            del hist[:-25000]
        self.save()

    def _order(self, order_id: str) -> dict | None:
        for order in self.orders:
            if str(order.get("order_id")) == str(order_id):
                return order
        return None

    def queue_buy(self, symbol: str, name: str, shares: int, reference_price: float, profile: str,
                  analysis: dict | None = None, reason: str = "AUTO_READY",
                  requires_autotrader: bool = True) -> tuple[bool, str, str | None]:
        symbol = str(symbol).upper()
        shares = int(shares or 0)
        reference_price = _f(reference_price)
        if not symbol or shares < 1 or reference_price <= 0:
            return False, "INVALID_ORDER", None
        if self.has_position(symbol):
            return False, "POSITION_EXISTS", None
        if self.has_pending_order(symbol, "BUY"):
            return False, "ORDER_EXISTS", None

        now = _now()
        snapshot = {
            "company": (analysis or {}).get("unternehmensscore"),
            "entry": (analysis or {}).get("einstieg_score"),
            "trap": (analysis or {}).get("trap_score"),
            "quality": (analysis or {}).get("fundamental_score"),
        }
        order_id = "ORD-" + uuid.uuid4().hex[:10].upper()
        order = {
            "order_id": order_id,
            "created": now,
            "updated": now,
            "side": "BUY",
            "status": "PENDING",
            "symbol": symbol,
            "name": name or symbol,
            "shares": shares,
            "reference_price": reference_price,
            "profile": profile,
            "sector": str((analysis or {}).get("sektor") or (analysis or {}).get("sector") or ""),
            "reason": reason,
            "requires_autotrader": bool(requires_autotrader),
            "entry_snapshot": snapshot,
            "status_reason": "WAITING_FOR_FRESH_MARKET_QUOTE",
        }
        self.orders.append(order)
        self.save()
        return True, "OK", order_id

    def queue_sell(self, symbol: str, reason: str = "EXIT", requires_autotrader: bool = True) -> tuple[bool, str, str | None]:
        symbol = str(symbol).upper()
        if not self.has_position(symbol):
            return False, "NO_POSITION", None
        if self.has_pending_order(symbol, "SELL"):
            return False, "ORDER_EXISTS", None
        p = self.positions[symbol]
        order_id = "ORD-" + uuid.uuid4().hex[:10].upper()
        now = _now()
        order = {
            "order_id": order_id,
            "created": now,
            "updated": now,
            "side": "SELL",
            "status": "PENDING",
            "symbol": symbol,
            "name": p.get("name", symbol),
            "shares": int(p.get("shares", 0) or 0),
            "reference_price": _f(p.get("last_price", p.get("entry_price"))),
            "profile": p.get("profile", "balanced"),
            "sector": p.get("sector", ""),
            "reason": reason,
            "requires_autotrader": bool(requires_autotrader),
            "status_reason": "WAITING_FOR_FRESH_MARKET_QUOTE",
        }
        self.orders.append(order)
        self.save()
        return True, "OK", order_id

    def mark_order(self, order_id: str, status: str, reason: str = "") -> bool:
        order = self._order(order_id)
        if not order:
            return False
        order["status"] = str(status).upper()
        order["status_reason"] = reason
        order["updated"] = _now()
        self.save()
        return True

    def cancel_pending_for_symbol(self, symbol: str, side: str | None = None, reason: str = "CANCELLED") -> int:
        symbol = str(symbol).upper()
        count = 0
        for order in self.pending_orders(side):
            if str(order.get("symbol", "")).upper() == symbol:
                order["status"] = "CANCELLED"
                order["status_reason"] = reason
                order["updated"] = _now()
                count += 1
        if count:
            self.save()
        return count

    def execute_pending(self, order_id: str, fill_price: float, *, market_price: float | None = None,
                        quote_time: str | None = None, quote_source: str | None = None,
                        slippage_bps: float = 0.0) -> tuple[bool, str, float]:
        order = self._order(order_id)
        if not order or str(order.get("status", "")).upper() != "PENDING":
            return False, "ORDER_NOT_PENDING", 0.0
        side = str(order.get("side", "BUY")).upper()
        symbol = str(order.get("symbol", "")).upper()
        price = _f(fill_price)
        if price <= 0:
            return False, "INVALID_PRICE", 0.0

        if side == "BUY":
            if self.has_position(symbol):
                self.mark_order(order_id, "CANCELLED", "POSITION_EXISTS")
                return False, "POSITION_EXISTS", 0.0
            shares = int(order.get("shares", 0) or 0)
            value = shares * price
            if shares < 1 or value > self.cash + 1e-9:
                self.mark_order(order_id, "REJECTED", "NOT_ENOUGH_CASH")
                return False, "NOT_ENOUGH_CASH", 0.0
            now = _now()
            trade_id = uuid.uuid4().hex[:12].upper()
            self.positions[symbol] = {
                "symbol": symbol,
                "name": order.get("name", symbol),
                "shares": shares,
                "entry_price": price,
                "last_price": price,
                "high_price": price,
                "entry_value": value,
                "profile": order.get("profile", "balanced"),
                "sector": order.get("sector", ""),
                "trade_id": trade_id,
                "order_id": order_id,
                "signal_time": order.get("created"),
                "opened": now,
                "updated": now,
                "reference_price": _f(order.get("reference_price")),
                "entry_snapshot": order.get("entry_snapshot", {}),
                "quote_time": quote_time,
                "quote_source": quote_source,
                "quote_fresh": True,
            }
            self.state["cash"] = self.cash - value
            self.trades.append({
                "time": now, "side": "BUY", "symbol": symbol, "name": order.get("name", symbol),
                "shares": shares, "price": price, "market_price": _f(market_price, price),
                "value": value, "profile": order.get("profile", "balanced"),
                "trade_id": trade_id, "order_id": order_id, "sector": order.get("sector", ""),
                "reason": order.get("reason", "AUTO_READY"), "pnl": 0.0,
                "slippage_bps": _f(slippage_bps), "quote_time": quote_time,
            })
            order["status"] = "FILLED"
            order["status_reason"] = "FILLED"
            order["filled"] = now
            order["fill_price"] = price
            order["market_price"] = _f(market_price, price)
            order["slippage_bps"] = _f(slippage_bps)
            order["updated"] = now
            self.save()
            self.record_equity_snapshot("BUY", 0)
            return True, "OK", 0.0

        # SELL
        if not self.has_position(symbol):
            self.mark_order(order_id, "CANCELLED", "NO_POSITION")
            return False, "NO_POSITION", 0.0
        p = self.positions[symbol]
        shares = int(p.get("shares", 0) or 0)
        value = shares * price
        cost = shares * _f(p.get("entry_price"))
        pnl = value - cost
        now = _now()
        self.state["cash"] = self.cash + value
        self.trades.append({
            "time": now, "side": "SELL", "symbol": symbol, "name": p.get("name", symbol),
            "shares": shares, "price": price, "market_price": _f(market_price, price),
            "value": value, "profile": p.get("profile", "balanced"),
            "trade_id": p.get("trade_id"), "order_id": order_id, "sector": p.get("sector", ""),
            "reason": order.get("reason", "EXIT"), "pnl": pnl,
            "slippage_bps": _f(slippage_bps), "quote_time": quote_time,
        })
        del self.positions[symbol]
        order["status"] = "FILLED"
        order["status_reason"] = "FILLED"
        order["filled"] = now
        order["fill_price"] = price
        order["market_price"] = _f(market_price, price)
        order["slippage_bps"] = _f(slippage_bps)
        order["updated"] = now
        self.save()
        self.record_equity_snapshot("SELL", 0)
        return True, "OK", pnl

    # Compatibility helpers retained for existing UI/tests. Direct BUY/SELL are
    # still available for legacy state, but 0.9.10 AutoTrader routes new orders
    # through queue + execute_pending.
    def buy(self, symbol: str, name: str, shares: int, price: float, profile: str,
            analysis: dict | None = None, reason: str = "AUTO_READY") -> tuple[bool, str]:
        ok, reason_code, oid = self.queue_buy(symbol, name, shares, price, profile, analysis, reason, requires_autotrader=False)
        if not ok or not oid:
            return False, reason_code
        ok2, reason2, _ = self.execute_pending(oid, price, market_price=price, slippage_bps=0.0)
        return ok2, reason2

    def sell(self, symbol: str, price: float, reason: str = "EXIT") -> tuple[bool, str, float]:
        ok, reason_code, oid = self.queue_sell(symbol, reason, requires_autotrader=False)
        if not ok or not oid:
            return False, reason_code, 0.0
        return self.execute_pending(oid, price, market_price=price, slippage_bps=0.0)
