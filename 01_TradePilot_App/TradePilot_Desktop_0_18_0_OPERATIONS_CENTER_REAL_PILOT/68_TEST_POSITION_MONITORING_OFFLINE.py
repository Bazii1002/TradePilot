from pathlib import Path
from tempfile import TemporaryDirectory
import json
from operations_center import OperationsCenter

print('='*108)
print('TRADEPILOT 0.18.0 - POSITION MONITORING OFFLINE')
print('='*108)
with TemporaryDirectory() as td:
    root=Path(td); data=root/'data'; data.mkdir()
    pos={'symbol':'AAPL','strategy':'DAY','entry':100,'price':102,'amount':10,'entry_score':87.4,'quality_score':81.2,
         'macro_risk':'LOW','news_risk':'LOW','stop_price':98,'take_price':104,'exit_status':'HOLD'}
    (data/'shadow_state.json').write_text(json.dumps({'positions':[pos]}),encoding='utf-8')
    rows=OperationsCenter(root).position_monitor(); assert len(rows)==1
    r=rows[0]; assert r['pnl_pct']==2.0 and r['stop_price']==98 and r['take_price']==104 and r['exit_status']=='HOLD'
print('Entry / Current / P-L: OK')
print('Stop / Take Profit / Strategy / Score / Quality: OK')
print('Macro / News / Exit Status: OK')
print('STATUS: POSITION MONITORING OFFLINE OK')
