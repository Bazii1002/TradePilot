TradePilot 1.0 UI Prototype 0.6.6.2

Key naming (frozen):
- eToro Öffentlicher Key = API Key = HTTP x-api-key
- eToro Privater Key = User-Key = HTTP x-user-key

Instrument lookup fix:
GET /api/v1/market-data/search?internalSymbolFull=AAPL
The API portal guide documents internalSymbolFull for exact ticker resolution.

Safety:
- Manual REAL BUY only
- hard max 10 EUR
- leverage 1
- max one open REAL position during test
- AutoTrader remains locked
