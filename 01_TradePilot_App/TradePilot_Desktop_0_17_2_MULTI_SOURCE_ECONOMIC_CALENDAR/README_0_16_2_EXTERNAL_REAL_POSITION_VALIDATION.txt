TradePilot 0.16.2 - External REAL Position Validation
=====================================================

Ziel:
Eine vom Nutzer selbst direkt bei eToro eröffnete REAL-Position wird von TradePilot READ-ONLY erkannt und beobachtet.
TradePilot eröffnet oder schließt in diesem Build KEINE externe Position automatisch.

Neue Tests:
49_TEST_EXTERNAL_REAL_POSITION_OBSERVER_NO_POST.bat
  - echter Broker GET
  - Position-ID / Instrument-ID / Symbol anzeigen
  - Production Execution State bleibt unverändert
  - POST Calls = 0

50_TEST_EXTERNAL_POSITION_RESTART_RECOVERY_NO_POST.bat
  - simuliert App-Neustart durch neue Observer-Instanz
  - vergleicht Broker-Position-IDs
  - kein Auto-Retry / kein POST

51_TEST_EXTERNAL_POSITION_EXIT_PREVIEW_OFFLINE.bat
  - testet nur die Brücke zur bestehenden Exit Engine mit Fixture
  - kein erfundener Live-Kurs
  - kein automatischer CLOSE

52_SHOW_EXTERNAL_POSITION_VALIDATION.bat
  - zeigt die letzte gespeicherte Read-only-Beobachtung

Sicherheitsregel:
EXTERNAL = OBSERVE ONLY. Eine externe Brokerposition wird NICHT stillschweigend als TradePilot-Position adoptiert.
REAL AUTO bleibt LOCKED/OFF.
