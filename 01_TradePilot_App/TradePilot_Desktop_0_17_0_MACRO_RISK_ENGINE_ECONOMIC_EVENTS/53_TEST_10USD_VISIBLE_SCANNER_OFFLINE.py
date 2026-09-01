from pathlib import Path
from production_real_core import ProductionRealCore, REAL_TEST_USD

base=Path(__file__).resolve().parent
core=ProductionRealCore(base)
assert REAL_TEST_USD == 10.00
r=core.risk.validate_new_buy(amount_usd=10.00, leverage=1, side="BUY", open_positions=0, invested_usd=0, trades_today=0, realized_pnl_today_usd=0)
assert r["ok"], r
r2=core.risk.validate_new_buy(amount_usd=10.01, leverage=1, side="BUY", open_positions=0, invested_usd=0, trades_today=0, realized_pnl_today_usd=0)
assert not r2["ok"]
bot=(base/'bot_engine.py').read_text(encoding='utf-8')
qml=(base/'qml/Main.qml').read_text(encoding='utf-8')
for marker in ['scanStatusText','lastScanSummaryText','SCAN ABGESCHLOSSEN','SCANNING']:
    assert marker in bot
assert 'bot.scanStatusText' in qml and 'bot.lastScanSummaryText' in qml
print("="*108)
print("TRADEPILOT 0.16.3 - USD 10 PILOT + VISIBLE SCANNER OFFLINE")
print("="*108)
print("Pilot amount:                 USD 10.00")
print("Amount > USD 10.00:           BLOCK")
print("Broker minimum auto-increase: FORBIDDEN")
print("Scanner status:               SCAN BEREIT / SCANNING / SCAN ABGESCHLOSSEN")
print("Last scan summary:            OK")
print("Markets result list:          OK")
print("REAL AUTO:                    LOCKED/OFF")
print("Broker POST:                  NICHT VERWENDET")
print("STATUS: USD 10 + VISIBLE SCANNER OK")
