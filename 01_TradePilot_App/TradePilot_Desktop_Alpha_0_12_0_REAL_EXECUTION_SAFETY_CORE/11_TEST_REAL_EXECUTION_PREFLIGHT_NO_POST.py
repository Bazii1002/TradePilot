from pathlib import Path
from real_execution import RealExecutionManager

APP=Path(__file__).resolve().parent
print('='*100)
print('TRADEPILOT DESKTOP ALPHA 0.12.0 - REAL EXECUTION PREFLIGHT (NO POST)')
print('='*100)
print('Es wird nur GET/READ-ONLY ausgeführt. KEINE Order wird gesendet.\n')
m=RealExecutionManager(APP)
try:
    s=m.safety_status()
    print(f"Broker GET:             {'OK' if s['broker_ok'] else 'FEHLER'}")
    print(f"REAL Execution Flag:    {'ENABLED' if s['execution_enabled'] else 'LOCKED'}")
    print(f"REAL AutoTrading Flag:  {'ENABLED' if s['auto_enabled'] else 'LOCKED'}")
    print(f"Kill Switch:            {'AKTIV' if s['kill_switch'] else 'AUS'}")
    print(f"Uncertain Lock:         {'AKTIV' if s['uncertain_lock'] else 'AUS'}")
    print(f"Open REAL Positions:    {s['open_positions']}")
    print(f"Max Trade:              {s['max_trade_eur']:.2f} EUR")
    print(f"Max REAL Positions:     {s['max_open_positions']}")
    print(f"Daily Loss Gate:        {s['max_daily_loss_eur']:.2f} EUR")
    p=m.preflight_buy('AAPL', min(10.0,s['max_trade_eur']), 'MANUAL_TEST')
    print('\nORDER REVIEW (NO POST)')
    print(f"Ticker:                 {p['symbol']}")
    print(f"Instrument-ID:          {p['instrument_id']}")
    print(f"Budget:                 {p['budget_eur']:.2f} EUR")
    print(f"Orderbetrag:            {p['amount_usd']:.2f} USD")
    print(f"Leverage:               {p['leverage']}x")
    print('\nSTATUS: PREFLIGHT OK')
    print('KEINE ORDER WURDE GESENDET')
except Exception as exc:
    print(f'\nSTATUS: BLOCKIERT\n{exc}')
