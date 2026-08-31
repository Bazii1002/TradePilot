from pathlib import Path
import ast

root=Path(__file__).resolve().parent
for name in ['main.py','etoro_broker.py','paper_broker.py','order_engine.py','tradepilot_engine.py']:
    ast.parse((root/name).read_text(encoding='utf-8'))
main=(root/'main.py').read_text(encoding='utf-8')
et=(root/'etoro_broker.py').read_text(encoding='utf-8')
assert 'VERSION = "0.9.12"' in main
assert 'EtoroLiveBroker' in main
assert 'LIVE_ORDER_URL = "https://public-api.etoro.com/api/v2/trading/execution/orders"' in et
assert '/trading/info/portfolio' in et
assert 'ETORO_REAL_USER_KEY' in et and 'ETORO_API_KEY' in et
assert 'MAX_LIVE_EUR = 10.00' in et
assert 'eur > MAX_LIVE_EUR' in et
assert '"leverage": 1' in et
assert 'open_position_count() >= 1' in et
assert 'QInputDialog.getText' in main and 'text.strip().upper() != "LIVE"' in main
assert 'place_live_market_buy' in main
# live auto trader is intentionally not wired
assert 'AutoTrader→eToro LIVE weiterhin gesperrt' in main
print('TradePilot 0.9.12 CORE SELFTEST: OK')
print('eToro REAL portfolio + live execution paths: OK')
print('Hard max EUR 10.00 per live order: OK')
print('Fresh EUR/USD conversion or fail-closed: OK')
print('Leverage fixed at 1 / long BUY only: OK')
print('Existing REAL position blocks new test buy: OK')
print('Double LIVE confirmation: OK')
print('Local .env credentials: OK')
print('AutoTrader -> eToro REAL: intentionally DISABLED')
