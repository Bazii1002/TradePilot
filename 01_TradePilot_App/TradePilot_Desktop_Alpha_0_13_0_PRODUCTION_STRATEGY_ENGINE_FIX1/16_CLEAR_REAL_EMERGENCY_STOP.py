from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('Der REAL Kill Switch wird nur entfernt; es wird KEINE Order gesendet.')
c=input('Exakt UNLOCK eingeben: ')
if c.strip().upper()=='UNLOCK':
    m.clear_kill_switch(); print('REAL Kill Switch entfernt.')
else:
    print('Abgebrochen.')
