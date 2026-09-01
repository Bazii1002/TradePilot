from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from etoro_live_manual import EtoroManualLiveBroker, EtoroLiveError, MAX_LIVE_EUR

OPEN_URL_REAL = "https://public-api.etoro.com/api/v2/trading/execution/orders"
CLOSE_URL_REAL = "https://public-api.etoro.com/api/v1/trading/execution/market-close-orders/positions/{position_id}"
PORTFOLIO_URL_REAL = "https://public-api.etoro.com/api/v1/trading/info/portfolio"


class RealExecutionError(RuntimeError):
    pass


def _read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _pick(d: dict, *names: str):
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return None


def _portfolio_root(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("clientPortfolio"), dict):
        return payload["clientPortfolio"]
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def _positions(payload: Any) -> list[dict]:
    root = _portfolio_root(payload)
    for key in ("positions", "openPositions", "open_positions"):
        rows = root.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def _position_id(row: dict) -> str:
    raw = _pick(row, "positionId", "positionID", "PositionId", "id")
    return "" if raw is None else str(raw)


def _instrument_id(row: dict) -> int | None:
    raw = _pick(row, "instrumentId", "instrumentID", "InstrumentId", "marketId")
    try:
        value = int(raw)
        return value if value > 0 else None
    except Exception:
        return None


@dataclass(frozen=True)
class SafetyConfig:
    enabled: bool
    auto_enabled: bool
    max_trade_eur: float
    max_open_positions: int
    max_daily_loss_eur: float


class RealExecutionManager:
    """REAL execution layer with fail-closed safety and no POST retries.

    TradePilot never retries a state-changing request automatically. If a POST returns
    an ambiguous result (timeout/network failure or no broker confirmation), an
    uncertainty lock is written. Further REAL execution is blocked until the user
    reconciles the account state.
    """

    def __init__(self, app_dir: Path, timeout: float = 20.0):
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.central_env = self.app_dir.parent.parent / ".env"
        self.local_env = self.app_dir / ".env"
        self.timeout = float(timeout)
        self.session = requests.Session()
        self.manual = EtoroManualLiveBroker(self.app_dir, timeout=self.timeout)
        self.log_path = self.data_dir / "real_execution.jsonl"
        self.uncertain_lock = self.data_dir / "REAL_EXECUTION_UNCERTAIN.json"
        self.kill_switch = self.data_dir / "REAL_KILL_SWITCH.lock"
        self.position_state = self.data_dir / "real_positions_state.json"

    def _env(self) -> dict[str, str]:
        merged: dict[str, str] = {}
        merged.update(_read_env(self.central_env))
        merged.update(_read_env(self.local_env))
        for key in (
            "TRADEPILOT_REAL_EXECUTION_ENABLED", "TRADEPILOT_REAL_AUTOTRADING_ENABLED",
            "TRADEPILOT_MAX_REAL_TRADE_EUR", "TRADEPILOT_MAX_REAL_POSITIONS",
            "TRADEPILOT_MAX_DAILY_LOSS_EUR",
        ):
            if os.getenv(key):
                merged[key] = os.getenv(key, "")
        return merged

    def config(self) -> SafetyConfig:
        e = self._env()
        def yes(name: str) -> bool:
            return e.get(name, "").strip().upper() in {"YES", "TRUE", "1", "ON"}
        try: max_trade = min(MAX_LIVE_EUR, float(e.get("TRADEPILOT_MAX_REAL_TRADE_EUR", MAX_LIVE_EUR)))
        except Exception: max_trade = MAX_LIVE_EUR
        try: max_pos = max(1, min(3, int(e.get("TRADEPILOT_MAX_REAL_POSITIONS", "1"))))
        except Exception: max_pos = 1
        try: max_loss = max(1.0, min(20.0, float(e.get("TRADEPILOT_MAX_DAILY_LOSS_EUR", "20"))))
        except Exception: max_loss = 20.0
        return SafetyConfig(yes("TRADEPILOT_REAL_EXECUTION_ENABLED"), yes("TRADEPILOT_REAL_AUTOTRADING_ENABLED"), max_trade, max_pos, max_loss)

    def _headers(self, request_id: str | None = None) -> dict[str, str]:
        h = self.manual._headers()
        h["x-request-id"] = request_id or str(uuid.uuid4())
        return h

    def _log(self, event: str, **fields):
        record = {"ts": datetime.now().astimezone().isoformat(), "event": event, **fields}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    def _decode(self, resp: requests.Response) -> Any:
        try: payload = resp.json()
        except Exception: payload = resp.text
        if not resp.ok:
            text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else str(payload)
            raise RealExecutionError(f"eToro API {resp.status_code}: {text[:700]}")
        return payload

    def portfolio(self) -> Any:
        r = self.session.get(PORTFOLIO_URL_REAL, headers=self._headers(), timeout=self.timeout)
        return self._decode(r)

    def position_rows(self) -> list[dict]:
        return _positions(self.portfolio())

    def safety_status(self) -> dict:
        cfg = self.config()
        try:
            count = len(self.position_rows())
            broker_ok = True
            error = ""
        except Exception as exc:
            count = -1; broker_ok = False; error = str(exc)
        return {
            "execution_enabled": cfg.enabled,
            "auto_enabled": cfg.auto_enabled,
            "max_trade_eur": cfg.max_trade_eur,
            "max_open_positions": cfg.max_open_positions,
            "max_daily_loss_eur": cfg.max_daily_loss_eur,
            "open_positions": count,
            "broker_ok": broker_ok,
            "error": error,
            "kill_switch": self.kill_switch.exists(),
            "uncertain_lock": self.uncertain_lock.exists(),
        }

    def _assert_common(self, *, require_auto: bool = False):
        cfg = self.config()
        if not cfg.enabled:
            raise RealExecutionError("REAL execution ist nicht freigeschaltet (TRADEPILOT_REAL_EXECUTION_ENABLED=YES fehlt).")
        if require_auto and not cfg.auto_enabled:
            raise RealExecutionError("REAL AutoTrading ist nicht freigeschaltet (TRADEPILOT_REAL_AUTOTRADING_ENABLED=YES fehlt).")
        if self.kill_switch.exists():
            raise RealExecutionError("REAL Kill Switch ist aktiv.")
        if self.uncertain_lock.exists():
            raise RealExecutionError("REAL execution ist wegen eines unklaren früheren Orderstatus gesperrt. Erst Reconcile ausführen.")
        return cfg

    def preflight_buy(self, symbol: str, budget_eur: float, strategy: str = "MANUAL") -> dict:
        cfg = self.config()
        if budget_eur <= 0 or budget_eur > cfg.max_trade_eur or budget_eur > MAX_LIVE_EUR:
            raise RealExecutionError(f"Trade blockiert: maximal {cfg.max_trade_eur:.2f} EUR pro REAL-Trade.")
        rows = self.position_rows()
        if len(rows) >= cfg.max_open_positions:
            raise RealExecutionError(f"Trade blockiert: bereits {len(rows)} REAL-Position(en), Limit {cfg.max_open_positions}.")
        prepared = self.manual.prepare_market_buy(symbol, budget_eur)
        prepared["strategy"] = str(strategy).upper()
        prepared["safety"] = {
            "max_trade_eur": cfg.max_trade_eur,
            "max_open_positions": cfg.max_open_positions,
            "max_daily_loss_eur": cfg.max_daily_loss_eur,
        }
        self._log("PREFLIGHT_BUY", symbol=prepared["symbol"], instrument_id=prepared["instrument_id"], budget_eur=prepared["budget_eur"], strategy=prepared["strategy"])
        return prepared

    def _confirm_position(self, *, position_id: str = "", instrument_id: int | None = None, attempts: int = 3) -> dict | None:
        for i in range(attempts):
            try:
                for row in self.position_rows():
                    pid = _position_id(row)
                    iid = _instrument_id(row)
                    if position_id and pid == str(position_id):
                        return row
                    if not position_id and instrument_id is not None and iid == instrument_id:
                        return row
            except Exception:
                pass
            if i < attempts - 1:
                time.sleep(1.2)
        return None

    def execute_buy(self, prepared: dict, confirmation: str, *, auto: bool = False) -> dict:
        cfg = self._assert_common(require_auto=auto)
        symbol = str(prepared.get("symbol") or "").upper()
        budget = round(float(prepared.get("budget_eur", 0)), 2)
        if auto:
            expected = "AUTO"
        else:
            expected = f"LIVE BUY {symbol} {budget:.2f}"
        if str(confirmation or "").strip().upper() != expected:
            raise RealExecutionError(f"Bestätigung muss exakt '{expected}' lauten.")
        if budget > cfg.max_trade_eur or budget > MAX_LIVE_EUR:
            raise RealExecutionError("REAL Budget verletzt Sicherheitslimit.")

        gate = self.manual.validate_execution_gate(prepared, "LIVE")
        body = {
            "action": "open", "transaction": "buy", "instrumentId": gate["instrument_id"],
            "orderType": "mkt", "amount": gate["amount_usd"], "orderCurrency": "usd",
            "leverage": 1, "stopLossType": "fixed",
        }
        request_id = str(uuid.uuid4())
        self._log("POST_BUY_START", request_id=request_id, symbol=symbol, instrument_id=gate["instrument_id"], amount_usd=gate["amount_usd"], strategy=prepared.get("strategy", "MANUAL"))
        try:
            resp = self.session.post(OPEN_URL_REAL, headers=self._headers(request_id), json=body, timeout=self.timeout)
            payload = self._decode(resp)
        except Exception as exc:
            lock = {"ts": time.time(), "kind": "BUY", "request_id": request_id, "symbol": symbol, "instrument_id": gate["instrument_id"], "reason": str(exc)}
            self.uncertain_lock.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            self._log("POST_BUY_UNCERTAIN", **lock)
            raise RealExecutionError("BUY-Status ist unklar. KEIN Retry. REAL wurde gesperrt; Reconcile erforderlich.") from exc

        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else (payload if isinstance(payload, dict) else {})
        position_id = str(_pick(data, "positionId", "positionID", "PositionId") or "")
        order_id = str(_pick(data, "orderId", "orderID", "OrderId", "id") or "")
        confirmed = self._confirm_position(position_id=position_id, instrument_id=gate["instrument_id"])
        if confirmed is None:
            lock = {"ts": time.time(), "kind": "BUY", "request_id": request_id, "symbol": symbol, "instrument_id": gate["instrument_id"], "position_id": position_id, "order_id": order_id, "reason": "POST accepted but portfolio confirmation missing"}
            self.uncertain_lock.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            self._log("POST_BUY_UNCONFIRMED", **lock)
            raise RealExecutionError("Orderantwort erhalten, Position aber nicht sicher im Portfolio bestätigt. REAL gesperrt; Reconcile erforderlich.")

        result = {"ok": True, "status": "CONFIRMED", "request_id": request_id, "symbol": symbol, "instrument_id": gate["instrument_id"], "position_id": _position_id(confirmed) or position_id, "order_id": order_id, "amount_usd": gate["amount_usd"], "budget_eur": gate["budget_eur"], "strategy": prepared.get("strategy", "MANUAL")}
        self._log("BUY_CONFIRMED", **result)
        self._write_position_state(result)
        return result

    def _write_position_state(self, entry: dict):
        state = self.load_position_state()
        pid = str(entry.get("position_id") or "")
        if pid:
            state[pid] = {**entry, "saved_at": time.time()}
            tmp = self.position_state.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
            tmp.replace(self.position_state)

    def load_position_state(self) -> dict:
        try:
            raw = json.loads(self.position_state.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def close_position(self, position_id: str, confirmation: str, *, auto: bool = False) -> dict:
        self._assert_common(require_auto=auto)
        pid = str(position_id or "").strip()
        if not pid:
            raise RealExecutionError("Position-ID fehlt.")
        if auto:
            expected = "AUTO"
        else:
            expected = f"LIVE CLOSE {pid}"
        if str(confirmation or "").strip().upper() != expected:
            raise RealExecutionError(f"Bestätigung muss exakt '{expected}' lauten.")

        before = { _position_id(r): r for r in self.position_rows() }
        if pid not in before:
            raise RealExecutionError("Position-ID ist im aktuellen REAL-Portfolio nicht offen; Close wird blockiert.")
        request_id = str(uuid.uuid4())
        url = CLOSE_URL_REAL.format(position_id=pid)
        self._log("POST_CLOSE_START", request_id=request_id, position_id=pid)
        try:
            resp = self.session.post(url, headers=self._headers(request_id), json={"UnitsToDeduct": None}, timeout=self.timeout)
            payload = self._decode(resp)
        except Exception as exc:
            lock = {"ts": time.time(), "kind": "CLOSE", "request_id": request_id, "position_id": pid, "reason": str(exc)}
            self.uncertain_lock.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            self._log("POST_CLOSE_UNCERTAIN", **lock)
            raise RealExecutionError("CLOSE-Status ist unklar. KEIN Retry. REAL wurde gesperrt; Reconcile erforderlich.") from exc

        gone = False
        for i in range(3):
            try:
                ids = {_position_id(r) for r in self.position_rows()}
                if pid not in ids:
                    gone = True; break
            except Exception:
                pass
            if i < 2: time.sleep(1.2)
        if not gone:
            lock = {"ts": time.time(), "kind": "CLOSE", "request_id": request_id, "position_id": pid, "reason": "POST accepted but position still present"}
            self.uncertain_lock.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            self._log("POST_CLOSE_UNCONFIRMED", **lock)
            raise RealExecutionError("Close-Antwort erhalten, Schließung aber nicht sicher bestätigt. REAL gesperrt; Reconcile erforderlich.")

        state = self.load_position_state(); state.pop(pid, None)
        self.position_state.write_text(json.dumps(state, indent=2), encoding="utf-8")
        result = {"ok": True, "status": "CONFIRMED", "request_id": request_id, "position_id": pid, "response": payload if isinstance(payload, dict) else {}}
        self._log("CLOSE_CONFIRMED", position_id=pid, request_id=request_id)
        return result

    def reconcile(self, clear_uncertain_if_safe: bool = False) -> dict:
        rows = self.position_rows()
        broker_ids = {_position_id(r) for r in rows if _position_id(r)}
        state = self.load_position_state()
        local_ids = set(state.keys())
        orphan_broker = sorted(broker_ids - local_ids)
        stale_local = sorted(local_ids - broker_ids)
        uncertain = None
        if self.uncertain_lock.exists():
            try: uncertain = json.loads(self.uncertain_lock.read_text(encoding="utf-8"))
            except Exception: uncertain = {"reason": "unreadable uncertain lock"}
        safe_to_clear = False
        if uncertain:
            kind = str(uncertain.get("kind") or "")
            pid = str(uncertain.get("position_id") or "")
            iid = uncertain.get("instrument_id")
            if kind == "BUY":
                matched = any((_position_id(r) == pid if pid else False) or (_instrument_id(r) == iid if iid else False) for r in rows)
                safe_to_clear = matched or not rows
            elif kind == "CLOSE" and pid:
                safe_to_clear = pid not in broker_ids
        if clear_uncertain_if_safe and uncertain and safe_to_clear:
            self.uncertain_lock.unlink(missing_ok=True)
            self._log("UNCERTAIN_LOCK_CLEARED_BY_RECONCILE", kind=uncertain.get("kind"))
        result = {"broker_positions": len(rows), "broker_position_ids": sorted(broker_ids), "local_position_ids": sorted(local_ids), "orphan_broker": orphan_broker, "stale_local": stale_local, "uncertain_lock": bool(uncertain), "uncertain_safe_to_clear": safe_to_clear}
        self._log("RECONCILE", **result)
        return result

    def activate_kill_switch(self, reason: str = "manual"):
        self.kill_switch.write_text(json.dumps({"ts": time.time(), "reason": reason}, indent=2), encoding="utf-8")
        self._log("KILL_SWITCH_ON", reason=reason)

    def clear_kill_switch(self):
        self.kill_switch.unlink(missing_ok=True)
        self._log("KILL_SWITCH_OFF")
