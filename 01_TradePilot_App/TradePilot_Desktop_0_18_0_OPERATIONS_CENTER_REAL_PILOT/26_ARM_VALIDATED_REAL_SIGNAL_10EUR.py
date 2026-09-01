from pathlib import Path
from real_execution import RealExecutionManager
from real_signal_handoff import load_handoff
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('='*112); print('TRADEPILOT 0.14.1 FIX1 - ARM VALIDATED REAL SIGNAL'); print('='*112)
print('ACHTUNG: Bereitet den frisch validierten Echtgeld-Trade vor. NOCH KEIN POST.')
try:
    h=load_handoff(APP,require_fresh=True)
    p=m.preflight_buy(h['symbol'],h['budget_eur'],h.get('strategy','DAY'))
    if int(p['instrument_id'])!=int(h['instrument_id']): raise RuntimeError('BLOCK: Instrument-ID weicht vom validierten Handoff ab.')
    if abs(float(p['budget_eur'])-float(h['budget_eur']))>1e-9: raise RuntimeError('BLOCK: Budget weicht vom validierten Handoff ab.')
    print(f"Signal: {h['symbol']} | Instrument {h['instrument_id']} | Q {h['quality_score']:.1f} | {h['quality_confirmations']}/{h['quality_checks']}")
    print(f"Order:  {p['budget_eur']:.2f} EUR | ~{p['amount_usd']:.2f} USD | BUY | 1x")
    expected=f"ARM REAL BUY {p['symbol']} {float(p['budget_eur']):.2f} EUR"
    phrase=input(f'Zum ARMEN exakt eingeben: {expected}\n> ')
    if phrase.strip()!=expected: raise RuntimeError('ARM abgebrochen: Bestätigung falsch.')
    m.arm_buy(p)
    print('ARM AKTIV: maximal 10 Minuten. Noch kein Broker POST.')
    print(f"Nächster Schritt nur bewusst: 27_EXECUTE_VALIDATED_REAL_BUY_10EUR.bat")
except Exception as e:
    print('BLOCKIERT:',e)
