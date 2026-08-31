from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AutoTraderLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, event: str, symbol: str = "—", **payload) -> None:
        rec = {"time": _now(), "event": event, "symbol": str(symbol or "—").upper(), **payload}
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def recent(self, limit: int = 100) -> list[dict]:
        try:
            if not self.path.exists():
                return []
            lines = self.path.read_text(encoding="utf-8").splitlines()[-max(1, int(limit)):]
            out = []
            for line in lines:
                try:
                    x = json.loads(line)
                    if isinstance(x, dict):
                        out.append(x)
                except Exception:
                    pass
            return out
        except Exception:
            return []
