from pathlib import Path
import json
from production_real_core import ProductionRealCore
s=ProductionRealCore(Path(__file__).resolve().parent).status()
print('='*96)
print('TRADEPILOT 0.16.0 - PRODUCTION REAL CORE STATUS')
print('='*96)
print(json.dumps(s,ensure_ascii=False,indent=2))
print('STATUS: READ ONLY')
