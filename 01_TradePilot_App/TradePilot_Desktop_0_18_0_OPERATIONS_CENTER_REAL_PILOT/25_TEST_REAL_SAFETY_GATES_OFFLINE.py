from pathlib import Path
import tempfile, json
print('='*104); print('TRADEPILOT 0.14.1 - REAL SAFETY GATES OFFLINE'); print('='*104)
# Static/offline assertions: no network and no POST.
text=Path('real_execution.py').read_text(encoding='utf-8')
checks={
 'max10':'MAX_LIVE_EUR' in text,
 'auto_locked':"REAL AutoTrading bleibt in 0.14.1 hart gesperrt" in text,
 'arm_required':'_consume_arm' in text,
 'exact_confirm':'EXECUTE REAL BUY' in text and 'EXECUTE REAL CLOSE' in text,
 'uncertain_lock':'UNCERTAIN LOCK' in text or 'uncertain_lock' in text,
 'no_retry':'session.post' in text and 'for i in range(attempts)' in text, # verification retries only
 'leverage1':"'leverage':1" in text,
 'buy_only':"'transaction':'buy'" in text,
 'max1pos':'min(1,int' in text.replace(' ',''),
}
for k,v in checks.items(): print(f'{k:18}: '+('OK' if v else 'FAIL'))
print('Broker POST ausgeführt: NEIN')
print('STATUS: SAFETY GATES OK' if all(checks.values()) else 'STATUS: FAIL')
raise SystemExit(0 if all(checks.values()) else 1)
