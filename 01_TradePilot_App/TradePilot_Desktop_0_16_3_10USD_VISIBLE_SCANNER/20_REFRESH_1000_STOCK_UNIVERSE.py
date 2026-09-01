from pathlib import Path
from universe_provider import StockUniverseProvider

print('='*96)
print('TRADEPILOT 0.13.3 - 1000 STOCK UNIVERSE REFRESH')
print('='*96)
p=StockUniverseProvider(Path(__file__).resolve().parent)
try:
    rows=p.refresh()
    print(f'Universe geladen: {len(rows)} Aktien')
    print(f'Quelle:           {p.last_source}')
    print(f'Cache:            {p.cache_file}')
    print('STATUS: OK')
except Exception as exc:
    rows=p.load(allow_refresh=False)
    print(f'LIVE-Refresh FEHLER: {exc}')
    print(f'Fallback verfügbar: {len(rows)} Aktien')
    print('STATUS: NICHT 1000 - Netzwerk/Quelle prüfen')
