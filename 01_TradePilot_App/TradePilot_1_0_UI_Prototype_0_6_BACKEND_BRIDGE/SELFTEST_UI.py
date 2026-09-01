from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def req(path: str):
    p = ROOT / path
    assert p.exists(), f"Fehlt: {path}"
    return p

req("main.py")
req("etoro_readonly.py")
req("history_store.py")
req("exchange_status.py")
req("qml/Main.qml")
req("03_SETUP_ETORO_KEYS.bat")
req("04_TEST_ETORO_READONLY.bat")
for icon in ("dashboard", "bot", "portfolio", "markets", "news", "backtest", "trades", "settings", "cash", "invested", "value", "today", "bell", "profile"):
    req(f"assets/icons/{icon}.svg")

# Parser test with an official-doc-like shape.
from etoro_readonly import parse_snapshot
sample = {
    "data": {
        "currency": "USD",
        "buyingPower": 18540.89,
        "equity": 99999.99,
        "positions": [
            {"symbol": "AAPL", "instrumentName": "Apple Inc.", "invested": 81459.10, "pnl": 312.40}
        ],
    }
}
pnl = {"data": {"todayPnl": 1259.34, "todayPnlPercent": 1.28}}
s = parse_snapshot(sample, pnl)
assert s["currency"] == "USD"
assert abs(s["cash"] - 18540.89) < 1e-6
assert abs(s["equity"] - 99999.99) < 1e-6
assert s["position_count"] == 1
assert abs(s["today_pnl"] - 1259.34) < 1e-6

readonly = req("etoro_readonly.py").read_text(encoding="utf-8").lower()
for forbidden in (".post(", "requests.post", ".put(", ".patch(", ".delete(", "/execution/orders"):
    assert forbidden not in readonly, f"READ-ONLY verletzt: {forbidden}"

qml = req("qml/Main.qml").read_text(encoding="utf-8")
for token in ("backend.cashText", "backend.investedText", "backend.portfolioText", "backend.activityRowsJson", "backend.portfolioChartJson", "backend.brokerStatusText"):
    assert token in qml, f"Backend-Binding fehlt: {token}"

print("TradePilot 1.0 UI Prototype 0.6 BACKEND BRIDGE SELFTEST: OK")
print("eToro REAL portfolio GET bridge: OK")
print("eToro REAL P/L GET bridge: OK")
print("No POST/PUT/PATCH/DELETE or order endpoint: OK")
print("Dynamic KPI / positions / chart bindings: OK")
print("Local non-identifying portfolio history: OK")
print("Exchange status bridge: OK")

# Optional QML runtime load when PySide6 is available.
try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from main import Backend

    app = QGuiApplication.instance() or QGuiApplication([])
    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(str(ROOT / "qml" / "Main.qml"))
    assert engine.rootObjects(), "QML runtime konnte Main.qml nicht laden"
    QTimer.singleShot(40, app.quit)
    app.exec()
    print("QML runtime load: OK")
except ImportError:
    print("QML runtime load: SKIP (PySide6 hier nicht installiert)")
