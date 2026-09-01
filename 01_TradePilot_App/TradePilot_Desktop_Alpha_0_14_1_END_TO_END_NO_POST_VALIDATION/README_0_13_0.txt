TradePilot Desktop Alpha 0.13.0 - Production Strategy Engine
============================================================

Ziel
----
Ersetzt die künstliche Zufalls-/Stresstest-Signalquelle durch eine deterministische
technische Signal-Engine mit echten Marktdaten. Echtgeld-Autotrading bleibt gesperrt.

Strategien
----------
1 FAST   : 5-Minuten-Kerzen, kurzer Horizont
2 DAY    : 15-Minuten-Kerzen, Intraday
3 WEEK   : 1-Stunden-Kerzen, Swing
4 INVEST : Tageskerzen, langfristig

Bewertung
---------
- Trend: Kurs / schneller SMA / langsamer SMA
- Momentum: prozentuale Kursänderung
- RSI
- Volumen relativ zum 20-Bar-Durchschnitt
- ATR-basierte Volatilität

Signal
------
BUY / WATCH / WAIT werden nachvollziehbar aus dem Score und Trendfilter erzeugt.
Bestehende Shadow-Positionen behalten ihre Eröffnungsstrategie.
Exits: Stop-Loss, Take-Profit oder schwaches Strategiesignal nach Mindesthaltezeit.

Sicherheit
----------
- Bot Engine enthält keinen Broker-POST.
- REAL AUTOTRADING bleibt LOCKED.
- Die in 0.12.1 hart deaktivierten state-changing REAL-POSTs bleiben deaktiviert.
- Marktdatenfehler führen zu WAIT/NO_DATA, nicht zu einem Trade.
- Scans laufen in einem Worker-Thread, damit die Qt-Oberfläche nicht durch Netzabrufe blockiert.

Tests
-----
01_SELFTEST_UI.bat
18_TEST_PRODUCTION_STRATEGY_ENGINE_OFFLINE.bat

Danach App starten:
00_START_TRADEPILOT_ALPHA.bat

Für echte Marktdaten muss yfinance installiert sein (requirements.txt / Install-BAT).
