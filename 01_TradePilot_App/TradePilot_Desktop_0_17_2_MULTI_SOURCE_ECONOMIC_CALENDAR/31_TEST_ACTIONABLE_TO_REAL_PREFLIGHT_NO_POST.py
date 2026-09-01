from __future__ import annotations
from pathlib import Path
import json

from universe_provider import StockUniverseProvider
from fast_scanner import ThousandStockFastScanner
from strategy_engine import StrategyAnalyzer
from real_execution import RealExecutionManager, RealExecutionError
from real_signal_handoff import save_handoff, clear_handoff

app=Path(__file__).resolve().parent
clear_handoff(app)  # alte/stale Übergabe vor jedem frischen Test löschen
print('='*116)
print('TRADEPILOT 0.14.1 - LIVE END-TO-END ACTIONABLE -> REAL PREFLIGHT (HARD NO POST)')
print('='*116)
print('Dieser Test darf GET/READ-ONLY verwenden. REAL BUY/CLOSE POST ist im Test technisch abgefangen.')

# 1) Real 1000-stock universe and live market scan.
provider=StockUniverseProvider(app)
universe=provider.load(allow_refresh=True)
symbols=[r['symbol'] for r in universe][:1000]
print(f'Universe: {len(symbols)} | Quelle: {provider.last_source}')
if len(symbols)<900:
    print('ABBRUCH: Kein ~1000-Aktien-Universe verfügbar. Zuerst Test 20 ausführen.')
    raise SystemExit(2)

scanner=ThousandStockFastScanner(app, StrategyAnalyzer())
rows,metrics=scanner.scan(2, symbols, held_symbols=(), force_full=True)
actionable=sorted(
    [r for r in rows if r.get('is_actionable')],
    key=lambda r:(float(r.get('quality_score') or 0),float(r.get('score') or 0)),
    reverse=True,
)
print(f"Scanned:       {metrics['scanned']} / {metrics['universe']}")
print(f"Candidates:    {metrics['candidates']}")
print(f"Deep:          {metrics['deep']}")
print(f"Finalists:     {metrics['finalists']}")
print(f"ACTIONABLE:    {metrics.get('actionable',0)}")
print(f"Errors:        {metrics['errors']}")
print(f"Duration:      {metrics['duration']:.1f}s")

if not actionable:
    print('\nSAFE STOP: Dieser Scan hat kein ACTIONABLE-Signal erzeugt.')
    print('Ohne ACTIONABLE gibt es absichtlich keinen REAL-Preflight und keine ARM-Vorschau.')
    print('Broker POST: 0')
    print('STATUS: END-TO-END SAFE STOP OK')
    raise SystemExit(0)

chosen=actionable[0]
symbol=str(chosen['symbol']).upper()
print('\nACTIONABLE HANDOFF')
print(f"Symbol:         {symbol}")
print(f"Strategy Score: {float(chosen.get('score') or 0):.1f}")
print(f"Quality Score:  {float(chosen.get('quality_score') or 0):.1f} (Bestätigungsgrad, keine Gewinnwahrscheinlichkeit)")
print(f"Confirmations:  {chosen.get('quality_confirmations',0)}/{chosen.get('quality_checks',5)}")

# 2) Broker manager, but POST is replaced by a hard trap BEFORE any operation.
manager=RealExecutionManager(app)
post_calls={'count':0}
def FORBIDDEN_POST(*args,**kwargs):
    post_calls['count'] += 1
    raise AssertionError('SAFETY FAILURE: POST wurde in einem NO-POST-Test aufgerufen.')
manager.session.post=FORBIDDEN_POST
# Also guard the manual broker session in case its implementation changes later.
try:
    manager.manual.session.post=FORBIDDEN_POST
except Exception:
    pass

# Snapshot ARM file to prove this test does not arm REAL execution persistently.
arm_path=manager.arm_file
arm_before=arm_path.read_bytes() if arm_path.exists() else None

# 3) Read-only safety status + portfolio reconciliation.
status=manager.safety_status()
print('\nREAL SAFETY / READ-ONLY')
print(f"Broker GET:              {'OK' if status.get('broker_ok') else 'FEHLER'}")
print(f"REAL Execution enabled:  {status.get('execution_enabled')} (darf für diesen Test False sein)")
print(f"REAL AutoTrading:        {status.get('auto_enabled')} (muss False sein)")
print(f"Open REAL positions:     {status.get('open_positions')}")
print(f"Kill Switch:             {status.get('kill_switch')}")
print(f"Uncertain Lock:          {status.get('uncertain_lock')}")
if not status.get('broker_ok'):
    print('ABBRUCH SAFE: Broker-READ fehlgeschlagen. Kein Preflight.')
    print(f"Fehler: {status.get('error','')}")
    print(f"Broker POST Calls: {post_calls['count']}")
    raise SystemExit(3)
if status.get('kill_switch') or status.get('uncertain_lock'):
    print('ABBRUCH SAFE: Kill Switch oder Uncertain Lock aktiv. Kein Preflight.')
    print(f"Broker POST Calls: {post_calls['count']}")
    raise SystemExit(4)

recon=manager.reconcile(clear_uncertain_if_safe=False)
print(f"Reconcile broker positions: {recon.get('broker_positions')}")
print(f"Orphan broker:              {recon.get('orphan_broker')}")
print(f"Stale local:                {recon.get('stale_local')}")

# 4) REAL preflight for the actual ACTIONABLE signal. This performs read-only broker/instrument work only.
try:
    prepared=manager.preflight_buy(symbol,10.00,'DAY')
except RealExecutionError as exc:
    print('\nSAFE BLOCK: REAL Preflight hat den Trade blockiert.')
    print(str(exc))
    print(f"Broker POST Calls: {post_calls['count']}")
    if post_calls['count'] != 0:
        raise AssertionError('NO-POST invariant verletzt')
    raise SystemExit(5)

# 5) In-memory ARM + exact confirmation + payload preview. Do NOT call arm_buy/execute_buy.
confirmation=f"EXECUTE REAL BUY {prepared['symbol']} {float(prepared['budget_eur']):.2f} EUR"
payload={
    'action':'open',
    'transaction':'buy',
    'instrumentId':int(prepared['instrument_id']),
    'orderType':'mkt',
    'amount':float(prepared['amount_usd']),
    'orderCurrency':'usd',
    'leverage':1,
}
arm_preview={
    'kind':'BUY', 'persistent':False, 'ttl_seconds':600,
    'symbol':prepared['symbol'], 'instrument_id':int(prepared['instrument_id']),
    'budget_eur':float(prepared['budget_eur']), 'amount_usd':float(prepared['amount_usd']),
}

assert float(prepared['budget_eur']) <= 10.0
assert payload['leverage']==1
assert payload['transaction']=='buy' and payload['action']=='open'
assert status.get('auto_enabled') is False
assert post_calls['count']==0
arm_after=arm_path.read_bytes() if arm_path.exists() else None
assert arm_after==arm_before, 'NO-POST Test darf REAL ARM-State nicht verändern.'
handoff=save_handoff(app,prepared,chosen)

print('\nREAL PREFLIGHT - NO POST')
print(f"Symbol:                  {prepared['symbol']}")
print(f"Instrument-ID:           {prepared['instrument_id']}")
print(f"Budget:                  {float(prepared['budget_eur']):.2f} EUR")
print(f"Order amount:            {float(prepared['amount_usd']):.2f} USD")
print('Leverage:                1x')
print(f"ARM Preview:             {json.dumps(arm_preview,ensure_ascii=False)}")
print(f"Exact confirmation:      {confirmation}")
print(f"Payload Preview:         {json.dumps(payload,ensure_ascii=False)}")
print(f"Persistent ARM geändert: NEIN")
print(f"Validated Handoff:        {handoff['symbol']} / ID {handoff['instrument_id']} / max. 5 min gültig")
print(f"Broker POST Calls:       {post_calls['count']}")
print('REAL BUY ausgeführt:     NEIN')
print('REAL CLOSE ausgeführt:   NEIN')
print('\nSTATUS: LIVE END-TO-END ACTIONABLE -> REAL PREFLIGHT NO POST OK')
