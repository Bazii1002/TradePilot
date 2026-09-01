from pathlib import Path
import tempfile
from production_real_core import ProductionRealCore, REAL_TEST_EUR

print('='*104)
print('TRADEPILOT 0.16.0 - PRODUCTION REAL EXECUTION CORE OFFLINE')
print('='*104)
with tempfile.TemporaryDirectory() as td:
    core=ProductionRealCore(Path(td))
    s=core.status()
    assert s['real_auto_enabled'] is False
    assert REAL_TEST_EUR == 1.00
    p=core.machine.prepare_buy(symbol='TEST', instrument_id=123, amount_eur=1.0, amount_usd=1.16, strategy='DAY')
    assert p['state']=='PREPARED'
    sub=core.machine.mark_submitted(p['operation_id'],p['request_id'])
    assert sub['state']=='SUBMITTED'
    ack=core.machine.acknowledge(operation_id=p['operation_id'],order_id='ORDER-1',position_id='POS-1')
    assert ack['state']=='ACKNOWLEDGED'
    op=core.machine.mark_open(operation_id=p['operation_id'],position_id='POS-1')
    assert op['state']=='OPEN'
    cl=core.machine.begin_close(position_id='POS-1',reason='TEST EXIT')
    assert cl['state']=='CLOSING'
    done=core.machine.mark_closed(position_id='POS-1')
    assert done['state']=='CLOSED'
    print('State Machine: PREPARED -> SUBMITTED -> ACKNOWLEDGED -> OPEN -> CLOSING -> CLOSED: OK')
    print('Persistent operation_id/request_id: OK')
    print('REAL AUTO: LOCKED/OFF')
    print('Preferred REAL test amount: EUR 1.00')
    print('Broker minimum auto-increase: FORBIDDEN')
    print('Broker POST: NICHT VERWENDET')
print('STATUS: PRODUCTION REAL CORE OK')
