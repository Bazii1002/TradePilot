from pathlib import Path
from etoro_live_manual import EtoroManualLiveBroker, EtoroLiveError, MAX_LIVE_EUR

print("=" * 98)
print("TRADEPILOT 0.6.6.5 - FINAL REAL EXECUTION GATE TEST (NO POST)")
print("=" * 98)
print("Frische Revalidierung nach LIVE: Portfolio + Instrument-ID + EUR/USD.")
print("Dieser Test ruft ausschließlich das GET/READ-ONLY Gate auf. KEINE Order wird gesendet.\n")

broker=EtoroManualLiveBroker(Path(__file__).resolve().parent)
try:
    prepared=broker.prepare_market_buy("AAPL", MAX_LIVE_EUR)
    try:
        broker.validate_execution_gate(prepared, "FALSCH")
        raise RuntimeError("Gate akzeptierte falsche Bestätigung")
    except EtoroLiveError:
        pass
    gate=broker.validate_execution_gate(prepared, "LIVE")
    print("FINAL EXECUTION GATE")
    print("-" * 54)
    print(f"Ticker:            {gate['symbol']}")
    print(f"Instrument-ID:     {gate['instrument_id']}")
    print("Instrument frisch: OK / Cache umgangen")
    print(f"Budget:            {gate['budget_eur']:.2f} EUR")
    print(f"EUR/USD frisch:    {gate['eurusd']:.5f}")
    print(f"Orderbetrag:       {gate['amount_usd']:.2f} USD")
    print("Side:              BUY")
    print("Leverage:          1x")
    print("Open-Position-Gate: OK")
    print("Bestätigung LIVE:  OK")
    print("\nSTATUS: FINAL-GATE OK")
    print("KEINE ORDER WURDE GESENDET")
except EtoroLiveError as exc:
    print("ERGEBNIS: BLOCKIERT")
    print(str(exc))
    raise SystemExit(2)
