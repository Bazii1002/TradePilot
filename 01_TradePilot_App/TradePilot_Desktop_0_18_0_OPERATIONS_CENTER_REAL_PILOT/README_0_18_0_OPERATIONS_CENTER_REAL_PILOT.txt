TradePilot 0.18.0 – Operations Center & REAL Pilot
===================================================

Dieser Build bündelt die bestehenden Scanner-, Strategie-, Macro-, Risk- und REAL-Safety-Komponenten in einen sichtbaren Operations-Betrieb der Desktop-App.

Neu in 0.18.0
- Bot Operations Center: RUNNING/STOPPED/SCANNING, letzter und nächster Scan, Scan-Zusammenfassung.
- Letztes ACTIONABLE-Signal und letzte Bot-Entscheidung sichtbar.
- Shadow Position Monitoring mit Entry, Current, P/L, Stop, Take Profit, Strategie, Score, Quality, Macro/News und Exit-Status.
- Trade History erweitert um Score/Quality/Macro-Kontext.
- Bot Operations Log direkt auf der Trades-Seite.
- REAL Execution Audit zeigt ausschließlich State-Transitions; Credential-Felder werden nicht dargestellt.
- Broker-Reconcile-Zeitpunkt und REAL Readiness im UI.
- Persistenter Shadow-State inkl. safe resume intent nach App-Neustart.
- REAL Execution State bleibt persistent; automatische POST-Retries bleiben verboten.
- Modi sichtbar: SHADOW / REAL MANUAL / REAL AUTO LOCKED.

Wichtige Safety-Regeln
- REAL AUTO bleibt LOCKED/OFF.
- REAL Pilot-Limit bleibt USD 10.00.
- Leverage 1x, BUY only, max. 1 REAL-Position, max. 3 neue REAL-Trades/Tag.
- Broker-Mindestbetrag wird nie automatisch angehoben.
- Macro-Fail-Closed bleibt aktiv.
- Dieser Build aktiviert keine unbeaufsichtigten Echtgeld-POSTs.

Empfohlene Tests
01_SELFTEST_UI.bat
67_TEST_OPERATIONS_CENTER_OFFLINE.bat
68_TEST_POSITION_MONITORING_OFFLINE.bat
69_TEST_AUDIT_AND_REAL_LOCK_OFFLINE.bat
70_TEST_RESTART_PERSISTENCE_OFFLINE.bat
71_TEST_OPERATIONS_UI_WIRING_OFFLINE.bat

Danach die App normal über 00_START_TRADEPILOT_DESKTOP.bat bzw. die installierte Desktop-Verknüpfung starten.
