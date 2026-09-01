from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent; m=RealExecutionManager(APP)
print('='*104); print('TRADEPILOT 0.14.0 - ARM + MANUAL REAL CLOSE'); print('='*104)
try:
 rows=m.position_rows();
 if not rows: raise RuntimeError('Keine offene REAL-Position gefunden.')
 print('Offene Position-IDs:')
 for r in rows: print(' ',r.get('positionId') or r.get('id'), 'instrument', r.get('instrumentId'))
 pid=input('Position-ID zum Schließen eingeben: ').strip(); m.arm_close(pid)
 phrase=input(f'Zum AUSFÜHREN exakt eingeben: EXECUTE REAL CLOSE {pid}\n> ')
 r=m.close_position(pid,phrase); print('REAL CLOSE VERIFIZIERT'); print('Position-ID:',r['position_id']); print('Request-ID:',r['request_id'])
except Exception as e: print('BLOCKIERT/FEHLER:',e)
