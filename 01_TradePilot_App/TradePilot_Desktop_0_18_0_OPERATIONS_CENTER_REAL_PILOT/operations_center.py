from __future__ import annotations

"""TradePilot 0.18.0 Operations Center read model.

Pure-Python aggregation layer for UI/diagnostics. It never calls a broker POST and
never enables REAL AUTO. It reads local persisted Shadow/REAL state and produces
safe monitoring/audit summaries.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REAL_AUTO_LOCKED = True

class OperationsCenter:
    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / 'data'

    @staticmethod
    def _read_json(path: Path, default):
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            return raw
        except Exception:
            return default

    def shadow_state(self) -> dict[str, Any]:
        raw = self._read_json(self.data_dir/'shadow_state.json', {})
        return raw if isinstance(raw, dict) else {}

    def real_state(self) -> dict[str, Any]:
        raw = self._read_json(self.data_dir/'production_real_state.json', {'state':'IDLE'})
        return raw if isinstance(raw, dict) else {'state':'LOCKED'}

    def real_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        path = self.data_dir/'production_real_audit.jsonl'
        if not path.exists():
            return []
        out=[]
        for line in path.read_text(encoding='utf-8').splitlines()[-limit:]:
            try: row=json.loads(line)
            except Exception: continue
            if not isinstance(row, dict): continue
            # Explicitly strip credential-like fields if ever present.
            out.append({k:v for k,v in row.items() if k.lower() not in {'api_key','user_key','private_key','public_key','headers','authorization'}})
        return list(reversed(out))

    def position_monitor(self) -> list[dict[str, Any]]:
        rows=[]
        for p in self.shadow_state().get('positions') or []:
            if not isinstance(p, dict): continue
            row=dict(p)
            try:
                entry=float(row.get('entry') or 0); now=float(row.get('price') or entry)
                row['pnl_pct']=round((now/entry-1)*100,2) if entry else 0.0
            except Exception: row['pnl_pct']=0.0
            row.setdefault('exit_status','HOLD')
            row.setdefault('macro_risk','—')
            row.setdefault('news_risk','—')
            rows.append(row)
        return rows

    def restart_recovery(self) -> dict[str, Any]:
        sh=self.shadow_state(); real=self.real_state(); rs=str(real.get('state') or 'IDLE')
        return {
            'shadow_was_running': bool(sh.get('was_running',False)),
            'shadow_action': 'RESUME_SHADOW' if sh.get('was_running') else 'READY',
            'real_state': rs,
            'real_auto': 'LOCKED',
            'real_fail_closed': rs in {'SUBMITTED','ACKNOWLEDGED','CLOSING','UNCERTAIN','LOCKED'},
            'post_retry': False,
        }

    def summary(self) -> dict[str, Any]:
        sh=self.shadow_state(); rec=self.restart_recovery()
        return {
            'bot_status': 'RUNNING' if sh.get('was_running') else 'STOPPED',
            'strategy_level': sh.get('level',2),
            'last_scan': sh.get('last_scan','—'),
            'last_scan_summary': sh.get('last_scan_summary','—'),
            'positions': len(sh.get('positions') or []),
            'trades': len(sh.get('trades') or []),
            'last_actionable': sh.get('last_actionable'),
            'last_decision_reason': sh.get('last_decision_reason','—'),
            'restart': rec,
            'real_auto_locked': REAL_AUTO_LOCKED,
            'generated_at': datetime.now().isoformat(timespec='seconds'),
        }
