TradePilot Desktop Alpha 0.14.0 - REAL ROUNDTRIP VALIDATION

Ziel: kontrollierter manueller REAL BUY -> Broker Verify -> CLOSE -> Verify.

SICHERHEIT
- REAL AutoTrading bleibt hart gesperrt.
- Standardmäßig ist TRADEPILOT_REAL_EXECUTION_ENABLED nicht aktiv.
- Maximal 10 EUR pro REAL-Trade.
- Maximal 1 offene REAL-Position.
- BUY only / Leverage 1x.
- Kein automatischer Retry eines state-changing POST.
- Timeout/unklare Antwort => UNCERTAIN LOCK.
- Jeder Live-Schritt braucht ARM + exakte lokale Texteingabe.
- Keine Order beim App-Start oder Scannerlauf.

TESTREIHENFOLGE
01_SELFTEST_UI.bat
25_TEST_REAL_SAFETY_GATES_OFFLINE.bat
24_TEST_REAL_PREFLIGHT_NO_POST.bat
17_TEST_REAL_ROUNDTRIP_VALIDATION_NO_POST.bat
29_REAL_RECONCILE_NO_POST.bat

ERST DANACH und nur bewusst: TRADEPILOT_REAL_EXECUTION_ENABLED=YES in zentraler C:\TradePilot\.env setzen.
26_ARM_REAL_BUY_10EUR.bat
27_MANUAL_REAL_BUY_10EUR.bat
28_ARM_AND_CLOSE_REAL_POSITION.bat

Die aktuellen offiziellen eToro Builders-Unterlagen (Sep 2026) nennen v2 /trading/execution/orders für REAL Execution; Portfolio Reads bleiben v1.
