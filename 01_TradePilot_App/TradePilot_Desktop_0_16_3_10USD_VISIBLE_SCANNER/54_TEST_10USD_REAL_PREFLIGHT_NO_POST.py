from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker
from production_real_core import RiskManager

ROOT=Path(__file__).resolve().parent
print('='*108)
print('TRADEPILOT 0.16.3 - USD 10.00 REAL PREFLIGHT / HARD NO POST')
print('='*108)
print('GET/READ-ONLY ist erlaubt. Dieser Test sendet KEINEN Broker POST.')
broker=EtoroManualLiveBroker(ROOT)
if not broker.has_credentials():
    print('Broker GET: SKIP - keine Credentials')
    print('Broker POST: 0')
    raise SystemExit(0)
open_positions=broker.open_position_count()
risk=RiskManager().validate_new_buy(amount_usd=10.0, leverage=1, side='BUY', open_positions=open_positions, invested_usd=0, trades_today=0, realized_pnl_today_usd=0)
if not risk['ok']:
    raise SystemExit('RISK GATE BLOCK: '+', '.join(risk['reasons']))
inst=broker.search_exact_instrument('AAPL')
iid=broker._instrument_id(inst)
print('Symbol:          AAPL')
print(f'Instrument-ID:   {iid}')
print('Order amount:    10.00 USD')
print('Leverage:        1x')
print('Auto-increase:   NEIN')
print('Payload Preview: {"action":"open","transaction":"buy","instrumentId":%d,"orderType":"mkt","amount":10.0,"orderCurrency":"usd","leverage":1}' % iid)
print('Broker POST:     0')
print('STATUS: USD 10.00 PREFLIGHT OK / NO POST')
