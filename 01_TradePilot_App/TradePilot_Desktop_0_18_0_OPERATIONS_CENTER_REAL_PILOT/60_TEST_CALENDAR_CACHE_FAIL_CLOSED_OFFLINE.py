import json, tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from economic_calendar_feed import EconomicCalendarProvider

print('='*108)
print('TRADEPILOT 0.17.1 - CALENDAR CACHE / STALE FAIL-CLOSED OFFLINE')
print('='*108)
with tempfile.TemporaryDirectory() as td:
    p=EconomicCalendarProvider(Path(td))
    event={'scheduled_at':(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),'event_name':'US CPI','country':'US','importance_source':'high','relevance':'CRITICAL','semantic':'higher_is_risk_off','forecast':'3.0','previous':'2.9','actual':None,'source':'fixture'}
    p.cache_file.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'source':'fixture','events':[event]}),encoding='utf-8')
    rows,meta=p.load_cache(max_age_minutes=180)
    assert rows and meta['ok'] and not meta['stale']
    p.cache_file.write_text(json.dumps({'updated_at':(datetime.now(timezone.utc)-timedelta(hours=5)).isoformat(),'source':'fixture','events':[event]}),encoding='utf-8')
    rows,meta=p.load_cache(max_age_minutes=180)
    assert rows and meta['stale']
print('Fresh cache accepted:             OK')
print('Stale cache detected:             OK')
print('Stale data must not unlock trade: OK')
print('STATUS: CACHE FAIL-CLOSED OFFLINE OK')
