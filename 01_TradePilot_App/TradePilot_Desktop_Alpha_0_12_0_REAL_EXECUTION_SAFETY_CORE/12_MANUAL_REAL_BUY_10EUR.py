from pathlib import Path
from real_execution import RealExecutionManager

APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('='*100)
print('TRADEPILOT 0.12.0 - MANUAL REAL BUY')
print('='*100)
print('ACHTUNG: Dieses Werkzeug kann eine ECHTE Echtgeldorder senden.')
print('Kein automatischer POST-Retry. Bei unklarem Status wird REAL gesperrt.\n')
try:
    p=m.preflight_buy('AAPL', 10.0, 'MANUAL')
    print(f"Ticker:        {p['symbol']}")
    print(f"Instrument-ID: {p['instrument_id']}")
    print(f"Budget:        {p['budget_eur']:.2f} EUR")
    print(f"USD Amount:    {p['amount_usd']:.2f} USD")
    print('BUY · Market · Leverage 1x')
    print('\nZum Abbrechen einfach Enter drücken.')
    phrase=f"LIVE BUY {p['symbol']} {p['budget_eur']:.2f}"
    c=input(f"Für die echte Order exakt eingeben: {phrase}\n> ")
    if not c.strip():
        print('ABGEBROCHEN. Keine Order gesendet.')
    else:
        r=m.execute_buy(p,c)
        print('\nORDER BESTÄTIGT')
        print(f"Status:      {r['status']}")
        print(f"Position-ID: {r['position_id'] or 'vom Portfolio bestätigt'}")
        print(f"Order-ID:    {r['order_id'] or '—'}")
        print('Kein Retry wurde ausgeführt.')
except Exception as exc:
    print(f'\nBLOCKIERT/FEHLER: {exc}')
