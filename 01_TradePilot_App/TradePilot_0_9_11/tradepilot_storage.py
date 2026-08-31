from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path


WATCHLIST_FILENAME = "TradePilot_watchlist.json"


def watchlist_path(base_dir: Path | None = None) -> Path:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent
    return Path(base_dir) / WATCHLIST_FILENAME


def load_watchlist(path: Path) -> dict[str, dict]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            data = {
                str(item.get("symbol", "")).upper(): item
                for item in data
                if isinstance(item, dict) and item.get("symbol")
            }
        if not isinstance(data, dict):
            return {}

        clean: dict[str, dict] = {}
        for symbol, item in data.items():
            if not isinstance(item, dict):
                continue
            symbol = str(symbol).strip().upper()
            if not symbol:
                continue
            item = dict(item)
            item["symbol"] = symbol
            if not isinstance(item.get("history"), list):
                item["history"] = []
            item.setdefault("delta_unternehmensscore", None)
            item.setdefault("delta_einstieg_score", None)
            item.setdefault("delta_trap_score", None)
            clean[symbol] = item
        return clean
    except Exception:
        return {}


def save_watchlist(path: Path, watchlist: dict[str, dict]) -> None:
    path.write_text(
        json.dumps(watchlist, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _native_number(value, as_int: bool = False):
    if value is None:
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return int(number) if as_int else number
    except Exception:
        return None


def snapshot_from_record(record: dict) -> dict:
    keys = (
        "symbol", "name", "waehrung", "kurs", "unternehmensscore",
        "einstieg_score", "trap_score", "fundamental_score",
        "entwicklungs_score", "bewertungs_score", "einstieg_roh",
        "drawdown", "status", "status_text", "modell", "modell_text",
        "sektor", "branche", "updated",
    )
    return {key: record.get(key) for key in keys}


def _score_delta(new, old):
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)):
        return None
    return int(new - old)


def record_from_analysis(data: dict) -> dict:
    trend = data.get("trend", {}) or {}
    return {
        "symbol": str(data.get("symbol", "")).upper(),
        "name": str(data.get("name", data.get("symbol", ""))),
        "waehrung": str(data.get("waehrung", "")),
        "kurs": _native_number(trend.get("kurs")),
        "unternehmensscore": _native_number(data.get("unternehmensscore"), True),
        "einstieg_score": _native_number(data.get("einstieg_score"), True),
        "trap_score": _native_number(data.get("trap_score"), True),
        "fundamental_score": _native_number(data.get("fundamental_score"), True),
        "entwicklungs_score": _native_number(data.get("entwicklungs_score"), True),
        "bewertungs_score": _native_number(data.get("bewertungs_score"), True),
        "einstieg_roh": _native_number(data.get("einstieg_roh"), True),
        "drawdown": _native_number(trend.get("drawdown")),
        "status": str(data.get("i_status", "")),
        "status_text": str(data.get("i_text", "")),
        "modell": str(data.get("modell", "")),
        "modell_text": str(data.get("modell_text", "")),
        "sektor": str(data.get("sektor", "")),
        "branche": str(data.get("branche", "")),
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


def merge_analysis(watchlist: dict[str, dict], data: dict) -> dict:
    symbol = str(data.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("Analyse enthält kein Symbol.")

    previous = watchlist.get(symbol)
    new = record_from_analysis(data)
    history: list[dict] = []

    if isinstance(previous, dict):
        history = list(previous.get("history", []))
        previous_snapshot = snapshot_from_record(previous)
        previous_stamp = previous_snapshot.get("updated")
        if previous_stamp and (not history or history[-1].get("updated") != previous_stamp):
            history.append(previous_snapshot)
        history = history[-60:]

        new["delta_unternehmensscore"] = _score_delta(
            new.get("unternehmensscore"), previous.get("unternehmensscore")
        )
        new["delta_einstieg_score"] = _score_delta(
            new.get("einstieg_score"), previous.get("einstieg_score")
        )
        new["delta_trap_score"] = _score_delta(
            new.get("trap_score"), previous.get("trap_score")
        )
        new["previous_updated"] = previous.get("updated")
    else:
        new["delta_unternehmensscore"] = None
        new["delta_einstieg_score"] = None
        new["delta_trap_score"] = None
        new["previous_updated"] = None

    new["history"] = history
    watchlist[symbol] = new
    return new
