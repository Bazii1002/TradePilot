from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from strategy_engine import ProductionStrategyEngine, STRATEGIES
from universe_provider import StockUniverseProvider
from fast_scanner import ThousandStockFastScanner


class BotEngine(QObject):
    changed = Signal()
    scanFinished = Signal(object, str)

    def __init__(self, app_dir: Path, macro_engine=None):
        super().__init__()
        self.app_dir = Path(app_dir)
        self.macro_engine = macro_engine
        self.data_dir = self.app_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "shadow_state.json"
        self.strategy = ProductionStrategyEngine()
        self.universe_provider = StockUniverseProvider(self.app_dir)
        self.fast_scanner = ThousandStockFastScanner(self.app_dir, self.strategy.analyzer)
        self._universe_count = 0
        self._scanner_scanned = 0
        self._scanner_candidates = 0
        self._scanner_deep = 0
        self._scanner_finalists = 0
        self._scanner_signals = 0
        self._scanner_actionable = 0
        self._scanner_duration = 0.0
        self._scanner_cache = "—"
        self._scanner_source = "—"
        self._scanner_errors = 0
        self._running = False
        self._scan_busy = False
        self._level = 2
        self._scan_count = 0
        self._last_scan = "Noch kein Scan"
        self._last_scan_summary = "Noch kein abgeschlossener Scan"
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
        self.timer.timeout.connect(self._request_scan)
        self.scanFinished.connect(self._apply_scan)
        self._apply_interval()

    def _apply_interval(self):
        self.timer.setInterval(int(STRATEGIES[self._level]["scan_seconds"]) * 1000)

    def _log(self, text: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._events.insert(0, {"time": stamp, "text": text})
        self._events = self._events[:80]

    def _save_state(self):
        payload = {
            "level": self._level, "scan_count": self._scan_count,
            "positions": self._positions, "trades": self._trades[-300:],
            "events": self._events[:80], "paper_cash": self._paper_cash,
            "paper_equity": self._paper_equity, "pnl": self._pnl, "cycle": self._cycle,
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
            lvl = int(p.get("level", self._level))
            self._level = lvl if lvl in STRATEGIES else 2
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
    def levelName(self): return STRATEGIES[self._level]["name"]
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
    def tradesJson(self): return json.dumps(list(reversed(self._trades[-120:])))
    @Property(str, notify=changed)
    def eventsJson(self): return json.dumps(self._events)
    @Property(int, notify=changed)
    def universeCount(self): return self._universe_count
    @Property(int, notify=changed)
    def scannerScanned(self): return self._scanner_scanned
    @Property(int, notify=changed)
    def scannerCandidates(self): return self._scanner_candidates
    @Property(int, notify=changed)
    def scannerDeep(self): return self._scanner_deep
    @Property(int, notify=changed)
    def scannerFinalists(self): return self._scanner_finalists
    @Property(int, notify=changed)
    def scannerSignals(self): return self._scanner_signals
    @Property(int, notify=changed)
    def scannerActionable(self): return self._scanner_actionable
    @Property(str, notify=changed)
    def scannerDurationText(self): return f"{self._scanner_duration:.1f}s" if self._scanner_duration else "—"
    @Property(str, notify=changed)
    def scannerCacheText(self): return self._scanner_cache
    @Property(str, notify=changed)
    def scannerSourceText(self): return self._scanner_source
    @Property(int, notify=changed)
    def scannerErrors(self): return self._scanner_errors
    @Property(bool, notify=changed)
    def scanBusy(self): return self._scan_busy
    @Property(str, notify=changed)
    def scanStatusText(self):
        if self._scan_busy:
            return "SCANNING… · Marktdaten werden bewertet"
        if self._scan_count > 0:
            return "SCAN ABGESCHLOSSEN"
        return "SCAN BEREIT"
    @Property(str, notify=changed)
    def lastScanSummaryText(self): return self._last_scan_summary
    @Property(str, notify=changed)
    def macroGateText(self):
        if not self.macro_engine:
            return "MACRO · FAIL-CLOSED"
        g = self.macro_engine.gate()
        return f"MACRO {g['risk']} · {g['regime']} · " + ("NEW TRADES OK" if g['allow_new_trade'] else "NEW TRADES BLOCKED")
    @Property(str, notify=changed)
    def modeText(self): return "SHADOW · PRODUCTION SIGNALS"
    @Property(str, notify=changed)
    def realLockText(self): return "REAL AUTOTRADING LOCKED"

    @Slot()
    def startBot(self):
        if self._running:
            return
        self._running = True
        self._status = "RUNNING"
        self._log(f"Bot gestartet · echte Signal-Engine · {self.levelName}")
        self._apply_interval()
        self.timer.start()
        self._request_scan()
        self.changed.emit()

    @Slot()
    def stopBot(self):
        self.timer.stop()
        self._running = False
        self._status = "STOPPED"
        self._next_scan = "—"
        self._log("Bot gestoppt · Shadow-Positionen bleiben gespeichert")
        self._save_state()
        self.changed.emit()

    @Slot(int)
    def setLevel(self, level):
        level = int(level)
        if level not in STRATEGIES:
            return
        self._level = level
        self._apply_interval()
        if self._running:
            self.timer.start()
        self._log(f"Neue Strategie für neue Trades: {level} {self.levelName}")
        self._save_state()
        self.changed.emit()

    @Slot()
    def resetShadow(self):
        if self._running:
            self.stopBot()
        self._positions, self._trades, self._events = [], [], []
        self._paper_cash = self._paper_equity = 1000.0
        self._pnl = 0.0
        self._scan_count = self._cycle = 0
        self._last_action = "Shadow-Konto zurückgesetzt"
        try:
            self.state_file.unlink(missing_ok=True)
        except Exception:
            pass
        self.changed.emit()

    @Slot()
    def forceScan(self):
        self._request_scan()

    def _request_scan(self):
        if self._scan_busy:
            self._last_action = "SCAN läuft bereits · Doppelabruf blockiert"
            self.changed.emit()
            return
        self._scan_busy = True
        level = self._level
        self._status = "SCANNING" if self._running else "MANUAL SCAN"
        self._last_action = f"SCAN · {STRATEGIES[level]['name']} · echte Marktdaten"
        self.changed.emit()

        def worker():
            try:
                universe_rows = self.universe_provider.load(allow_refresh=True)
                symbols = [r.get("symbol") for r in universe_rows if r.get("symbol")][:1000]
                held = [p.get("symbol") for p in self._positions if p.get("symbol")]
                rows, metrics = self.fast_scanner.scan(level, symbols, held_symbols=held, force_full=False)
                payload = {"rows": rows, "metrics": metrics, "source": self.universe_provider.last_source}
                self.scanFinished.emit(payload, "")
            except Exception as exc:
                self.scanFinished.emit([], str(exc))

        threading.Thread(target=worker, daemon=True, name="production-strategy-scan").start()

    @Slot(object, str)
    def _apply_scan(self, rows, error):
        self._scan_busy = False
        self._cycle += 1
        self._scan_count += 1
        now = datetime.now()
        self._last_scan = now.strftime("%H:%M:%S")
        self._next_scan = f"in {STRATEGIES[self._level]['scan_seconds']} Sek." if self._running else "—"
        if error:
            self._status = "RUNNING · DATA ERROR" if self._running else "STOPPED"
            self._last_action = "WAIT · Marktdatenfehler · keine neue Position"
            self._last_scan_summary = f"SCAN FEHLER · {error[:80]}"
            self._log(self._last_action + f" · {error[:100]}")
            self.changed.emit()
            return

        if isinstance(rows, dict):
            metrics = rows.get("metrics") or {}
            self._market_rows = list(rows.get("rows") or [])
            self._universe_count = int(metrics.get("universe", 0))
            self._scanner_scanned = int(metrics.get("scanned", 0))
            self._scanner_candidates = int(metrics.get("candidates", 0))
            self._scanner_deep = int(metrics.get("deep", 0))
            self._scanner_finalists = int(metrics.get("finalists", 0))
            self._scanner_signals = int(metrics.get("signals", 0))
            self._scanner_actionable = int(metrics.get("actionable", 0))
            self._scanner_duration = float(metrics.get("duration", 0.0))
            self._scanner_cache = str(metrics.get("cache", "—"))
            self._scanner_errors = int(metrics.get("errors", 0))
            self._scanner_source = str(rows.get("source") or "—")
            self._last_scan_summary = (f"{self._scanner_scanned}/{self._universe_count or 1000} gescannt · "
                                       f"{self._scanner_candidates} Kandidaten · {self._scanner_finalists} Finalisten · "
                                       f"{self._scanner_actionable} ACTIONABLE · {self._scanner_duration:.1f}s")
        else:
            self._market_rows = list(rows or [])
        valid_rows = [r for r in self._market_rows if r.get("signal") != "NO_DATA" and r.get("price")]
        by_symbol = {r["symbol"]: r for r in valid_rows}

        # Existing positions retain their opening strategy/level.
        survivors = []
        any_closed = False
        for original in self._positions:
            p = dict(original)
            p["age"] = int(p.get("age", 0)) + 1
            row = by_symbol.get(p["symbol"])
            should_close, why, pnl_pct = self.strategy.exit_decision(p, row)
            if row and row.get("price"):
                p["price"] = float(row["price"])
            if pnl_pct is not None:
                p["pnl_pct"] = round(float(pnl_pct), 2)
            if should_close:
                qty = float(p.get("quantity") or (float(p["amount"]) / float(p["entry"])))
                value = qty * float(p.get("price") or p["entry"])
                profit = value - float(p["amount"])
                self._paper_cash += value
                self._pnl += profit
                self._trades.append({
                    "time": now.strftime("%H:%M:%S"), "symbol": p["symbol"], "side": "SELL",
                    "strategy": p["strategy"], "amount": round(value, 2), "pnl": round(profit, 2),
                    "reason": why,
                })
                self._last_action = f"SELL {p['symbol']} · {p['strategy']} · {profit:+.2f} USD · {why}"
                self._log(self._last_action)
                any_closed = True
            else:
                survivors.append(p)
        self._positions = survivors

        # At most one new shadow position per completed scan. Existing positions are never macro-force-closed.
        macro_gate = self.macro_engine.gate() if self.macro_engine else {
            "allow_new_trade": False, "position_multiplier": 0.0, "risk": "HIGH",
            "regime": "NEUTRAL", "reason": "Macro Engine nicht verfügbar → fail-closed"
        }
        if len(self._positions) < self._max_positions and self._paper_cash >= self._trade_size:
            held = {p["symbol"] for p in self._positions}
            candidate = next((r for r in valid_rows if r.get("is_actionable") and r.get("signal") == "BUY" and r["symbol"] not in held), None)
            macro_blocked = False
            if candidate and not macro_gate.get("allow_new_trade", False):
                self._last_action = f"MACRO BLOCK · {macro_gate.get('risk')} · {macro_gate.get('regime')} · {macro_gate.get('reason','')}"
                self._log(self._last_action)
                candidate = None
                macro_blocked = True
            if candidate:
                trade_size = round(self._trade_size * max(0.0, min(1.0, float(macro_gate.get("position_multiplier", 1.0)))), 2)
                if trade_size <= 0.0:
                    self._last_action = f"MACRO BLOCK · Positionsgröße 0% · {macro_gate.get('reason','')}"
                    candidate = None
                else:
                    price = float(candidate["price"])
                    self._paper_cash -= trade_size
                    pos = {
                        "symbol": candidate["symbol"], "strategy": self.levelName, "level": self._level,
                        "entry": price, "price": price, "amount": trade_size,
                        "quantity": trade_size / price, "age": 0, "pnl_pct": 0.0,
                        "opened": now.strftime("%H:%M:%S"), "entry_score": candidate["score"],
                        "macro_risk": macro_gate.get("risk"), "macro_regime": macro_gate.get("regime"),
                    }
                    self._positions.append(pos)
                    self._trades.append({
                        "time": now.strftime("%H:%M:%S"), "symbol": candidate["symbol"], "side": "BUY",
                        "strategy": self.levelName, "amount": trade_size, "pnl": 0.0,
                        "reason": (candidate.get("reason") or f"Score {candidate['score']:.1f}%") + f" · Macro {macro_gate.get('risk')}/{macro_gate.get('regime')}",
                    })
                    self._last_action = f"BUY {candidate['symbol']} · {self.levelName} · ${trade_size:.2f} SHADOW · Macro {macro_gate.get('risk')}/{macro_gate.get('regime')} · Score {candidate['score']:.1f} · Quality {candidate.get('quality_score',0):.1f}"
                    self._log(self._last_action)
            elif not any_closed and not macro_blocked:
                best = valid_rows[0] if valid_rows else None
                self._last_action = (f"WAIT · {best['symbol']} {best['score']:.1f}% · {best.get('reason','')}" if best
                                     else "WAIT · keine verwertbaren Marktdaten")
        elif not any_closed:
            self._last_action = "HOLD / RISK GATE · maximale Shadow-Positionen erreicht"

        market_value = 0.0
        for p in self._positions:
            qty = float(p.get("quantity") or (float(p["amount"]) / float(p["entry"])))
            market_value += qty * float(p.get("price") or p["entry"])
        self._paper_equity = self._paper_cash + market_value
        self._status = "RUNNING" if self._running else "STOPPED"
        self._save_state()
        self.changed.emit()
