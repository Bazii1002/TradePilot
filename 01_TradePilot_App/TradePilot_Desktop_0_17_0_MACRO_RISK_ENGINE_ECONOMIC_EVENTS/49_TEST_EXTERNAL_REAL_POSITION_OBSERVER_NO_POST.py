from pathlib import Path
from external_real_position_validator import ExternalRealPositionValidator
APP=Path(__file__).resolve().parent
print('='*108); print('TRADEPILOT 0.16.2 - EXTERNAL REAL POSITION OBSERVER / READ ONLY / HARD NO POST'); print('='*108)
try:
    r=ExternalRealPositionValidator(APP).observe()
    print('Broker GET:                 OK')
    print(f"Open REAL positions:        {r['broker_positions']}")
    print(f"Production execution state: {r['production_state']} (unchanged)")
    print('Mode:                       EXTERNAL OBSERVE ONLY')
    for i,p in enumerate(r['positions'],1):
        print(f"Position {i}:                 {p['symbol']} | position_id={p['position_id'] or 'n/a'} | instrument_id={p['instrument_id'] or 'n/a'}")
    if not r['positions']:
        print('Hinweis:                     Keine externe REAL-Position vorhanden. Test ist trotzdem sicher/grün.')
    print('Automatic CLOSE:            NEIN')
    print('Broker POST calls:          0')
    print('STATUS: EXTERNAL REAL POSITION OBSERVER OK')
except Exception as e:
    print('STATUS: BLOCKIERT'); print(str(e)); raise
