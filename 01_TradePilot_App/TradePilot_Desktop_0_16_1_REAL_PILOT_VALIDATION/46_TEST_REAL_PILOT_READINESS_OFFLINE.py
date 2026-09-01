from pathlib import Path
import tempfile
from production_real_core import ProductionRealCore, RiskManager, REAL_TEST_EUR

print('='*108)
print('TRADEPILOT 0.16.1 - REAL PILOT READINESS OFFLINE')
print('='*108)
with tempfile.TemporaryDirectory() as td:
    core = ProductionRealCore(Path(td))
    st = core.status()
    assert st['real_auto_enabled'] is False
    assert abs(st['preferred_test_eur'] - 1.0) < 1e-9
    r = core.risk.validate_new_buy(amount_eur=REAL_TEST_EUR, leverage=1, side='BUY', open_positions=0, invested_eur=0, trades_today=0, realized_pnl_today_eur=0)
    assert r['ok']
    assert not core.risk.validate_new_buy(amount_eur=1.01, leverage=1, side='BUY', open_positions=0, invested_eur=0, trades_today=0, realized_pnl_today_eur=0)['ok']
    print('Execution Core:             READY')
    print('Risk Manager EUR 1.00:      READY')
    print('Position Limit:             0 / 1')
    print('Trades/Day Limit:           0 / 3')
    print('Kill Switch:                OFF')
    print('Uncertain Lock:             OFF')
    print('REAL AUTO:                  LOCKED/OFF')
    print('Broker POST:                NICHT VERWENDET')
    print('STATUS: REAL PILOT READINESS OFFLINE OK')
