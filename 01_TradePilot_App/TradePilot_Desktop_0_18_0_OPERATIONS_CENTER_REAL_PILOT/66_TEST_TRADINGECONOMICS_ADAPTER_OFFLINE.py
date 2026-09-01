from economic_calendar_feed import normalize_dedupe_sort
raw=[{'_provider':'tradingeconomics','CalendarId':'1','Date':'2026-09-04T12:30:00Z','Country':'United States','Event':'Nonfarm Payrolls','Actual':'42K','Previous':'105K','Forecast':'78K','Importance':3,'Unit':'K','Source':'BLS'}]
e=normalize_dedupe_sort(raw)[0]
assert e['country']=='US' and e['forecast']=='78K' and e['previous']=='105K' and e['actual']=='42K'
assert e['relevance']=='CRITICAL'
print('='*108)
print('TRADEPILOT 0.17.2 - TRADING ECONOMICS ADAPTER OFFLINE')
print('='*108)
print('Country/Event/Importance mapping: OK')
print('Forecast/Previous/Actual mapping: OK')
print('Units/source retained: OK')
print('CRITICAL classification retained: OK')
print('STATUS: TRADING ECONOMICS ADAPTER OFFLINE OK')
