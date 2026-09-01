TradePilot 0.6.6.6 - Manual REAL Execution Readiness

- Baut auf dem getesteten 0.6.6.5 Final Gate auf.
- Revalidiert Portfolio, Instrument-ID und EUR/USD frisch.
- Erzeugt eine finale Payload-Vorschau fuer AAPL / max. 10 EUR / BUY / Hebel 1x.
- Echtgeld-POST ist in diesem Build absichtlich deaktiviert.
- execute_confirmed() und place_prepared() blockieren hart.
- AutoTrader -> REAL bleibt gesperrt.
- 10_TEST_EXECUTION_READINESS_NO_POST.bat sendet keine Order.
