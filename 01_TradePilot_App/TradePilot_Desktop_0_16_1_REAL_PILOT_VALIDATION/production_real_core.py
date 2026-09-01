from __future__ import annotations

"""TradePilot 0.16.0 Production REAL Execution Core.

This module intentionally does NOT enable unattended REAL trading. It provides the
production safety primitives needed before a later pilot: persistent state machine,
idempotency/duplicate protection, restart/timeout recovery, REAL exit decisions,
risk limits and an audit trail.

The preferred live validation amount is EUR 1.00. The core never auto-increases a
requested amount to satisfy a broker minimum. A broker rejection remains a rejection.
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from strategy_engine import ProductionStrategyEngine

REAL_TEST_EUR = 1.00
MAX_REAL_TRADE_EUR = 1.00
MAX_REAL_POSITIONS = 1
MAX_TRADES_PER_DAY = 3
MAX_INVESTED_CAPITAL_EUR = 1.00
MAX_DAILY_LOSS_EUR = 20.00
LEVERAGE = 1
REAL_AUTO_ENABLED = False

STATES = {
    "IDLE", "PREPARED", "SUBMITTED", "ACKNOWLEDGED", "OPEN",
    "CLOSING", "CLOSED", "UNCERTAIN", "LOCKED",
}


class ProductionRealError(RuntimeError):
    pass


@dataclass
class RiskLimits:
    max_trade_eur: float = MAX_REAL_TRADE_EUR
    max_open_positions: int = MAX_REAL_POSITIONS
    max_trades_per_day: int = MAX_TRADES_PER_DAY
    max_invested_capital_eur: float = MAX_INVESTED_CAPITAL_EUR
    max_daily_loss_eur: float = MAX_DAILY_LOSS_EUR
    leverage: int = LEVERAGE
    buy_only: bool = True
    auto_retry_post: bool = False
    auto_enabled: bool = REAL_AUTO_ENABLED


class JsonStore:
    def __init__(self, path: Path, default: dict[str, Any]):
        self.path = Path(path)
        self.default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else dict(self.default)
        except Exception:
            return dict(self.default)

    def write(self, payload: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, event: str, **fields: Any) -> None:
        rec = {
            "ts": datetime.now().astimezone().isoformat(),
            "event": event,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")


class RiskManager:
    """Fail-closed REAL risk gate. No broker-minimum auto-bump is ever allowed."""

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()

    def validate_new_buy(
        self,
        *,
        amount_eur: float,
        leverage: int,
        side: str,
        open_positions: int,
        invested_eur: float,
        trades_today: int,
        realized_pnl_today_eur: float,
        kill_switch: bool = False,
        uncertain_lock: bool = False,
    ) -> dict[str, Any]:
        L = self.limits
        amount = round(float(amount_eur), 2)
        reasons: list[str] = []
        if L.auto_enabled:
            reasons.append("REAL AUTO must remain disabled in 0.16.0")
        if kill_switch:
            reasons.append("kill switch active")
        if uncertain_lock:
            reasons.append("uncertain lock active")
        if side.upper() != "BUY" or not L.buy_only:
            reasons.append("BUY-only gate")
        if int(leverage) != 1 or int(leverage) != L.leverage:
            reasons.append("leverage must be 1x")
        if amount <= 0 or amount > L.max_trade_eur:
            reasons.append(f"amount must be >0 and <= EUR {L.max_trade_eur:.2f}")
        if int(open_positions) >= L.max_open_positions:
            reasons.append("max REAL positions reached")
        if float(invested_eur) + amount > L.max_invested_capital_eur + 1e-9:
            reasons.append("max invested capital exceeded")
        if int(trades_today) >= L.max_trades_per_day:
            reasons.append("max trades/day reached")
        if float(realized_pnl_today_eur) <= -abs(L.max_daily_loss_eur):
            reasons.append("daily loss gate reached")
        return {"ok": not reasons, "reasons": reasons, "amount_eur": amount, "limits": asdict(L)}

    def broker_minimum_policy(self, requested_eur: float, broker_minimum_eur: float | None) -> dict[str, Any]:
        req = round(float(requested_eur), 2)
        minimum = None if broker_minimum_eur is None else round(float(broker_minimum_eur), 2)
        if minimum is not None and minimum > req:
            return {
                "ok": False,
                "requested_eur": req,
                "broker_minimum_eur": minimum,
                "auto_increase": False,
                "reason": "Broker minimum is higher; TradePilot blocks instead of increasing the order.",
            }
        return {"ok": True, "requested_eur": req, "broker_minimum_eur": minimum, "auto_increase": False}


class ExecutionStateMachine:
    """Persistent single-operation state machine with request/idempotency identity."""

    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)
        data = self.app_dir / "data"
        self.store = JsonStore(data / "production_real_state.json", {"state": "IDLE", "history": []})
        self.audit = AuditLog(data / "production_real_audit.jsonl")

    def snapshot(self) -> dict[str, Any]:
        s = self.store.read()
        if s.get("state") not in STATES:
            s["state"] = "LOCKED"
        return s

    def _save(self, state: str, **fields: Any) -> dict[str, Any]:
        if state not in STATES:
            raise ProductionRealError(f"Unknown state: {state}")
        old = self.snapshot()
        hist = list(old.get("history") or [])[-80:]
        hist.append({"ts": time.time(), "from": old.get("state", "IDLE"), "to": state})
        payload = {**old, **fields, "state": state, "updated_at": time.time(), "history": hist}
        self.store.write(payload)
        self.audit.add("STATE", from_state=old.get("state"), to_state=state, operation_id=payload.get("operation_id"), request_id=payload.get("request_id"))
        return payload

    def reset_if_closed(self) -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") in {"IDLE", "CLOSED"}:
            self.store.write({"state": "IDLE", "history": list(s.get("history") or [])[-80:]})
            return self.snapshot()
        raise ProductionRealError(f"Cannot reset active state {s.get('state')}")

    def prepare_buy(self, *, symbol: str, instrument_id: int, amount_eur: float, amount_usd: float, strategy: str) -> dict[str, Any]:
        current = self.snapshot().get("state")
        if current not in {"IDLE", "CLOSED"}:
            raise ProductionRealError(f"Another REAL operation is active: {current}")
        op = str(uuid.uuid4())
        req = str(uuid.uuid4())
        return self._save(
            "PREPARED", operation_id=op, request_id=req, kind="BUY", symbol=str(symbol).upper(),
            instrument_id=int(instrument_id), amount_eur=round(float(amount_eur), 2), amount_usd=round(float(amount_usd), 2),
            strategy=str(strategy).upper(), leverage=1, submitted_at=None, broker_order_id="", broker_position_id="",
        )

    def mark_submitted(self, operation_id: str, request_id: str) -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") != "PREPARED" or s.get("operation_id") != operation_id or s.get("request_id") != request_id:
            raise ProductionRealError("Duplicate/stale submit blocked")
        return self._save("SUBMITTED", submitted_at=time.time())

    def acknowledge(self, *, operation_id: str, order_id: str = "", position_id: str = "") -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") not in {"SUBMITTED", "ACKNOWLEDGED"} or s.get("operation_id") != operation_id:
            raise ProductionRealError("Unexpected broker acknowledgement")
        return self._save("ACKNOWLEDGED", broker_order_id=str(order_id), broker_position_id=str(position_id))

    def mark_open(self, *, operation_id: str, position_id: str) -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") not in {"SUBMITTED", "ACKNOWLEDGED", "OPEN"} or s.get("operation_id") != operation_id:
            raise ProductionRealError("OPEN transition blocked")
        return self._save("OPEN", broker_position_id=str(position_id), opened_at=time.time())

    def begin_close(self, *, position_id: str, reason: str) -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") != "OPEN" or str(s.get("broker_position_id")) != str(position_id):
            raise ProductionRealError("CLOSE transition blocked")
        close_req = str(uuid.uuid4())
        return self._save("CLOSING", close_request_id=close_req, close_reason=str(reason), close_started_at=time.time())

    def mark_closed(self, *, position_id: str) -> dict[str, Any]:
        s = self.snapshot()
        if s.get("state") != "CLOSING" or str(s.get("broker_position_id")) != str(position_id):
            raise ProductionRealError("CLOSED transition blocked")
        return self._save("CLOSED", closed_at=time.time())

    def mark_uncertain(self, reason: str) -> dict[str, Any]:
        return self._save("UNCERTAIN", uncertain_reason=str(reason), uncertain_at=time.time())

    def lock(self, reason: str) -> dict[str, Any]:
        return self._save("LOCKED", lock_reason=str(reason), locked_at=time.time())


class RecoveryManager:
    """Conservative startup/restart reconciliation. It never retries a POST."""

    def __init__(self, machine: ExecutionStateMachine):
        self.machine = machine

    @staticmethod
    def _position_ids(broker_positions: list[dict[str, Any]]) -> set[str]:
        out: set[str] = set()
        for row in broker_positions or []:
            if not isinstance(row, dict):
                continue
            raw = row.get("positionId", row.get("positionID", row.get("id")))
            if raw is not None:
                out.add(str(raw))
        return out

    def reconcile(self, broker_positions: list[dict[str, Any]]) -> dict[str, Any]:
        s = self.machine.snapshot()
        state = s.get("state")
        ids = self._position_ids(broker_positions)
        pid = str(s.get("broker_position_id") or "")

        if state in {"SUBMITTED", "ACKNOWLEDGED"}:
            # We cannot infer safely whether the broker accepted a timed-out order unless the
            # exact position is proven. Fail closed; no automatic retry.
            if pid and pid in ids:
                self.machine.mark_open(operation_id=str(s.get("operation_id")), position_id=pid)
                return {"ok": True, "action": "RECOVERED_OPEN", "post_retry": False}
            self.machine.mark_uncertain("Restart/recovery while order outcome is not proven")
            return {"ok": False, "action": "UNCERTAIN_LOCK", "post_retry": False}

        if state == "OPEN":
            if pid and pid in ids:
                return {"ok": True, "action": "OPEN_MATCH", "post_retry": False}
            self.machine.lock("Local OPEN position missing at broker")
            return {"ok": False, "action": "LOCKED_STALE_LOCAL", "post_retry": False}

        if state == "CLOSING":
            if pid and pid not in ids:
                self.machine.mark_closed(position_id=pid)
                return {"ok": True, "action": "RECOVERED_CLOSED", "post_retry": False}
            self.machine.mark_uncertain("Restart/recovery while close outcome is not proven")
            return {"ok": False, "action": "UNCERTAIN_CLOSE", "post_retry": False}

        if state in {"IDLE", "CLOSED"} and ids:
            self.machine.lock("Broker has REAL position(s) unknown to local state")
            return {"ok": False, "action": "LOCKED_ORPHAN_BROKER", "post_retry": False}

        return {"ok": state not in {"UNCERTAIN", "LOCKED"}, "action": "NO_CHANGE", "post_retry": False}


class RealExitEngine:
    """Reuse the production strategy's tested exit rules for REAL position monitoring."""

    @staticmethod
    def decision(position: dict[str, Any], market_row: dict[str, Any] | None) -> dict[str, Any]:
        should_close, reason, pnl_pct = ProductionStrategyEngine.exit_decision(position, market_row)
        return {
            "close": bool(should_close),
            "reason": str(reason),
            "pnl_pct": pnl_pct,
            "strategy_level": int(position.get("level", 2)),
        }


class ProductionRealCore:
    """0.16.0 orchestration shell. REAL AUTO remains disabled by design."""

    def __init__(self, app_dir: Path, limits: RiskLimits | None = None):
        self.app_dir = Path(app_dir)
        self.risk = RiskManager(limits)
        self.machine = ExecutionStateMachine(self.app_dir)
        self.recovery = RecoveryManager(self.machine)
        self.exit_engine = RealExitEngine()
        self.kill_switch = self.app_dir / "data" / "REAL_KILL_SWITCH.lock"
        self.uncertain_lock = self.app_dir / "data" / "REAL_EXECUTION_UNCERTAIN.json"

    def status(self) -> dict[str, Any]:
        return {
            "version": "0.16.0",
            "real_auto_enabled": False,
            "preferred_test_eur": REAL_TEST_EUR,
            "limits": asdict(self.risk.limits),
            "state": self.machine.snapshot(),
            "kill_switch": self.kill_switch.exists(),
            "legacy_uncertain_lock": self.uncertain_lock.exists(),
        }
