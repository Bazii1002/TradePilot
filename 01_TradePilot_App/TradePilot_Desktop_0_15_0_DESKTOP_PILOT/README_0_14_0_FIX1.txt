TradePilot Desktop Alpha 0.14.0 FIX1
========================================

Fix: SELFTEST_UI.py was still checking obsolete 0.12.1 strings that required all REAL POST code to be absent/hard-disabled.
0.14.0 intentionally contains the manual REAL roundtrip transport, therefore the correct safety assertions now verify:
- REAL execution is default LOCKED unless TRADEPILOT_REAL_EXECUTION_ENABLED is explicitly enabled
- REAL AutoTrading stays hard LOCKED
- ARM window is required and limited to 10 minutes
- exact BUY/CLOSE confirmation strings are present
- strategy/bot engine still contains no REAL POST

No trading logic, scanner logic, strategy logic, QML layout, credentials, or broker endpoints were changed in FIX1.
