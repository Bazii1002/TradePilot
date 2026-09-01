from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PortfolioHistoryStore:
    """Stores only non-identifying account totals for the local dashboard chart.

    0.6.5 records one snapshot per minute while TradePilot is running. No account
    id, API key, user key, ticker or order payload is written here.
    """

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

    def append(
        self,
        equity: float | None,
        cash: float | None,
        invested: float | None,
        open_pnl: float | None = None,
        today_pnl: float | None = None,
        position_count: int | None = None,
    ) -> list[dict]:
        rows = self.load()
        if equity is None:
            return rows
        now = datetime.now(timezone.utc)
        point = {
            "time": now.isoformat(timespec="seconds"),
            "equity": round(float(equity), 6),
            "cash": None if cash is None else round(float(cash), 6),
            "invested": None if invested is None else round(float(invested), 6),
            "open_pnl": None if open_pnl is None else round(float(open_pnl), 6),
            "today_pnl": None if today_pnl is None else round(float(today_pnl), 6),
            "position_count": None if position_count is None else int(position_count),
        }

        # At most one point per minute. A refresh in the same minute updates the
        # existing point, so temporary retries do not inflate the chart history.
        if rows:
            try:
                last_time = datetime.fromisoformat(str(rows[-1].get("time", "")).replace("Z", "+00:00"))
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                age = (now - last_time.astimezone(timezone.utc)).total_seconds()
                if age < 60:
                    rows[-1] = point
                else:
                    rows.append(point)
            except Exception:
                rows.append(point)
        else:
            rows.append(point)

        # Roughly 30 days at one-minute cadence if the app stayed online 24/7.
        if len(rows) > 43_200:
            rows = rows[-43_200:]
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return rows

    @staticmethod
    def normalized_points(rows: list[dict], limit: int = 120) -> list[float]:
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
