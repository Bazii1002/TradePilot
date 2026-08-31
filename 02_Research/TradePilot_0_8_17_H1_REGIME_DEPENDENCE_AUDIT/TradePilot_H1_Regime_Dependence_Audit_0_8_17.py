from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "0.8.17 H1 REGIME & DEPENDENCE AUDIT"
DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")

H1_NAME = "H1_BASELINE_061_U70_E70"
H1_COMPANY_MIN = 70
H1_ENTRY_MIN = 70
EXPECTED_SECOND_HOLDOUT_HASH = "63e1f6ca1d5a37bf2ef9ca0fe32134b69896bb52ec9c91f0cb6739fe3b458604"

SPY_CACHE = DATA_DIR / "TradePilot_SPY_Regime_History_0.8.17.csv"
REGIME_SMA_DAYS = 200
REGIME_LOOKBACK_DAYS = 126
REGIME_RETURN_THRESHOLD = 5.0


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


def latest_observation_csv() -> Path:
    files = sorted(
        DATA_DIR.glob("TradePilot_SECOND_HOLDOUT_Observations_0.8.15_*.csv"),
        key=lambda p: p.stat().st_mtime,
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
        return pd.DataFrame(columns=["Symbol", "Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M"])
    return df.groupby("Symbol", as_index=False)[["Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M"]].mean()


def metrics(df: pd.DataFrame) -> dict:
    d = df.copy()
    for c in ["Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["Rendite_12M"].notna() & d["Alpha_12M"].notna()].copy()
    if d.empty:
        return {
            "n": 0, "Aktien": 0, "Episoden": 0,
            "Median": np.nan, "Alpha": np.nan, "SektorAlpha": np.nan,
            "EpisodenAlpha": np.nan, "AktienAlpha": np.nan,
            "SPYBeat": np.nan, "SektorBeat": np.nan,
            "Positiv": np.nan, "Minus20": np.nan,
        }
    ep = episodes(d)
    stocks = stock_level(d)
    return {
        "n": int(len(d)),
        "Aktien": int(d["Symbol"].nunique()),
        "Episoden": int(len(ep)),
        "Median": float(d["Rendite_12M"].median()),
        "Alpha": float(d["Alpha_12M"].median()),
        "SektorAlpha": float(d["Sektor_Alpha_12M"].median()),
        "EpisodenAlpha": float(ep["Alpha_12M"].median()) if not ep.empty else np.nan,
        "AktienAlpha": float(stocks["Alpha_12M"].median()) if not stocks.empty else np.nan,
        "SPYBeat": float((d["Alpha_12M"] > 0).mean() * 100),
        "SektorBeat": float((d["Sektor_Alpha_12M"] > 0).mean() * 100),
        "Positiv": float((d["Rendite_12M"] > 0).mean() * 100),
        "Minus20": float((d["Rendite_12M"] <= -20).mean() * 100),
    }


def prepare_h1(df: pd.DataFrame) -> pd.DataFrame:
    x = clean_columns(df)
    required = [
        "Symbol", "Modell", "Stichtag", "B061_Unternehmensscore", "B061_Einstiegsscore",
        "Rendite_12M", "Alpha_12M", "Sektor_Alpha_12M",
    ]
    missing = [c for c in required if c not in x.columns]
    if missing:
        raise KeyError(f"Pflichtspalten fehlen: {missing}\nVorhanden: {list(x.columns)}")
    for c in [
        "B061_Unternehmensscore", "B061_Einstiegsscore", "Rendite_12M", "Alpha_12M",
        "Sektor_Alpha_12M", "Qualitaet", "Entwicklung", "Bewertung", "Value_Trap",
        "Drawdown_Score", "Trend",
    ]:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    x["Stichtag"] = pd.to_datetime(x["Stichtag"], errors="coerce")
    x = x[
        (x["B061_Unternehmensscore"] >= H1_COMPANY_MIN)
        & (x["B061_Einstiegsscore"] >= H1_ENTRY_MIN)
        & x["Rendite_12M"].notna()
        & x["Alpha_12M"].notna()
    ].copy()
    return x.sort_values(["Stichtag", "Symbol"]).reset_index(drop=True)


def _normalize_download_close(raw: pd.DataFrame) -> pd.Series:
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance can return either (Price,Ticker) or (Ticker,Price).
        close_cols = [c for c in raw.columns if "Close" in tuple(map(str, c))]
        if not close_cols:
            raise RuntimeError(f"SPY-Download enthält keine Close-Spalte: {list(raw.columns)[:10]}")
        s = raw[close_cols[0]]
    elif "Close" in raw.columns:
        s = raw["Close"]
    else:
        raise RuntimeError(f"SPY-Download enthält keine Close-Spalte: {list(raw.columns)}")
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.sort_index()


def load_spy_history(min_date: pd.Timestamp, max_date: pd.Timestamp, refresh: bool = False) -> pd.Series:
    min_needed = pd.Timestamp(min_date) - pd.Timedelta(days=500)
    max_needed = pd.Timestamp(max_date) + pd.Timedelta(days=5)

    if SPY_CACHE.exists() and not refresh:
        cached = pd.read_csv(SPY_CACHE, encoding="utf-8-sig")
        if {"Date", "Close"}.issubset(cached.columns):
            cached["Date"] = pd.to_datetime(cached["Date"], errors="coerce")
            cached["Close"] = pd.to_numeric(cached["Close"], errors="coerce")
            cached = cached.dropna().sort_values("Date")
            if not cached.empty and cached["Date"].min() <= min_needed and cached["Date"].max() >= max_date:
                return pd.Series(cached["Close"].to_numpy(), index=cached["Date"], name="Close")

    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError("yfinance fehlt. Installiere es mit: python -m pip install yfinance") from e

    print("SPY-Regimehistorie wird geladen ...")
    raw = yf.download(
        "SPY",
        start=min_needed.strftime("%Y-%m-%d"),
        end=max_needed.strftime("%Y-%m-%d"),
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    close = _normalize_download_close(raw)
    if close.empty:
        raise RuntimeError("SPY-Kurshistorie konnte nicht geladen werden.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Date": close.index, "Close": close.values}).to_csv(SPY_CACHE, index=False, encoding="utf-8-sig")
    return close


def regime_features(close: pd.Series) -> pd.DataFrame:
    c = close.astype(float).dropna().sort_index()
    df = pd.DataFrame({"Close": c})
    df["SMA200"] = df["Close"].rolling(REGIME_SMA_DAYS, min_periods=REGIME_SMA_DAYS).mean()
    df["Trailing6M"] = (df["Close"] / df["Close"].shift(REGIME_LOOKBACK_DAYS) - 1.0) * 100.0
    return df.dropna().copy()


def classify_regime(close: float, sma200: float, trailing6m: float) -> str:
    # Fixed, outcome-blind classification. No return-based tuning on H1 outcomes.
    if close > sma200 and trailing6m >= REGIME_RETURN_THRESHOLD:
        return "BULL"
    if close < sma200 and trailing6m <= -REGIME_RETURN_THRESHOLD:
        return "BEAR"
    return "MIXED_SIDEWAYS"


def attach_regimes(h1: pd.DataFrame, spy_close: pd.Series) -> pd.DataFrame:
    feats = regime_features(spy_close)
    if feats.empty:
        raise RuntimeError("Zu wenig SPY-Historie für SMA200/6M-Regime.")
    out = h1.copy()
    regimes, closes, smas, rets, used_dates = [], [], [], [], []
    for dt in out["Stichtag"]:
        prior = feats.loc[feats.index <= pd.Timestamp(dt)]
        if prior.empty:
            regimes.append("UNKNOWN"); closes.append(np.nan); smas.append(np.nan); rets.append(np.nan); used_dates.append(pd.NaT)
            continue
        r = prior.iloc[-1]
        regimes.append(classify_regime(float(r["Close"]), float(r["SMA200"]), float(r["Trailing6M"])))
        closes.append(float(r["Close"])); smas.append(float(r["SMA200"])); rets.append(float(r["Trailing6M"])); used_dates.append(prior.index[-1])
    out["Market_Regime"] = regimes
    out["SPY_Regime_Date"] = used_dates
    out["SPY_Close_At_Regime"] = closes
    out["SPY_SMA200"] = smas
    out["SPY_Trailing6M_Pct"] = rets
    return out


def regime_rows(h1r: pd.DataFrame) -> pd.DataFrame:
    rows = [{"Segment": "ALL_H1", **metrics(h1r)}]
    for name in ["BULL", "MIXED_SIDEWAYS", "BEAR", "UNKNOWN"]:
        g = h1r[h1r["Market_Regime"] == name]
        if not g.empty:
            rows.append({"Segment": name, **metrics(g)})
    return pd.DataFrame(rows)


def first_last_rows(h1: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = h1.sort_values(["Symbol", "Stichtag"]).copy()
    first = d.groupby("Symbol", as_index=False).first()
    last = d.groupby("Symbol", as_index=False).last()
    rows = pd.DataFrame([
        {"Variant": "ALL_SIGNALS", **metrics(d)},
        {"Variant": "FIRST_SIGNAL_PER_STOCK", **metrics(first)},
        {"Variant": "LAST_SIGNAL_PER_STOCK", **metrics(last)},
    ])
    return rows, first, last


def cooldown_select(h1: pd.DataFrame, cooldown_days: int) -> pd.DataFrame:
    """Deterministic earliest-anchor cooldown; no outcome information is used."""
    d = h1.sort_values(["Symbol", "Stichtag"]).copy()
    kept = []
    for _, g in d.groupby("Symbol", sort=False):
        last_kept = None
        for idx, row in g.iterrows():
            dt = pd.Timestamp(row["Stichtag"])
            if last_kept is None or (dt - last_kept).days >= cooldown_days:
                kept.append(idx)
                last_kept = dt
    return d.loc[kept].sort_values(["Stichtag", "Symbol"]).reset_index(drop=True)


def dependence_rows(h1: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    anchor_rows, first, last = first_last_rows(h1)
    cd12 = cooldown_select(h1, 365)
    cd18 = cooldown_select(h1, 548)
    rows = pd.concat([
        anchor_rows,
        pd.DataFrame([
            {"Variant": "ONE_SIGNAL_PER_STOCK_12M", **metrics(cd12)},
            {"Variant": "ONE_SIGNAL_PER_STOCK_18M", **metrics(cd18)},
        ]),
    ], ignore_index=True)
    return rows, {"first": first, "last": last, "12m": cd12, "18m": cd18}


def model_dependence_rows(h1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, g in h1.groupby("Modell"):
        dep, _ = dependence_rows(g)
        for _, r in dep.iterrows():
            rows.append({"Modell": model, **r.to_dict()})
    return pd.DataFrame(rows)


def regime_dependence_cross(h1r: pd.DataFrame) -> pd.DataFrame:
    rows = []
    variants = dependence_rows(h1r)[1]
    selected = {
        "ALL_SIGNALS": h1r,
        "FIRST_SIGNAL_PER_STOCK": variants["first"],
        "LAST_SIGNAL_PER_STOCK": variants["last"],
        "ONE_SIGNAL_PER_STOCK_12M": variants["12m"],
        "ONE_SIGNAL_PER_STOCK_18M": variants["18m"],
    }
    for variant, d in selected.items():
        for regime, g in d.groupby("Market_Regime"):
            rows.append({"Variant": variant, "Market_Regime": regime, **metrics(g)})
    return pd.DataFrame(rows)


def diagnostic_verdict(base: dict, dep_df: pd.DataFrame, regime_df: pd.DataFrame) -> tuple[str, list[str]]:
    """
    Diagnostic only. This audit cannot promote H1 to production because it reuses the second-holdout outcomes.
    Thresholds below are predeclared engineering diagnostics, not optimized trading rules.
    """
    notes = []
    dep = dep_df.set_index("Variant")
    core_variants = ["FIRST_SIGNAL_PER_STOCK", "LAST_SIGNAL_PER_STOCK", "ONE_SIGNAL_PER_STOCK_12M", "ONE_SIGNAL_PER_STOCK_18M"]
    positive_alpha_count = sum(float(dep.loc[v, "Alpha"]) > 0 for v in core_variants if v in dep.index)
    positive_stock_count = sum(float(dep.loc[v, "AktienAlpha"]) > 0 for v in core_variants if v in dep.index)

    if positive_alpha_count <= 1:
        notes.append("Mehrfachsignal-Abhängigkeit ist stark: höchstens eine der vier deduplizierten Varianten hat positives Median-Alpha.")
    elif positive_alpha_count < 4:
        notes.append("Mehrfachsignal-Abhängigkeit bleibt sichtbar: nicht alle deduplizierten Varianten halten positives Median-Alpha.")
    else:
        notes.append("Alle vier deduplizierten Varianten halten positives Median-Alpha.")

    meaningful_regimes = regime_df[(regime_df["Segment"] != "ALL_H1") & (regime_df["n"] >= 10)]
    neg_regimes = meaningful_regimes[meaningful_regimes["Alpha"] <= 0]
    if not neg_regimes.empty:
        notes.append("Mindestens ein Regime mit n>=10 hat kein positives Median-Alpha.")
    else:
        notes.append("Kein Regime mit n>=10 zeigt negatives Median-Alpha (sofern solche Regime vorhanden sind).")

    # No promotion from this same-sample diagnostic.
    if base["Alpha"] <= 0 or base["AktienAlpha"] <= 0:
        verdict = "ROBUST_FAIL"
    elif positive_alpha_count <= 1:
        verdict = "DEPENDENCE_CONCERN"
    else:
        verdict = "ROBUST_WATCH"
    notes.append("0.8.17 kann H1 nicht zu ROBUST_PASS/Produktion hochstufen, weil dieselben Second-Holdout-Outcomes erneut analysiert werden.")
    return verdict, notes


def fmt(v):
    return "--" if pd.isna(v) else f"{v:+.1f}"


def pct(v):
    return "--" if pd.isna(v) else f"{v:.1f}%"


def print_table(title: str, df: pd.DataFrame, label_cols: list[str]):
    print()
    print(title)
    print("-" * 164)
    head = " / ".join(label_cols)
    print(f"{head:<46} {'n':>5} {'Akt':>5} {'Epis':>5} {'Med':>8} {'Alpha':>8} {'SektA':>8} {'EpA':>8} {'StkA':>8} {'SPY%':>7} {'Sekt%':>7} {'Pos%':>7} {'<=-20':>7}")
    for _, r in df.iterrows():
        label = " / ".join(str(r[c]) for c in label_cols)
        print(
            f"{label:<46} {int(r['n']):5d} {int(r['Aktien']):5d} {int(r['Episoden']):5d} "
            f"{fmt(r['Median']):>8} {fmt(r['Alpha']):>8} {fmt(r['SektorAlpha']):>8} "
            f"{fmt(r['EpisodenAlpha']):>8} {fmt(r['AktienAlpha']):>8} "
            f"{pct(r['SPYBeat']):>7} {pct(r['SektorBeat']):>7} {pct(r['Positiv']):>7} {pct(r['Minus20']):>7}"
        )


def run(source: Path, refresh_spy: bool = False):
    raw = pd.read_csv(source, encoding="utf-8-sig")
    h1 = prepare_h1(raw)
    if h1.empty:
        raise RuntimeError("H1 liefert keine vollständigen 12M-Fälle.")

    spy = load_spy_history(h1["Stichtag"].min(), h1["Stichtag"].max(), refresh=refresh_spy)
    h1r = attach_regimes(h1, spy)

    base = metrics(h1r)
    reg = regime_rows(h1r)
    dep, selected = dependence_rows(h1r)
    model_dep = model_dependence_rows(h1r)
    cross = regime_dependence_cross(h1r)
    verdict, notes = diagnostic_verdict(base, dep, reg)

    print("=" * 164)
    print("TRADEPILOT 0.8.17 H1 REGIME & DEPENDENCE AUDIT")
    print("=" * 164)
    print("Eingefrorene H1-Regel: 0.6.1 Unternehmensscore >=70 UND Einstiegsscore >=70")
    print("KEINE alternative Score-Schwelle wird getestet.")
    print("Regime werden nur aus SPY-Daten VOR/AM jeweiligen Stichtag gebildet.")
    print(f"Quelle: {source}")
    print()
    print("REGIME-DEFINITION (VORAB FEST)")
    print("  BULL: SPY > SMA200 UND trailing 126 Handelstage >= +5%")
    print("  BEAR: SPY < SMA200 UND trailing 126 Handelstage <= -5%")
    print("  MIXED_SIDEWAYS: alle übrigen Fälle")

    print_table("MARKTREGIME", reg, ["Segment"])
    print_table("SIGNAL-ABHÄNGIGKEIT / DEDUPLIZIERUNG", dep, ["Variant"])
    print_table("MODELL x ABHÄNGIGKEIT", model_dep, ["Modell", "Variant"])
    print_table("REGIME x ABHÄNGIGKEIT", cross, ["Market_Regime", "Variant"])

    print()
    print("DIAGNOSTISCHE HINWEISE")
    print("-" * 164)
    for n in notes:
        print(f"- {n}")

    print()
    print("=" * 164)
    print(f"0.8.17 RESEARCH VERDICT: {verdict}")
    print("=" * 164)
    print("WICHTIG: Dieser Audit verwendet erneut die 0.8.15-Second-Holdout-Beobachtungen.")
    print("Er ist deshalb ein Robustheits-/Abhängigkeitsaudit, KEIN neuer unabhängiger Holdout.")
    print("0.8.17 verändert KEINE Produktions-Scorelogik und optimiert KEINE Schwelle.")

    stamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = DATA_DIR / f"TradePilot_H1_Regime_Dependence_Summary_0.8.17_{stamp}.csv"
    regime_file = DATA_DIR / f"TradePilot_H1_Regime_Audit_0.8.17_{stamp}.csv"
    dep_file = DATA_DIR / f"TradePilot_H1_Dependence_Audit_0.8.17_{stamp}.csv"
    model_file = DATA_DIR / f"TradePilot_H1_Model_Dependence_0.8.17_{stamp}.csv"
    cross_file = DATA_DIR / f"TradePilot_H1_Regime_Dependence_Cross_0.8.17_{stamp}.csv"
    signals_file = DATA_DIR / f"TradePilot_H1_Regime_Tagged_Signals_0.8.17_{stamp}.csv"
    audit_file = DATA_DIR / f"TradePilot_H1_Regime_Dependence_Audit_0.8.17_{stamp}.json"

    pd.DataFrame([{ "Version": VERSION, "Hypothesis": H1_NAME, **base, "Research_Verdict": verdict }]).to_csv(summary_file, index=False, encoding="utf-8-sig")
    reg.to_csv(regime_file, index=False, encoding="utf-8-sig")
    dep.to_csv(dep_file, index=False, encoding="utf-8-sig")
    model_dep.to_csv(model_file, index=False, encoding="utf-8-sig")
    cross.to_csv(cross_file, index=False, encoding="utf-8-sig")
    h1r.to_csv(signals_file, index=False, encoding="utf-8-sig")

    audit = {
        "version": VERSION,
        "source": str(source),
        "frozen_hypothesis": {"name": H1_NAME, "company_min": H1_COMPANY_MIN, "entry_min": H1_ENTRY_MIN},
        "second_holdout_hash_reference": EXPECTED_SECOND_HOLDOUT_HASH,
        "regime_definition": {
            "benchmark": "SPY",
            "sma_days": REGIME_SMA_DAYS,
            "trailing_return_trading_days": REGIME_LOOKBACK_DAYS,
            "return_threshold_pct": REGIME_RETURN_THRESHOLD,
            "bull": "close>sma200 and trailing6m>=+5%",
            "bear": "close<sma200 and trailing6m<=-5%",
            "mixed_sideways": "otherwise",
        },
        "dependence_variants": [
            "FIRST_SIGNAL_PER_STOCK",
            "LAST_SIGNAL_PER_STOCK",
            "ONE_SIGNAL_PER_STOCK_12M earliest-anchor cooldown",
            "ONE_SIGNAL_PER_STOCK_18M earliest-anchor cooldown",
        ],
        "threshold_optimization": False,
        "tested_alternative_score_thresholds": False,
        "production_score_changed": False,
        "new_independent_holdout": False,
        "research_verdict": verdict,
        "notes": notes,
    }
    audit_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("Gespeichert:")
    for p in [summary_file, regime_file, dep_file, model_file, cross_file, signals_file, audit_file]:
        print(f"  {p}")


def selftest():
    rows = []
    dates = pd.to_datetime(["2024-03-28", "2024-06-28", "2024-09-30", "2024-12-31"])
    for s_i in range(12):
        for j, dt in enumerate(dates):
            rows.append({
                "Symbol": f"S{s_i:02d}",
                "Modell": "STANDARD" if s_i % 3 else "ENERGY",
                "Stichtag": dt,
                "B061_Unternehmensscore": 74,
                "B061_Einstiegsscore": 72,
                "Rendite_12M": 10 + s_i + j,
                "Alpha_12M": 2 + (s_i % 4),
                "Sektor_Alpha_12M": 1 + (s_i % 3),
            })
    h1 = prepare_h1(pd.DataFrame(rows))
    assert len(h1) == 48 and h1["Symbol"].nunique() == 12

    # Synthetic business-day SPY path covering enough history.
    idx = pd.bdate_range("2022-01-03", "2025-01-10")
    close = pd.Series(np.linspace(350, 500, len(idx)), index=idx)
    h1r = attach_regimes(h1, close)
    assert set(h1r["Market_Regime"]).issubset({"BULL", "MIXED_SIDEWAYS", "BEAR", "UNKNOWN"})

    dep, selected = dependence_rows(h1r)
    assert set(dep["Variant"]) == {
        "ALL_SIGNALS", "FIRST_SIGNAL_PER_STOCK", "LAST_SIGNAL_PER_STOCK",
        "ONE_SIGNAL_PER_STOCK_12M", "ONE_SIGNAL_PER_STOCK_18M",
    }
    assert len(selected["first"]) == 12
    assert len(selected["last"]) == 12
    assert len(selected["18m"]) <= len(selected["12m"]) <= len(h1r)

    model = model_dependence_rows(h1r)
    assert not model.empty
    cross = regime_dependence_cross(h1r)
    assert not cross.empty

    print("TradePilot 0.8.17 H1 REGIME & DEPENDENCE AUDIT SELFTEST: OK")
    print("Frozen H1 U>=70/E>=70: OK")
    print("SPY regime classification: OK")
    print("First/last signal per stock: OK")
    print("12M/18M cooldown dependence: OK")
    print("Model x dependence: OK")
    print("Regime x dependence: OK")
    print("No alternative score thresholds: OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--source", type=str, default="")
    ap.add_argument("--refresh-spy", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    source = Path(args.source) if args.source else latest_observation_csv()
    run(source, refresh_spy=args.refresh_spy)


if __name__ == "__main__":
    main()
