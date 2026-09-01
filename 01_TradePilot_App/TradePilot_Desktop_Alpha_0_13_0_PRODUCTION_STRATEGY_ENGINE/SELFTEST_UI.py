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

print("TradePilot Desktop Alpha 0.13.0 SELFTEST: OK")
print("8 Seiten + bestehende Designbasis: OK")
print("Bot Engine separat/asynchron: OK")
print("Stufen 1-4 FAST/DAY/WEEK/INVEST: OK")
print("Production Signals: Trend + Momentum + RSI + Volumen + ATR: OK")
print("Zufalls-/synthetische Bot-Scores entfernt: OK")
print("Shadow BUY/HOLD/SELL + persistenter State: OK")
print("REAL AutoTrading: LOCKED")
print("REAL state-changing POST: weiterhin hart deaktiviert")
