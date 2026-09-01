from pathlib import Path
from universe_provider import StockUniverseProvider
from fast_scanner import ThousandStockFastScanner
from strategy_engine import StrategyAnalyzer
import time

app=Path(__file__).resolve().parent
print('='*100)
print('TRADEPILOT 0.13.3 - 1000 STOCK FAST SCANNER LIVE TEST (NO BROKER POST)')
print('='*100)
u=StockUniverseProvider(app)
rows=u.load(allow_refresh=True)
syms=[r['symbol'] for r in rows][:1000]
print(f'Universe: {len(syms)} | Quelle: {u.last_source}')
if len(syms)<900:
    print('ABBRUCH: Kein ~1000-Aktien-Universe verfügbar. Zuerst Test 20 ausführen.')
    raise SystemExit(2)
scanner=ThousandStockFastScanner(app, StrategyAnalyzer())
t0=time.perf_counter()
out,metrics=scanner.scan(2,syms,held_symbols=(),force_full=True)
print(f"Scanned:     {metrics['scanned']} / {metrics['universe']}")
print(f"Candidates:  {metrics['candidates']}")
print(f"Deep:        {metrics['deep']}")
print(f"BUY Signals: {metrics['signals']}")
print(f"Errors:      {metrics['errors']}")
print(f"Duration:    {metrics['duration']:.1f}s")
print('Top 10:')
for r in out[:10]: print(f"  {r['symbol']:<7} {r['score']:>5.1f}% {r['signal']:<5} {r.get('reason','')}")
print('REAL Broker POST: NICHT VERWENDET')
print('STATUS: LIVE FAST SCAN BEENDET')
