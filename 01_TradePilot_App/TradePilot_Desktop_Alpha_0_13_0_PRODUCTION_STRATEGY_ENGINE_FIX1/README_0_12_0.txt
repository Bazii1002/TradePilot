TRADEPILOT DESKTOP ALPHA 0.12.0 - REAL EXECUTION SAFETY CORE
============================================================

ZWECK
-----
Dieser Build verbindet die bestehende Desktop-App/Shadow-Stresstest-Engine mit einer separaten,
fail-closed REAL-Execution-Schicht. Die REAL-Schicht kann kontrollierte manuelle BUY- und CLOSE-
Transaktionen ausführen, Broker-Positionen danach zurücklesen, unklare Orderzustände sperren,
Position-State speichern, Reconcile durchführen und einen lokalen Kill Switch aktivieren.

WICHTIGE ARCHITEKTURREGEL
-------------------------
Der bestehende 0.11.0 Shadow-Stresstest-Bot nutzt absichtlich simulierte Scores/Signale. Diese
Testlogik wird NICHT mit REAL AutoTrading verbunden. TRADEPILOT_REAL_AUTOTRADING_ENABLED darf
erst genutzt werden, wenn die echte Produktionsstrategie/Trading Engine an die Execution-Schicht
angeschlossen und separat getestet wurde.

REAL SAFETY
-----------
- Maximal 10 EUR pro REAL-Trade (zusätzlich konfigurierbar nach unten)
- Standard: maximal 1 offene REAL-Position
- BUY only für Open-Test, Leverage 1x
- Kein automatischer POST-Retry
- Bei Timeout/unklarem Zustand: REAL_EXECUTION_UNCERTAIN.json -> neue Orders blockiert
- Nach POST: Broker-Portfolio wird gelesen und Position/Close muss bestätigt werden
- Kill Switch: data/REAL_KILL_SWITCH.lock
- Credentials nur aus lokaler/zentraler .env, niemals ins ZIP
- Logs: data/real_execution.jsonl

OFFIZIELLE eToro-PFADE (Stand Build-Erstellung)
-----------------------------------------------
Open:  POST https://public-api.etoro.com/api/v2/trading/execution/orders
Close: POST https://public-api.etoro.com/api/v1/trading/execution/market-close-orders/positions/{positionId}
Portfolio: GET https://public-api.etoro.com/api/v1/trading/info/portfolio

TESTREIHENFOLGE
---------------
1. 01_SELFTEST_UI.bat
2. 04_TEST_ETORO_READONLY.bat
3. 11_TEST_REAL_EXECUTION_PREFLIGHT_NO_POST.bat
4. 13_RECONCILE_REAL_STATE.bat

Erst NACH diesen Tests und bewusster Freischaltung in C:\TradePilot\.env:
  TRADEPILOT_REAL_EXECUTION_ENABLED=YES

kann 12_MANUAL_REAL_BUY_10EUR.bat einen echten Trade senden. Dafür ist zusätzlich die exakte
Bestätigung LIVE BUY AAPL 10.00 erforderlich.

14_MANUAL_CLOSE_REAL_POSITION.bat schließt eine vom Broker aktuell bestätigte Position nur nach
Eingabe ihrer Position-ID und exakter Bestätigung LIVE CLOSE <positionId>.

15_REAL_EMERGENCY_STOP.bat setzt den lokalen Kill Switch. Er verhindert neue TradePilot REAL-
Ausführungen, schließt aber niemals automatisch bestehende Positionen.

REAL AUTOTRADING
----------------
Die Infrastruktur-Flag existiert, bleibt aber bewusst nicht an die Shadow-Signalquelle gekoppelt.
Die nächste fachliche Stufe ist die Integration der verifizierten Produktionsstrategie in die
Execution Engine. Testsignale dürfen niemals Echtgeld bewegen.
