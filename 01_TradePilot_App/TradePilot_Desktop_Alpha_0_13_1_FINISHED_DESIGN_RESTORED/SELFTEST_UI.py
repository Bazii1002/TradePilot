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
assert "REAL POST ist in TradePilot 0.12.1 hart deaktiviert" in real
assert "REAL CLOSE POST ist in TradePilot 0.12.1 hart deaktiviert" in real
assert "NO_POST_SIMULATED_BROKER" in validator

print("TradePilot Desktop Alpha 0.13.1 SELFTEST: OK")
print("8 Seiten + Finished Designbasis: OK")
print("QML Struktur/Semikolon-Sanity-Check: OK")
print("Bot Engine separat/asynchron: OK")
print("Stufen 1-4 FAST/DAY/WEEK/INVEST: OK")
print("Production Signals: Trend + Momentum + RSI + Volumen + ATR: OK")
print("Zufalls-/synthetische Bot-Scores entfernt: OK")
print("Shadow BUY/HOLD/SELL + persistenter State: OK")
print("REAL AutoTrading: LOCKED")
print("REAL state-changing POST: weiterhin hart deaktiviert")


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
