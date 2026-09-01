TradePilot 0.17.2 - Multi-Source Economic Calendar
==================================================

Purpose
- Preserve the 0.17.0/0.17.1 Macro Risk Engine.
- Improve calendar data quality without changing REAL execution.

Provider chain (GET/read-only)
1. Existing TradePilot/Xoomar calendar feed.
2. Optional Trading Economics REST calendar when TRADEPILOT_TRADING_ECONOMICS_KEY is configured.
3. Optional custom JSON feeds through TRADEPILOT_ECONOMIC_CALENDAR_URLS.

Merge behavior
- Events are normalized and deduplicated by country + normalized event name + release minute.
- Missing country/Forecast/Previous/Actual/unit fields are enriched field-by-field.
- Actual is preferred as soon as any provider reports it.
- Source provenance is retained per event/field.

Safety
- No broker POST is introduced or modified.
- Missing Actual after a HIGH/CRITICAL release is RELEASE DATA PENDING and blocks new trades.
- Missing/conflicting/stale data never creates Risk-On or increases position size.
- Existing positions remain monitored; no macro panic close path exists.

Optional Trading Economics setup
Set TRADEPILOT_TRADING_ECONOMICS_KEY in C:\TradePilot\.env or your secure local environment.
Do not paste credentials into chats and do not include them in ZIPs.

Tests
63_TEST_MULTI_SOURCE_CALENDAR_MERGE_OFFLINE.bat
64_TEST_RELEASE_PENDING_FAIL_CLOSED_OFFLINE.bat
65_SHOW_CALENDAR_PROVIDER_STATUS.bat
66_TEST_TRADINGECONOMICS_ADAPTER_OFFLINE.bat
