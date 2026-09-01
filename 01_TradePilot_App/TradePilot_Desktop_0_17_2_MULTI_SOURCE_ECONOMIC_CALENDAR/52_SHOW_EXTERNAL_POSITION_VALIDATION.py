from pathlib import Path
import json
p=Path(__file__).resolve().parent/'data'/'external_real_position_validation.json'
print('='*90); print('TRADEPILOT 0.16.2 - LAST EXTERNAL REAL POSITION VALIDATION'); print('='*90)
if not p.exists():
    print('Noch keine Beobachtung gespeichert. Starte zuerst Test 49.')
else:
    r=json.loads(p.read_text(encoding='utf-8'))
    print(json.dumps(r,ensure_ascii=False,indent=2))
    print('\nOBSERVE ONLY · Broker POST calls: 0')
