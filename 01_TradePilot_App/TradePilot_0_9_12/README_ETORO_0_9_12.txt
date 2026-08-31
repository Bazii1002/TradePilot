TradePilot 0.9.12 - eToro REAL Safety Integration

Scope
- Connect to the eToro REAL portfolio using local API key + REAL user key.
- Manual LIVE BUY only.
- Hard budget limit: EUR 10.00 per order.
- EUR budget is converted to USD using a fresh Yahoo EURUSD=X quote; if FX is unavailable, order is refused.
- Leverage fixed at 1; no shorting in this connector.
- A new live test buy is refused if the REAL portfolio already has an open position.
- Two-step confirmation, including typing LIVE.
- AutoTrader -> eToro REAL execution is intentionally NOT connected in 0.9.12.
- Credentials stored in local .env and must never be committed.

Official eToro paths used
- Real portfolio: GET /api/v1/trading/info/portfolio
- Real order: POST /api/v2/trading/execution/orders
- Instrument search: GET /api/v1/market-data/search

Important
A EUR 10 budget may be below eToro's minimum order size for a particular instrument/account. TradePilot never raises the amount automatically; eToro's rejection is shown instead.
