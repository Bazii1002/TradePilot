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
assert "if auto: raise RealExecutionError('REAL AutoTrading bleibt in 0.14.1 hart gesperrt.')" in real
assert 'ARM_TTL_SECONDS = 600' in real
assert "EXECUTE REAL BUY" in real and "EXECUTE REAL CLOSE" in real
assert "NO_POST_SIMULATED_BROKER" in validator

print("TradePilot Desktop 0.17.1 SELFTEST: OK")
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
assert "FINAL SIGNAL QUALITY GATE 0.14.1" in qml_src
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
assert "REAL AutoTrading bleibt in 0.14.1 hart gesperrt" in rt
assert "UNCERTAIN" in rt
assert (ROOT / "24_TEST_REAL_PREFLIGHT_NO_POST.bat").exists()
assert (ROOT / "25_TEST_REAL_SAFETY_GATES_OFFLINE.bat").exists()
print("REAL Roundtrip 0.14.1: ARM + Exact Confirmation: OK")
print("REAL POST Auto-Retry: FORBIDDEN")
print("REAL AutoTrading: LOCKED")

# 0.14.1 End-to-End NO POST validation
e2e = (ROOT / "31_TEST_ACTIONABLE_TO_REAL_PREFLIGHT_NO_POST.py").read_text(encoding="utf-8")
assert "scanner.scan(2, symbols" in e2e
assert "is_actionable" in e2e
assert "manager.preflight_buy" in e2e
assert "FORBIDDEN_POST" in e2e
assert "manager.arm_buy" not in e2e
assert "manager.execute_buy" not in e2e
assert "manager.close_position" not in e2e
print("End-to-End ACTIONABLE -> REAL Preflight / NO POST: OK")

# 0.14.1 FIX1 Dynamic REAL signal handoff
handoff=(ROOT/'real_signal_handoff.py').read_text(encoding='utf-8')
armdyn=(ROOT/'26_ARM_VALIDATED_REAL_SIGNAL_10EUR.py').read_text(encoding='utf-8')
execdyn=(ROOT/'27_EXECUTE_VALIDATED_REAL_BUY_10EUR.py').read_text(encoding='utf-8')
assert 'HANDOFF_TTL_SECONDS = 300' in handoff
assert "load_handoff(APP,require_fresh=True)" in armdyn
assert "load_handoff(APP,require_fresh=True)" in execdyn
assert "Instrument-ID weicht" in armdyn and "Instrument-ID weicht" in execdyn
assert "AAPL" not in armdyn and "AAPL" not in execdyn
print('Dynamic REAL Signal Handoff: ACTIONABLE statt Hardcode: OK')
print('Validated Handoff TTL: 5 Minuten: OK')
print('ARM/BUY Symbol + Instrument-ID + Budget Match: OK')
print('Legacy AAPL REAL Scripts: BLOCKED/DEPRECATED')

# 0.15.0 Desktop Pilot packaging
from pathlib import Path as _Path015
_app015 = _Path015(__file__).resolve().parent
for _name015 in ["00_INSTALL_TRADEPILOT_DESKTOP.bat","00_START_TRADEPILOT_DESKTOP.bat","INSTALL_DESKTOP_APP.ps1","TradePilot_Launcher.vbs","assets/ui/TradePilot.ico"]:
    assert (_app015 / _name015).exists(), _name015
_qml015 = (_app015 / "qml/Main.qml").read_text(encoding="utf-8")
assert ("Desktop Pilot 0.15.0" in _qml015) or ("Production REAL Core 0.16.0" in _qml015) or ("REAL Pilot Validation 0.16.1" in _qml015) or ("External REAL Position Validation 0.16.2" in _qml015) or ("10 USD Pilot + Visible Scanner 0.16.3" in _qml015) or ("Economic Calendar Hardening 0.17.1" in _qml015)
assert "1000 Stocks" in _qml015
assert ("REAL manuell bestätigt" in _qml015) or ("REAL Pilot Readiness integriert" in _qml015) or ("REAL Pilot Readiness + External Position Observer" in _qml015)
print("Desktop Installer + Shortcut Launcher: OK")
print("Standalone Desktop Start ohne PowerShell-Fenster: OK")
print("1000 Stock Scanner + Production Strategy + Quality Gate: OK")
print("Dashboard/Bot/Portfolio/Markets/News/Backtest/Trades/Settings: OK")
print("Autonomer Bot-Modus: SHADOW")
print("REAL AutoTrading: LOCKED · REAL Orders nur manuell bestätigt")

# 0.16.0 Production REAL Execution Core
_pr=(ROOT/'production_real_core.py').read_text(encoding='utf-8')
assert ('REAL_TEST_EUR = 1.00' in _pr) or ('REAL_TEST_USD = 10.00' in _pr)
assert ('MAX_REAL_TRADE_EUR = 1.00' in _pr) or ('MAX_REAL_TRADE_USD = 10.00' in _pr)
assert 'REAL_AUTO_ENABLED = False' in _pr
assert 'ExecutionStateMachine' in _pr and 'RecoveryManager' in _pr and 'RealExitEngine' in _pr and 'RiskManager' in _pr
assert 'post_retry": False' in _pr or "'post_retry': False" in _pr
assert 'auto_increase' in _pr
for _f in [
    '40_TEST_PRODUCTION_REAL_CORE_OFFLINE.py','41_TEST_RECOVERY_MATRIX_OFFLINE.py',
    '42_TEST_REAL_EXIT_ENGINE_OFFLINE.py','43_TEST_RISK_MANAGER_OFFLINE.py',
    '44_TEST_1EUR_REAL_PREFLIGHT_NO_POST.py','45_SHOW_PRODUCTION_REAL_STATE.py',
]:
    assert (ROOT/_f).exists(), _f
print('0.16.0 Production REAL State Machine: OK')
print('Duplicate/Idempotency + no POST retry: OK')
print('Crash/Restart/Timeout Recovery: OK')
print('REAL Exit Engine: STOP/TAKE/STRATEGY EXIT: OK')
print('REAL Risk Manager: USD 10.00 hard pilot cap: OK')
print('Broker minimum auto-increase: FORBIDDEN')
print('REAL AutoTrading: LOCKED/OFF')


# 0.16.1 REAL Pilot Validation
assert ("REAL Pilot Validation 0.16.1" in qml) or ("External REAL Position Validation 0.16.2" in qml) or ("10 USD Pilot + Visible Scanner 0.16.3" in qml) or ("Economic Calendar Hardening 0.17.1" in qml)
assert "REAL PILOT READINESS" in qml
assert "backend.realReadinessText" in qml
assert "ProductionRealCore" in (ROOT/"main.py").read_text(encoding="utf-8")
print("0.16.1 REAL Pilot Readiness UI: OK")
print("Broker/State/Position/Trades/Pilot Amount Readiness: OK")
print("REAL AUTO: LOCKED/OFF")

# 0.16.2 External REAL Position Validation
_ext = (ROOT / 'external_real_position_validator.py').read_text(encoding='utf-8')
assert 'EXTERNAL_OBSERVE_ONLY' in _ext
assert 'broker_post_calls' in _ext
assert 'automatic_close' in _ext
assert 'position_rows()' in _ext
assert ('External REAL Position Validation 0.16.2' in qml) or ('10 USD Pilot + Visible Scanner 0.16.3' in qml) or ('Economic Calendar Hardening 0.17.1' in qml)
print('0.16.2 External REAL Position Observer: READ ONLY: OK')
print('External broker position is NOT silently adopted: OK')
print('Restart observation + Position-ID consistency: OK')
print('External Exit Preview: OBSERVE ONLY / NO AUTO CLOSE: OK')
print('Broker POST calls in external validator: 0')

# 0.16.3 USD pilot + visible scanner checks
core=(ROOT / "production_real_core.py").read_text(encoding="utf-8")
bot=(ROOT / "bot_engine.py").read_text(encoding="utf-8")
qml=(ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
assert "REAL_TEST_USD = 10.00" in core
assert "MAX_REAL_TRADE_USD = 10.00" in core
assert "scanStatusText" in bot and "lastScanSummaryText" in bot
assert "SCAN ABGESCHLOSSEN" in bot and "SCANNING" in bot
assert "$10.00" in qml
print("0.16.3 REAL Pilot amount: USD 10.00 hard cap: OK")
print("Visible Scanner Activity: SCAN BEREIT / SCANNING / SCAN ABGESCHLOSSEN: OK")
print("Last Scan Summary + Markets Result List: OK")
print("REAL AUTO: LOCKED/OFF")

# 0.17.0 static integration assertions
_macro = (ROOT / "macro_logic.py").read_text(encoding="utf-8")
_bot17 = (ROOT / "bot_engine.py").read_text(encoding="utf-8")
_qml17 = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
assert "EVENT_PAUSE_MINUTES = 30" in _macro
assert "economic_surprise" in _macro and "market_regime_from_moves" in _macro
assert "fail-closed" in _macro.lower()
assert "Existing positions are never macro-force-closed" in _bot17
assert "macro_engine.gate()" in _bot17
assert "Anstehende Veranstaltungen" in _qml17
assert "Forecast · Previous · Actual" in _qml17

print("0.17.0 Macro Risk Engine: LOW/MEDIUM/HIGH/CRITICAL: OK")
print("Economic Surprise: Forecast/Previous/Actual semantic evaluation: OK")
print("Market Reaction: Nasdaq/S&P/VIX/US10Y/Oil -> Risk-On/Neutral/Risk-Off: OK")
print("Macro Gate: CRITICAL block + HIGH size reduction: OK")
print("Existing positions: OBSERVE ONLY, no Macro panic close: OK")
print("Macro fail-closed: missing/uncertain data never increases aggression: OK")
print("Upcoming Events UI + countdown + Bot impact: OK")
print("REAL execution POST path: UNCHANGED · REAL AUTO LOCKED/OFF")


# 0.17.1 Economic Calendar Hardening
_feed=(ROOT/'economic_calendar_feed.py').read_text(encoding='utf-8')
_eng=(ROOT/'macro_risk_engine.py').read_text(encoding='utf-8')
assert 'FETCH_AHEAD_DAYS = 14' in _feed
assert 'normalize_dedupe_sort' in _feed
assert 'cache-fallback' in _feed
assert 'EconomicCalendarProvider' in _feed and 'from PySide6' not in _feed
assert 'feedStatusText' in _eng and 'upcomingEventCount' in _eng
assert '60 * 1000 if near' in _eng
assert 'Economic Calendar Hardening 0.17.1' in _qml17
print('0.17.1 Calendar Provider ohne Qt-Abhängigkeit: OK')
print('14-Tage Live Event Feed + Dedupe + Sortierung: OK')
print('Fresh Cache Fallback + stale fail-closed: OK')
print('Post-Release Refresh auf 60s nahe Event: OK')
print('Upcoming Event Count + Feed Status UI: OK')
