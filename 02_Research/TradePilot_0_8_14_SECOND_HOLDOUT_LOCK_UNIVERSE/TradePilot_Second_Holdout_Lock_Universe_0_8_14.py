
from __future__ import annotations
import csv, hashlib, io, json, re, sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

VERSION = "0.8.14 SECOND HOLDOUT LOCK + UNIVERSE"

DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")
LOCK_0811 = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_11_TRUE_HOLDOUT_LOCK\TradePilot_0_8_11_SEEN_SYMBOLS.csv")
HOLDOUT_0812 = DATA_DIR / "TradePilot_True_Holdout_Universe_0.8.12.1.csv"

EXPECTED_FIRST_HOLDOUT_HASH = "34b38c903865506f8cfb1d80560a6717abf9b33c73ed8c6a2432c52e16fc310c"
EXPECTED_FIRST_HOLDOUT_COUNT = 999
EXPECTED_SEEN_0811_COUNT = 494

IWM_CSV_URL = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/latest-holdings.csv"

FROZEN_HYPOTHESES = {
    "H1_BASELINE_061_U70_E70": {
        "model_scope": "ALL",
        "rule": "B061_Unternehmensscore >= 70 AND B061_Einstiegsscore >= 70",
        "reason_frozen": "New hypothesis observed after 0.8.13; 0.8.13 does NOT count as confirmation.",
        "status_before_second_holdout": "UNCONFIRMED_NEW_HYPOTHESIS",
    },
    "H2_CAP_TRAP20_59_DD40_59": {
        "model_scope": "CAPITAL_MARKETS",
        "rule": "Value_Trap between 20 and 59 inclusive AND Drawdown_Score between 40 and 59 inclusive",
        "reason_frozen": "Only specialized candidate that survived 0.8.13 as WATCH.",
        "status_before_second_holdout": "WATCH",
    },
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def norm_symbol(s) -> str:
    s = str(s).strip().upper()
    s = s.replace(".", "-")
    s = re.sub(r"\s+", "", s)
    return s

def load_symbols(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Datei fehlt: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).replace("\ufeff","").strip() for c in df.columns]
    if "Symbol" in df.columns:
        c = "Symbol"
    elif "Ticker" in df.columns:
        c = "Ticker"
    else:
        c = df.columns[0]
    return sorted(set(norm_symbol(x) for x in df[c].dropna() if str(x).strip()))

def verify_previous_locks():
    seen_0811 = load_symbols(LOCK_0811)
    if len(seen_0811) != EXPECTED_SEEN_0811_COUNT:
        raise RuntimeError(
            f"0.8.11 Symbolanzahl abweichend: erwartet {EXPECTED_SEEN_0811_COUNT}, gefunden {len(seen_0811)}"
        )

    if not HOLDOUT_0812.exists():
        raise FileNotFoundError(f"Erster Holdout fehlt: {HOLDOUT_0812}")

    h = sha256_file(HOLDOUT_0812)
    if h != EXPECTED_FIRST_HOLDOUT_HASH:
        raise RuntimeError(
            "0.8.12.1 Holdout-Hash stimmt nicht mehr.\n"
            f"Erwartet: {EXPECTED_FIRST_HOLDOUT_HASH}\nGefunden: {h}"
        )

    first_holdout = load_symbols(HOLDOUT_0812)
    if len(first_holdout) != EXPECTED_FIRST_HOLDOUT_COUNT:
        raise RuntimeError(
            f"0.8.12.1 Holdout-Anzahl abweichend: erwartet {EXPECTED_FIRST_HOLDOUT_COUNT}, gefunden {len(first_holdout)}"
        )

    excluded = sorted(set(seen_0811).union(first_holdout))
    return seen_0811, first_holdout, excluded

def fetch_iwm_csv() -> bytes:
    req = Request(
        IWM_CSV_URL,
        headers={
            "User-Agent": "Mozilla/5.0 TradePilotResearch/0.8.14",
            "Accept": "text/csv,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(req, timeout=60) as r:
        return r.read()

def parse_iwm_csv(raw: bytes) -> pd.DataFrame:
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Ticker,Name,Sector,Asset Class"):
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("IWM CSV Header 'Ticker,Name,Sector,Asset Class' nicht gefunden.")

    payload = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(payload))
    df.columns = [str(c).strip() for c in df.columns]

    required = ["Ticker","Name","Sector","Asset Class"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"IWM CSV Spalten fehlen: {missing}")

    # Rule-blind universe construction:
    # only actual equity positions with a non-empty ticker.
    x = df.copy()
    x["Ticker"] = x["Ticker"].astype(str).map(norm_symbol)
    x["Asset Class"] = x["Asset Class"].astype(str).str.strip()
    x = x[
        (x["Asset Class"].str.lower() == "equity") &
        (x["Ticker"] != "") &
        (x["Ticker"] != "NAN") &
        (~x["Ticker"].str.startswith("-"))
    ].copy()

    # Keep useful metadata only; selection does NOT use returns/scores/valuation.
    keep = [c for c in ["Ticker","Name","Sector","Asset Class","Location","Exchange","Currency"] if c in x.columns]
    x = x[keep].drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    return x

def build_second_holdout(iwm: pd.DataFrame, excluded_symbols):
    excluded = set(excluded_symbols)
    x = iwm.copy()
    x["Already_Used"] = x["Ticker"].isin(excluded)

    removed = x[x["Already_Used"]].copy().reset_index(drop=True)
    holdout = x[~x["Already_Used"]].copy().reset_index(drop=True)

    holdout = holdout.rename(columns={"Ticker":"Symbol","Name":"Company"})
    removed = removed.rename(columns={"Ticker":"Symbol","Name":"Company"})

    holdout["Universe_Source"] = "iShares IWM / Russell 2000 holdings"
    removed["Universe_Source"] = "iShares IWM / Russell 2000 holdings"

    holdout = holdout.sort_values("Symbol").reset_index(drop=True)
    removed = removed.sort_values("Symbol").reset_index(drop=True)
    return holdout, removed

def verify_second_holdout(holdout: pd.DataFrame, all_previous):
    prev = set(all_previous)
    syms = set(holdout["Symbol"])
    overlap = sorted(syms.intersection(prev))
    if overlap:
        raise RuntimeError(f"SECOND HOLDOUT verletzt: {len(overlap)} alte Symbole enthalten: {overlap[:20]}")
    if holdout["Symbol"].duplicated().any():
        d = holdout.loc[holdout["Symbol"].duplicated(),"Symbol"].tolist()
        raise RuntimeError(f"Doppelte Holdout-Symbole: {d[:20]}")
    return True

def write_lock_and_outputs(raw_iwm, iwm, holdout, removed, seen_0811, first_holdout, all_previous):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent

    out_universe = DATA_DIR / "TradePilot_Second_Holdout_Universe_0.8.14.csv"
    local_universe = here / "TradePilot_Second_Holdout_Universe_0.8.14.csv"
    excluded_file = here / "TradePilot_0_8_14_EXCLUDED_PREVIOUSLY_USED.csv"
    rules_file = here / "TradePilot_0_8_14_FROZEN_HYPOTHESES.csv"
    lock_file = here / "TradePilot_0_8_14_SECOND_HOLDOUT_LOCK.json"

    holdout.to_csv(out_universe, index=False, encoding="utf-8-sig")
    holdout.to_csv(local_universe, index=False, encoding="utf-8-sig")
    removed.to_csv(excluded_file, index=False, encoding="utf-8-sig")

    pd.DataFrame([
        {"Hypothesis": k, **v} for k,v in FROZEN_HYPOTHESES.items()
    ]).to_csv(rules_file, index=False, encoding="utf-8-sig")

    holdout_hash = sha256_file(out_universe)

    lock = {
        "version": VERSION,
        "created_local": datetime.now().isoformat(timespec="seconds"),
        "purpose": "Freeze two post-0.8.13 hypotheses and create a second symbol-level holdout before testing either hypothesis.",
        "frozen_hypotheses": FROZEN_HYPOTHESES,
        "previous_data": {
            "research_seen_0_8_11_count": len(seen_0811),
            "first_holdout_0_8_12_1_count": len(first_holdout),
            "unique_previously_used_symbols": len(all_previous),
            "first_holdout_sha256": EXPECTED_FIRST_HOLDOUT_HASH,
        },
        "universe_source": {
            "name": "iShares Russell 2000 ETF (IWM) latest holdings CSV",
            "url": IWM_CSV_URL,
            "raw_csv_sha256": sha256_bytes(raw_iwm),
            "equity_holdings_after_asset_filter": int(len(iwm)),
        },
        "second_holdout": {
            "excluded_previously_used": int(len(removed)),
            "final_symbol_count": int(len(holdout)),
            "overlap_with_all_previous": 0,
            "csv_path": str(out_universe),
            "csv_sha256": holdout_hash,
        },
        "selection_policy": [
            "Only IWM membership and Asset Class=Equity are used.",
            "No price return, alpha, score, valuation or fundamental metric is used to select symbols.",
            "All 0.8.11 discovery symbols and all 0.8.12.1 first-holdout symbols are excluded.",
            "H1 and H2 thresholds are frozen before second-holdout outcomes are evaluated.",
            "The second holdout must not be modified after its hash is created."
        ],
        "method_limits": [
            "Current IWM holdings imply survivorship/current-membership bias.",
            "The market period will still overlap with earlier tests.",
            "Yahoo historical fundamentals remain not fully revision-safe point-in-time.",
            "This is stronger symbol-level replication, not scientific proof."
        ]
    }

    lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_universe, lock_file, holdout_hash

def selftest():
    a = ["AAA","BBB"]
    b = ["CCC","DDD"]
    all_prev = sorted(set(a+b))
    df = pd.DataFrame({
        "Ticker":["AAA","EEE","FFF","CCC"],
        "Name":["A","E","F","C"],
        "Sector":["Industrials"]*4,
        "Asset Class":["Equity"]*4
    })
    h, r = build_second_holdout(df, all_prev)
    assert sorted(h["Symbol"].tolist()) == ["EEE","FFF"]
    assert sorted(r["Symbol"].tolist()) == ["AAA","CCC"]
    verify_second_holdout(h, all_prev)
    assert norm_symbol("BRK.B") == "BRK-B"

    sample = (
        'iShares Russell 2000 ETF\n'
        'Fund Holdings as of,"Aug 28, 2026"\n'
        'Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Quantity,Price,Location,Exchange,Currency,FX Rate,Market Currency,Accrual Date\n'
        '"XYZ","EXAMPLE","Industrials","Equity","1","0.1","1","1","1","United States","NYSE","USD","1","USD","-"\n'
        '"CASH","CASH","Cash","Cash and/or Derivatives","1","0.1","1","1","1","United States","-","USD","1","USD","-"\n'
    ).encode("utf-8")
    parsed = parse_iwm_csv(sample)
    assert parsed["Ticker"].tolist() == ["XYZ"]

    print("TradePilot 0.8.14 SECOND HOLDOUT LOCK + UNIVERSE SELFTEST: OK")
    print("Previous-universe exclusion logic: OK")
    print("IWM CSV parser: OK")
    print("Equity-only filter: OK")
    print("Frozen hypotheses: 2")
    print("No return/score selection: OK")

def main():
    if "--selftest" in sys.argv:
        selftest()
        return

    print("="*118)
    print("TRADEPILOT 0.8.14 SECOND HOLDOUT LOCK + UNIVERSE")
    print("="*118)
    print("Dieser Schritt testet NOCH KEINE Hypothese.")
    print("H1: 0.6.1 U>=70 / E>=70")
    print("H2: CAPITAL_MARKETS Trap20-59 + DD40-59")
    print("Beide Regeln werden VOR dem zweiten Holdout-Ergebnis eingefroren.")
    print()

    seen_0811, first_holdout, all_previous = verify_previous_locks()
    print(f"0.8.11 Discovery-Symbole:        {len(seen_0811)}")
    print(f"0.8.12.1 First-Holdout-Symbole:  {len(first_holdout)}")
    print(f"Einzigartige bereits verwendete: {len(all_previous)}")
    print(f"First-Holdout-Hash geprüft:       OK")
    print()

    print("Lade offizielle IWM/Russell-2000-Holdings ...")
    raw = fetch_iwm_csv()
    iwm = parse_iwm_csv(raw)
    print(f"IWM Equity-Holdings erkannt:      {len(iwm)}")

    holdout, removed = build_second_holdout(iwm, all_previous)
    verify_second_holdout(holdout, all_previous)

    out_universe, lock_file, h = write_lock_and_outputs(
        raw, iwm, holdout, removed, seen_0811, first_holdout, all_previous
    )

    print()
    print("="*118)
    print("SECOND HOLDOUT ERFOLGREICH EINGEFROREN")
    print("="*118)
    print(f"IWM Equity-Holdings:                    {len(iwm)}")
    print(f"Wegen früherer Nutzung ausgeschlossen:  {len(removed)}")
    print(f"Finale neue Second-Holdout-Symbole:      {len(holdout)}")
    print(f"Overlap mit ALLEN bisherigen Symbolen:   0")
    print()
    print(f"Dauerhaft gespeichert: {out_universe}")
    print(f"Lock/Audit:             {lock_file}")
    print(f"Second-Holdout-Hash:    {h}")
    print()
    print("AB JETZT:")
    print("- H1 und H2 nicht mehr verändern.")
    print("- Second-Holdout-Liste nicht mehr verändern.")
    print("- Erst 0.8.15 darf die Ergebnisse dieser Aktien ansehen.")
    print("- Keine Produktions-Scorelogik wurde verändert.")
    print("="*118)

if __name__ == "__main__":
    main()
