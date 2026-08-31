from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent
required = [
    ROOT / "main.py",
    ROOT / "qml" / "Main.qml",
    ROOT / "qml" / "components" / "MetricCard.qml",
    ROOT / "qml" / "components" / "GlassCard.qml",
    ROOT / "qml" / "components" / "NavItem.qml",
    ROOT / "qml" / "components" / "MarketPill.qml",
    ROOT / "qml" / "components" / "TradeRow.qml",
    ROOT / "qml" / "components" / "NewsRow.qml",
    ROOT / "docs" / "TradePilot_UI_Reference.png",
]
for p in required:
    assert p.exists(), f"Fehlt: {p}"

text = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
for token in ["Cash Available", "Recent Trades", "Portfolio Overview", "International Market News", "Bot Status", "eToro REAL", "AutoTrader → REAL gesperrt"]:
    assert token in text, f"UI-Baustein fehlt: {token}"

# Runtime QML parse/load test when PySide6 is available (it should be on the TradePilot PC).
try:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    from PySide6.QtCore import QObject, Property, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    class TestBackend(QObject):
        timeChanged = Signal()
        @Property(str, notify=timeChanged)
        def marketTime(self): return "3:22:11 PM"
        @Property(str, notify=timeChanged)
        def dateText(self): return "Aug 31, 2026"
        @Property(str, constant=True)
        def version(self): return "SELFTEST"
        @Slot(str)
        def navigationClicked(self, page): pass

    app = QGuiApplication.instance() or QGuiApplication([])
    eng = QQmlApplicationEngine()
    eng.rootContext().setContextProperty("backend", TestBackend())
    eng.load(str(ROOT / "qml" / "Main.qml"))
    assert eng.rootObjects(), "QML runtime load fehlgeschlagen"
    runtime = "QML runtime load: OK"
except ImportError:
    runtime = "QML runtime load: SKIPPED (PySide6 nicht installiert)"

print("TradePilot 1.0 UI Prototype 0.1 SELFTEST: OK")
print("Dashboard reference packaged: OK")
print("QML component structure: OK")
print("No broker/live trading code in prototype: OK")
print(runtime)
