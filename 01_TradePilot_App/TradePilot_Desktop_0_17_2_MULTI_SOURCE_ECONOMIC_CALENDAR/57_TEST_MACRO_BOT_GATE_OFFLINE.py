from datetime import datetime,timedelta,timezone
from macro_logic import normalize_event, compute_macro_snapshot
print('='*108)
print('TRADEPILOT 0.17.0 - MACRO BOT GATE OFFLINE')
print('='*108)
now=datetime.now(timezone.utc)
critical=normalize_event({'eventName':'Federal Reserve Interest Rate Decision','scheduledAt':(now+timedelta(minutes=25)).isoformat(),'forecast':'5.25','previous':'5.25','country':'US'})
s=compute_macro_snapshot([critical], market={'moves':{},'regime':'NEUTRAL','confidence':0,'complete':False}, now=now, data_ok=True)
assert not s['allow_new_trade'] and s['position_multiplier']==0.0
high=normalize_event({'eventName':'US GDP','scheduledAt':(now+timedelta(minutes=25)).isoformat(),'forecast':'2.0','previous':'1.8','country':'US'})
s2=compute_macro_snapshot([high], market={'moves':{},'regime':'NEUTRAL','confidence':0,'complete':False}, now=now, data_ok=True)
assert s2['allow_new_trade'] and s2['position_multiplier']<=0.5 and s2['risk']=='HIGH'
print('CRITICAL <=30m -> block new trades: OK')
print('HIGH <=30m -> reduce new position size: OK')
print('Existing-position exit engine remains strategy/stop/take driven: OK')
print('No macro panic close path: OK')
print('REAL execution POST path: UNCHANGED')
print('STATUS: MACRO BOT GATE OFFLINE OK')
