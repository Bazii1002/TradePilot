from pathlib import Path
from real_execution import RealExecutionManager, _position_id, _instrument_id
APP=Path(__file__).resolve().parent
m=RealExecutionManager(APP)
print('='*100)
print('TRADEPILOT 0.12.0 - MANUAL REAL POSITION CLOSE')
print('='*100)
print('ACHTUNG: Dieses Werkzeug kann eine ECHTE REAL-Position vollständig schließen.\n')
try:
    rows=m.position_rows()
    if not rows:
        print('Keine offenen REAL-Positionen gefunden. Keine Aktion.')
        raise SystemExit(0)
    print('Offene Positionen:')
    for i,r in enumerate(rows,1):
        print(f"[{i}] Position-ID={_position_id(r) or '?'} · Instrument-ID={_instrument_id(r) or '?'}")
    pid=input('\nPosition-ID zum vollständigen Schließen eingeben (Enter = Abbruch): ').strip()
    if not pid:
        print('ABGEBROCHEN. Keine Order gesendet.')
        raise SystemExit(0)
    phrase=f'LIVE CLOSE {pid}'
    c=input(f"Zur echten Schließung exakt eingeben: {phrase}\n> ")
    r=m.close_position(pid,c)
    print(f"\nCLOSE BESTÄTIGT · Position-ID {r['position_id']}")
except SystemExit:
    pass
except Exception as exc:
    print(f'\nBLOCKIERT/FEHLER: {exc}')
