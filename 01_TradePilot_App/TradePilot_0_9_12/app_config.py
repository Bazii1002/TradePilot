from __future__ import annotations
import json
from pathlib import Path

DEFAULTS = {
    "theme": "dark",
    "language": "de",
    "bot_profile": "balanced",
    "bot_enabled": False,
    "demo_capital": 10000.0,
    "scan_source": "watchlist",
    # 0.9.10: lightweight price polling. This is not exchange-grade live data.
    "auto_refresh_enabled": True,
    "quote_refresh_seconds": 60,
    # Scheduled full AutoTrader scans are opt-in because an active AutoTrader
    # may create paper trades when a scheduled scan finds READY candidates.
    "auto_scan_enabled": False,
    "auto_scan_minutes": 15,
    # 0.9.10 paper Order Engine
    "paper_slippage_bps": 5.0,
    "pending_order_max_age_hours": 96,
    "pending_order_max_gap_pct": 3.0,
    # 0.9.10 hard user-defined risk cap. The Risk Manager may invest less, never more.
    "max_trade_value": 1000.0,
}


def config_path(app_dir: Path) -> Path:
    return app_dir / "tradepilot_settings.json"


def load_config(app_dir: Path) -> dict:
    path = config_path(app_dir)
    data = dict(DEFAULTS)
    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update({k: raw[k] for k in DEFAULTS if k in raw})
    except Exception:
        pass

    if data["theme"] not in {"dark", "light"}:
        data["theme"] = "dark"
    if data["language"] not in {"de", "en"}:
        data["language"] = "de"
    if data.get("bot_profile") not in {"defensive", "balanced", "offensive", "speculative"}:
        data["bot_profile"] = "balanced"
    if data.get("scan_source") not in {"watchlist", "core30", "combined"}:
        data["scan_source"] = "watchlist"

    data["bot_enabled"] = bool(data.get("bot_enabled", False))
    data["auto_refresh_enabled"] = bool(data.get("auto_refresh_enabled", True))
    data["auto_scan_enabled"] = bool(data.get("auto_scan_enabled", False))

    try:
        data["demo_capital"] = max(100.0, float(data.get("demo_capital", 10000.0)))
    except Exception:
        data["demo_capital"] = 10000.0

    try:
        sec = int(data.get("quote_refresh_seconds", 60))
    except Exception:
        sec = 60
    data["quote_refresh_seconds"] = sec if sec in {30, 60, 120, 300} else 60

    try:
        minutes = int(data.get("auto_scan_minutes", 15))
    except Exception:
        minutes = 15
    data["auto_scan_minutes"] = minutes if minutes in {5, 15, 30, 60} else 15

    try:
        bps = float(data.get("paper_slippage_bps", 5.0))
    except Exception:
        bps = 5.0
    data["paper_slippage_bps"] = min(100.0, max(0.0, bps))

    try:
        hours = int(data.get("pending_order_max_age_hours", 96))
    except Exception:
        hours = 96
    data["pending_order_max_age_hours"] = max(1, min(336, hours))

    try:
        gap = float(data.get("pending_order_max_gap_pct", 3.0))
    except Exception:
        gap = 3.0
    data["pending_order_max_gap_pct"] = max(0.25, min(20.0, gap))

    try:
        max_trade = float(data.get("max_trade_value", 1000.0))
    except Exception:
        max_trade = 1000.0
    data["max_trade_value"] = max(1.0, min(1_000_000.0, max_trade))
    return data


def save_config(app_dir: Path, config: dict) -> None:
    path = config_path(app_dir)
    clean = {k: config.get(k, v) for k, v in DEFAULTS.items()}
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
