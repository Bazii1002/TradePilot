from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker, EtoroLiveError, MAX_LIVE_EUR

print("=" * 102)
print("TRADEPILOT 0.6.6.6 - MANUAL REAL EXECUTION READINESS (NO POST)")
print("=" * 102)
print("Finale GET-Revalidierung + Payload-Vorschau. KEIN POST, KEINE Order.\n")

broker=EtoroManualLiveBroker(Path(__file__).resolve().parent)
try:
    prepared=broker.prepare_market_buy("AAPL", MAX_LIVE_EUR)
    ready=broker.build_execution_readiness(prepared, "LIVE")
    p=ready["payload_preview"]
    print("EXECUTION READINESS")
    print("-" * 58)
    print(f"Ticker:             {ready['symbol']}")
    print(f"Instrument-ID:      {ready['instrument_id']}")
    print(f"Budget:             {ready['budget_eur']:.2f} EUR")
    print(f"EUR/USD frisch:     {ready['eurusd']:.5f}")
    print(f"Orderbetrag:        {ready['amount_usd']:.2f} USD")
    print(f"Payload Action:     {p['action']}")
    print(f"Payload Side:       {p['transaction']}")
    print(f"Payload OrderType:  {p['orderType']}")
    print(f"Payload Currency:   {p['orderCurrency']}")
    print(f"Payload Leverage:   {p['leverage']}x")
    print("AutoTrader REAL:    LOCKED")
    print("POST-Funktion:      DEAKTIVIERT")
    print("\nSTATUS: EXECUTION READINESS OK")
    print("KEINE ORDER WURDE GESENDET")
except EtoroLiveError as exc:
    print("ERGEBNIS: BLOCKIERT")
    print(str(exc))
    raise SystemExit(2)
