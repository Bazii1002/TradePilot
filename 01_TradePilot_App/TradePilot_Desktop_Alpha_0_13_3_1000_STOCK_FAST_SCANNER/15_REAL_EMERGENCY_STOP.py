from pathlib import Path
from real_execution import RealExecutionManager
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
m.activate_kill_switch('manual emergency stop')
print('REAL KILL SWITCH IST JETZT AKTIV.')
print('Neue REAL BUY/CLOSE-Ausführungen werden blockiert.')
print('Hinweis: Der Kill Switch schließt bestehende Broker-Positionen NICHT automatisch.')
