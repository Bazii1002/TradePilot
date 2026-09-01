from pathlib import Path
from external_real_position_validator import ExternalRealPositionValidator
APP=Path(__file__).resolve().parent
print('='*108); print('TRADEPILOT 0.16.2 - EXTERNAL POSITION EXIT PREVIEW / OFFLINE / NO POST'); print('='*108)
v=ExternalRealPositionValidator(APP)
# No real broker order and no invented live market data. Deterministic fixture only tests the bridge.
position={'symbol':'FIXTURE','open_rate':100.0}
market={'close':90.0,'score':20.0,'signal':'WAIT'}
r=v.exit_preview(position, market)
print('Exit Engine bridge:          OK')
print('Observe only:                ', r['observe_only'])
print('Decision available:          ', r['available'])
print('Automatic CLOSE:             NEIN')
print('Broker POST calls:           0')
assert r['observe_only'] and r['broker_post_calls']==0
print('STATUS: EXTERNAL POSITION EXIT PREVIEW OFFLINE OK')
