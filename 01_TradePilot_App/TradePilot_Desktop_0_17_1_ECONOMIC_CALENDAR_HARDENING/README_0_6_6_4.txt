TradePilot 1.0 UI Prototype 0.6.6.4 - Manual REAL Order Preparation

Basis: getestetes 0.6.6.3 Instrument Lookup (AAPL -> exakter Treffer).

Neu:
- Zentrale Secret-Datei C:\TradePilot\.env als versionsunabhängiger Fallback.
- Lokale .env bleibt aus Kompatibilitätsgründen lesbar.
- 07_MIGRATE_ENV_TO_CENTRAL.bat kopiert eine vorhandene befüllte .env, ohne Schlüssel anzuzeigen.
- 03_SETUP_ETORO_KEYS.bat schreibt neue Keys künftig zentral nach C:\TradePilot\.env.
- 08_TEST_MANUAL_REAL_ORDER_PREPARATION.bat führt einen NO-POST-Test aus:
  Portfolio lesen -> AAPL exakt auflösen -> EUR/USD laden -> 10 EUR in USD berechnen -> Review anzeigen.

Sicherheit unverändert:
- max. 10,00 EUR
- BUY only
- Hebel 1x
- max. 1 offene REAL-Position in der manuellen Testphase
- keine automatische Mindestorder-Erhöhung
- AutoTrader -> REAL gesperrt
- Instrument-ID niemals raten/hardcoden

WICHTIG: 08_TEST_MANUAL_REAL_ORDER_PREPARATION.bat sendet KEINE Order.
