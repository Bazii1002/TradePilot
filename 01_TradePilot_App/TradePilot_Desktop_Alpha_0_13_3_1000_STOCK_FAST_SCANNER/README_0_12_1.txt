TRADEPILOT DESKTOP ALPHA 0.12.1 - REAL ROUNDTRIP VALIDATION
===========================================================

ZWECK
-----
Dieser Build validiert den vollständigen Order-Lebenszyklus BUY -> Broker-State -> lokaler State
-> Reconcile -> CLOSE -> finaler Reconcile, ohne eine Finanztransaktion auszuführen.

SICHERHEITSGRENZE
-----------------
Alle state-changing REAL Broker-POSTs sind in 0.12.1 hart deaktiviert.
12_MANUAL_REAL_BUY_10EUR und 14_MANUAL_CLOSE_REAL_POSITION sind deshalb absichtlich gesperrt.
Der bestehende Shadow-/Paper-Bot bleibt weiterhin vom REAL-Transport getrennt.

WAS TEST 17 MACHT
-----------------
1. Liest das REAL-Portfolio per GET für das Preflight-Gate.
2. Löst AAPL und den aktuellen EUR/USD-Wert mit der bestehenden getesteten Logik auf.
3. Baut die BUY-Payload nur als Vorschau.
4. Simuliert die Broker-Bestätigung inklusive Position-ID im Arbeitsspeicher.
5. Prüft Broker-State gegen lokalen Position-State.
6. Baut eine vollständige CLOSE-Vorschau.
7. Simuliert das Schließen.
8. Prüft, dass Broker- und lokaler State danach beide leer sind.
9. Schreibt den Validierungsreport nach data/roundtrip_validation_last.json.

TESTREIHENFOLGE
---------------
1. 01_SELFTEST_UI.bat
2. 04_TEST_ETORO_READONLY.bat
3. 11_TEST_REAL_EXECUTION_PREFLIGHT_NO_POST.bat
4. 13_RECONCILE_REAL_STATE.bat
5. 17_TEST_REAL_ROUNDTRIP_VALIDATION_NO_POST.bat

REAL AUTOTRADING
----------------
FAST/DAY/WEEK/INVEST laufen weiterhin als Shadow-Stresstest. Die Testsignale sind nicht an eine
state-changing Broker-Schnittstelle gekoppelt.
