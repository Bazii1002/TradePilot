TRADEPILOT DESKTOP ALPHA 0.13.5 - SCANNER OPTIMIZATION

Neu in 0.13.5:
- 1000-Aktien Fast Scanner bleibt erhalten.
- Fehlende Symbole werden einmal in kleineren Batches erneut versucht.
- Persistenter data\invalid_symbols.json Fehlercache.
- Kein voreiliges Blacklisting: erst nach 3 Fehlversuchen folgt 7 Tage Quarantaene, danach erneuter Test.
- Deep Analysis bleibt auf Fast Top 50 + offene Positionen begrenzt.
- Neue Finalistenstufe: Top 12 nach Deep Analysis.
- Neue Shadow-BUYs duerfen nur aus diesen Final Top 12 kommen.
- Bestehende Positionen werden weiterhin unabhaengig vom Ranking analysiert.
- Markets UI zeigt Universe, Scanned, Candidates, Deep, Finalists, BUY Signals, Duration.
- REAL AutoTrading bleibt LOCKED; kein Broker POST in Scanner-Tests.

Empfohlene Tests:
01_SELFTEST_UI.bat
19_TEST_1000_STOCK_FAST_SCANNER_OFFLINE.bat
20_REFRESH_1000_STOCK_UNIVERSE.bat
21_TEST_1000_STOCK_FAST_SCANNER_LIVE.bat
22_SHOW_SCANNER_HEALTH.bat
