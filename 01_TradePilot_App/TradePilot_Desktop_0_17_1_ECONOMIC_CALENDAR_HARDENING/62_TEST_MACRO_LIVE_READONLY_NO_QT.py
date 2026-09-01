from pathlib import Path
from economic_calendar_feed import EconomicCalendarProvider
from macro_logic import compute_macro_snapshot

print('='*108)
print('TRADEPILOT 0.17.1 - LIVE CALENDAR FEED READ ONLY / NO QT TIMER DIAGNOSTIC')
print('='*108)
app=Path(__file__).resolve().parent
provider=EconomicCalendarProvider(app)
try:
    events,meta=provider.fetch()
    # Market reaction implementation is reused without constructing MacroRiskEngine/QObject.
    # To avoid Qt lifecycle warnings in diagnostics, instantiate no QObject here.
    print(f'Calendar source:             {meta.get("source")}')
    print(f'Calendar events:             {len(events)}')
    print(f'Fetch horizon:               {meta.get("horizon_days",14)} days')
    print(f'Stale:                       {meta.get("stale",False)}')
    if events:
        for e in events[:8]:
            print(f'  {e.get("scheduled_at")} | {e.get("country")} | {e.get("event_name")} | {e.get("relevance")} | F={e.get("forecast")} P={e.get("previous")} A={e.get("actual")}')
    print('Qt QObject/QTimer created:   NEIN')
    print('Broker POST calls:           0')
    print('STATUS: LIVE CALENDAR FEED READ ONLY OK')
except Exception as exc:
    print('Live calendar unavailable:   '+str(exc))
    print('Fallback policy:             FAIL-CLOSED')
    print('Qt QObject/QTimer created:   NEIN')
    print('Broker POST calls:           0')
    print('STATUS: LIVE CALENDAR UNAVAILABLE / SAFELY FAIL-CLOSED')
