from __future__ import annotations

import json
import math
import random
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


LEVELS = {
    1: {"name": "FAST", "interval": 5, "hold_cycles": 3, "threshold": 0.78},
    2: {"name": "DAY", "interval": 7, "hold_cycles": 5, "threshold": 0.74},
    3: {"name": "WEEK", "interval": 9, "hold_cycles": 8, "threshold": 0.70},
    4: {"name": "INVEST", "interval": 12, "hold_cycles": 12, "threshold": 0.66},
}
UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "TSLA", "ORCL", "ADBE", "AVGO", "NFLX"]


class BotEngine(QObject):
    changed = Signal()

    def __init__(self, app_dir: Path):
        super().__init__()
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "shadow_state.json"
        self._running = False
        self._level = 2
        self._scan_count = 0
        self._last_scan = "Noch kein Scan"
        self._next_scan = "—"
        self._status = "STOPPED"
        self._last_action = "Bot wartet auf Start"
        self._market_rows = []
        self._positions = []
        self._trades = []
        self._events = []
        self._paper_cash = 1000.0
        self._paper_equity = 1000.0
        self._pnl = 0.0
        self._max_positions = 3
        self._trade_size = 10.0
        self._cycle = 0
        self._load_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._cycle_once)
        self._apply_interval()

    def _apply_interval(self):
        self.timer.setInterval(LEVELS[self._level]["interval"] * 1000)

    def _log(self, text: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._events.insert(0, {"time": stamp, "text": text})
        self._events = self._events[:60]

    def _save_state(self):
        payload = {
            "level": self._level,
            "scan_count": self._scan_count,
            "positions": self._positions,
            "trades": self._trades[-200:],
            "events": self._events[:60],
            "paper_cash": self._paper_cash,
            "paper_equity": self._paper_equity,
            "pnl": self._pnl,
            "cycle": self._cycle,
        }
        try:
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.state_file)
        except Exception:
            pass

    def _load_state(self):
        if not self.state_file.exists():
            return
        try:
            p = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._level = int(p.get("level", self._level)) if int(p.get("level", self._level)) in LEVELS else 2
            self._scan_count = int(p.get("scan_count", 0))
            self._positions = list(p.get("positions") or [])
            self._trades = list(p.get("trades") or [])
            self._events = list(p.get("events") or [])
            self._paper_cash = float(p.get("paper_cash", 1000.0))
            self._paper_equity = float(p.get("paper_equity", 1000.0))
            self._pnl = float(p.get("pnl", 0.0))
            self._cycle = int(p.get("cycle", 0))
        except Exception:
            pass

    @Property(bool, notify=changed)
    def running(self): return self._running

    @Property(str, notify=changed)
    def statusText(self): return self._status

    @Property(str, notify=changed)
    def levelName(self): return LEVELS[self._level]["name"]

    @Property(int, notify=changed)
    def level(self): return self._level

    @Property(str, notify=changed)
    def lastScanText(self): return self._last_scan

    @Property(str, notify=changed)
    def nextScanText(self): return self._next_scan

    @Property(int, notify=changed)
    def scanCount(self): return self._scan_count

    @Property(int, notify=changed)
    def openPositions(self): return len(self._positions)

    @Property(int, notify=changed)
    def tradeCount(self): return len(self._trades)

    @Property(str, notify=changed)
    def lastActionText(self): return self._last_action

    @Property(str, notify=changed)
    def paperCashText(self): return f"${self._paper_cash:,.2f}"

    @Property(str, notify=changed)
    def paperEquityText(self): return f"${self._paper_equity:,.2f}"

    @Property(str, notify=changed)
    def pnlText(self):
        sign = "+" if self._pnl > 0 else ""
        return f"{sign}${self._pnl:,.2f}"

    @Property(str, notify=changed)
    def marketRowsJson(self): return json.dumps(self._market_rows)

    @Property(str, notify=changed)
    def positionsJson(self): return json.dumps(self._positions)

    @Property(str, notify=changed)
    def tradesJson(self): return json.dumps(list(reversed(self._trades[-100:])))

    @Property(str, notify=changed)
    def eventsJson(self): return json.dumps(self._events)

    @Property(str, notify=changed)
    def modeText(self): return "SHADOW / PAPER"

    @Property(str, notify=changed)
    def realLockText(self): return "REAL AUTOTRADING LOCKED"

    @Slot()
    def startBot(self):
        if self._running:
            return
        self._running = True
        self._status = "RUNNING"
        self._log(f"Bot gestartet · Stufe {self._level} {self.levelName}")
        self._apply_interval()
        self.timer.start()
        self._cycle_once()
        self.changed.emit()

    @Slot()
    def stopBot(self):
        self.timer.stop()
        self._running = False
        self._status = "STOPPED"
        self._next_scan = "—"
        self._log("Bot gestoppt · offene Shadow-Positionen bleiben gespeichert")
        self._save_state()
        self.changed.emit()

    @Slot(int)
    def setLevel(self, level):
        level = int(level)
        if level not in LEVELS:
            return
        self._level = level
        self._apply_interval()
        if self._running:
            self.timer.start()
        self._log(f"Neue Bot-Stufe für neue Trades: {level} {LEVELS[level]['name']}")
        self._save_state()
        self.changed.emit()

    @Slot()
    def resetShadow(self):
        if self._running:
            self.stopBot()
        self._positions = []
        self._trades = []
        self._events = []
        self._paper_cash = 1000.0
        self._paper_equity = 1000.0
        self._pnl = 0.0
        self._scan_count = 0
        self._cycle = 0
        self._last_action = "Shadow-Konto zurückgesetzt"
        try:
            self.state_file.unlink(missing_ok=True)
        except Exception:
            pass
        self.changed.emit()

    @Slot()
    def forceScan(self):
        self._cycle_once()

    def _cycle_once(self):
        self._cycle += 1
        self._scan_count += 1
        now = datetime.now()
        self._last_scan = now.strftime("%H:%M:%S")
        self._next_scan = f"in {LEVELS[self._level]['interval']} Sek."
        rnd = random.Random(int(now.strftime("%Y%m%d%H%M")) * 1000 + self._cycle * 17 + self._level)
        threshold = LEVELS[self._level]["threshold"]

        rows = []
        for i, symbol in enumerate(UNIVERSE):
            base = 0.48 + 0.22 * math.sin((self._cycle + i) / 2.7)
            score = min(0.98, max(0.05, base + rnd.uniform(-0.22, 0.22)))
            signal = "BUY" if score >= threshold else ("WATCH" if score >= threshold - 0.10 else "WAIT")
            rows.append({"symbol": symbol, "score": round(score * 100, 1), "signal": signal, "strategy": self.levelName})
        self._market_rows = sorted(rows, key=lambda x: x["score"], reverse=True)

        # Update/close existing positions. Each position keeps its opening strategy/level.
        survivors = []
        closed = False
        for p in self._positions:
            p = dict(p)
            p["age"] = int(p.get("age", 0)) + 1
            drift = rnd.uniform(-0.012, 0.015)
            p["price"] = round(float(p["price"]) * (1.0 + drift), 4)
            pnl_pct = (p["price"] / float(p["entry"]) - 1.0) * 100.0
            p["pnl_pct"] = round(pnl_pct, 2)
            required = LEVELS[int(p.get("level", 2))]["hold_cycles"]
            should_close = p["age"] >= required and (abs(pnl_pct) >= 0.25 or rnd.random() > 0.55)
            if should_close:
                value = self._trade_size * (1.0 + pnl_pct / 100.0)
                profit = value - self._trade_size
                self._paper_cash += value
                self._pnl += profit
                self._trades.append({
                    "time": now.strftime("%H:%M:%S"), "symbol": p["symbol"], "side": "SELL",
                    "strategy": p["strategy"], "amount": round(value, 2), "pnl": round(profit, 2),
                    "reason": "Strategy exit / Stresstest"
                })
                self._last_action = f"SELL {p['symbol']} · {p['strategy']} · {profit:+.2f} USD"
                self._log(self._last_action)
                closed = True
            else:
                survivors.append(p)
        self._positions = survivors

        # Open at most one new position per cycle.
        if len(self._positions) < self._max_positions and self._paper_cash >= self._trade_size:
            held = {p["symbol"] for p in self._positions}
            candidate = next((r for r in self._market_rows if r["signal"] == "BUY" and r["symbol"] not in held), None)
            if candidate:
                base_price = 80 + (sum(ord(c) for c in candidate["symbol"]) % 420)
                price = round(base_price * (0.97 + rnd.random() * 0.06), 4)
                self._paper_cash -= self._trade_size
                pos = {
                    "symbol": candidate["symbol"], "strategy": self.levelName, "level": self._level,
                    "entry": price, "price": price, "amount": self._trade_size, "age": 0, "pnl_pct": 0.0,
                    "opened": now.strftime("%H:%M:%S")
                }
                self._positions.append(pos)
                self._trades.append({
                    "time": now.strftime("%H:%M:%S"), "symbol": candidate["symbol"], "side": "BUY",
                    "strategy": self.levelName, "amount": self._trade_size, "pnl": 0.0,
                    "reason": f"Score {candidate['score']:.1f}%"
                })
                self._last_action = f"BUY {candidate['symbol']} · {self.levelName} · $10.00 SHADOW"
                self._log(self._last_action)
            elif not closed:
                best = self._market_rows[0] if self._market_rows else None
                self._last_action = f"WAIT · bester Score {best['score']:.1f}% ({best['symbol']})" if best else "WAIT"
        elif not closed:
            self._last_action = "HOLD / RISK GATE · maximale Shadow-Positionen erreicht"

        market_value = sum(self._trade_size * (1.0 + float(p.get("pnl_pct", 0.0)) / 100.0) for p in self._positions)
        self._paper_equity = self._paper_cash + market_value
        self._save_state()
        self.changed.emit()
