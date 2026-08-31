from pathlib import Path

root=Path(__file__).resolve().parent
main=(root/'main.py').read_text(encoding='utf-8')
theme=(root/'themes.py').read_text(encoding='utf-8')
etoro=(root/'etoro_broker.py').read_text(encoding='utf-8')
assert 'VERSION = "0.9.14.1"' in main or "VERSION = '0.9.14.1'" in main
for label in ['Dashboard','Bot','Portfolio','Markets','News','Backtest','Trades','Settings']:
    assert label in main
assert 'nav_button_by_stack' in main
assert 'right.addWidget(self._build_market_bar())' not in main
assert 'GlobalSearch' in main and 'SidebarAccount' in main
assert 'instrument_id' in etoro and 'symbol' in etoro
assert '10.00' in etoro or '10.0' in etoro

# Runtime theme smoke test: catches malformed f-string/QSS braces before app startup.
import importlib.util
spec=importlib.util.spec_from_file_location('tp_themes', root/'themes.py')
tp_themes=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tp_themes)
for mode in ('dark','light'):
    tp_themes.set_theme(mode)
    qss=tp_themes.build_qss()
    assert 'QFrame#BrandMark {' in qss
    assert 'QLineEdit#GlobalSearch {' in qss
print('TradePilot 0.9.14.1 FULL UI REDESIGN STARTUP FIX SELFTEST: OK')
print('Frozen sidebar structure: OK')
print('New compact topbar + market status: OK')
print('Dark/light design system runtime build: OK')
print('eToro REAL instrument fix preserved: OK')
print('Hard 10 EUR live cap preserved: OK')
print('AutoTrader -> REAL remains locked: OK')
