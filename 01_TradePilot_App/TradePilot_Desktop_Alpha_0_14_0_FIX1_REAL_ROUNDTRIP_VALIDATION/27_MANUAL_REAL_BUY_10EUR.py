from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent; m=RealExecutionManager(APP)
print('='*104); print('TRADEPILOT 0.14.0 - MANUAL REAL BUY 10 EUR'); print('='*104)
print('DIESER SCHRITT KANN EINE ECHTE ECHTGELDORDER SENDEN.')
try:
 p=m.preflight_buy('AAPL',10.0,'MANUAL'); print(f"AAPL | Instrument {p['instrument_id']} | {p['budget_eur']:.2f} EUR | ~{p['amount_usd']:.2f} USD | BUY | 1x")
 phrase=input('Zum AUSFÜHREN exakt eingeben: EXECUTE REAL BUY AAPL 10.00 EUR\n> ')
 r=m.execute_buy(p,phrase); print('REAL BUY VERIFIZIERT'); print('Position-ID:',r['position_id']); print('Request-ID:',r['request_id']); print('Order-ID:',r['order_id'] or '(nicht geliefert)')
except Exception as e: print('BLOCKIERT/FEHLER:',e)
