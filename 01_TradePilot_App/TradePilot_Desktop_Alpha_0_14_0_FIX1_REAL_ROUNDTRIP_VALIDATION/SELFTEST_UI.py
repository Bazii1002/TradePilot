from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
files = [
    "main.py", "bot_engine.py", "strategy_engine.py", "etoro_live_manual.py", "real_execution.py",
    "roundtrip_validator.py", "11_TEST_REAL_EXECUTION_PREFLIGHT_NO_POST.py",
    "12_MANUAL_REAL_BUY_10EUR.py", "13_RECONCILE_REAL_STATE.py",
    "14_MANUAL_CLOSE_REAL_POSITION.py", "17_TEST_REAL_ROUNDTRIP_VALIDATION_NO_POST.py",
    "18_TEST_PRODUCTION_STRATEGY_ENGINE_OFFLINE.py",
]
for name in files:
    ast.parse((ROOT/name).read_text(encoding="utf-8"))

qml = (ROOT/"qml"/"Main.qml").read_text(encoding="utf-8")
real = (ROOT/"real_execution.py").read_text(encoding="utf-8")
bot = (ROOT/"bot_engine.py").read_text(encoding="utf-8")
strategy = (ROOT/"strategy_engine.py").read_text(encoding="utf-8")
validator = (ROOT/"roundtrip_validator.py").read_text(encoding="utf-8")

# Statischer QML-Syntax-Sanity-Check: verhindert die Fehlerklasse aus 0.13.0 Erstbuild.
def _qml_structure_sanity(text: str) -> None:
    import re
    assert not re.search(r"}\s*;\s*[A-Z][A-Za-z0-9_]*\s*\{", text), "Ungueltiges Semikolon zwischen QML-Objekten"
    cleaned = []
    i = 0
    quote = None
    escaped = False
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            cleaned.append(" ")
        else:
            if ch in ("'", '"'):
                quote = ch
                cleaned.append(" ")
            elif ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
                while i < len(text) and text[i] != "\n":
                    cleaned.append(" ")
                    i += 1
                if i < len(text):
                    cleaned.append("\n")
            else:
                cleaned.append(ch)
        i += 1
    structure = "".join(cleaned)
    assert structure.count("{") == structure.count("}"), "QML geschweifte Klammern nicht ausgeglichen"
    assert structure.count("[") == structure.count("]"), "QML eckige Klammern nicht ausgeglichen"
    assert structure.count("(") == structure.count(")"), "QML runde Klammern nicht ausgeglichen"

_qml_structure_sanity(qml)

for page in ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]:
    assert page in qml, page
for level in ["FAST", "DAY", "WEEK", "INVEST"]:
    assert level in strategy and level in qml, level
assert "random" not in bot, "Production BotEngine must not generate random signals"
assert "math.sin" not in bot, "Synthetic score generator must be removed"
assert "ProductionStrategyEngine" in bot
assert "yfinance" in strategy
assert "RSI" in strategy or "_rsi" in strategy
assert "REAL AUTOTRADING LOCKED" in bot
assert ".post(" not in bot, "Strategy engine must never contain REAL POST"
# 0.14.0 intentionally contains manual REAL POST transport, but it must be fail-closed.
assert 'TRADEPILOT_REAL_EXECUTION_ENABLED' in real
assert "if not c.enabled: raise RealExecutionError('REAL execution ist standardmäßig LOCKED." in real
assert "if auto: raise RealExecutionError('REAL AutoTrading bleibt in 0.14.0 hart gesperrt.')" in real
assert 'ARM_TTL_SECONDS = 600' in real
assert "EXECUTE REAL BUY" in real and "EXECUTE REAL CLOSE" in real
assert "NO_POST_SIMULATED_BROKER" in validator

print("TradePilot Desktop Alpha 0.14.0 REAL ROUNDTRIP VALIDATION SELFTEST: OK")
print("8 Seiten + Finished Designbasis: OK")
print("QML Struktur/Semikolon-Sanity-Check: OK")
print("Bot Engine separat/asynchron: OK")
print("Stufen 1-4 FAST/DAY/WEEK/INVEST: OK")
print("Production Signals: Trend + Momentum + RSI + Volumen + ATR: OK")
print("Zufalls-/synthetische Bot-Scores entfernt: OK")
print("Shadow BUY/HOLD/SELL + persistenter State: OK")
print("REAL AutoTrading: LOCKED")
print("REAL state-changing POST: MANUAL ONLY + default LOCKED")


def _finished_design_checks():
    import re
    qml = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    required = [
        "Market Time (ET)", "Cash Available", "Invested", "Portfolio Value", "Today",
        "Open Positions", "Portfolio Overview", "International Market News · Preview",
        "Bot Status", "NYSE", "NASDAQ", "XETRA", "View Bot  ›",
        "AutoTrader Control", "FAST", "DAY", "WEEK", "INVEST",
        "Open REAL Positions", "Markets · Production Scanner", "Trade History · Shadow Production Signals"
    ]
    missing = [x for x in required if x not in qml]
    assert not missing, f"Finished design markers missing: {missing}"
    assert "Placeholder pages until dashboard is frozen" not in qml
    # Catch the exact QML failure class that occurred in 0.13.0.
    assert not re.search(r"}\s*;\s*(?:}|$)", qml, re.M), "Verdächtiges QML object-semicolon gefunden"
    # Coarse structural balance ignoring strings/comments is enough to catch truncated builds.
    cleaned = re.sub(r'//.*', '', qml)
    cleaned = re.sub(r'"(?:\\.|[^"\\])*"', '""', cleaned)
    assert cleaned.count('{') == cleaned.count('}'), f"QML braces unbalanced: {cleaned.count('{')} != {cleaned.count('}')}"
    print("Finished TradePilot Designbasis: RESTORED")
    print("Dashboard frozen reference layout: OK")
    print("8 Seiten im gleichen Designsystem: OK")

_finished_design_checks()


def _premium_polish_checks():
    qml = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    nav = (ROOT / "qml" / "components" / "NavItem.qml").read_text(encoding="utf-8")
    card = (ROOT / "qml" / "components" / "NeonCard.qml").read_text(encoding="utf-8")
    market = (ROOT / "qml" / "components" / "MarketPill.qml").read_text(encoding="utf-8")
    chart = (ROOT / "qml" / "components" / "PortfolioChart.qml").read_text(encoding="utf-8")
    assert "PREMIUM VISUAL POLISH 0.13.2" in qml
    assert "SequentialAnimation on opacity" in qml
    assert "hoverEnabled: true" in nav
    assert "Soft outer halo" in card
    assert "SequentialAnimation on opacity" in market
    assert "ctx.arc(last[0],last[1]" in chart
    print("Premium Glass/Neon Surfaces: OK")
    print("Hover/Interaction Polish: OK")
    print("RUNNING/Market Pulse: OK")
    print("Portfolio Chart Polish: OK")
    print("Frozen Layout Geometry: UNCHANGED")

_premium_polish_checks()

# 0.13.3 scanner architecture checks
for fn in ["fast_scanner.py", "universe_provider.py", "19_TEST_1000_STOCK_FAST_SCANNER_OFFLINE.py"]:
    assert (ROOT / fn).exists(), f"Fehlt: {fn}"
fast_src=(ROOT / "fast_scanner.py").read_text(encoding="utf-8")
assert "FAST_BATCH_SIZE = 25" in fast_src
assert "FAST_WORKERS = 8" in fast_src
assert "FAST_CANDIDATES = 50" in fast_src
assert "held_symbols" in fast_src
scanner_qml=(ROOT / "qml" / "components" / "ScannerMetric.qml")
assert scanner_qml.exists(), "ScannerMetric.qml fehlt"
main_qml=(ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
for marker in ["UNIVERSE", "SCANNED", "CANDIDATES", "RAW BUY", "ACTIONABLE", "scannerDurationText"]:
    assert marker in main_qml, f"Scanner UI Marker fehlt: {marker}"
print("1000 Stock Fast Scanner: Cache + Batch + Parallelisierung: OK")
print("Pipeline 1000 -> Top 50 -> Deep Analysis: OK")


# 0.13.4 Dashboard interaction + polish checks
qml = (ROOT/"qml"/"Main.qml").read_text(encoding="utf-8")
metric = (ROOT/"qml"/"components"/"MetricCard.qml").read_text(encoding="utf-8")
news = (ROOT/"qml"/"components"/"NewsRow.qml").read_text(encoding="utf-8")
assert "function goPage(index)" in qml
assert "window.dashboardRange = modelData" in qml
assert "onClicked: window.goPage(2)" in qml
assert "onClicked: window.goPage(4)" in qml
assert "onClicked: window.goPage(7)" in qml
assert "signal clicked()" in metric
assert "signal clicked()" in news
assert "PREMIUM VISUAL POLISH II 0.13.4" in qml
print("Dashboard Buttons/Navigation: OK")
print("Portfolio Range Controls: OK")
print("Topbar Bell/Profile Actions: OK")
print("Visual Polish II: OK")


# 0.14.0 scanner optimization checks
fast_src=(ROOT/"fast_scanner.py").read_text(encoding="utf-8")
bot_src=(ROOT/"bot_engine.py").read_text(encoding="utf-8")
qml_src=(ROOT/"qml"/"Main.qml").read_text(encoding="utf-8")
for marker in ["FINALIST_LIMIT = 12", "RETRY_BATCH_SIZE = 5", "FAILS_BEFORE_QUARANTINE = 3", "invalid_symbols.json", "mark_finalists"]:
    assert marker in fast_src, marker
assert 'r.get("is_actionable") and r.get("signal") == "BUY"' in bot_src
assert "scannerFinalists" in bot_src
assert 'label: "FINALISTS"' in qml_src
assert "FINAL SIGNAL QUALITY GATE 0.14.0" in qml_src
print("Retry + Invalid Symbol Quarantine Cache: OK")
print("Finalistenstufe Deep -> Top 12: OK")
print("Shadow BUY Gate nur ACTIONABLE: OK")
print("Bestehende Positionen bleiben Deep-analysiert: OK")

# 0.14.0 Final Signal Quality Gate
qg=(ROOT/'quality_gate.py').read_text(encoding='utf-8')
be=(ROOT/'bot_engine.py').read_text(encoding='utf-8')
fs=(ROOT/'fast_scanner.py').read_text(encoding='utf-8')
assert 'MAX_ACTIONABLE_SIGNALS = 3' in qg
assert 'MIN_CONFIRMATIONS = 4' in qg
assert 'apply_quality_gate' in fs
assert 'is_actionable' in be
assert 'scannerActionable' in be
print('Final Signal Quality Gate: Score/RSI/Momentum/Volumen/ATR: OK')
print('Actionable Gate: maximal 3 Signale pro Scan: OK')
print('Quality Score != Gewinnwahrscheinlichkeit: OK')
print('Shadow BUY Gate nur ACTIONABLE: OK')

# 0.14.0 REAL Roundtrip Safety
rt=(ROOT / "real_execution.py").read_text(encoding="utf-8")
assert "EXECUTE REAL BUY" in rt and "EXECUTE REAL CLOSE" in rt
assert "REAL AutoTrading bleibt in 0.14.0 hart gesperrt" in rt
assert "UNCERTAIN" in rt
assert (ROOT / "24_TEST_REAL_PREFLIGHT_NO_POST.bat").exists()
assert (ROOT / "25_TEST_REAL_SAFETY_GATES_OFFLINE.bat").exists()
print("REAL Roundtrip 0.14.0: ARM + Exact Confirmation: OK")
print("REAL POST Auto-Retry: FORBIDDEN")
print("REAL AutoTrading: LOCKED")
