from datetime import datetime, timezone, timedelta
from economic_calendar_feed import normalize_dedupe_sort, FETCH_AHEAD_DAYS

print('='*108)
print('TRADEPILOT 0.17.1 - ECONOMIC CALENDAR HARDENING OFFLINE')
print('='*108)
now=datetime.now(timezone.utc)
raw=[
 {'scheduledAt':(now+timedelta(hours=2)).isoformat(),'eventName':'US CPI','country':'US','importance':'high','forecast':'3.0%','previous':'2.9%'},
 {'scheduledAt':(now+timedelta(hours=2)).isoformat(),'eventName':'US CPI','country':'US','importance':'high','forecast':'3.0%','previous':'2.9%','actual':'3.3%'},
 {'date':(now+timedelta(hours=1)).isoformat(),'name':'Retail Sales','currency':'USD','impact':'medium','Forecast':'0.4%','Previous':'0.2%'},
 {'datetime':(now+timedelta(days=1)).isoformat(),'title':'FOMC Rate Decision','countryCode':'US','importanceLevel':'critical'},
]
rows=normalize_dedupe_sort(raw)
assert len(rows)==3, rows
assert rows[0]['event_name']=='Retail Sales'
cpi=[x for x in rows if x['event_name']=='US CPI'][0]
assert cpi['actual']=='3.3%'
assert cpi['relevance']=='CRITICAL'
assert cpi['surprise']['direction']=='NEGATIVE'
assert FETCH_AHEAD_DAYS==14
print('Multiple source field variants:   OK')
print('Deduplication richer duplicate:   OK')
print('Chronological sorting:            OK')
print('Forecast/Previous/Actual mapping: OK')
print('14-day event horizon:             OK')
print('STATUS: CALENDAR HARDENING OFFLINE OK')
