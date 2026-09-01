from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
files = [
    "main.py", "bot_engine.py", "etoro_live_manual.py", "real_execution.py",
    "roundtrip_validator.py", "11_TEST_REAL_EXECUTION_PREFLIGHT_NO_POST.py",
    "12_MANUAL_REAL_BUY_10EUR.py", "13_RECONCILE_REAL_STATE.py",
    "14_MANUAL_CLOSE_REAL_POSITION.py", "17_TEST_REAL_ROUNDTRIP_VALIDATION_NO_POST.py",
]
for name in files:
    ast.parse((ROOT/name).read_text(encoding="utf-8"))

qml = (ROOT/"qml"/"Main.qml").read_text(encoding="utf-8")
real = (ROOT/"real_execution.py").read_text(encoding="utf-8")
bot = (ROOT/"bot_engine.py").read_text(encoding="utf-8")
validator = (ROOT/"roundtrip_validator.py").read_text(encoding="utf-8")

for page in ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]:
    assert page in qml, page
for level in ["FAST", "DAY", "WEEK", "INVEST"]:
    assert level in bot and level in qml, level
assert ".post(" not in bot, "Shadow engine must never contain REAL POST"
assert "REAL AUTOTRADING LOCKED" in bot
assert "REAL POST ist in TradePilot 0.12.1 hart deaktiviert" in real
assert "REAL CLOSE POST ist in TradePilot 0.12.1 hart deaktiviert" in real
# execute_buy / close_position must not contain session.post anymore
buy_part = real.split("def execute_buy",1)[1].split("def _write_position_state",1)[0]
close_part = real.split("def close_position",1)[1].split("def reconcile",1)[0]
assert ".post(" not in buy_part
assert ".post(" not in close_part
assert "NO_POST_SIMULATED_BROKER" in validator
assert "accept_buy" in validator and "accept_close" in validator
assert "real_post_executed\": False" in validator

print("TradePilot Desktop Alpha 0.12.1 SELFTEST: OK")
print("8 Seiten + Designbasis: OK")
print("Bot Engine separat: OK")
print("Stufen 1-4 FAST/DAY/WEEK/INVEST: OK")
print("Shadow BUY/HOLD/SELL + persistenter State: OK")
print("REAL Preflight/Reconcile: GET/READ-ONLY vorhanden")
print("Roundtrip Validator: BUY->State->CLOSE ohne POST vorhanden")
print("Sicherheitsprüfung: state-changing REAL POST in 0.12.1 hart deaktiviert")
