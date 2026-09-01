TRADEPILOT 1.0 UI PROTOTYPE 0.6 - BACKEND BRIDGE
=================================================

Ziel dieser Version:
- Das eingefrorene Dashboard-Design 0.5.1 bleibt die Basis.
- Python liefert jetzt echte Daten an QML.
- eToro REAL wird ausschließlich READ-ONLY abgefragt.
- Es existiert in 0.6 KEIN Order-Endpunkt und kein HTTP POST/PUT/PATCH/DELETE.

Ablauf am Surface:
1) 01_SELFTEST_UI.bat
2) Einmalig: 03_SETUP_ETORO_KEYS.bat
3) 04_TEST_ETORO_READONLY.bat
4) 02_START_UI_PROTOTYPE.bat

Die Keys stehen nur lokal in .env. .env niemals committen.

Was jetzt echt ist:
- eToro Verbindungsstatus
- Cash/Buying Power, soweit der Portfolio-Payload den Wert liefert
- Invested/Portfolio Value, soweit direkt oder sicher ableitbar
- offene Positionen im linken Panel
- Today P/L nur wenn eToro einen eindeutigen Daily/Today-Wert liefert
- NYSE/NASDAQ/XETRA Status aus dem lokalen Exchange-Status-Modul
- Portfolio-Verlauf wird ab dem ersten erfolgreichen Start lokal aufgezeichnet

Was noch Preview ist:
- International Market News
- Bot-Seite und alle anderen Seiten
- Trade-History: 0.6 zeigt offene Positionen statt erfundener Trades

WICHTIG:
Wenn eToro ein Feld nicht eindeutig liefert, zeigt TradePilot „—“ statt einen Wert zu erfinden.

0.6.3 PAYLOAD MAPPING FIX
- Unterstützt das auf REAL beobachtete eToro-Envelope `clientPortfolio` zusätzlich zu `data`.
- Kontofelder werden defensiv auch in wenigen verschachtelten Ebenen gesucht.
- Positionen werden nur aus expliziten Positions-Listen gelesen; unbekannte Listen werden nicht geraten.
- 06_DIAGNOSE_ETORO_PAYLOAD_SCHEMA.bat zeigt ausschließlich Feldpfade/Datentypen, niemals Werte.
- Weiterhin READ ONLY: keine Order-Endpunkte, keine POST/PUT/PATCH/DELETE Requests.
