from pathlib import Path
from real_execution import RealExecutionManager
from real_signal_handoff import load_handoff, clear_handoff
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('='*112); print('TRADEPILOT 0.14.1 FIX1 - EXECUTE VALIDATED REAL BUY 10 EUR'); print('='*112)
print('DIESER SCHRITT KANN GENAU EINE ECHTE ECHTGELDORDER SENDEN. KEIN AUTO-RETRY.')
try:
    h=load_handoff(APP,require_fresh=True)
    p=m.preflight_buy(h['symbol'],h['budget_eur'],h.get('strategy','DAY'))
    if int(p['instrument_id'])!=int(h['instrument_id']): raise RuntimeError('BLOCK: Instrument-ID weicht vom validierten Handoff ab.')
    arm=m.arm_status()
    if not arm.get('armed') or arm.get('kind')!='BUY': raise RuntimeError('BLOCK: Kein gültiges BUY-ARM.')
    for k,v in [('symbol',p['symbol']),('instrument_id',int(p['instrument_id']))]:
        if str(arm.get(k))!=str(v): raise RuntimeError(f'BLOCK: ARM-{k} passt nicht zum validierten Signal.')
    if abs(float(arm.get('budget_eur',-1))-float(p['budget_eur']))>1e-9: raise RuntimeError('BLOCK: ARM-Budget passt nicht.')
    status=m.safety_status()
    print(f"Signal: {p['symbol']} | Instrument {p['instrument_id']} | {p['budget_eur']:.2f} EUR | ~{p['amount_usd']:.2f} USD | BUY | 1x")
    print(f"REAL Execution enabled: {status.get('execution_enabled')}")
    print(f"Open REAL positions:    {status.get('open_positions')}")
    print(f"Kill Switch:            {status.get('kill_switch')}")
    print(f"Uncertain Lock:         {status.get('uncertain_lock')}")
    expected=f"EXECUTE REAL BUY {p['symbol']} {float(p['budget_eur']):.2f} EUR"
    phrase=input(f'LETZTE BESTÄTIGUNG – exakt eingeben: {expected}\n> ')
    r=m.execute_buy(p,phrase,auto=False)
    clear_handoff(APP)
    print('REAL BUY VERIFIZIERT')
    print('Position-ID:',r['position_id'])
    print('Request-ID:',r['request_id'])
    print('Order-ID:',r['order_id'] or '(nicht geliefert)')
    print('NÄCHSTER SCHRITT: Reconcile, danach CLOSE separat armen. Kein automatischer CLOSE.')
except Exception as e:
    print('BLOCKIERT/FEHLER:',e)
