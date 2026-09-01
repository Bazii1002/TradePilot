from pathlib import Path
from roundtrip_validator import RoundtripValidator

APP = Path(__file__).resolve().parent
print('='*104)
print('TRADEPILOT DESKTOP ALPHA 0.12.1 - REAL ROUNDTRIP VALIDATION (NO POST)')
print('='*104)
print('GET/READ-ONLY Preflight + simulierter Broker-Roundtrip. KEIN REAL BUY, KEIN REAL CLOSE.\n')

try:
    r = RoundtripValidator(APP).run('AAPL', 10.0, 'DAY')
    print('BUY PREVIEW')
    print(f"Ticker:                 {r['symbol']}")
    print(f"Instrument-ID:          {r['instrument_id']}")
    print(f"Budget:                 {r['budget_eur']:.2f} EUR")
    print(f"Orderbetrag:            {r['amount_usd']:.2f} USD")
    print(f"Strategie:              {r['strategy']}")
    print(f"BUY-Reconcile:          {'OK' if r['buy_reconcile_ok'] else 'FEHLER'}")
    print(f"Sim Position-ID:        {r['simulated_position_id']}")
    print('\nCLOSE VALIDATION')
    print(f"Close-Reconcile:        {'OK' if r['close_reconcile_ok'] else 'FEHLER'}")
    print(f"Broker Positionen Ende: {r['final_broker_positions']}")
    print(f"Lokale Positionen Ende: {r['final_local_positions']}")
    print('REAL POST ausgeführt:    NEIN')
    print('\nSTATUS: ROUNDTRIP VALIDATION OK' if r['ok'] else '\nSTATUS: BLOCKIERT')
    print('KEINE FINANZTRANSAKTION WURDE AUSGEFÜHRT')
except Exception as exc:
    print(f'\nSTATUS: BLOCKIERT\n{exc}')
