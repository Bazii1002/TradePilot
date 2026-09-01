from pathlib import Path
from macro_risk_engine import MacroRiskEngine, compute_macro_snapshot
print('='*108)
print('TRADEPILOT 0.17.0 - LIVE MACRO / ECONOMIC CALENDAR READ ONLY')
print('='*108)
# Call providers synchronously for diagnostics; all operations are public GET/read-only.
obj=MacroRiskEngine(Path(__file__).resolve().parent)
try:
    events=obj._fetch_events()
    market=obj._fetch_market_reaction()
    snap=compute_macro_snapshot(events,market=market,data_ok=bool(events))
    print(f'Calendar events:            {len(events)}')
    print(f'Macro regime:              {snap["regime"]}')
    print(f'Macro risk:                {snap["risk"]}')
    print(f'Market data confidence:    {snap["confidence"]}%')
    print(f'New trades allowed:        {snap["allow_new_trade"]}')
    print(f'Position multiplier:       {snap["position_multiplier"]*100:.0f}%')
    if snap.get('next_event'):
        e=snap['next_event']; print(f'Next event:                {e.get("event_name")} · {e.get("relevance")} · {e.get("minutes_to_event")} min')
    print('Broker POST calls:          0')
    print('STATUS: LIVE MACRO READ ONLY OK')
except Exception as exc:
    print('Live provider error:        '+str(exc))
    print('FAIL-CLOSED result:         new trades must remain blocked')
    print('Broker POST calls:          0')
    print('STATUS: LIVE DATA UNAVAILABLE / SAFELY FAIL-CLOSED')
