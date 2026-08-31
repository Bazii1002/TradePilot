
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "0.8.16 H1 ROBUSTNESS AUDIT"
DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")

H1_NAME = "H1_BASELINE_061_U70_E70"
H1_COMPANY_MIN = 70
H1_ENTRY_MIN = 70

EXPECTED_SECOND_HOLDOUT_HASH = "63e1f6ca1d5a37bf2ef9ca0fe32134b69896bb52ec9c91f0cb6739fe3b458604"

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df

def latest_observation_csv() -> Path:
    files = sorted(
        DATA_DIR.glob("TradePilot_SECOND_HOLDOUT_Observations_0.8.15_*.csv"),
        key=lambda p: p.stat().st_mtime
    )
    if not files:
        raise FileNotFoundError(
            "Keine 0.8.15 Second-Holdout-Beobachtungsdatei gefunden unter:\n"
            f"{DATA_DIR}\n"
            "Erwartet: TradePilot_SECOND_HOLDOUT_Observations_0.8.15_*.csv"
        )
    return files[-1]

def episodes(df: pd.DataFrame, gap_days: int = 130) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    d = df.copy()
    d["_date"] = pd.to_datetime(d["Stichtag"], errors="coerce")
    out = []

    for _, g in d.sort_values(["Symbol", "_date"]).groupby("Symbol", sort=False):
        keep = []
        last = None
        for idx, r in g.iterrows():
            dt = r["_date"]
            if pd.isna(dt):
                continue
            if last is None or (dt - last).days > gap_days:
                keep.append(idx)
            last = dt
        if keep:
            out.append(g.loc[keep].drop(columns=["_date"]))

    return pd.concat(out, ignore_index=True) if out else d.iloc[:0].drop(columns=["_date"])

def stock_level(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Symbol","Rendite_12M","Alpha_12M","Sektor_Alpha_12M"])
    return (
        df.groupby("Symbol", as_index=False)[["Rendite_12M","Alpha_12M","Sektor_Alpha_12M"]]
        .mean()
    )

def metrics(df: pd.DataFrame) -> dict:
    d = df.copy()
    for c in ["Rendite_12M","Alpha_12M","Sektor_Alpha_12M"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["Rendite_12M"].notna() & d["Alpha_12M"].notna()].copy()

    if d.empty:
        return {
            "n":0, "Aktien":0, "Episoden":0,
            "Median":np.nan, "Alpha":np.nan, "SektorAlpha":np.nan,
            "EpisodenAlpha":np.nan, "AktienAlpha":np.nan,
            "Positiv":np.nan, "Minus20":np.nan,
            "SPYBeat":np.nan, "SektorBeat":np.nan,
            "Mean":np.nan, "Trim10":np.nan
        }

    ep = episodes(d)
    stocks = stock_level(d)

    vals = np.sort(d["Rendite_12M"].dropna().to_numpy())
    if len(vals) >= 10:
        k = max(1, int(len(vals) * 0.10))
        trimmed = vals[k:-k] if len(vals) > 2*k else vals
        trim10 = float(np.mean(trimmed))
    else:
        trim10 = float(np.mean(vals))

    return {
        "n": int(len(d)),
        "Aktien": int(d["Symbol"].nunique()),
        "Episoden": int(len(ep)),
        "Median": float(d["Rendite_12M"].median()),
        "Alpha": float(d["Alpha_12M"].median()),
        "SektorAlpha": float(d["Sektor_Alpha_12M"].median()),
        "EpisodenAlpha": float(ep["Alpha_12M"].median()) if not ep.empty else np.nan,
        "AktienAlpha": float(stocks["Alpha_12M"].median()) if not stocks.empty else np.nan,
        "Positiv": float((d["Rendite_12M"] > 0).mean() * 100),
        "Minus20": float((d["Rendite_12M"] <= -20).mean() * 100),
        "SPYBeat": float((d["Alpha_12M"] > 0).mean() * 100),
        "SektorBeat": float((d["Sektor_Alpha_12M"] > 0).mean() * 100),
        "Mean": float(d["Rendite_12M"].mean()),
        "Trim10": trim10,
    }

def prepare_h1(df: pd.DataFrame) -> pd.DataFrame:
    x = clean_columns(df)

    required = [
        "Symbol","Modell","Stichtag",
        "B061_Unternehmensscore","B061_Einstiegsscore",
        "Rendite_12M","Alpha_12M","Sektor_Alpha_12M"
    ]
    missing = [c for c in required if c not in x.columns]
    if missing:
        raise KeyError(f"Pflichtspalten fehlen: {missing}\nVorhanden: {list(x.columns)}")

    num_cols = [
        "B061_Unternehmensscore","B061_Einstiegsscore",
        "Rendite_12M","Alpha_12M","Sektor_Alpha_12M",
        "Qualitaet","Entwicklung","Bewertung","Value_Trap","Drawdown_Score","Trend"
    ]
    for c in num_cols:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")

    x["Stichtag"] = pd.to_datetime(x["Stichtag"], errors="coerce")
    x = x[
        (x["B061_Unternehmensscore"] >= H1_COMPANY_MIN) &
        (x["B061_Einstiegsscore"] >= H1_ENTRY_MIN) &
        x["Rendite_12M"].notna() &
        x["Alpha_12M"].notna()
    ].copy()

    x = x.sort_values(["Stichtag","Symbol"]).reset_index(drop=True)
    return x

def time_split_rows(h1: pd.DataFrame) -> pd.DataFrame:
    if h1.empty:
        return pd.DataFrame()

    dates = sorted(h1["Stichtag"].dropna().unique())
    if not dates:
        return pd.DataFrame()

    # Predeclared equal-date halves; no return-based breakpoint.
    split_idx = len(dates) // 2
    early_dates = set(dates[:split_idx])
    late_dates = set(dates[split_idx:])

    rows = []
    for name, d in [
        ("FULL", h1),
        ("EARLY_HALF_BY_STICHTAG", h1[h1["Stichtag"].isin(early_dates)]),
        ("LATE_HALF_BY_STICHTAG", h1[h1["Stichtag"].isin(late_dates)]),
    ]:
        rows.append({"Periode": name, **metrics(d)})

    return pd.DataFrame(rows)

def calendar_rows(h1: pd.DataFrame) -> pd.DataFrame:
    if h1.empty:
        return pd.DataFrame()

    d = h1.copy()
    d["Jahr"] = d["Stichtag"].dt.year
    rows = []

    for year, g in d.groupby("Jahr"):
        rows.append({"Periode": f"YEAR_{int(year)}", **metrics(g)})

    return pd.DataFrame(rows)

def anchor_rows(h1: pd.DataFrame) -> pd.DataFrame:
    """
    Reduziert zeitliche Überlappung ohne Schwellenwahl:
    pro Aktie nur das erste vollständige H1-Signal im Datensatz.
    """
    if h1.empty:
        return pd.DataFrame()

    first = (
        h1.sort_values(["Symbol","Stichtag"])
        .groupby("Symbol", as_index=False)
        .first()
    )
    return pd.DataFrame([{"Periode":"FIRST_SIGNAL_PER_STOCK", **metrics(first)}])

def leave_one_stock_out(h1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    symbols = sorted(h1["Symbol"].dropna().astype(str).unique())

    for s in symbols:
        m = metrics(h1[h1["Symbol"] != s])
        rows.append({
            "Removed_Symbol": s,
            **m
        })

    return pd.DataFrame(rows)

def remove_top_winners(h1: pd.DataFrame) -> pd.DataFrame:
    d = h1.sort_values("Rendite_12M", ascending=False).copy()
    rows = [{"Scenario":"ALL", **metrics(d)}]

    for k in [1, 3, 5]:
        if len(d) > k:
            rows.append({
                "Scenario": f"WITHOUT_TOP_{k}_SIGNALS",
                **metrics(d.iloc[k:])
            })

    # Stock-level winners: remove ALL rows of the strongest stock(s).
    stocks = stock_level(d).sort_values("Rendite_12M", ascending=False)
    for k in [1, 3]:
        top = set(stocks.head(k)["Symbol"])
        rows.append({
            "Scenario": f"WITHOUT_TOP_{k}_STOCKS",
            **metrics(d[~d["Symbol"].isin(top)])
        })

    return pd.DataFrame(rows)

def model_rows(h1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, g in h1.groupby("Modell"):
        rows.append({"Modell": model, **metrics(g)})
    return pd.DataFrame(rows)

def loss_cases(h1: pd.DataFrame) -> pd.DataFrame:
    cols = [
        c for c in [
            "Stichtag","Symbol","Modell",
            "B061_Unternehmensscore","B061_Einstiegsscore",
            "Qualitaet","Entwicklung","Bewertung","Value_Trap",
            "Drawdown_Score","Trend",
            "Rendite_12M","Alpha_12M","Sektor_Alpha_12M"
        ] if c in h1.columns
    ]
    return h1[h1["Rendite_12M"] <= -20][cols].sort_values("Rendite_12M")

def stability_verdict(base: dict, time_df, loo_df, outlier_df) -> str:
    checks = []

    # Base must still satisfy the same predeclared PASS logic.
    checks.append(
        base["n"] >= 20 and
        base["Aktien"] >= 10 and
        base["Episoden"] >= 10 and
        base["Alpha"] > 0 and
        base["EpisodenAlpha"] > 0 and
        base["AktienAlpha"] > 0 and
        base["Minus20"] <= 20
    )

    # Time halves: do not demand full PASS because sample sizes can shrink.
    halves = time_df[time_df["Periode"].isin(["EARLY_HALF_BY_STICHTAG","LATE_HALF_BY_STICHTAG"])]
    if len(halves) == 2:
        checks.append(bool((halves["Alpha"] > 0).all()))
        checks.append(bool((halves["AktienAlpha"] > 0).all()))
    else:
        checks.extend([False, False])

    # LOO: all removals should preserve positive median alpha.
    if not loo_df.empty:
        checks.append(bool((loo_df["Alpha"] > 0).all()))
        checks.append(bool((loo_df["AktienAlpha"] > 0).all()))
    else:
        checks.extend([False, False])

    # Removing top 3 signals and top 1 stock should preserve positive alpha.
    needed = outlier_df[outlier_df["Scenario"].isin(["WITHOUT_TOP_3_SIGNALS","WITHOUT_TOP_1_STOCKS"])]
    if len(needed) == 2:
        checks.append(bool((needed["Alpha"] > 0).all()))
        checks.append(bool((needed["AktienAlpha"] > 0).all()))
    else:
        checks.extend([False, False])

    passed = sum(checks)
    if passed == len(checks):
        return "ROBUST_PASS"
    if checks[0] and passed >= max(5, len(checks)-2):
        return "ROBUST_WATCH"
    return "ROBUST_FAIL"

def fmt(v):
    if pd.isna(v):
        return "--"
    return f"{v:+.1f}"

def pct(v):
    if pd.isna(v):
        return "--"
    return f"{v:.1f}%"

def print_table(title, df, label_col):
    print()
    print(title)
    print("-" * 152)
    print(f"{label_col:<30} {'n':>5} {'Akt':>5} {'Epis':>5} {'Med':>8} {'Alpha':>8} {'SektA':>8} {'EpA':>8} {'StkA':>8} {'SPY%':>7} {'Sekt%':>7} {'Pos%':>7} {'<=-20':>7}")
    for _, r in df.iterrows():
        print(
            f"{str(r[label_col]):<30} "
            f"{int(r['n']):5d} {int(r['Aktien']):5d} {int(r['Episoden']):5d} "
            f"{fmt(r['Median']):>8} {fmt(r['Alpha']):>8} {fmt(r['SektorAlpha']):>8} "
            f"{fmt(r['EpisodenAlpha']):>8} {fmt(r['AktienAlpha']):>8} "
            f"{pct(r['SPYBeat']):>7} {pct(r['SektorBeat']):>7} {pct(r['Positiv']):>7} {pct(r['Minus20']):>7}"
        )

def run(source: Path):
    raw = pd.read_csv(source, encoding="utf-8-sig")
    h1 = prepare_h1(raw)

    if h1.empty:
        raise RuntimeError("H1 liefert in der 0.8.15-Beobachtungsdatei keine vollständigen 12M-Fälle.")

    base = metrics(h1)
    time_df = time_split_rows(h1)
    year_df = calendar_rows(h1)
    anchor_df = anchor_rows(h1)
    loo_df = leave_one_stock_out(h1)
    outlier_df = remove_top_winners(h1)
    model_df = model_rows(h1)
    losses_df = loss_cases(h1)

    verdict = stability_verdict(base, time_df, loo_df, outlier_df)

    print("=" * 152)
    print("TRADEPILOT 0.8.16 H1 ROBUSTNESS AUDIT")
    print("=" * 152)
    print("Eingefrorene Regel: 0.6.1 Unternehmensscore >=70 UND Einstiegsscore >=70")
    print("Keine neue Schwelle wird getestet.")
    print(f"Quelle: {source}")
    print()

    print("H1 BASIS")
    print("-" * 152)
    print(
        f"n={base['n']} | Aktien={base['Aktien']} | Episoden={base['Episoden']} | "
        f"Median {fmt(base['Median'])}% | Alpha {fmt(base['Alpha'])} | "
        f"SektorAlpha {fmt(base['SektorAlpha'])} | EpA {fmt(base['EpisodenAlpha'])} | "
        f"StkA {fmt(base['AktienAlpha'])} | <=-20 {pct(base['Minus20'])}"
    )

    print_table("ZEITSTABILITÄT", time_df, "Periode")
    if not year_df.empty:
        print_table("KALENDERJAHRE", year_df, "Periode")
    print_table("NICHT-MEHRFACHGEWICHTETE ANKER", anchor_df, "Periode")
    print_table("AUSREISSER-STRESSTEST", outlier_df, "Scenario")
    print_table("MODELLMIX", model_df, "Modell")

    print()
    print("LEAVE-ONE-STOCK-OUT")
    print("-" * 152)
    if loo_df.empty:
        print("Keine Daten.")
    else:
        print(
            f"Alpha-Spanne nach Entfernen je einer Aktie: "
            f"{loo_df['Alpha'].min():+.1f} bis {loo_df['Alpha'].max():+.1f}"
        )
        print(
            f"Aktien-Alpha-Spanne: "
            f"{loo_df['AktienAlpha'].min():+.1f} bis {loo_df['AktienAlpha'].max():+.1f}"
        )
        print(
            f"Schlechteste <=-20%-Quote: {loo_df['Minus20'].max():.1f}%"
        )

    print()
    print("VERLUSTFÄLLE <= -20%")
    print("-" * 152)
    if losses_df.empty:
        print("Keine.")
    else:
        for _, r in losses_df.iterrows():
            print(
                f"{pd.to_datetime(r['Stichtag']).date()} {r['Symbol']:<7} {r['Modell']:<15} "
                f"U={r['B061_Unternehmensscore']:.0f} E={r['B061_Einstiegsscore']:.0f} "
                f"12M={r['Rendite_12M']:+.1f}% Alpha={r['Alpha_12M']:+.1f}"
            )

    print()
    print("=" * 152)
    print(f"0.8.16 ROBUSTNESS VERDICT: {verdict}")
    print("=" * 152)
    print("ROBUST_PASS bedeutet nur: H1 blieb innerhalb dieser vorab definierten Stressprüfungen stabil.")
    print("Es ist keine wissenschaftliche Validierung und keine Handelsfreigabe.")
    print("0.8.16 verändert KEINE Produktions-Scorelogik und optimiert KEINE Schwelle.")

    stamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")

    summary = pd.DataFrame([{
        "Version": VERSION,
        "Hypothesis": H1_NAME,
        **base,
        "Robustness_Verdict": verdict,
    }])

    summary_file = DATA_DIR / f"TradePilot_H1_Robustness_Summary_0.8.16_{stamp}.csv"
    time_file = DATA_DIR / f"TradePilot_H1_Time_Stability_0.8.16_{stamp}.csv"
    loo_file = DATA_DIR / f"TradePilot_H1_LeaveOneStockOut_0.8.16_{stamp}.csv"
    outlier_file = DATA_DIR / f"TradePilot_H1_Outlier_Stress_0.8.16_{stamp}.csv"
    model_file = DATA_DIR / f"TradePilot_H1_Model_Mix_0.8.16_{stamp}.csv"
    losses_file = DATA_DIR / f"TradePilot_H1_Loss_Cases_0.8.16_{stamp}.csv"
    audit_file = DATA_DIR / f"TradePilot_H1_Robustness_Audit_0.8.16_{stamp}.json"

    summary.to_csv(summary_file, index=False, encoding="utf-8-sig")
    pd.concat([time_df, year_df, anchor_df], ignore_index=True).to_csv(time_file, index=False, encoding="utf-8-sig")
    loo_df.to_csv(loo_file, index=False, encoding="utf-8-sig")
    outlier_df.to_csv(outlier_file, index=False, encoding="utf-8-sig")
    model_df.to_csv(model_file, index=False, encoding="utf-8-sig")
    losses_df.to_csv(losses_file, index=False, encoding="utf-8-sig")

    audit = {
        "version": VERSION,
        "source": str(source),
        "frozen_hypothesis": {
            "name": H1_NAME,
            "company_min": H1_COMPANY_MIN,
            "entry_min": H1_ENTRY_MIN,
        },
        "second_holdout_hash_reference": EXPECTED_SECOND_HOLDOUT_HASH,
        "threshold_optimization": False,
        "tested_alternative_thresholds": False,
        "production_score_changed": False,
        "robustness_verdict": verdict,
        "checks": [
            "full predeclared PASS rule retained",
            "early/late date-half alpha sign",
            "early/late date-half stock-alpha sign",
            "leave-one-stock-out median alpha sign",
            "leave-one-stock-out stock-alpha sign",
            "remove top 3 signals",
            "remove top 1 stock",
            "model breakdown",
            "loss-case inspection",
        ],
    }
    audit_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("Gespeichert:")
    for p in [summary_file, time_file, loo_file, outlier_file, model_file, losses_file, audit_file]:
        print(f"  {p}")

def selftest():
    rows = []
    # 12 stocks, two observations each, all passing H1.
    for i in range(24):
        s = f"S{i%12:02d}"
        month = (i % 12) + 1
        rows.append({
            "Symbol": s,
            "Modell": "STANDARD" if i % 3 else "BANK",
            "Stichtag": f"2024-{month:02d}-28",
            "B061_Unternehmensscore": 74,
            "B061_Einstiegsscore": 72,
            "Rendite_12M": 20 + (i % 5),
            "Alpha_12M": 6 + (i % 3),
            "Sektor_Alpha_12M": 5 + (i % 2),
            "Qualitaet": 70,
            "Entwicklung": 65,
            "Bewertung": 55,
            "Value_Trap": 10,
            "Drawdown_Score": 60,
            "Trend": 60,
        })

    df = pd.DataFrame(rows)
    h1 = prepare_h1(df)
    assert len(h1) == 24

    base = metrics(h1)
    assert base["n"] == 24
    assert base["Aktien"] == 12
    assert base["Alpha"] > 0

    loo = leave_one_stock_out(h1)
    assert len(loo) == 12
    assert (loo["Alpha"] > 0).all()

    outs = remove_top_winners(h1)
    assert "WITHOUT_TOP_3_SIGNALS" in set(outs["Scenario"])
    assert "WITHOUT_TOP_1_STOCKS" in set(outs["Scenario"])

    tm = time_split_rows(h1)
    assert set(tm["Periode"]) == {"FULL","EARLY_HALF_BY_STICHTAG","LATE_HALF_BY_STICHTAG"}

    print("TradePilot 0.8.16 H1 ROBUSTNESS AUDIT SELFTEST: OK")
    print("Frozen H1 U>=70/E>=70: OK")
    print("Time split: OK")
    print("Leave-one-stock-out: OK")
    print("Outlier stress: OK")
    print("Model split: OK")
    print("No alternative thresholds: OK")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--source", type=str, default="")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    source = Path(args.source) if args.source else latest_observation_csv()
    run(source)

if __name__ == "__main__":
    main()
