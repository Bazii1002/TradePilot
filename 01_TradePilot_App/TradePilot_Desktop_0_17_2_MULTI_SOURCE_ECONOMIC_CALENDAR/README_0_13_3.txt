TradePilot Desktop Alpha 0.13.3 - 1000 Stock Fast Scanner

Ziel:
- ~1000 US-Aktien im Schnellscan berücksichtigen
- nicht jede Aktie teuer tief analysieren
- Cache + 25er Kurs-Batches + bis zu 8 parallele Batch-Worker
- Top 50 -> strategy-spezifische Deep Analysis
- offene Shadow-Positionen werden immer mit in die Deep Analysis genommen
- REAL AutoTrading bleibt LOCKED

Universe:
- bevorzugt aktuelle Holdings des iShares Russell 1000 ETF (ca. 1.000 US Large/Mid Caps)
- lokal gespeichert unter data/stock_universe_1000.json
- bei fehlender Quelle sicherer Fallback auf die alte 74-Aktien-Datei; die UI zeigt dann die echte Anzahl an
- eToro-Handelbarkeit wird NICHT aus dem Universe angenommen. Vor REAL Execution bleibt der bestehende exakte eToro Instrument Resolver Pflicht.

Pipeline:
1000 -> FAST RANKING -> 50 -> DEEP ANALYSIS -> BUY/WATCH/WAIT -> Shadow/Risk

Tests:
19_TEST_1000_STOCK_FAST_SCANNER_OFFLINE.bat
20_REFRESH_1000_STOCK_UNIVERSE.bat
21_TEST_1000_STOCK_FAST_SCANNER_LIVE.bat
