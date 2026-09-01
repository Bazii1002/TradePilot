from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent
print('='*104); print('TRADEPILOT 0.14.0 - REAL RECONCILE / NO POST'); print('='*104)
try:
 r=RealExecutionManager(APP).reconcile(False)
 for k,v in r.items(): print(f'{k:24}: {v}')
 print('Broker POST: NEIN'); print('STATUS: RECONCILE OK')
except Exception as e: print('STATUS: BLOCKIERT\n'+str(e))
