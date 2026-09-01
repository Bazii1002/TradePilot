TradePilot 1.0 UI Prototype 0.6.6.1 — Manual LIVE Execution Bridge

Basis: 0.6.5 Live Dashboard Foundation.

Neu:
- Manueller eToro REAL BUY-Test direkt aus dem neuen QML-Dashboard.
- Harte Obergrenze 10,00 EUR pro Order.
- BUY only, Hebel 1x, keine Shorts.
- Maximal eine offene REAL-Position während der Testphase.
- Exakte Ticker -> instrumentId-Auflösung vor Bestätigung.
- Vor dem Versand werden Instrument-ID, EUR-Budget, EUR/USD und USD-Orderbetrag angezeigt.
- Finale Eingabe muss exakt LIVE lauten.
- Vorbereitete Order verfällt nach 120 Sekunden und ist nur einmal verwendbar.
- TradePilot erhöht einen vom Broker abgelehnten Mindestbetrag niemals automatisch.
- AutoTrader -> REAL bleibt gesperrt.

Git-Workflow:
0.6.6.1 gehört zuerst auf dev. stable bleibt auf dem letzten getesteten Stand, bis 0.6.6.1 erfolgreich geprüft wurde.
