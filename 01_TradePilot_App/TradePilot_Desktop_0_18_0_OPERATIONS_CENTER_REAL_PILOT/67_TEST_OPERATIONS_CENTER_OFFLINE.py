from pathlib import Path
from tempfile import TemporaryDirectory
import json
from operations_center import OperationsCenter, REAL_AUTO_LOCKED

print('='*108)
print('TRADEPILOT 0.18.0 - OPERATIONS CENTER OFFLINE')
print('='*108)
with TemporaryDirectory() as td:
    root=Path(td); data=root/'data'; data.mkdir()
    (data/'shadow_state.json').write_text(json.dumps({
        'was_running': True,'level':2,'last_scan':'16:42:18','last_scan_summary':'998/1000 · 50 · 12 · 1 ACTIONABLE',
        'positions':[],'trades':[{'symbol':'AAPL'}], 'last_actionable':{'symbol':'GIS','score':87.6,'quality_score':75.3},
        'last_decision_reason':'WAIT · Macro LOW'
    }),encoding='utf-8')
    (data/'production_real_state.json').write_text(json.dumps({'state':'IDLE'}),encoding='utf-8')
    ops=OperationsCenter(root); s=ops.summary()
    assert s['bot_status']=='RUNNING' and s['restart']['shadow_action']=='RESUME_SHADOW'
    assert s['real_auto_locked'] is True and REAL_AUTO_LOCKED is True
    assert s['last_actionable']['symbol']=='GIS'
print('Bot operations state + last scan/actionable: OK')
print('Persistent SHADOW restart intent: OK')
print('REAL AUTO: LOCKED')
print('STATUS: OPERATIONS CENTER OFFLINE OK')
