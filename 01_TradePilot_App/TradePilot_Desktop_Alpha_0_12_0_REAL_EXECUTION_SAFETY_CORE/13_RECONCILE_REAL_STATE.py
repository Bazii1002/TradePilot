from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('='*100)
print('TRADEPILOT 0.12.0 - REAL BROKER STATE RECONCILE (GET ONLY)')
print('='*100)
try:
    r=m.reconcile(clear_uncertain_if_safe=False)
    print(f"Broker Positionen:      {r['broker_positions']}")
    print(f"Lokale Position-IDs:    {len(r['local_position_ids'])}")
    print(f"Broker-only Positionen: {len(r['orphan_broker'])}")
    print(f"Stale lokale Einträge:  {len(r['stale_local'])}")
    print(f"Uncertain Lock:         {'JA' if r['uncertain_lock'] else 'NEIN'}")
    print(f"Sicher auflösbar:       {'JA' if r['uncertain_safe_to_clear'] else 'NEIN'}")
    if r['uncertain_lock'] and r['uncertain_safe_to_clear']:
        print('\nDer unklare Status kann nach manueller Kontrolle sicher freigegeben werden.')
        c=input('Zum Entfernen des Uncertain-Locks exakt CLEAR eingeben, sonst Enter: ')
        if c.strip().upper()=='CLEAR':
            m.reconcile(clear_uncertain_if_safe=True)
            print('Uncertain-Lock entfernt.')
    print('\nKeine Order wurde gesendet.')
except Exception as exc:
    print(f'FEHLER: {exc}')
