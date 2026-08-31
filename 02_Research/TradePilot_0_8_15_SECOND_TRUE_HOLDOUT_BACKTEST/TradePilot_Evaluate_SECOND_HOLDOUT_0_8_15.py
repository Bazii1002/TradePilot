
from __future__ import annotations
import hashlib, json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path(r"C:\TradePilot\03_Research_Data")
LOCK_JSON = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_14_SECOND_HOLDOUT_LOCK_UNIVERSE\TradePilot_0_8_14_SECOND_HOLDOUT_LOCK.json")
EXPECTED_SECOND_HASH = "63e1f6ca1d5a37bf2ef9ca0fe32134b69896bb52ec9c91f0cb6739fe3b458604"

def latest_raw():
    files = list(HERE.glob("TradePilot_Backtest_0.8.15_SECOND_HOLDOUT_RAW_*.csv"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None

def episodes(df, gap=130):
    if df.empty:
        return df.copy()
    d = df.copy()
    d["_d"] = pd.to_datetime(d["Stichtag"], errors="coerce")
    out = []
    for _, g in d.sort_values(["Symbol", "_d"]).groupby("Symbol", sort=False):
        keep = []
        last = None
        for idx, r in g.iterrows():
            if last is None or (r["_d"] - last).days > gap:
                keep.append(idx)
            last = r["_d"]
        out.append(g.loc[keep].drop(columns=["_d"]))
    return pd.concat(out, ignore_index=True) if out else d.iloc[:0]

def metrics(df):
    d = df.copy()
    for c in ["Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["Rendite_12M"].notna() & d["Alpha_12M"].notna()]

    if d.empty:
        return dict(
            n=0, Aktien=0, Episoden=0, Median=None, Alpha=None,
            SektorAlpha=None, EpisodenAlpha=None, AktienAlpha=None,
            Positiv=None, Minus20=None, SPYBeat=None, SectorBeat=None
        )

    ep = episodes(d)
    stock = d.groupby("Symbol")["Alpha_12M"].mean()

    return dict(
        n=len(d),
        Aktien=d["Symbol"].nunique(),
        Episoden=len(ep),
        Median=float(d["Rendite_12M"].median()),
        Alpha=float(d["Alpha_12M"].median()),
        SektorAlpha=float(d["Sektor_Alpha_12M"].median()),
        EpisodenAlpha=float(ep["Alpha_12M"].median()),
        AktienAlpha=float(stock.median()),
        Positiv=float((d["Rendite_12M"] > 0).mean() * 100),
        Minus20=float((d["Rendite_12M"] <= -20).mean() * 100),
        SPYBeat=float((d["Alpha_12M"] > 0).mean() * 100),
        SectorBeat=float((d["Sektor_Alpha_12M"] > 0).mean() * 100),
    )

def verdict(m):
    # Identisch zur vorab verwendeten konservativen Holdout-Regel.
    if m["n"] >= 20 and m["Aktien"] >= 10 and m["Episoden"] >= 10:
        if (
            m["Alpha"] is not None and m["Alpha"] > 0 and
            m["EpisodenAlpha"] is not None and m["EpisodenAlpha"] > 0 and
            m["AktienAlpha"] is not None and m["AktienAlpha"] > 0 and
            m["Minus20"] is not None and m["Minus20"] <= 20
        ):
            return "PASS"
        return "FAIL"

    if m["n"] >= 5 and m["Alpha"] is not None and m["Alpha"] > 0:
        return "WATCH"

    return "FAIL"

def verify_frozen_lock():
    if not LOCK_JSON.exists():
        raise FileNotFoundError(f"0.8.14 Lock fehlt: {LOCK_JSON}")
    lock = json.loads(LOCK_JSON.read_text(encoding="utf-8"))
    if lock.get("second_holdout", {}).get("csv_sha256") != EXPECTED_SECOND_HASH:
        raise RuntimeError("Second-Holdout-Hash im 0.8.14 Lock stimmt nicht.")
    frozen = lock.get("frozen_hypotheses", {})
    expected = {"H1_BASELINE_061_U70_E70", "H2_CAP_TRAP20_59_DD40_59"}
    if set(frozen) != expected:
        raise RuntimeError("Frozen Hypotheses im 0.8.14 Lock stimmen nicht.")
    return True

def run(path):
    verify_frozen_lock()

    x = pd.read_csv(path, encoding="utf-8-sig")
    x.columns = [str(c).replace("\ufeff", "").strip() for c in x.columns]

    numeric = [
        "Qualitaet", "Entwicklung", "Bewertung", "Value_Trap",
        "Drawdown_Score", "Trend",
        "B061_Unternehmensscore", "B061_Einstiegsscore",
        "Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M",
    ]
    for c in numeric:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")

    h1 = x[
        (x["B061_Unternehmensscore"] >= 70) &
        (x["B061_Einstiegsscore"] >= 70)
    ]

    h2 = x[
        (x["Modell"] == "CAPITAL_MARKETS") &
        (x["Value_Trap"] >= 20) &
        (x["Value_Trap"] <= 59) &
        (x["Drawdown_Score"] >= 40) &
        (x["Drawdown_Score"] <= 59)
    ]

    # References are fixed broad model baselines only, not alternative thresholds.
    tests = [
        ("REFERENCE_ALL", x, "REFERENCE"),
        ("H1_BASELINE_061_U70_E70", h1, None),
        ("REFERENCE_CAP_MODEL", x[x["Modell"] == "CAPITAL_MARKETS"], "REFERENCE"),
        ("H2_CAP_TRAP20_59_DD40_59", h2, None),
    ]

    rows = []
    for name, d, fixed_verdict in tests:
        m = metrics(d)
        rows.append({
            "Test": name,
            **m,
            "Verdict": fixed_verdict if fixed_verdict else verdict(m),
        })

    r = pd.DataFrame(rows)

    def f(v):
        return "--" if v is None or pd.isna(v) else f"{v:+.1f}"

    print()
    print("=" * 154)
    print("TRADEPILOT 0.8.15 SECOND TRUE HOLDOUT RESULTS")
    print("=" * 154)
    print("Es werden ausschließlich die VORHER eingefrorenen Hypothesen H1 und H2 bewertet.")
    print()
    print(
        f"{'Test':34} {'n':>6} {'Akt':>5} {'Epis':>5} {'Med':>8} {'Alpha':>8} "
        f"{'SektA':>8} {'EpA':>8} {'StkA':>8} {'SPY%':>7} {'Sekt%':>7} {'Pos%':>7} {'<=-20':>7} {'Verdict':>10}"
    )

    for _, q in r.iterrows():
        def pct(v):
            return "--" if pd.isna(v) else f"{v:.1f}%"
        print(
            f"{q.Test:<34} {int(q.n):6} {int(q.Aktien):5} {int(q.Episoden):5} "
            f"{f(q.Median):>8} {f(q.Alpha):>8} {f(q.SektorAlpha):>8} "
            f"{f(q.EpisodenAlpha):>8} {f(q.AktienAlpha):>8} "
            f"{pct(q.SPYBeat):>7} {pct(q.SectorBeat):>7} {pct(q.Positiv):>7} {pct(q.Minus20):>7} "
            f"{q.Verdict:>10}"
        )

    print()
    print("PASS-Regel wurde vor diesem Ergebnis festgelegt:")
    print("n>=20, >=10 Aktien, >=10 Episoden, Alpha/EpisodenAlpha/AktienAlpha >0 und <=-20%-Quote <=20%.")
    print("WATCH: n>=5 + positiver Median-Alpha bei zu kleiner Stichprobe. FAIL: sonst.")
    print("Keine andere Schwelle wurde getestet oder ausgewählt.")

    stamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_file = DATA / f"TradePilot_SECOND_HOLDOUT_Results_0.8.15_{stamp}.csv"
    obs_file = DATA / f"TradePilot_SECOND_HOLDOUT_Observations_0.8.15_{stamp}.csv"
    audit_file = DATA / f"TradePilot_SECOND_HOLDOUT_Audit_0.8.15_{stamp}.json"

    r.to_csv(result_file, index=False, encoding="utf-8-sig")
    x.to_csv(obs_file, index=False, encoding="utf-8-sig")

    audit = {
        "version": "0.8.15",
        "second_holdout_hash": EXPECTED_SECOND_HASH,
        "raw_source": str(path),
        "hypotheses_evaluated": [
            "H1_BASELINE_061_U70_E70",
            "H2_CAP_TRAP20_59_DD40_59",
        ],
        "exploratory_threshold_matrix": False,
        "threshold_optimization": False,
        "production_score_changed": False,
    }
    audit_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"Second-Holdout-Ergebnis: {result_file}")
    print(f"Beobachtungen archiviert: {obs_file}")
    print(f"Audit: {audit_file}")
    print("=" * 154)
    return r

def main():
    p = latest_raw()
    if p is None:
        raise FileNotFoundError("Keine 0.8.15 Second-Holdout Raw-CSV gefunden.")
    print(f"Quelle: {p}")
    run(p)

if __name__ == "__main__":
    main()
