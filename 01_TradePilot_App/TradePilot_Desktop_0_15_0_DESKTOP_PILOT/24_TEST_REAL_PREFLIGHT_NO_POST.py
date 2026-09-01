from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent
print('='*104); print('TRADEPILOT 0.14.0 - REAL PREFLIGHT / NO POST'); print('='*104)
m=RealExecutionManager(APP)
try:
 p=m.preflight_buy('AAPL',10.0,'MANUAL')
 print(f"Symbol: {p['symbol']} | Instrument: {p['instrument_id']} | Budget: {p['budget_eur']:.2f} EUR | USD: {p['amount_usd']:.2f}")
 print('Leverage: 1x | BUY only | Broker POST: NEIN')
 print('STATUS: PREFLIGHT OK')
except Exception as e: print('STATUS: BLOCKIERT\n'+str(e))
