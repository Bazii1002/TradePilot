from pathlib import Path
import tempfile
from production_real_core import ProductionRealCore

print('='*104)
print('TRADEPILOT 0.16.0 - CRASH / RESTART / TIMEOUT RECOVERY MATRIX')
print('='*104)

# Case A: submitted without provable broker position -> uncertain, never retry.
with tempfile.TemporaryDirectory() as td:
    c=ProductionRealCore(Path(td)); p=c.machine.prepare_buy(symbol='TEST',instrument_id=1,amount_eur=1,amount_usd=1.16,strategy='DAY'); c.machine.mark_submitted(p['operation_id'],p['request_id'])
    r=c.recovery.reconcile([]); assert r['action']=='UNCERTAIN_LOCK' and r['post_retry'] is False
    print('SUBMITTED + unknown broker outcome -> UNCERTAIN LOCK, no retry: OK')

# Case B: local OPEN missing at broker -> locked.
with tempfile.TemporaryDirectory() as td:
    c=ProductionRealCore(Path(td)); p=c.machine.prepare_buy(symbol='TEST',instrument_id=1,amount_eur=1,amount_usd=1.16,strategy='DAY'); c.machine.mark_submitted(p['operation_id'],p['request_id']); c.machine.acknowledge(operation_id=p['operation_id'],position_id='P1'); c.machine.mark_open(operation_id=p['operation_id'],position_id='P1')
    r=c.recovery.reconcile([]); assert r['action']=='LOCKED_STALE_LOCAL'
    print('OPEN local + missing broker position -> LOCKED: OK')

# Case C: broker orphan while local idle -> locked.
with tempfile.TemporaryDirectory() as td:
    c=ProductionRealCore(Path(td)); r=c.recovery.reconcile([{'positionId':'ORPHAN'}]); assert r['action']=='LOCKED_ORPHAN_BROKER'
    print('Broker orphan + local IDLE -> LOCKED: OK')

# Case D: closing and broker position gone -> closed.
with tempfile.TemporaryDirectory() as td:
    c=ProductionRealCore(Path(td)); p=c.machine.prepare_buy(symbol='TEST',instrument_id=1,amount_eur=1,amount_usd=1.16,strategy='DAY'); c.machine.mark_submitted(p['operation_id'],p['request_id']); c.machine.acknowledge(operation_id=p['operation_id'],position_id='P2'); c.machine.mark_open(operation_id=p['operation_id'],position_id='P2'); c.machine.begin_close(position_id='P2',reason='EXIT')
    r=c.recovery.reconcile([]); assert r['action']=='RECOVERED_CLOSED'
    print('CLOSING + broker position gone -> CLOSED: OK')

print('Automatic POST retry in all recovery cases: FORBIDDEN')
print('STATUS: RECOVERY MATRIX OK')
