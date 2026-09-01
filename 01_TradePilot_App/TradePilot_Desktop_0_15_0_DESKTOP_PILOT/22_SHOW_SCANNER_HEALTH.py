from pathlib import Path
import json, time
p=Path(__file__).resolve().parent/'data'/'invalid_symbols.json'
print('='*96); print('TRADEPILOT 0.13.5 - SCANNER HEALTH'); print('='*96)
if not p.exists():
    print('Noch keine persistierten Symbolfehler.'); print('STATUS: OK'); raise SystemExit(0)
data=json.loads(p.read_text(encoding='utf-8'))
rows=data.get('symbols',{})
q=[]
for s,r in sorted(rows.items()):
    until=float(r.get('quarantined_until',0) or 0)
    status='QUARANTINE' if until>time.time() else 'RETRYABLE'
    q.append((s,int(r.get('fail_count',0)),status,r.get('reason','')))
print(f'Bekannte Problemsymbole: {len(q)}')
print(f'Davon quarantiniert:    {sum(1 for x in q if x[2]=="QUARANTINE")}')
for s,c,st,reason in q[:40]: print(f'  {s:<8} fails={c:<2} {st:<10} {reason}')
if len(q)>40: print(f'  ... +{len(q)-40} weitere')
print('STATUS: OK')
