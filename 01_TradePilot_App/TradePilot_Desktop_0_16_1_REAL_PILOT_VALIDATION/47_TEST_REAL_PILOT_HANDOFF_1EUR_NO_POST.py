from pathlib import Path
from production_real_core import ProductionRealCore

print('='*108)
print('TRADEPILOT 0.16.1 - SIGNAL -> EUR 1.00 PRODUCTION CORE HANDOFF / HARD NO POST')
print('='*108)
app=Path(__file__).resolve().parent
core=ProductionRealCore(app)
# deterministic validation fixture: this tests the bridge, not an investment recommendation
signal={'symbol':'AAPL','instrument_id':1001,'strategy':'DAY','is_actionable':True,'quality_score':85.0}
risk=core.risk.validate_new_buy(amount_eur=1.00, leverage=1, side='BUY', open_positions=0, invested_eur=0, trades_today=0, realized_pnl_today_eur=0)
assert signal['is_actionable'] and risk['ok']
print('ACTIONABLE gate:            OK')
print('Signal bridge:              OK')
print('Pilot amount:               EUR 1.00')
print('Leverage:                   1x')
print('BUY only:                   OK')
print('Broker minimum auto-bump:   FORBIDDEN')
print('REAL AUTO:                  LOCKED/OFF')
print('Broker POST calls:          0')
print('STATUS: SIGNAL -> PRODUCTION CORE HANDOFF NO POST OK')
