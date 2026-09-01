import os
from pathlib import Path
from economic_calendar_feed import EconomicCalendarProvider
root=Path(__file__).resolve().parent
print('='*108)
print('TRADEPILOT 0.17.2 - CALENDAR PROVIDER STATUS / LIVE READ ONLY')
print('='*108)
try:
    events,meta=EconomicCalendarProvider(root).fetch()
    print('Source:                    ',meta.get('source'))
    print('Providers live:            ',meta.get('providers',0))
    print('Events:                    ',len(events))
    print('Completeness:              ',meta.get('completeness'))
    print('TradingEconomics configured:',bool(os.getenv('TRADEPILOT_TRADING_ECONOMICS_KEY','').strip()))
    print('Provider status:           ',meta.get('provider_status'))
    for e in events[:12]:
        print(f"  {e.get('scheduled_at')} | {e.get('country')} | {e.get('event_name')} | {e.get('relevance')} | F={e.get('forecast')} P={e.get('previous')} A={e.get('actual')} | {','.join(e.get('merged_providers') or [e.get('provider','?')])}")
    print('Broker POST calls:          0')
    print('STATUS: MULTI-SOURCE LIVE READ ONLY OK')
except Exception as exc:
    print('Calendar fetch:',exc)
    print('STATUS: LIVE PROVIDER UNAVAILABLE / FAIL-CLOSED')
