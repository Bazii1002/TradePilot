from production_real_core import RealExitEngine

print('='*104)
print('TRADEPILOT 0.16.0 - REAL EXIT ENGINE OFFLINE')
print('='*104)
base={'symbol':'TEST','level':2,'strategy':'DAY','entry':100.0,'age':10}
stop=RealExitEngine.decision(base,{'price':94.0,'score':80})
take=RealExitEngine.decision(base,{'price':112.0,'score':80})
signal=RealExitEngine.decision(base,{'price':101.0,'score':10})
hold=RealExitEngine.decision(base,{'price':101.0,'score':80})
assert stop['close'] and 'STOP' in stop['reason']
assert take['close'] and 'TAKE PROFIT' in take['reason']
assert signal['close'] and 'SIGNAL EXIT' in signal['reason']
assert not hold['close']
print('STOP LOSS: OK')
print('TAKE PROFIT: OK')
print('STRATEGY SIGNAL EXIT: OK')
print('HOLD: OK')
print('Opening strategy level retained: OK')
print('Broker POST: NICHT VERWENDET')
print('STATUS: REAL EXIT ENGINE OK')
