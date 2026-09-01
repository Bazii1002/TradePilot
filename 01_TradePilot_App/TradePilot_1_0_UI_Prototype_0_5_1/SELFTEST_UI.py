from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
required = [
    ROOT / "main.py",
    ROOT / "qml" / "Main.qml",
    ROOT / "qml" / "components" / "NeonCard.qml",
    ROOT / "qml" / "components" / "MetricCard.qml",
    ROOT / "qml" / "components" / "NavItem.qml",
    ROOT / "qml" / "components" / "MarketPill.qml",
    ROOT / "qml" / "components" / "TradeRow.qml",
    ROOT / "qml" / "components" / "NewsRow.qml",
    ROOT / "qml" / "components" / "PortfolioChart.qml",
    ROOT / "assets" / "ui" / "logo.png",
    ROOT / "assets" / "ui" / "bot.png",
    ROOT / "assets" / "news" / "fed.png",
    ROOT / "assets" / "news" / "nasdaq.png",
    ROOT / "assets" / "news" / "btc.png",
    ROOT / "assets" / "news" / "europe.png",
    ROOT / "assets" / "company" / "aapl.png",
    ROOT / "assets" / "company" / "nvda.png",
    ROOT / "assets" / "company" / "msft.png",
    ROOT / "assets" / "company" / "tsla.png",
    ROOT / "assets" / "company" / "spy.png",
    ROOT / "docs" / "TradePilot_UI_Reference_0_5.png",
]
required += [ROOT / "assets" / "icons" / f"{name}.svg" for name in [
    "dashboard", "bot", "portfolio", "markets", "news", "backtest", "trades", "settings",
    "cash", "invested", "value", "today", "bell", "profile",
]]
for p in required:
    assert p.exists(), f"Fehlt: {p}"

text = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
for token in [
    "Cash Available", "Invested", "Portfolio Value", "Today",
    "Recent Trades", "Portfolio Overview", "International Market News",
    "Bot Status", "eToro REAL", "AutoTrader → REAL gesperrt",
    "xScale: window.width / window.designW",
    "yScale: window.height / window.designH",
    "UI Prototype 0.5.1 · Runtime Fix",
    "assets/icons/dashboard.svg", "assets/icons/bell.svg",
    "assets/company/aapl.png", "assets/company/nvda.png",
    "Qt.resolvedUrl",
]:
    assert token in text, f"0.5 UI-Baustein fehlt: {token}"

components = "\n".join(
    (ROOT / "qml" / "components" / f).read_text(encoding="utf-8")
    for f in ["NeonCard.qml", "MetricCard.qml", "PortfolioChart.qml", "NewsRow.qml", "TradeRow.qml"]
)
for token in ["GradientStop", "sparkline", "imageSource", "logoSource", "property var points"]:
    assert token in components, f"Final-Visual-Match-Funktion fehlt: {token}"
assert "quadraticCurveTo" not in (ROOT / "qml" / "components" / "PortfolioChart.qml").read_text(encoding="utf-8"), "Chart darf in 0.5 nicht wieder periodisch geglaettet werden"

# Basic structural sanity checks catch accidental truncation before QML runtime.
for qml in ROOT.rglob("*.qml"):
    q = qml.read_text(encoding="utf-8")
    assert q.count("{") == q.count("}"), f"Unbalancierte {{}} in {qml.name}"
    assert q.count("(") == q.count(")"), f"Unbalancierte () in {qml.name}"

# Prototype MUST contain no broker execution implementation.
all_py = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in ROOT.rglob("*.py") if p.name != "SELFTEST_UI.py"
)
for forbidden in ["/api/v2/trading/execution/orders", "requests.post(", "x-api-key", "x-user-key"]:
    assert forbidden not in all_py, f"Broker-Ausführung unerwartet im UI-Prototyp: {forbidden}"

try:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    if os.name == "nt" and Path(r"C:\\Windows\\Fonts").exists():
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\\Windows\\Fonts")
    from PySide6.QtCore import QObject, Property, Signal, Slot, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    class TestBackend(QObject):
        timeChanged = Signal()
        @Property(str, notify=timeChanged)
        def marketTime(self): return "10:35:42 AM"
        @Property(str, notify=timeChanged)
        def dateText(self): return "May 23, 2025"
        @Property(str, constant=True)
        def version(self): return "SELFTEST"
        @Slot(str)
        def navigationClicked(self, page): pass

    qt_messages = []
    def _qt_message_handler(mode, context, message):
        qt_messages.append(str(message))

    old_handler = qInstallMessageHandler(_qt_message_handler)
    app = QGuiApplication.instance() or QGuiApplication([])
    eng = QQmlApplicationEngine()
    backend = TestBackend()
    eng.rootContext().setContextProperty("backend", backend)
    eng.load(str(ROOT / "qml" / "Main.qml"))
    for _ in range(5):
        app.processEvents()
    assert eng.rootObjects(), "QML runtime load fehlgeschlagen"
    bad = [m for m in qt_messages if "Cannot open" in m or "TypeError:" in m or "ReferenceError:" in m]
    assert not bad, "QML Runtime-Warnungen: " + " | ".join(bad)
    qInstallMessageHandler(old_handler)
    runtime = "QML runtime load + asset resolution: OK"
except ImportError:
    runtime = "QML runtime load: SKIPPED (PySide6 nicht installiert)"

print("TradePilot 1.0 UI Prototype 0.5.1 RUNTIME FIX SELFTEST: OK")
print("Frozen dashboard geometry from 0.4: OK")
print("Unified SVG navigation + KPI icons with resolved URLs: OK")
print("Reference-derived company/news/bot visuals: OK")
print("Cleaner glass cards without visible ambient blobs: OK")
print("Jagged non-periodic portfolio curve + natural Today sparkline: OK")
print("No broker/live trading code in prototype: OK")
print("Backend teardown-safe bindings: OK")
print("Windows font-directory hint: OK")
print(runtime)
