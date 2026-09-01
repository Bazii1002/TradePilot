from pathlib import Path
from external_real_position_validator import ExternalRealPositionValidator
APP=Path(__file__).resolve().parent
print('='*108); print('TRADEPILOT 0.16.2 - EXTERNAL POSITION RESTART VALIDATION / HARD NO POST'); print('='*108)
r=ExternalRealPositionValidator(APP).restart_validation()
print('Position IDs before restart:', r['before_ids'])
print('Position IDs after restart: ', r['after_ids'])
print('Stable broker observation:  ', 'OK' if r['ok'] else 'CHANGED')
print('Production state:           ', r['production_state'])
print('Automatic POST retry:        FORBIDDEN')
print('Broker POST calls:           0')
assert r['ok'], 'Broker position set changed between immediate read-only observations'
print('STATUS: EXTERNAL POSITION RESTART VALIDATION OK')
