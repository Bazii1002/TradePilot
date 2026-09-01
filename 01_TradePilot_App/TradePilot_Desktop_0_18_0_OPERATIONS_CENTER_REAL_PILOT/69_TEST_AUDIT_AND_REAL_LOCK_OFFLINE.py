from pathlib import Path
from tempfile import TemporaryDirectory
import json
from operations_center import OperationsCenter

print('='*108)
print('TRADEPILOT 0.18.0 - AUDIT + REAL LOCK OFFLINE')
print('='*108)
with TemporaryDirectory() as td:
    root=Path(td); data=root/'data'; data.mkdir()
    (data/'production_real_state.json').write_text(json.dumps({'state':'SUBMITTED'}),encoding='utf-8')
    (data/'production_real_audit.jsonl').write_text(json.dumps({'ts':'2026-09-01T16:00:00+02:00','event':'STATE','from_state':'PREPARED','to_state':'SUBMITTED','api_key':'SECRET'})+'\n',encoding='utf-8')
    ops=OperationsCenter(root); rec=ops.restart_recovery(); audit=ops.real_audit()
    assert rec['real_fail_closed'] and rec['post_retry'] is False and rec['real_auto']=='LOCKED'
    assert len(audit)==1 and 'api_key' not in audit[0]
print('REAL state transition audit readable: OK')
print('Credentials/secrets stripped from Operations audit: OK')
print('SUBMITTED restart -> fail-closed / no POST retry: OK')
print('REAL AUTO: LOCKED')
print('STATUS: AUDIT + REAL LOCK OFFLINE OK')
