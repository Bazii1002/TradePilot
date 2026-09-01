from __future__ import annotations
import math
import time
import pandas as pd
from fast_scanner import ThousandStockFastScanner, FAST_CANDIDATES
from strategy_engine import StrategyAnalyzer
from pathlib import Path


def frame(seed: int, bars: int = 80):
    rows=[]
    price=20.0 + (seed % 80)
    for i in range(bars):
        drift=((seed % 17)-6)*0.0007 + 0.0015*math.sin((i+seed)/7)
        price=max(2.0, price*(1+drift))
        vol=500_000 + ((seed*7919+i*3571) % 2_000_000)
        rows.append((price*0.995,price*1.008,price*0.992,price,vol))
    return pd.DataFrame(rows,columns=['Open','High','Low','Close','Volume'],index=pd.date_range('2026-01-01',periods=bars,freq='D'))

print('='*96)
print('TRADEPILOT 0.13.3 - 1000 STOCK FAST SCANNER OFFLINE TEST')
print('='*96)
symbols=[f'TP{i:04d}' for i in range(1000)]
frames={s:frame(i) for i,s in enumerate(symbols)}
scanner=ThousandStockFastScanner(Path('.'), StrategyAnalyzer())
t0=time.perf_counter()
ranked=scanner.rank_frames(2,symbols,frames,FAST_CANDIDATES)
elapsed=time.perf_counter()-t0
assert len(symbols)==1000
assert len(ranked)==50
assert ranked[0]['score'] >= ranked[-1]['score']
print(f'Universe:             {len(symbols)}')
print(f'Schnellscan bewertet: {len(frames)}')
print(f'Kandidaten:           {len(ranked)}')
print(f'Ranking-Laufzeit:     {elapsed:.3f}s (lokal/synthetisch)')
print('Batch-Größe LIVE:     25')
print('Parallel Worker LIVE: 8')
print('Deep Analysis:        nur Top 50 + offene Positionen')
print('REAL Broker POST:     NICHT VERWENDET')
print('STATUS: 1000 STOCK FAST SCANNER CORE OK')
