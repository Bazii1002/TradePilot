from pathlib import Path
from economic_calendar_feed import normalize_dedupe_sort
rows=[
 {'_provider':'xoomar','country':'US','eventName':'CPI (Consumer Price Index)','scheduledAt':'2026-09-11T12:30:00Z','importance':'high'},
 {'_provider':'tradingeconomics','Country':'United States','Event':'CPI','Date':'2026-09-11T12:30:00Z','Importance':3,'Forecast':'3.0%','Previous':'2.9%','Unit':'%'},
]
e=normalize_dedupe_sort(rows)
assert len(e)==1,e
x=e[0]
assert x['country']=='US' and x['forecast']=='3.0%' and x['previous']=='2.9%'
assert len(x.get('merged_providers',[]))>=2
print('='*108)
print('TRADEPILOT 0.17.2 - MULTI-SOURCE CALENDAR MERGE OFFLINE')
print('='*108)
print('Provider A timing + Provider B enrichment: OK')
print('Country normalization United States -> US: OK')
print('Forecast/Previous field-level merge: OK')
print('Duplicate event remains one event: OK')
print('STATUS: MULTI-SOURCE MERGE OFFLINE OK')
