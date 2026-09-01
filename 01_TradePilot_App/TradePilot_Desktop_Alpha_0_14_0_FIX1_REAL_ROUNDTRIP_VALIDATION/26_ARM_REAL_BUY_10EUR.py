from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent; m=RealExecutionManager(APP)
print('='*104); print('TRADEPILOT 0.14.0 - ARM REAL BUY'); print('='*104)
print('ACHTUNG: Dies bereitet einen echten Echtgeld-Trade vor. Es sendet NOCH KEINEN POST.')
try:
 p=m.preflight_buy('AAPL',10.0,'MANUAL'); print(f"AAPL | {p['instrument_id']} | {p['budget_eur']:.2f} EUR | ~{p['amount_usd']:.2f} USD | BUY | 1x")
 phrase=input('Zum ARMEN exakt eingeben: ARM REAL BUY AAPL 10.00 EUR\n> ')
 if phrase!='ARM REAL BUY AAPL 10.00 EUR': raise RuntimeError('ARM abgebrochen: Bestätigung falsch.')
 a=m.arm_buy(p); print('ARM aktiv für maximal 10 Minuten. Noch kein Broker POST.'); print('Nächster Schritt nur bewusst: 27_MANUAL_REAL_BUY_10EUR.bat')
except Exception as e: print('BLOCKIERT:',e)
