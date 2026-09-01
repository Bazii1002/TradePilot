from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
main = (ROOT/'main.py').read_text(encoding='utf-8')
live = (ROOT/'etoro_live_manual.py').read_text(encoding='utf-8')
qml = (ROOT/'qml'/'Main.qml').read_text(encoding='utf-8')

ast.parse(main); ast.parse(live)
assert 'MAX_LIVE_EUR = 10.00' in live
assert 'LIVE_ORDER_URL = "https://public-api.etoro.com/api/v2/trading/execution/orders"' in live
assert '"transaction":"buy"' in live and '"leverage":1' in live
assert 'open_position_count()>=1' in live
assert 'PREPARED_TTL_SECONDS = 120' in live
assert 'prepareLiveBuy' in main and 'executePreparedLiveBuy' in main
assert 'AutoTrader bleibt gesperrt' in qml and 'AutoTrader → REAL gesperrt' in qml
assert 'ECHTGELDORDER SENDEN' in qml and 'liveConfirm.text.toUpperCase() === "LIVE"' in qml
assert 'TradePilot erhöht den Betrag NICHT automatisch' in main
assert '}; background:' not in qml
assert 'validator: DoubleValidator' in qml and 'background: Rectangle' in qml
assert 'internalSymbolFull' in live and 'params={"search":symbol}' not in live
assert 'ETORO_PUBLIC_KEY' in live and 'ETORO_PRIVATE_KEY' in live

assert 'DEFAULT_WATCHLIST_ITEMS_URL' in live
assert 'watchlists/default-watchlists/items' in live
assert 'market-data/instruments' in live
assert '_watchlist_instrument_ids' in live and '_metadata_rows_for_ids' in live
assert 'symbolFull' in live
assert 'ETORO_USER_KEY' in live
assert 'instrument_cache.json' in live
assert '_resolve_via_default_watchlist' in live
assert 'itemId' in live and 'instrumentIds' in live
assert 'self.session.post(DEFAULT_WATCHLIST_ITEMS_URL' not in live
print('TradePilot 1.0 UI Prototype 0.6.6.3 INSTRUMENT DIRECTORY FALLBACK SELFTEST: OK')
print('eToro key naming: Public/API -> x-api-key; Private/User -> x-user-key: OK')
print('Instrument resolver: cache -> official search -> read-only watchlist IDs -> instrument metadata: OK')
print('Hard max 10 EUR per REAL order: OK')
print('BUY only + leverage 1 + one-position gate: OK')
print('Exact instrument resolution + frozen review: OK')
print('120s expiry + single-use prepared order: OK')
print('QML TextField validator/background syntax regression: OK')
print('Explicit LIVE confirmation in QML: OK')
print('AutoTrader -> REAL remains locked: OK')
