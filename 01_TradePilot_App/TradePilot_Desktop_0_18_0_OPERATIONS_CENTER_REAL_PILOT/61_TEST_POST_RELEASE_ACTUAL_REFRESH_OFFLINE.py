from datetime import datetime, timezone, timedelta
from macro_logic import normalize_event, compute_macro_snapshot

print('='*108)
print('TRADEPILOT 0.17.1 - POST RELEASE ACTUAL / SURPRISE OFFLINE')
print('='*108)
now=datetime.now(timezone.utc)
e=normalize_event({'scheduledAt':(now-timedelta(minutes=2)).isoformat(),'eventName':'US CPI','country':'US','importance':'high','forecast':'3.0%','previous':'2.9%','actual':'3.3%'})
market={'moves':{'NASDAQ':-1.1,'S&P 500':-0.8,'VIX':8.0,'US10Y':10.0,'OIL':0.5},'regime':'RISK-OFF','confidence':100,'complete':True}
s=compute_macro_snapshot([e],market=market,now=now,data_ok=True)
assert e['surprise']['direction']=='NEGATIVE'
assert s['risk']=='CRITICAL'
assert s['allow_new_trade'] is False
assert s['position_multiplier']==0.0
print('Actual re-evaluated vs Forecast:  OK')
print('Negative CPI surprise:            OK')
print('Market confirmation RISK-OFF:     OK')
print('New trades blocked:               OK')
print('Existing positions forced close:  NEIN')
print('STATUS: POST RELEASE SURPRISE OFFLINE OK')
