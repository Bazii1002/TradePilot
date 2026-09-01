from pathlib import Path
from universe_provider import StockUniverseProvider
from fast_scanner import ThousandStockFastScanner
from strategy_engine import StrategyAnalyzer

app=Path(__file__).resolve().parent
print('='*108)
print('TRADEPILOT 0.13.6 - FINAL SIGNAL QUALITY GATE LIVE TEST (NO BROKER POST)')
print('='*108)
u=StockUniverseProvider(app)
rows=u.load(allow_refresh=True)
syms=[r['symbol'] for r in rows][:1000]
print(f'Universe: {len(syms)} | Quelle: {u.last_source}')
if len(syms)<900:
    print('ABBRUCH: Kein ~1000-Aktien-Universe verfügbar. Zuerst Test 20 ausführen.')
    raise SystemExit(2)
scanner=ThousandStockFastScanner(app, StrategyAnalyzer())
out,metrics=scanner.scan(2,syms,held_symbols=(),force_full=True)
print(f"Scanned:       {metrics['scanned']} / {metrics['universe']}")
print(f"Candidates:    {metrics['candidates']}")
print(f"Deep:          {metrics['deep']}")
print(f"Finalists:     {metrics['finalists']}")
print(f"Raw BUY:       {metrics['raw_signals']}")
print(f"Final BUY:     {metrics['signals']}")
print(f"ACTIONABLE:    {metrics.get('actionable',0)}")
print(f"Errors final:  {metrics['errors']}")
print(f"Retried:       {metrics['retried']}")
print(f"Quarantined:   {metrics['quarantined']}")
print(f"Duration:      {metrics['duration']:.1f}s")
print('Top 12 Finalists / Quality Gate:')
for r in [x for x in out if x.get('is_finalist')][:12]:
    flag='ACTION' if r.get('is_actionable') else ('PASS' if r.get('quality_pass') else 'BLOCK')
    print(f"  {r['symbol']:<7} Score {r['score']:>5.1f} | Q {r.get('quality_score',0):>5.1f} | {r.get('quality_confirmations',0)}/5 | {flag:<6} | {r.get('reason','')}")
print('REAL Broker POST: NICHT VERWENDET')
print('STATUS: FINAL SIGNAL QUALITY GATE LIVE TEST BEENDET')
