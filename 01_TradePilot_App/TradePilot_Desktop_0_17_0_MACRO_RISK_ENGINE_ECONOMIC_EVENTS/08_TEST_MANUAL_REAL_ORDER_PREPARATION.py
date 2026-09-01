from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker, EtoroLiveError, MAX_LIVE_EUR

print("=" * 94)
print("TRADEPILOT 0.6.6.5 - MANUAL REAL ORDER PREPARATION TEST (NO POST)")
print("=" * 94)
print("Dieser Test liest Portfolio + Instrument + EUR/USD und bereitet nur eine Vorschau vor.")
print("KEINE Order wird gesendet. Es wird kein POST ausgeführt.\n")

broker = EtoroManualLiveBroker(Path(__file__).resolve().parent)
try:
    prepared = broker.prepare_market_buy("AAPL", MAX_LIVE_EUR)
    print("MANUAL REAL ORDER REVIEW")
    print("-" * 50)
    print(f"Ticker:            {prepared['symbol']}")
    print(f"Instrument-ID:     {prepared['instrument_id']}")
    print("Instrument:        verifiziert")
    print(f"Budget:            {prepared['budget_eur']:.2f} EUR")
    print(f"EUR/USD:           {prepared['eurusd']:.5f}")
    print(f"Orderbetrag:       {prepared['amount_usd']:.2f} USD")
    print("Side:              BUY")
    print(f"Leverage:          {prepared['leverage']}x")
    print("AutoTrader REAL:   LOCKED")
    print("\nSTATUS: VORBEREITUNG OK")
    print("KEINE ORDER WURDE GESENDET")
except EtoroLiveError as exc:
    print("ERGEBNIS: BLOCKIERT")
    print(str(exc))
    raise SystemExit(2)
