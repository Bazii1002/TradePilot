from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker, EtoroLiveError

print('='*90)
print('TRADEPILOT 0.6.6.3 - eToro INSTRUMENT DIRECTORY FALLBACK TEST (READ ONLY)')
print('='*90)
print('Key-Zuordnung: x-api-key = Öffentlicher Key | x-user-key = Privater Key')
print('Resolver-Kette: Local Cache -> Market-Data Search -> Standard-Watchlist (GET only)')
print('Keine Watchlist wird verändert und KEINE Order wird gesendet.\n')

b=EtoroManualLiveBroker(Path(__file__).resolve().parent)
try:
    row=b.search_exact_instrument('AAPL')
    iid=b._instrument_id(row)
    source=row.get('_resolutionSource','unknown')
    symbol=str(row.get('symbol') or row.get('internalSymbolFull') or 'AAPL').upper()
    print(f'Ticker:          {symbol}')
    print(f'Instrument-ID:   {iid}')
    print(f'Quelle:          {source}')
    print('Treffer:         OK / exakt')
    print('Cache:           lokal gespeichert')
except EtoroLiveError as exc:
    print('ERGEBNIS: BLOCKIERT')
    print(str(exc))
    raise SystemExit(2)
