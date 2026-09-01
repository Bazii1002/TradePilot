TradePilot Desktop Alpha 0.11.0 - Integrated Bot Stress Test
===========================================================

Ziel dieses Builds
------------------
Eine zusammenhaengende Desktop-App, waehrend die Bot Engine parallel im Hintergrund laeuft.

Enthalten
---------
- festgelegte TradePilot Dark-Mode Designsprache, optional Light Mode in Settings
- Sidebar: Dashboard, Bot, Portfolio, Markets, News, Backtest, Trades, Settings
- separate BotEngine im Hintergrund
- Stufe 1 FAST
- Stufe 2 DAY
- Stufe 3 WEEK
- Stufe 4 INVEST
- jede Shadow-Position behaelt ihre Strategie beim Oeffnen
- START/STOP, manueller Scan, Status, Scanner, Positionen, Trade-Historie, Engine Log
- persistenter Shadow-State unter data/shadow_state.json
- eToro Portfolio bleibt REAL READ ONLY
- zentrale C:\TradePilot\.env wird weiter verwendet

SICHERHEIT
----------
Dieser Build fuehrt KEINE automatischen Echtgeld-Orders aus.
Der Stresstest handelt ausschliesslich SHADOW/PAPER.
Die bestehende Manual-REAL-Readiness aus 0.6.6.6 bleibt im Paket, der POST ist dort weiterhin deaktiviert.

Start
-----
1) 01_SELFTEST_UI.bat
2) 00_START_TRADEPILOT_ALPHA.bat
3) In der App auf Bot wechseln, FAST/DAY/WEEK/INVEST waehlen und START BOT klicken.

Der Bot darf waehrend der UI-Nutzung weiterlaufen. Ein Seitenwechsel stoppt die Engine nicht.
