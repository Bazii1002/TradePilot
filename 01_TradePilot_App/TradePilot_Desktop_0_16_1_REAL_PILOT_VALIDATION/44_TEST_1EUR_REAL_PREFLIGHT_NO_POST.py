from pathlib import Path
from real_execution import RealExecutionManager
from production_real_core import RiskManager

ROOT=Path(__file__).resolve().parent
print('='*108)
print('TRADEPILOT 0.16.0 - EUR 1.00 REAL PREFLIGHT / HARD NO POST')
print('='*108)
print('GET/READ-ONLY ist erlaubt. Dieser Test sendet KEINEN Broker POST.')
manager=RealExecutionManager(ROOT)
status=manager.safety_status()
if not status.get('broker_ok'):
    raise SystemExit('BROKER GET FEHLER: '+str(status.get('error')))
risk=RiskManager().validate_new_buy(amount_eur=1.0,leverage=1,side='BUY',open_positions=max(0,int(status.get('open_positions',0))),invested_eur=0,trades_today=0,realized_pnl_today_eur=0,kill_switch=bool(status.get('kill_switch')),uncertain_lock=bool(status.get('uncertain_lock')))
if not risk['ok']:
    raise SystemExit('RISK GATE BLOCK: '+', '.join(risk['reasons']))
# Use AAPL only as a read-only instrument-resolution probe; this script NEVER arms or posts.
p=manager.manual.prepare_market_buy('AAPL',1.00)
print(f"Symbol:          {p['symbol']}")
print(f"Instrument-ID:   {p['instrument_id']}")
print(f"Budget:          {p['budget_eur']:.2f} EUR")
print(f"Order amount:    {p['amount_usd']:.2f} USD")
print('Leverage:        1x')
print('Auto-increase:   NEIN')
print('Broker POST:     0')
print('Hinweis: Ob eToro EUR 1.00 tatsächlich als Mindestorder akzeptiert, wird NICHT durch einen GET garantiert.')
print('STATUS: EUR 1.00 PREFLIGHT OK / NO POST')
