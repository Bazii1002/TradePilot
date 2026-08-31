
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import pandas as pd

VERSION = "0.8.11 TRUE HOLDOUT LOCK"
DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")

FROZEN_RULES = {
    "STANDARD_RECOVERY": {
        "model": "STANDARD",
        "rule": "Drawdown_Score >= 80 AND Bewertung <= 54",
        "status": "WATCH",
        "origin": "0.8.7-0.8.10 research"
    },
    "BANK_BASELINE": {
        "model": "BANK",
        "rule": "BANK model baseline; no hard trend filter",
        "status": "KEEP_AS_REFERENCE",
        "origin": "0.8.6-0.8.10 research"
    },
    "BANK_TREND_CONFIRMATION": {
        "model": "BANK",
        "rule": "Trend between 55 and 79 inclusive",
        "status": "PASS_AS_CONFIRMATION_CANDIDATE",
        "origin": "0.8.9-0.8.10 research"
    },
    "CAPITAL_MARKETS_PRIMARY": {
        "model": "CAPITAL_MARKETS",
        "rule": "Value_Trap between 20 and 59 inclusive AND Drawdown_Score between 40 and 59 inclusive",
        "status": "PASS_CANDIDATE",
        "origin": "0.8.7-0.8.10 research"
    },
    "CAPITAL_MARKETS_SECONDARY": {
        "model": "CAPITAL_MARKETS",
        "rule": "Qualitaet between 55 and 69 inclusive AND Entwicklung <= 54",
        "status": "PASS_CANDIDATE",
        "origin": "0.8.7-0.8.10 research"
    },
    "ENERGY": {
        "model": "ENERGY",
        "rule": "No new candidate rule",
        "status": "INSUFFICIENT_EVIDENCE",
        "origin": "0.8.10 research"
    },
}

def clean_columns(df):
    df = df.copy()
    df.columns = [str(c).replace("\ufeff","").strip() for c in df.columns]
    return df

def file_sha256(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def find_research_csv():
    if not DATA_DIR.exists():
        return None
    files = list(DATA_DIR.glob("TradePilot_Backtest_0.8.5.1_SCORE_AUDIT_FIX_*.csv"))
    if not files:
        files = list(DATA_DIR.glob("*.csv"))
    return max(files, key=lambda p:p.stat().st_mtime) if files else None

def build_lock(csv: Path, output_dir: Path):
    raw = pd.read_csv(csv, sep=None, engine="python")
    raw = clean_columns(raw)

    symbol_col = None
    for c in ["Symbol","Aktie","Ticker","symbol","ticker"]:
        if c in raw.columns:
            symbol_col = c
            break
    if symbol_col is None:
        raise KeyError(f"Keine Symbolspalte gefunden. Vorhanden: {list(raw.columns)}")

    symbols = sorted(set(raw[symbol_col].dropna().astype(str).str.strip()))
    symbol_bytes = "\n".join(symbols).encode("utf-8")
    symbol_hash = hashlib.sha256(symbol_bytes).hexdigest()

    lock = {
        "version": VERSION,
        "purpose": "Freeze all previously seen symbols and research rules before any external holdout is collected.",
        "source_csv": str(csv),
        "source_csv_sha256": file_sha256(csv),
        "seen_symbol_count": len(symbols),
        "seen_symbols_sha256": symbol_hash,
        "rules_frozen": FROZEN_RULES,
        "important": [
            "No threshold optimization is allowed after this lock when evaluating the future external holdout.",
            "Any symbol listed in seen_symbols must be excluded from the future external holdout.",
            "PASS/WATCH labels are research labels only, not trading approval.",
            "The existing S&P/current-universe dataset is NOT a true unseen holdout because it was used during rule discovery."
        ]
    }

    (output_dir/"TradePilot_0_8_11_HOLDOUT_LOCK.json").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    pd.DataFrame({"Symbol":symbols}).to_csv(
        output_dir/"TradePilot_0_8_11_SEEN_SYMBOLS.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([
        {"Kandidat":k, **v} for k,v in FROZEN_RULES.items()
    ]).to_csv(output_dir/"TradePilot_0_8_11_FROZEN_RULES.csv", index=False, encoding="utf-8-sig")
    return lock

def verify_lock(output_dir: Path):
    p = output_dir/"TradePilot_0_8_11_HOLDOUT_LOCK.json"
    s = output_dir/"TradePilot_0_8_11_SEEN_SYMBOLS.csv"
    r = output_dir/"TradePilot_0_8_11_FROZEN_RULES.csv"
    if not (p.exists() and s.exists() and r.exists()):
        return False, "Lock-Dateien fehlen."
    data=json.loads(p.read_text(encoding="utf-8"))
    syms=clean_columns(pd.read_csv(s))
    ok = len(syms)==data["seen_symbol_count"] and len(FROZEN_RULES)==len(pd.read_csv(r))
    return ok, f"Seen Symbols: {len(syms)} | Frozen Rules: {len(FROZEN_RULES)}"

def selftest(tmp: Path):
    rows = [
        {"\ufeffSymbol":"AAA","Modell":"STANDARD","Stichtag":"2024-01-01"},
        {"\ufeffSymbol":"BBB","Modell":"BANK","Stichtag":"2024-01-01"},
        {"\ufeffSymbol":"AAA","Modell":"STANDARD","Stichtag":"2024-04-01"},
    ]
    csv=tmp/"selftest.csv"
    pd.DataFrame(rows).to_csv(csv,index=False,encoding="utf-8-sig")
    lock=build_lock(csv,tmp)
    assert lock["seen_symbol_count"]==2
    ok,msg=verify_lock(tmp)
    assert ok
    print("TradePilot 0.8.11 TRUE HOLDOUT LOCK SELFTEST: OK")
    print("UTF-8-BOM: OK")
    print("Symbol-Deduplizierung: OK")
    print("Frozen Rules: OK")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    here=Path(__file__).resolve().parent

    if args.selftest:
        testdir=here/"_selftest_tmp"
        testdir.mkdir(exist_ok=True)
        try:
            selftest(testdir)
        finally:
            import shutil
            shutil.rmtree(testdir, ignore_errors=True)
        return

    csv=find_research_csv()
    if csv is None:
        print("FEHLER: Keine Research-CSV in C:\\TradePilot\\03_Research_Data gefunden.")
        print("Erwartet wird die Full-CSV aus 0.8.5.1.")
        sys.exit(2)

    print("="*110)
    print("TRADEPILOT 0.8.11 TRUE HOLDOUT LOCK")
    print("="*110)
    print(f"Research-Datenordner: {DATA_DIR}")
    print(f"Quelle: {csv}")
    lock=build_lock(csv,here)
    ok,msg=verify_lock(here)
    if not ok:
        print("FEHLER beim Verifizieren des Locks:", msg)
        sys.exit(3)

    print(f"Bisher gesehene Symbole eingefroren: {lock['seen_symbol_count']}")
    print(f"Symbol-Hash: {lock['seen_symbols_sha256']}")
    print(f"CSV-Hash:    {lock['source_csv_sha256']}")
    print(f"Eingefrorene Regeln: {len(FROZEN_RULES)}")
    print("")
    print("ERSTELLT:")
    print("  TradePilot_0_8_11_HOLDOUT_LOCK.json")
    print("  TradePilot_0_8_11_SEEN_SYMBOLS.csv")
    print("  TradePilot_0_8_11_FROZEN_RULES.csv")
    print("")
    print("WICHTIG:")
    print("Ab diesem Lock dürfen diese Schwellen für den nächsten externen Holdout-Test nicht mehr angepasst werden.")
    print("Alle hier gelisteten Symbole müssen aus dem zukünftigen externen Holdout ausgeschlossen werden.")
    print("0.8.11 verändert KEINE Produktions-Scorelogik.")
    print("="*110)

if __name__=="__main__":
    main()
