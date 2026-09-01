from datetime import datetime, timezone, timedelta
from macro_logic import normalize_event, compute_macro_snapshot
now=datetime(2026,9,11,12,35,tzinfo=timezone.utc)
e=normalize_event({'country':'US','eventName':'CPI','scheduledAt':'2026-09-11T12:30:00Z','forecast':'3.0%','previous':'2.9%','actual':None})
s=compute_macro_snapshot([e], market={'moves':{},'regime':'NEUTRAL','confidence':0,'complete':False}, now=now, data_ok=True)
assert s['allow_new_trade'] is False and s['position_multiplier']==0.0
assert 'ausstehend' in s['reason'].lower()
print('='*108)
print('TRADEPILOT 0.17.2 - RELEASE PENDING FAIL-CLOSED OFFLINE')
print('='*108)
print('CRITICAL event released but Actual missing: DETECTED')
print('New trades: BLOCKED')
print('Position multiplier: 0%')
print('Existing positions force-close: NEIN')
print('STATUS: RELEASE PENDING FAIL-CLOSED OFFLINE OK')
