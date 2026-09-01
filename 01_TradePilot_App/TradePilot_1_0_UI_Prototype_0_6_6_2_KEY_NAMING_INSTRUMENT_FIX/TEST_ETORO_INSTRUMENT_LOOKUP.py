from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker
print('='*82)
print('TRADEPILOT 0.6.6.2 - eToro INSTRUMENT LOOKUP TEST (READ ONLY)')
print('='*82)
print('Key-Zuordnung: x-api-key = Öffentlicher Key | x-user-key = Privater Key')
b=EtoroManualLiveBroker(Path(__file__).resolve().parent)
row=b.search_exact_instrument('AAPL')
print('Ticker:         AAPL')
print('Instrument-ID: ', b._instrument_id(row))
print('Treffer:        OK / exakt')
print('Keine Order wurde gesendet.')
