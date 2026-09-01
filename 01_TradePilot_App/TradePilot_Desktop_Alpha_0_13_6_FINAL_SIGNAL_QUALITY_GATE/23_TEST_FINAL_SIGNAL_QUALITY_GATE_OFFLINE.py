from quality_gate import apply_quality_gate, MAX_ACTIONABLE_SIGNALS, MIN_CONFIRMATIONS, MIN_QUALITY_SCORE

rows=[]
for i in range(12):
    rows.append({
        'symbol':f'Q{i+1:02d}','strategy':'DAY','score':90-i*0.7,'signal':'BUY','price':100.0,
        'rsi':60+i*0.7,'momentum_pct':2.0-i*0.08,'volume_ratio':2.2-i*0.05,
        'atr_pct':1.45+i*0.03,'is_finalist':True,
    })
# Deliberately weak confirmation despite BUY label.
rows[-1].update({'rsi':78,'momentum_pct':-0.5,'volume_ratio':0.7,'atr_pct':5.0})
marked,n=apply_quality_gate(rows,2,(),MAX_ACTIONABLE_SIGNALS)
assert n <= 3
assert n > 0
assert sum(bool(r.get('is_actionable')) for r in marked)==n
assert not marked[-1]['quality_pass']
assert all(r['quality_confirmations']>=MIN_CONFIRMATIONS for r in marked if r.get('is_actionable'))
assert all(r['quality_score']>=MIN_QUALITY_SCORE for r in marked if r.get('is_actionable'))
print('='*100)
print('TRADEPILOT 0.13.6 - FINAL SIGNAL QUALITY GATE OFFLINE TEST')
print('='*100)
print(f'Finalisten geprüft:       {len(marked)}')
print(f'Min. Bestätigungen:      {MIN_CONFIRMATIONS}/5')
print(f'Min. Quality Score:      {MIN_QUALITY_SCORE:.0f}')
print(f'Max. Actionable/Scan:    {MAX_ACTIONABLE_SIGNALS}')
print(f'Actionable im Test:      {n}')
print('Quality Score:           Bestätigungsgrad, KEINE Gewinnwahrscheinlichkeit')
print('News/AI:                 NICHT erfunden / nicht Bestandteil dieses Gates')
print('REAL Broker POST:        NICHT VERWENDET')
print('STATUS: FINAL SIGNAL QUALITY GATE CORE OK')
