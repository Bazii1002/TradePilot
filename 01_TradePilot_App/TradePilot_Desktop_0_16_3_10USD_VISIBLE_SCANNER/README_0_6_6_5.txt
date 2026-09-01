TradePilot 1.0 UI Prototype 0.6.6.5 - Manual REAL Execution Gate

Neu gegenüber 0.6.6.4:
- Die Eingabe LIVE löst vor einem möglichen POST einen zweiten, frischen Sicherheitscheck aus.
- Portfolio/offene Positionen werden erneut gelesen.
- AAPL/Symbol <-> Instrument-ID wird ohne lokalen Cache erneut offiziell verifiziert.
- EUR/USD wird frisch geladen. Ändert sich dadurch der gerundete USD-Orderbetrag, wird blockiert und eine neue Review verlangt.
- Review läuft nach 120 Sekunden ab und ist single-use.
- Hardlimit 10 EUR, BUY only, Hebel 1x, max. eine REAL-Position bleiben unverändert.
- Kein automatischer Retry eines Execution-POST.
- AutoTrader -> REAL bleibt gesperrt.

TESTABLAUF:
1) 01_SELFTEST_UI.bat
2) 08_TEST_MANUAL_REAL_ORDER_PREPARATION.bat
3) 09_TEST_FINAL_EXECUTION_GATE_NO_POST.bat

09 ist ausdrücklich NO POST und sendet keine Order.
