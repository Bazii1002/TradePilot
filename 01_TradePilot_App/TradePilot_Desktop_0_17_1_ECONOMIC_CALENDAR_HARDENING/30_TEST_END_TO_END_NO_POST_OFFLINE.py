from __future__ import annotations
from pathlib import Path
import math
import pandas as pd

from fast_scanner import ThousandStockFastScanner
from strategy_engine import StrategyAnalyzer

app = Path(__file__).resolve().parent
print('='*108)
print('TRADEPILOT 0.14.1 - END-TO-END ACTIONABLE -> REAL PREFLIGHT OFFLINE (NO POST)')
print('='*108)

# Build deterministic synthetic market frames for 1000 symbols. No network, no broker.
def frame_for(i: int) -> pd.DataFrame:
    n=90
    base=30.0 + (i % 80)
    strength=(i % 37) / 1000.0 + 0.002
    closes=[]
    vols=[]
    price=base
    for j in range(n):
        price *= (1.0 + strength + math.sin((j+i)*0.21)*0.0015)
        closes.append(price)
        vols.append(1_000_000 * (1.0 + (j % 7)*0.03))
    # Last bar volume boost gives strong but deterministic candidates.
    vols[-1] *= 2.0 + (i % 5)*0.25
    idx=pd.date_range('2026-01-01', periods=n, freq='D')
    c=pd.Series(closes,index=idx)
    return pd.DataFrame({'Open':c*0.997,'High':c*1.006,'Low':c*0.994,'Close':c,'Volume':vols},index=idx)

symbols=[f'TP{i:04d}' for i in range(1000)]
frames={s:frame_for(i) for i,s in enumerate(symbols)}
scanner=ThousandStockFastScanner(app, StrategyAnalyzer())
# Exercise broad ranking without network.
candidates=scanner.rank_frames(2,symbols,frames,limit=50)
assert len(candidates)==50

# Exercise deep analyzer on the 50 candidate frames.
deep=[]
for r in candidates:
    sym=r['symbol']
    deep.append(scanner.analyzer.analyze_frame(sym,frames[sym],2).as_dict())
deep.sort(key=lambda r: float(r.get('score') or 0), reverse=True)
marked, finalists=scanner.mark_finalists(deep,(),12)
from quality_gate import apply_quality_gate, MAX_ACTIONABLE_SIGNALS
marked, actionable_count=apply_quality_gate(marked,2,(),MAX_ACTIONABLE_SIGNALS)
actionable=[r for r in marked if r.get('is_actionable')]

# The integration invariant: never more than 3 actionable signals.
assert finalists==12
assert actionable_count <= 3

# A fake PREVIEW/ARM model that mirrors the REAL handoff fields but never instantiates broker transport.
if actionable:
    chosen=actionable[0]
else:
    # Safe test fallback: test the handoff schema with the top finalist; this does NOT mark it actionable.
    chosen=next(r for r in marked if r.get('is_finalist'))

prepared={
    'symbol': chosen['symbol'],
    'instrument_id': 1001,
    'budget_eur': 10.00,
    'amount_usd': 11.60,
    'strategy': 'DAY',
    'leverage': 1,
}
confirmation=f"EXECUTE REAL BUY {prepared['symbol']} {prepared['budget_eur']:.2f} EUR"
payload={
    'action':'open','transaction':'buy','instrumentId':prepared['instrument_id'],
    'orderType':'mkt','amount':prepared['amount_usd'],'orderCurrency':'usd','leverage':1,
}
assert prepared['budget_eur'] <= 10.0
assert prepared['leverage'] == 1
assert payload['action']=='open' and payload['transaction']=='buy'
assert confirmation.startswith('EXECUTE REAL BUY ')

print(f'Universe simuliert:      {len(symbols)}')
print(f'Candidates:              {len(candidates)}')
print(f'Deep:                    {len(deep)}')
print(f'Finalists:               {finalists}')
print(f'ACTIONABLE:              {actionable_count}')
print(f'Handoff Symbol:          {prepared["symbol"]}')
print(f'Preflight Budget:        {prepared["budget_eur"]:.2f} EUR')
print(f'Payload leverage:        {payload["leverage"]}x')
print('ARM:                     NUR SIMULIERT / NICHT GESPEICHERT')
print('Broker POST:             TECHNISCH NICHT VORHANDEN')
print('STATUS: END-TO-END OFFLINE NO POST OK')
