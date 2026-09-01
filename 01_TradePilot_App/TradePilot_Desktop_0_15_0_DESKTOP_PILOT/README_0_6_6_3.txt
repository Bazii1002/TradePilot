TradePilot 1.0 UI Prototype 0.6.6.3 - Instrument Directory Fallback

Ziel
----
Der eToro REAL Portfolio-Zugriff funktioniert, aber GET /market-data/search liefert bei dem getesteten Live-Key reproduzierbar HTTP 400 ohne Body.
0.6.6.3 rät deshalb keine Instrument-ID und sendet ohne eindeutige ID keine Order.

Resolver-Kette
--------------
1. Lokaler instrument_cache.json (nur bereits sicher aufgelöste IDs)
2. Offizieller GET /api/v1/market-data/search?internalSymbolFull=...
3. READ-ONLY Fallback: GET /api/v1/watchlists/default-watchlists/items
   - liefert vertrauenswürdige Instrument-IDs aus der eigenen Standard-Watchlist
4. Metadaten-Verifikation: GET /api/v1/market-data/instruments?instrumentIds=...
   - symbolFull/internalSymbolFull muss exakt dem angefragten Ticker entsprechen
   - erst danach wird die ID lokal gecacht

Wenn AAPL nicht in der Standard-Watchlist liegt, blockiert TradePilot und bittet darum, AAPL manuell in der eToro-App zur Standard-Watchlist hinzuzufügen. TradePilot verändert Watchlists nicht automatisch.

Sicherheit
----------
- Öffentlicher Key = API Key = x-api-key
- Privater Key = User-Key = x-user-key
- Maximal 10 EUR pro LIVE-Order
- BUY only, Hebel 1x
- Maximal eine offene REAL-Position in dieser Testphase
- AutoTrader -> REAL bleibt gesperrt
- Instrument-Lookup-Test ist GET-only
- instrument_cache.json enthält nur Ticker/Instrument-ID/Name/Quelle/Zeit, keine Keys oder Account-ID
