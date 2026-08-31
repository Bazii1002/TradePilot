TradePilot 0.9.10 – Performance, Risk & Position Management
============================================================

WICHTIG
-------
TradePilot 0.9.10 sendet KEINE echten Broker-Orders. Käufe und Verkäufe laufen
weiterhin ausschließlich im lokalen Paper-Konto.

NEU IN 0.9.10
-------------
1. Performance & Risk Seite
   - Gesamtperformance und Gesamt-P/L
   - Trefferquote geschlossener Paper-Trades
   - Max Drawdown
   - Profit Factor
   - lokale Equity-Kurve
   - Sektor-Exposure

2. Risk & Position Management
   - sichtbare Limits je Risikoprofil
   - Investitionsquote, Cashreserve und maximale Positionen
   - Stop-Loss, Take-Profit und Trailing-Stop je Position
   - Positionsplaner für die aktuell analysierte Aktie
   - dynamische Positionsgröße nach Signalstärke und Volatilität
   - harter, vom Nutzer festgelegter Maximalbetrag pro Trade

3. Börsenstatus
   - NYSE, NASDAQ, XETRA und Wien
   - Grün = reguläre Sitzung offen
   - Rot = geschlossen
   - Countdown bis Öffnung bzw. Schließung
   - Wochenenden und wichtige volle Feiertage werden lokal berücksichtigt
   - Sonderhandelstage können abweichen; Paper-Orders benötigen weiterhin
     zusätzlich einen frischen Kurs vom Datenanbieter.

4. Bestehende 0.9.9 Order Engine bleibt aktiv
   - Pending Orders bei geschlossenem Markt
   - frischer Intraday-Kurs für Paper-Fills
   - Slippage
   - Cash-/Portfolio-/Sektorprüfung direkt vor dem Fill
   - Kurslücken-Schutz

START
-----
PowerShell:

& C:\Users\bazala\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\TradePilot\TradePilot_0_9_10\main.py

SELBSTTEST
----------
& C:\Users\bazala\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\TradePilot\TradePilot_0_9_10\SELFTEST_0_9_10.py

Erwartete letzte Zeile:
TradePilot 0.9.10 CORE SELFTEST: OK

HINWEIS ZUM ERSTEN TEST
-----------------------
0.9.10 übernimmt lokale Einstellungen und das Paper-Konto aus 0.9.9, sofern
vorhanden. Bereits vorgemerkte Orders behalten ihre alte Stückzahl. Um die neue
dynamische Positionsgrößen-Logik vollständig zu testen, das Paper-Konto einmal
unter Einstellungen zurücksetzen und anschließend einen neuen Core-30-Scan starten.
