TRADEPILOT 0.9.11 - eToro Demo Broker Integration (Stage 1)

SICHERHEITSUMFANG
- Nur eToro DEMO / Virtual Portfolio.
- Echtgeld-Endpunkt ist absichtlich nicht implementiert.
- AutoTrader sendet in 0.9.11 noch KEINE Orders an eToro.
- Manuelle Demo-BUY-Tests erfordern jedes Mal eine Bestätigung.
- Manueller Testbetrag ist hart auf maximal 250 USD begrenzt.
- API Key und Demo User Key werden lokal in .env gespeichert.

START
1) 01_SELFTEST_0_9_11.bat
2) 02_START_TRADEPILOT.bat
3) Settings -> eToro Demo API
4) API Key + Demo User Key eintragen -> Keys lokal speichern
5) Verbindung testen
6) Erst wenn Verbindung grün ist: optional manuellen kleinen Demo BUY testen

NÄCHSTE STUFE
Nach erfolgreicher Verbindung, Portfolio-Read und manueller Demo-Ausführung bauen wir
0.9.12: Reconciliation/Orderstatus + kontrollierte AutoTrader->eToro Demo-Ausführung.
