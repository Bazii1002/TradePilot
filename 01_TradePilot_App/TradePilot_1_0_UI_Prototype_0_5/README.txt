TradePilot 1.0 UI Prototype 0.5 – Final Visual Match
====================================================

Ziel
----
0.5 ist die letzte reine Visual-Match-Runde für das eingefrorene Dashboard-Konzept.
Die Dashboard-Geometrie aus 0.4 bleibt bestehen. Verbessert werden nur visuelle Details,
die im Surface-Screenshot noch deutlich vom Referenzbild abgewichen sind.

Verbessert gegenüber 0.4
------------------------
- Einheitliche SVG-Line-Icons in Sidebar, KPI-Cards, Glocke und Profil.
- Echte Referenz-Assets für AAPL, NVDA, MSFT, TSLA und SPY statt Buchstaben-Platzhaltern.
- Glass-Cards ohne die sichtbaren dunklen Ambient-Kreise aus 0.4.
- Zurückhaltendere Borders und Neon-Unterkanten für weniger "Qt-Box"-Wirkung.
- Portfolio-Chart mit unregelmäßiger, direkt gezeichneter Kurslinie statt periodischer Wellenform.
- Today-Sparkline ebenfalls unregelmäßiger und näher am Konzept.
- Referenzbild 0.5 liegt unter docs\TradePilot_UI_Reference_0_5.png.

Wichtig
-------
- REINER UI-PROTOTYP.
- KEINE Broker-Ausführung.
- KEINE eToro-Keys notwendig.
- "eToro REAL" ist nur visuelle Statusdarstellung.
- AutoTrader -> REAL bleibt als gesperrt dargestellt.
- Bestehende Research-/Broker-/Safety-Logik wird NICHT verändert.
- News, Portfolio-Werte und Trades sind Demo-Daten zur Layoutprüfung.

Start
-----
1) 01_SELFTEST_UI.bat
2) 02_START_UI_PROTOTYPE.bat

Nach Freigabe
-------------
Wenn dieses Dashboard visuell freigegeben wird, wird nicht erneut am Grundlayout gebaut.
Danach werden echte Backend-Daten schrittweise angebunden und die restlichen Seiten in
dieser Designsprache umgesetzt.
