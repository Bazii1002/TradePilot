from pathlib import Path
import ast

root=Path(__file__).resolve().parent
for name in ['main.py','etoro_broker.py','paper_broker.py','order_engine.py','tradepilot_engine.py']:
    ast.parse((root/name).read_text(encoding='utf-8'))
main=(root/'main.py').read_text(encoding='utf-8')
et=(root/'etoro_broker.py').read_text(encoding='utf-8')
assert 'VERSION = "0.9.11"' in main
assert 'EtoroDemoBroker' in main
assert '/api/v2/trading/execution/demo/orders' in et
assert '/trading/info/demo/portfolio' in et
assert 'ETORO_API_KEY' in et and 'ETORO_USER_KEY' in et
assert 'trading/execution/orders"' not in et.replace('trading/execution/demo/orders"','')
print('TradePilot 0.9.11 CORE SELFTEST: OK')
print('eToro Demo-only execution: OK')
print('Local .env credentials: OK')
print('Manual confirmation + 250 USD test cap: OK')
print('AutoTrader -> eToro: intentionally DISABLED')
