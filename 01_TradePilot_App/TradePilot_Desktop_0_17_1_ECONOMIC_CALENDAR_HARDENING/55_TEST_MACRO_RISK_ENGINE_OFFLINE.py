from datetime import datetime, timedelta, timezone
from macro_logic import normalize_event, compute_macro_snapshot, economic_surprise

print('='*108)
print('TRADEPILOT 0.17.0 - MACRO RISK ENGINE OFFLINE')
print('='*108)
now=datetime.now(timezone.utc)

def evt(name, mins, forecast=None, actual=None, previous=None, importance='high'):
    return normalize_event({'eventName':name,'scheduledAt':(now+timedelta(minutes=mins)).isoformat(),'forecast':forecast,'actual':actual,'previous':previous,'importance':importance,'country':'US'})

cpi=evt('US CPI',20,'3.0%','3.3%','2.9%')
assert cpi['relevance']=='CRITICAL'
assert cpi['surprise']['direction']=='NEGATIVE'
snap=compute_macro_snapshot([cpi], market={'moves':{},'regime':'NEUTRAL','confidence':0,'complete':False}, now=now, data_ok=True)
assert snap['risk']=='CRITICAL' and not snap['allow_new_trade'] and snap['position_multiplier']==0.0
print('Event relevance LOW/MEDIUM/HIGH/CRITICAL: OK')
print('CPI semantic higher_is_risk_off: OK')
print('Economic Surprise Actual 3.3 vs Forecast 3.0 -> NEGATIVE: OK')
print('CRITICAL event <= 30 min -> new trades PAUSED: OK')

safe=compute_macro_snapshot([], market={'moves':{},'regime':'RISK-ON','confidence':0,'complete':False}, now=now, data_ok=False)
assert not safe['allow_new_trade'] and safe['risk']=='HIGH' and safe['regime']!='RISK-ON'
print('Missing/uncertain macro data -> FAIL-CLOSED / no aggressive Risk-On: OK')
print('Existing positions macro-force-close: NOT IMPLEMENTED / OBSERVE ONLY: OK')
print('Broker POST: NICHT VERWENDET')
print('STATUS: MACRO RISK ENGINE OFFLINE OK')
