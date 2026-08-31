TradePilot 0.9.13 — NEW DESIGN + eToro LIVE instrument fix

WICHTIG
- Echtgeld-Modus: manueller Test bis maximal 10,00 EUR pro Order.
- AutoTrader -> eToro REAL ist weiterhin NICHT freigeschaltet.
- Vor LIVE wird der Ticker exakt auf ein eToro-Instrument aufgelöst.
- Instrument-ID, EUR-Budget, FX-Kurs und USD-Orderbetrag werden VOR der LIVE-Eingabe angezeigt.
- Die vorbereitete Order wird nach Bestätigung nicht neu berechnet.
- Request enthält instrumentId UND das exakt geprüfte Symbol.
- Bei Mehrdeutigkeit / fehlender ID / FX-Fehler / bestehender Position: fail closed.

DESIGN
- neues TradePilot Dashboard mit Cash Available / Invested / Portfolio Value / Today
- Recent Trades + Portfolio Overview + Watchlist + TradePilot Status
- überarbeitetes Dark/Light Designsystem
- kompaktere Sidebar/Topbar, modernere Cards, Tabellen und Status-Pills

START
1) 01_SELFTEST_0_9_13.bat
2) 02_START_TRADEPILOT.bat
3) Settings -> eToro REAL API -> Verbindung testen
4) Vor echtem BUY den letzten Bestätigungsdialog kontrollieren.
