from pathlib import Path
from etoro_readonly import EtoroReadOnlyClient
from production_real_core import ProductionRealCore

print('='*108)
print('TRADEPILOT 0.16.1 - BROKER REAL PILOT READINESS / READ ONLY / HARD NO POST')
print('='*108)
app=Path(__file__).resolve().parent
client=EtoroReadOnlyClient(app)
core=ProductionRealCore(app)
if not client.has_credentials():
    print('Broker GET:                 SKIP - keine Credentials gefunden')
    print('REAL AUTO:                  LOCKED/OFF')
    print('Broker POST calls:          0')
    print('STATUS: OFFLINE READINESS OK / NO POST')
    raise SystemExit(0)
s=client.snapshot()
positions=list(s.get('positions') or [])
st=core.status()
state=(st.get('state') or {}).get('state','IDLE')
kill=bool(st.get('kill_switch'))
uncertain=bool(st.get('legacy_uncertain_lock') or state in {'UNCERTAIN','LOCKED'})
ready=(not kill and not uncertain and len(positions)<1)
print('Broker GET:                 OK')
print(f'Open REAL positions:        {len(positions)} / 1')
print(f'Execution state:            {state}')
print(f'Kill Switch:                {kill}')
print(f'Uncertain/Locked:           {uncertain}')
print('Pilot amount:               EUR 1.00')
print('REAL AUTO:                  LOCKED/OFF')
print('Broker POST calls:          0')
print('Readiness:                  ' + ('READY · MANUAL PILOT' if ready else 'BLOCKED'))
print('STATUS: BROKER REAL PILOT READINESS NO POST OK')
