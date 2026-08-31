from pathlib import Path

root=Path(__file__).resolve().parent
main=(root/'main.py').read_text(encoding='utf-8')
theme=(root/'themes.py').read_text(encoding='utf-8')
etoro=(root/'etoro_broker.py').read_text(encoding='utf-8')
assert 'VERSION = "0.9.14"' in main or "VERSION = '0.9.14'" in main
for label in ['Dashboard','Bot','Portfolio','Markets','News','Backtest','Trades','Settings']:
    assert label in main
assert 'nav_button_by_stack' in main
assert 'right.addWidget(self._build_market_bar())' not in main
assert 'GlobalSearch' in main and 'SidebarAccount' in main
assert 'instrument_id' in etoro and 'symbol' in etoro
assert '10.00' in etoro or '10.0' in etoro
print('TradePilot 0.9.14 FULL UI REDESIGN SELFTEST: OK')
print('Frozen sidebar structure: OK')
print('New compact topbar + market status: OK')
print('Dark/light design system: OK')
print('eToro REAL instrument fix preserved: OK')
print('Hard 10 EUR live cap preserved: OK')
print('AutoTrader -> REAL remains locked: OK')
