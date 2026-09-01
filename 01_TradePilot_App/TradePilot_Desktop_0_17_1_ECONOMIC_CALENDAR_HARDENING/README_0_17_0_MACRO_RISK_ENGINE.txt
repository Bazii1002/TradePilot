TradePilot 0.17.0 - Macro Risk Engine + Economic Events

Builds on 0.16.3 without redesigning the production strategy.

NEW
- Economic calendar based on the existing TradePilot/xoomar calendar foundation
- LOW / MEDIUM / HIGH / CRITICAL event relevance normalization
- Forecast / Previous / Actual parsing
- Economic Surprise with event-specific higher-is-risk-on/off semantics
- Market reaction: Nasdaq, S&P 500, VIX, US10Y, Oil
- RISK-ON / NEUTRAL / RISK-OFF macro regime
- 30-minute CRITICAL event new-trade pause
- HIGH event position-size reduction
- Existing positions are monitored; no macro panic close
- Fail-closed: missing/uncertain data never makes trading more aggressive
- News page now includes "Anstehende Veranstaltungen" with countdown and bot impact
- Bot page shows Macro Gate

SAFETY
REAL execution POST logic is unchanged. REAL AUTO remains locked/off.

TESTS
55_TEST_MACRO_RISK_ENGINE_OFFLINE.bat
56_TEST_MARKET_REACTION_ENGINE_OFFLINE.bat
57_TEST_MACRO_BOT_GATE_OFFLINE.bat
58_TEST_MACRO_LIVE_READONLY.bat
