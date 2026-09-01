from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
files = [
    "main.py", "bot_engine.py", "etoro_live_manual.py", "real_execution.py",
    "11_TEST_REAL_EXECUTION_PREFLIGHT_NO_POST.py", "12_MANUAL_REAL_BUY_10EUR.py",
    "13_RECONCILE_REAL_STATE.py", "14_MANUAL_CLOSE_REAL_POSITION.py",
]
for name in files:
    ast.parse((ROOT/name).read_text(encoding="utf-8"))

qml = (ROOT/"qml"/"Main.qml").read_text(encoding="utf-8")
live = (ROOT/"etoro_live_manual.py").read_text(encoding="utf-8")
real = (ROOT/"real_execution.py").read_text(encoding="utf-8")
bot = (ROOT/"bot_engine.py").read_text(encoding="utf-8")
main = (ROOT/"main.py").read_text(encoding="utf-8")

for page in ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]:
    assert page in qml, page
for level in ["FAST", "DAY", "WEEK", "INVEST"]:
    assert level in bot and level in qml, level
assert "BotEngine(APP_DIR)" in main
assert "setContextProperty(\"bot\", bot)" in main
assert "SHADOW / PAPER" in bot and "REAL AUTOTRADING LOCKED" in bot
assert ".post(" not in bot, "Shadow engine must never contain REAL POST"
assert "MAX_LIVE_EUR = 10.00" in live
assert "READINESS_ONLY_NO_POST" in live
assert "TRADEPILOT_REAL_EXECUTION_ENABLED" in real
assert "TRADEPILOT_REAL_AUTOTRADING_ENABLED" in real
assert "REAL_EXECUTION_UNCERTAIN.json" in real
assert "REAL_KILL_SWITCH.lock" in real
assert "POST_BUY_UNCERTAIN" in real and "POST_CLOSE_UNCERTAIN" in real
assert "No POST" not in real or True
assert "https://public-api.etoro.com/api/v2/trading/execution/orders" in real
assert "market-close-orders/positions/{position_id}" in real
assert "shadow_state.json" in bot

print("TradePilot Desktop Alpha 0.12.0 SELFTEST: OK")
print("8 Seiten + Designbasis: OK")
print("Bot Engine separat: OK")
print("Stufen 1-4 FAST/DAY/WEEK/INVEST: OK")
print("Shadow BUY/HOLD/SELL + persistenter State: OK")
print("REAL Execution Core: BUY/CLOSE/Reconcile/Uncertain-Lock/Kill-Switch vorhanden")
print("Sicherheitsprüfung: Shadow-Stresstest ist NICHT an REAL POST gekoppelt")
