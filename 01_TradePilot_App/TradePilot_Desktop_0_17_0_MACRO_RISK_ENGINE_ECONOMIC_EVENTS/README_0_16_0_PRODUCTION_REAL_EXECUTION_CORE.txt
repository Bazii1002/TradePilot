TRADEPILOT 0.16.0 - PRODUCTION REAL EXECUTION CORE
=================================================

Dieser Build bündelt die geplanten Entwicklungsblöcke 0.16.0 bis 0.16.4:
- persistente REAL Execution State Machine
- Operation-/Request-ID und Duplicate-Schutz
- Crash/Restart/Timeout-Recovery ohne POST-Retry
- REAL Exit Engine auf Basis der bestehenden Production Strategy Exit-Regeln
- REAL Risk Manager
- bevorzugter Echtgeld-Testbetrag EUR 1.00
- KEINE automatische Erhöhung auf ein Broker-Mindestvolumen
- Kill Switch / Uncertain Lock fail-closed
- Audit-Log unter data/production_real_audit.jsonl

WICHTIG:
REAL AUTOTRADING bleibt in 0.16.0 standardmäßig AUS und wird durch diesen Build nicht autonom freigeschaltet.
Der Build stellt den abgesicherten Unterbau für einen späteren REAL-AUTO-Pilot bereit.

Neue Tests:
40_TEST_PRODUCTION_REAL_CORE_OFFLINE.bat
41_TEST_RECOVERY_MATRIX_OFFLINE.bat
42_TEST_REAL_EXIT_ENGINE_OFFLINE.bat
43_TEST_RISK_MANAGER_OFFLINE.bat
44_TEST_1EUR_REAL_PREFLIGHT_NO_POST.bat   (GET/READ-ONLY, kein POST)
45_SHOW_PRODUCTION_REAL_STATE.bat

Empfohlene Reihenfolge:
1) 01_SELFTEST_UI.bat
2) 40...
3) 41...
4) 42...
5) 43...
6) 44... erst mit lokalen eToro-Keys

TradePilot darf bei unbekanntem Orderstatus niemals automatisch denselben POST wiederholen.
