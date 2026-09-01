from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from strategy_engine import STRATEGIES

MAX_ACTIONABLE_SIGNALS = 3
MIN_CONFIRMATIONS = 4
MIN_QUALITY_SCORE = 72.0


@dataclass(frozen=True)
class QualityDecision:
    quality_score: float
    confirmations: int
    checks: int
    passed: bool
    reason: str


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def evaluate_quality(row: dict, level: int) -> QualityDecision:
    """Final signal quality gate using only existing production indicators.

    This is intentionally NOT a probability model. It checks whether an existing
    BUY signal is internally well-confirmed before it may become actionable.
    """
    cfg = STRATEGIES[int(level)]
    score = _f(row.get('score'))
    rsi = _f(row.get('rsi'), 50.0)
    momentum = _f(row.get('momentum_pct'))
    volume = _f(row.get('volume_ratio'), 1.0)
    atr = _f(row.get('atr_pct'))
    buy_threshold = _f(cfg.get('buy_score'), 70.0)
    target_atr = max(0.01, _f(cfg.get('volatility_target'), 1.0))

    checks = [
        ('Score-Puffer', score >= buy_threshold + 5.0),
        ('RSI-Zone', 52.0 <= rsi <= 70.0),
        ('Momentum', momentum > 0.0),
        ('Volumen', volume >= 1.10),
        ('ATR', atr > 0.0 and atr <= target_atr * 1.65),
    ]
    confirmations = sum(1 for _, ok in checks if ok)

    # Quality score is a bounded confirmation score, not a win probability.
    score_margin = max(0.0, min(15.0, score - buy_threshold)) / 15.0 * 30.0
    rsi_component = max(0.0, 1.0 - abs(rsi - 61.0) / 18.0) * 20.0
    momentum_component = max(0.0, min(1.0, momentum / 2.0)) * 18.0
    volume_component = max(0.0, min(1.0, (volume - 1.0) / 2.5)) * 17.0
    atr_ratio = atr / target_atr if target_atr else 99.0
    atr_component = max(0.0, 1.0 - abs(atr_ratio - 1.0) / 1.5) * 15.0 if atr > 0 else 0.0
    quality_score = round(max(0.0, min(100.0, score_margin + rsi_component + momentum_component + volume_component + atr_component)), 1)

    passed = bool(
        row.get('signal') == 'BUY'
        and confirmations >= MIN_CONFIRMATIONS
        and quality_score >= MIN_QUALITY_SCORE
    )
    ok_names = [name for name, ok in checks if ok]
    fail_names = [name for name, ok in checks if not ok]
    reason = f"{confirmations}/{len(checks)} Bestätigungen · Q {quality_score:.1f}"
    if fail_names:
        reason += ' · fehlt: ' + ', '.join(fail_names)
    return QualityDecision(quality_score, confirmations, len(checks), passed, reason)


def apply_quality_gate(rows: list[dict], level: int, held_symbols: Iterable[str] = (), max_actionable: int = MAX_ACTIONABLE_SIGNALS) -> tuple[list[dict], int]:
    held = {str(s).upper() for s in held_symbols if s}
    marked=[]
    eligible=[]
    for row in rows:
        item=dict(row)
        is_held=str(item.get('symbol','')).upper() in held
        item['is_held']=is_held
        decision=evaluate_quality(item, level)
        item['quality_score']=decision.quality_score
        item['quality_confirmations']=decision.confirmations
        item['quality_checks']=decision.checks
        item['quality_pass']=bool(decision.passed and item.get('is_finalist') and not is_held)
        item['quality_reason']=decision.reason
        item['is_actionable']=False
        if item['quality_pass']:
            eligible.append(item)
        marked.append(item)

    # Relative ranking is intentionally deterministic. At most three can become
    # actionable, even when all twelve finalists technically pass the gate.
    eligible.sort(key=lambda r: (_f(r.get('quality_score')), _f(r.get('score'))), reverse=True)
    actionable_symbols={r.get('symbol') for r in eligible[:max(0,int(max_actionable))]}
    for item in marked:
        item['is_actionable']=item.get('symbol') in actionable_symbols
    return marked, len(actionable_symbols)
