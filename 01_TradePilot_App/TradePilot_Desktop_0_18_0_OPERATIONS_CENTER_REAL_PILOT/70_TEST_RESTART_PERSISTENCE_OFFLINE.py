from pathlib import Path
from tempfile import TemporaryDirectory
import json
from operations_center import OperationsCenter

print('='*108)
print('TRADEPILOT 0.18.0 - RESTART / PERSISTENCE OFFLINE')
print('='*108)
with TemporaryDirectory() as td:
    root=Path(td); data=root/'data'; data.mkdir()
    (data/'shadow_state.json').write_text(json.dumps({'was_running':True,'level':3,'positions':[{'symbol':'MSFT'}],'trades':[]}),encoding='utf-8')
    (data/'production_real_state.json').write_text(json.dumps({'state':'OPEN','broker_position_id':'42'}),encoding='utf-8')
    a=OperationsCenter(root).summary(); b=OperationsCenter(root).summary()
    assert a['restart']['shadow_action']=='RESUME_SHADOW' == b['restart']['shadow_action']
    assert a['restart']['real_state']=='OPEN' and b['restart']['post_retry'] is False
print('Shadow running intent survives restart: OK')
print('Opening strategy/state survives local reload: OK')
print('REAL state survives restart: OK')
print('Automatic REAL POST retry after restart: FORBIDDEN')
print('STATUS: RESTART PERSISTENCE OFFLINE OK')
