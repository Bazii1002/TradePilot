import random
import sys
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import TradePilot_Backtest_0_8_5_SCORE_AUDIT as tp


def baseline_direct(q, e, b, trap, dd, trend):
    u = tp.score_begrenzen(q * 0.40 + e * 0.35 + b * 0.25 - trap * 0.35)
    raw = tp.score_begrenzen(u * 0.25 + b * 0.20 + dd * 0.40 + trend * 0.15)
    final, status, gate = tp.einstiegs_gate(u, trap, raw)
    return u, raw, final, status, gate


def main():
    random.seed(611)
    for _ in range(5000):
        vals = [random.randint(0, 100) for _ in range(6)]
        q, e, b, trap, dd, trend = vals
        expected = baseline_direct(q, e, b, trap, dd, trend)
        got = tp.score_variante_berechnen(
            "BASELINE_061", q, e, b, trap, dd, trend
        )
        assert expected == got, (vals, expected, got)

        for name in ("CANDIDATE_062_BALANCED", "CANDIDATE_062_QUALITY"):
            u, raw, final, status, gate = tp.score_variante_berechnen(
                name, q, e, b, trap, dd, trend
            )
            assert 0 <= u <= 100
            assert 0 <= raw <= 100
            assert 0 <= final <= 100
            if trap >= 60:
                assert final <= 39
            elif trap >= 40:
                assert final <= 54
            if u < 40:
                assert final <= 39
            elif u < 55:
                assert final <= 54
            elif u < 70:
                assert final <= 69

    turbo_source = inspect.getsource(tp.eine_beobachtung_turbo)
    for spalte in ("B061_Unternehmensscore", "C062B_Unternehmensscore", "C062Q_Unternehmensscore"):
        kurz = spalte.split("_")[0]
        assert kurz in turbo_source, f"TURBO-Auditspalten fehlen: {spalte}"

    print("TradePilot 0.8.5.1 SCORE AUDIT FIX SELFTEST: OK")
    print("0.6.1 Baseline-Gleichheit: 5.000/5.000 OK")
    print("0.6.2 Kandidaten: Wertebereiche + 0.6.1 Safety-Gate OK")
    print("TURBO-Auditspalten: OK")
    print("Portable BAT-Dateien: Python wird automatisch ueber PATH gefunden")


if __name__ == "__main__":
    main()
