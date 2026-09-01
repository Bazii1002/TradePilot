TradePilot 0.14.1 FIX1 - Dynamic REAL Signal Handoff

- Test 31 speichert nach vollständigem HARD-NO-POST-Preflight das aktuelle ACTIONABLE-Signal für max. 5 Minuten.
- 26_ARM_VALIDATED_REAL_SIGNAL_10EUR.bat prüft Signal, Instrument-ID und 10-EUR-Budget erneut und armt nur exakt dieses Signal.
- 27_EXECUTE_VALIDATED_REAL_BUY_10EUR.bat kann erst nach gültigem Handoff + ARM + exakter Texteingabe einen manuellen REAL BUY auslösen.
- Alte AAPL-hardcodierte 26/27-Skripte sind absichtlich blockiert.
- REAL AutoTrading bleibt LOCKED. Kein automatischer POST-Retry.
- ZIP enthält keine .env/Keys.
