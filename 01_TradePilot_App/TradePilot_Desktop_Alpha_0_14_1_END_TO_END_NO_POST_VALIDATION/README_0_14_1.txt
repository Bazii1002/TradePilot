TradePilot Desktop Alpha 0.14.1 - END-TO-END NO POST VALIDATION

Ziel:
- kompletter Pfad vom ~1000-Aktien-Scanner bis unmittelbar vor REAL Execution
- echtes ACTIONABLE-Signal -> Broker READ/Portfolio -> REAL Preflight -> ARM/Payload Preview
- KEIN persistentes ARM in Test 31
- KEIN REAL BUY/CLOSE POST; POST ist im Test technisch abgefangen
- REAL AutoTrading bleibt LOCKED

Neue Tests:
30_TEST_END_TO_END_NO_POST_OFFLINE.bat
31_TEST_ACTIONABLE_TO_REAL_PREFLIGHT_NO_POST.bat

Test 31 kann echte GET/READ-ONLY API-Aufrufe und echte Marktdaten verwenden.
Er sendet keine Order. Wenn kein ACTIONABLE Signal vorliegt oder ein Safety Gate blockiert, stoppt er fail-closed.

Production Strategy Engine, Scanner-Ranking und REAL Execution Safety-Regeln wurden inhaltlich nicht verändert; 0.14.1 ergänzt die End-to-End-Validierung und sichtbare Versionskennung.
