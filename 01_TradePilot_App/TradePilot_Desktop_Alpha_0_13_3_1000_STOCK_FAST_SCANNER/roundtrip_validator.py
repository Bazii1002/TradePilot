from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SimulatedBrokerState:
    positions: list[dict]

    def snapshot(self) -> list[dict]:
        return [dict(p) for p in self.positions]

    def accept_buy(self, prepared: dict) -> dict:
        pid = f"SIM-{int(time.time() * 1000)}"
        row = {
            "positionId": pid,
            "instrumentId": int(prepared["instrument_id"]),
            "symbol": str(prepared["symbol"]),
            "amount": float(prepared["amount_usd"]),
            "leverage": 1,
            "strategy": str(prepared.get("strategy") or "MANUAL"),
        }
        self.positions.append(row)
        return row

    def accept_close(self, position_id: str) -> bool:
        before = len(self.positions)
        self.positions = [p for p in self.positions if str(p.get("positionId")) != str(position_id)]
        return len(self.positions) < before


def validate_prepared_roundtrip(prepared: dict, strategy: str = "DAY") -> dict[str, Any]:
    """Pure no-network state-machine validation for an already prepared order."""
    sim = SimulatedBrokerState([])
    buy_payload = {
        "action": "open",
        "transaction": "buy",
        "instrumentId": int(prepared["instrument_id"]),
        "orderType": "mkt",
        "amount": float(prepared["amount_usd"]),
        "orderCurrency": "usd",
        "leverage": 1,
    }
    broker_position = sim.accept_buy(prepared)
    pid = str(broker_position["positionId"])
    local_state = {
        pid: {
            "status": "CONFIRMED_SIMULATION",
            "symbol": prepared["symbol"],
            "instrument_id": prepared["instrument_id"],
            "position_id": pid,
            "amount_usd": prepared["amount_usd"],
            "budget_eur": prepared["budget_eur"],
            "strategy": strategy.upper(),
        }
    }
    broker_ids_after_buy = {str(p["positionId"]) for p in sim.snapshot()}
    local_ids_after_buy = set(local_state)
    buy_reconcile_ok = broker_ids_after_buy == local_ids_after_buy == {pid}

    close_payload = {"positionId": pid, "mode": "FULL_CLOSE"}
    close_accepted = sim.accept_close(pid)
    local_state.pop(pid, None)
    broker_ids_after_close = {str(p["positionId"]) for p in sim.snapshot()}
    local_ids_after_close = set(local_state)
    close_reconcile_ok = close_accepted and not broker_ids_after_close and not local_ids_after_close

    return {
        "ok": bool(buy_reconcile_ok and close_reconcile_ok),
        "transport": "NO_POST_SIMULATED_BROKER",
        "symbol": prepared["symbol"],
        "instrument_id": prepared["instrument_id"],
        "budget_eur": prepared["budget_eur"],
        "amount_usd": prepared["amount_usd"],
        "strategy": strategy.upper(),
        "buy_payload_preview": buy_payload,
        "simulated_position_id": pid,
        "buy_reconcile_ok": buy_reconcile_ok,
        "close_payload_preview": close_payload,
        "close_reconcile_ok": close_reconcile_ok,
        "final_broker_positions": len(broker_ids_after_close),
        "final_local_positions": len(local_ids_after_close),
        "real_post_executed": False,
    }


class RoundtripValidator:
    """READ-only preflight plus simulated BUY/CLOSE broker lifecycle."""

    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)
        # Lazy import keeps the pure state-machine test independent of market packages.
        from real_execution import RealExecutionManager
        self.manager = RealExecutionManager(self.app_dir)
        self.report_path = self.app_dir / "data" / "roundtrip_validation_last.json"

    def run(self, symbol: str = "AAPL", budget_eur: float = 10.0, strategy: str = "DAY") -> dict[str, Any]:
        prepared = self.manager.preflight_buy(symbol, budget_eur, strategy)
        report = validate_prepared_roundtrip(prepared, strategy)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
