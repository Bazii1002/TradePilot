from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PortfolioHistoryStore:
    """Stores only non-identifying account totals for the local dashboard chart."""

    def __init__(self, app_dir: Path):
        self.dir = Path(app_dir) / "data"
        self.path = self.dir / "portfolio_history.json"
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
        except Exception:
            return []

    def append(self, equity: float | None, cash: float | None, invested: float | None) -> list[dict]:
        rows = self.load()
        if equity is None:
            return rows
        now = datetime.now(timezone.utc)
        point = {
            "time": now.isoformat(timespec="seconds"),
            "equity": round(float(equity), 6),
            "cash": None if cash is None else round(float(cash), 6),
            "invested": None if invested is None else round(float(invested), 6),
        }
        should_append = True
        if rows:
            try:
                last_time = datetime.fromisoformat(str(rows[-1].get("time", "")).replace("Z", "+00:00"))
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                age = (now - last_time.astimezone(timezone.utc)).total_seconds()
                same = float(rows[-1].get("equity")) == float(equity)
                if age < 300 and same:
                    should_append = False
                elif age < 60:
                    rows[-1] = point
                    should_append = False
            except Exception:
                pass
        if should_append:
            rows.append(point)
        if len(rows) > 2000:
            rows = rows[-2000:]
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return rows

    @staticmethod
    def normalized_points(rows: list[dict], limit: int = 80) -> list[float]:
        values = []
        for row in rows[-limit:]:
            try:
                values.append(float(row["equity"]))
            except Exception:
                continue
        if len(values) < 2:
            return []
        lo, hi = min(values), max(values)
        if hi - lo < 1e-9:
            return [0.5 for _ in values]
        pad = (hi - lo) * 0.08
        lo -= pad
        hi += pad
        return [(v - lo) / (hi - lo) for v in values]
