from pathlib import Path
from universe_provider import StockUniverseProvider
from fast_scanner import ThousandStockFastScanner
from strategy_engine import StrategyAnalyzer

app=Path(__file__).resolve().parent
print('='*104)
print('TRADEPILOT 0.13.5 - 1000 STOCK OPTIMIZED LIVE TEST (NO BROKER POST)')
print('='*104)
u=StockUniverseProvider(app)
rows=u.load(allow_refresh=True)
syms=[r['symbol'] for r in rows][:1000]
print(f'Universe: {len(syms)} | Quelle: {u.last_source}')
if len(syms)<900:
    print('ABBRUCH: Kein ~1000-Aktien-Universe verfügbar. Zuerst Test 20 ausführen.')
    raise SystemExit(2)
scanner=ThousandStockFastScanner(app, StrategyAnalyzer())
out,metrics=scanner.scan(2,syms,held_symbols=(),force_full=True)
print(f"Scanned:      {metrics['scanned']} / {metrics['universe']}")
print(f"Candidates:   {metrics['candidates']}")
print(f"Deep:         {metrics['deep']}")
print(f"Finalists:    {metrics['finalists']}")
print(f"Raw BUY:      {metrics['raw_signals']}")
print(f"Final BUY:    {metrics['signals']}")
print(f"Errors final: {metrics['errors']}")
print(f"Retried:      {metrics['retried']}")
print(f"Quarantined:  {metrics['quarantined']}")
print(f"Duration:     {metrics['duration']:.1f}s")
print('Top 12 Finalists:')
for r in [x for x in out if x.get('is_finalist')][:12]:
    print(f"  {r['symbol']:<7} {r['score']:>5.1f}% {r['signal']:<5} {r.get('reason','')}")
print('REAL Broker POST: NICHT VERWENDET')
print('STATUS: OPTIMIZED LIVE FAST SCAN BEENDET')
