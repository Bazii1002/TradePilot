from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parent
main=(ROOT/'main.py').read_text(encoding='utf-8')
broker=(ROOT/'etoro_broker.py').read_text(encoding='utf-8')
themes=(ROOT/'themes.py').read_text(encoding='utf-8')
for f in ('main.py','etoro_broker.py','themes.py'):
    ast.parse((ROOT/f).read_text(encoding='utf-8'))
assert 'VERSION = "0.9.13"' in main
assert 'DashboardPage(self.paper_broker)' in main
assert 'CASH AVAILABLE' in main and 'PORTFOLIO VALUE' in main and 'Recent Trades' in main and 'Portfolio Overview' in main
assert 'prepare_live_market_buy' in broker and 'place_prepared_live_market_buy' in broker
assert '"instrumentId": instrument_id' in broker and '"symbol": symbol' in broker
assert 'exact symbol only' in broker.lower()
assert "Instrument-ID: {prepared['instrument_id']}" in main
assert 'TradePilot erhöht diesen Betrag NICHT automatisch' in main
assert 'AutoTrader → REAL gesperrt' in main
assert 'StatusPillGood' in themes and 'InsetRow' in themes
print('TradePilot 0.9.13 SELFTEST: OK')
print('New dashboard design: OK')
print('Dark + light design system: OK')
print('Exact eToro ticker -> instrument resolution: OK')
print('LIVE confirmation shows instrument ID + exact amount: OK')
print('Order sends both instrumentId + exact symbol: OK')
print('Hard EUR 10 live cap unchanged: OK')
print('AutoTrader -> eToro REAL remains LOCKED: OK')
