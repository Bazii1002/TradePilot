TradePilot Desktop Alpha 0.13.6 - Final Signal Quality Gate

Neu:
- 1000 -> Top 50 -> Deep -> Top 12 -> Quality Gate -> max. 3 ACTIONABLE
- Quality Gate prüft vorhandene Produktionsindikatoren: Score-Puffer, RSI, Momentum, Volumen, ATR
- Quality Score ist ein Bestätigungsgrad und ausdrücklich KEINE Gewinnwahrscheinlichkeit
- Keine erfundenen News/AI-Daten
- Shadow BUY darf nur noch is_actionable verwenden
- Bestehende Positionen bleiben unabhängig vom Gate überwacht
- REAL AutoTrading und state-changing Broker POST bleiben gesperrt

Tests:
01_SELFTEST_UI.bat
19_TEST_1000_STOCK_FAST_SCANNER_OFFLINE.bat
21_TEST_1000_STOCK_FAST_SCANNER_LIVE.bat
22_SHOW_SCANNER_HEALTH.bat
23_TEST_FINAL_SIGNAL_QUALITY_GATE_OFFLINE.bat
