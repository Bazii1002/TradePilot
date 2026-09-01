from pathlib import Path
root=Path(__file__).resolve().parent
qml=(root/'qml/Main.qml').read_text(encoding='utf-8')
bot=(root/'bot_engine.py').read_text(encoding='utf-8')
main=(root/'main.py').read_text(encoding='utf-8')
print('='*108)
print('TRADEPILOT 0.18.0 - OPERATIONS UI WIRING OFFLINE')
print('='*108)
for text in ['Bot Operations Center','ACTIONABLE','Entscheidung','BOT OPERATIONS LOG','REAL EXECUTION AUDIT · STATE ONLY','Trade History & Execution Audit']:
    assert text in qml, text
for text in ['restartRecoveryText','lastDecisionReasonText','actionableText','operationsStatusText','stop_price','take_price']:
    assert text in bot, text
for text in ['realAuditJson','lastReconcileText','operationsReadinessSummary','tradingModesText']:
    assert text in main, text
assert 'REAL AUTO LOCKED' in qml and 'SHADOW · REAL MANUAL · REAL AUTO LOCKED' in main
print('Bot Operations UI: OK')
print('Position Monitoring UI data: OK')
print('Trade History + Bot Log + REAL Audit: OK')
print('Broker Reconcile / Risk / REAL Readiness UI: OK')
print('Modes: SHADOW / REAL MANUAL / REAL AUTO LOCKED: OK')
print('STATUS: OPERATIONS UI WIRING OFFLINE OK')
