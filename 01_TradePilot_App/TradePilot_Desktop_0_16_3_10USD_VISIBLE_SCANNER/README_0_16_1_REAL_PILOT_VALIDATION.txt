TRADEPILOT 0.16.1 - REAL PILOT VALIDATION

Ziel:
- 0.16.0 Production REAL Core mit sichtbarer REAL Readiness in der Desktop-App verbinden.
- Keine unbeaufsichtigten REAL Orders aktivieren.
- Pilotbetrag weiterhin EUR 1.00, keine automatische Erhoehung.

Neu:
- REAL Pilot Readiness Panel im Bot-Bereich.
- Broker Connection, Execution State, Position Limit, Trades Today, Pilot Amount.
- Kill Switch / Uncertain-Lock fail-closed in Readiness.
- REAL AUTO bleibt LOCKED.
- 0.16.1 End-to-End Pilot Validation Tests 46-48.

Tests:
01_SELFTEST_UI.bat
46_TEST_REAL_PILOT_READINESS_OFFLINE.bat
47_TEST_REAL_PILOT_HANDOFF_1EUR_NO_POST.bat
48_TEST_REAL_PILOT_BROKER_READINESS_NO_POST.bat
