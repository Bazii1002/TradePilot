from pathlib import Path
from real_signal_handoff import load_handoff
APP=Path(__file__).resolve().parent
print('='*96); print('TRADEPILOT 0.14.1 FIX1 - VALIDATED REAL HANDOFF'); print('='*96)
try:
 h=load_handoff(APP,require_fresh=False)
 print(f"Symbol: {h['symbol']} | Instrument: {h['instrument_id']} | Budget: {h['budget_eur']:.2f} EUR")
 print(f"Q: {h['quality_score']:.1f} | {h['quality_confirmations']}/{h['quality_checks']} | Alter: {h['age_seconds']:.0f}s | TTL: {h['ttl_seconds']}s")
 print('Fresh:', h['age_seconds'] <= h['ttl_seconds'])
except Exception as e: print('Kein Handoff:',e)
