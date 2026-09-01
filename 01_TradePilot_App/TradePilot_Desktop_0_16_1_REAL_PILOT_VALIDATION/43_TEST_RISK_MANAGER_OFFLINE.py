from production_real_core import RiskManager

print('='*104)
print('TRADEPILOT 0.16.0 - REAL RISK MANAGER OFFLINE')
print('='*104)
r=RiskManager()
def check(name, **kw):
    base=dict(amount_eur=1.0,leverage=1,side='BUY',open_positions=0,invested_eur=0,trades_today=0,realized_pnl_today_eur=0,kill_switch=False,uncertain_lock=False)
    base.update(kw); out=r.validate_new_buy(**base); print(f'{name:<34}: {"PASS" if out["ok"] else "BLOCK"}'); return out
assert check('Nominal EUR 1.00')['ok']
assert not check('Amount > EUR 1.00',amount_eur=1.01)['ok']
assert not check('Leverage != 1x',leverage=2)['ok']
assert not check('SELL/short',side='SELL')['ok']
assert not check('Already 1 REAL position',open_positions=1)['ok']
assert not check('Max trades/day reached',trades_today=3)['ok']
assert not check('Daily loss reached',realized_pnl_today_eur=-20)['ok']
assert not check('Kill switch',kill_switch=True)['ok']
assert not check('Uncertain lock',uncertain_lock=True)['ok']
pol=r.broker_minimum_policy(1.0,10.0); assert pol['ok'] is False and pol['auto_increase'] is False
print('Broker minimum EUR 10 vs requested EUR 1 -> BLOCK, never auto-increase: OK')
print('REAL AUTO: OFF')
print('STATUS: REAL RISK MANAGER OK')
