
from __future__ import annotations
import argparse, hashlib, json, re, sys
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

VERSION = "0.8.12.1 TRUE HOLDOUT UNIVERSE HTML FIX"

LOCK_DIR = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_11_TRUE_HOLDOUT_LOCK")
DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")

SOURCES = {
    "SP400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "SP600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def normalize_symbol(s: str) -> str:
    s = str(s).strip().upper()
    # Yahoo Finance uses hyphen for class shares such as BRK-B.
    s = s.replace(".", "-")
    s = re.sub(r"\s+", "", s)
    return s

def load_seen_symbols():
    p = LOCK_DIR / "TradePilot_0_8_11_SEEN_SYMBOLS.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"Seen-Symbol-Datei fehlt:\n{p}\n"
            "Bitte zuerst 0.8.11 TRUE HOLDOUT LOCK erfolgreich ausführen."
        )
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.columns = [str(c).replace("\ufeff","").strip() for c in df.columns]
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    seen = sorted(set(normalize_symbol(x) for x in df[col].dropna()))
    return seen, p

def fetch_html(url: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 TradePilotResearch/0.8.12",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    with urlopen(req, timeout=30) as r:
        return r.read()

def parse_wikipedia_tables(html_bytes: bytes, source_name: str):
    # IMPORTANT: read_html gets a FILE-LIKE object.
    # Passing raw bytes directly can make pandas/lxml treat the complete
    # HTML payload incorrectly and can flood the terminal with HTML.
    try:
        tables = pd.read_html(BytesIO(html_bytes))
    except ImportError as e:
        raise RuntimeError(
            "HTML-Parser fehlt. Bitte einmal ausführen:\n"
            "python -m pip install lxml\n"
            "und danach den Builder erneut starten."
        ) from e
    except Exception as e:
        # Never dump the full HTML response into PowerShell.
        raise RuntimeError(
            f"HTML-Tabelle von {source_name} konnte nicht gelesen werden: "
            f"{type(e).__name__}: {str(e)[:300]}"
        ) from None

    candidates = []
    for t in tables:
        cols = [str(c).strip() for c in t.columns]
        t.columns = cols
        symbol_col = None
        for c in ["Symbol", "Ticker symbol", "Ticker", "Ticker Symbol"]:
            if c in t.columns:
                symbol_col = c
                break
        if symbol_col is None:
            continue

        name_col = None
        for c in ["Security", "Company", "Company name", "Name"]:
            if c in t.columns:
                name_col = c
                break

        sector_col = None
        for c in ["GICS Sector", "Sector"]:
            if c in t.columns:
                sector_col = c
                break

        for _, row in t.iterrows():
            sym = normalize_symbol(row.get(symbol_col, ""))
            if not sym or sym == "NAN":
                continue
            name = str(row.get(name_col, "")).strip() if name_col else ""
            sector = str(row.get(sector_col, "")).strip() if sector_col else ""
            candidates.append({
                "Symbol": sym,
                "Company": "" if name == "nan" else name,
                "Sector": "" if sector == "nan" else sector,
                "Source_Index": source_name,
            })

    if not candidates:
        raise RuntimeError(
            f"Auf der Quelle {source_name} wurde keine Symboltabelle erkannt. "
            "Die Wikipedia-Seite könnte ihr Tabellenformat geändert haben."
        )

    return pd.DataFrame(candidates).drop_duplicates(subset=["Symbol"]).reset_index(drop=True)

def build_universe():
    seen, seen_path = load_seen_symbols()
    seen_set = set(seen)

    source_frames = []
    source_meta = []

    for source_name, url in SOURCES.items():
        print(f"Lade {source_name}: {url}")
        html = fetch_html(url)
        parsed = parse_wikipedia_tables(html, source_name)
        source_frames.append(parsed)
        source_meta.append({
            "source": source_name,
            "url": url,
            "html_sha256": sha256_bytes(html),
            "raw_symbols": int(parsed["Symbol"].nunique()),
        })
        print(f"  Gefunden: {parsed['Symbol'].nunique()} Symbole")

    combined = pd.concat(source_frames, ignore_index=True)

    # If a symbol somehow occurs in both source lists, keep one row and document both.
    grouped = combined.groupby("Symbol", as_index=False).agg({
        "Company": "first",
        "Sector": "first",
        "Source_Index": lambda s: "+".join(sorted(set(str(x) for x in s if pd.notna(x))))
    })

    grouped["Already_Seen"] = grouped["Symbol"].isin(seen_set)
    holdout = grouped[~grouped["Already_Seen"]].copy().sort_values("Symbol").reset_index(drop=True)
    excluded = grouped[grouped["Already_Seen"]].copy().sort_values("Symbol").reset_index(drop=True)

    return holdout, excluded, grouped, seen, seen_path, source_meta

def verify_holdout(holdout: pd.DataFrame, seen):
    seen_set = set(seen)
    overlap = sorted(set(holdout["Symbol"]).intersection(seen_set))
    dupes = holdout[holdout["Symbol"].duplicated()]["Symbol"].tolist()
    if overlap:
        raise RuntimeError(f"HOLDOUT FEHLER: {len(overlap)} bereits gesehene Symbole enthalten: {overlap[:20]}")
    if dupes:
        raise RuntimeError(f"HOLDOUT FEHLER: doppelte Symbole: {dupes[:20]}")
    return True

def save_outputs(here: Path, holdout, excluded, combined, seen, seen_path, source_meta):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    universe_file = DATA_DIR / "TradePilot_True_Holdout_Universe_0.8.12.1.csv"
    excluded_file = here / "TradePilot_0_8_12_1_EXCLUDED_ALREADY_SEEN.csv"
    audit_file = here / "TradePilot_0_8_12_1_UNIVERSE_AUDIT.json"
    local_copy = here / "TradePilot_True_Holdout_Universe_0.8.12.1.csv"

    holdout.to_csv(universe_file, index=False, encoding="utf-8-sig")
    holdout.to_csv(local_copy, index=False, encoding="utf-8-sig")
    excluded.to_csv(excluded_file, index=False, encoding="utf-8-sig")

    csv_bytes = universe_file.read_bytes()
    audit = {
        "version": VERSION,
        "purpose": "Build a rule-blind external symbol holdout before any holdout backtest is run.",
        "seen_symbols_source": str(seen_path),
        "seen_symbol_count": len(seen),
        "source_indexes": source_meta,
        "combined_external_symbols_before_seen_filter": int(combined["Symbol"].nunique()),
        "excluded_as_already_seen": int(len(excluded)),
        "final_holdout_symbol_count": int(len(holdout)),
        "holdout_csv": str(universe_file),
        "holdout_csv_sha256": sha256_bytes(csv_bytes),
        "selection_policy": [
            "Only index membership is used to select symbols.",
            "No score, return, alpha, fundamental or price outcome is used during universe construction.",
            "All symbols present in 0.8.11 SEEN_SYMBOLS are excluded.",
            "No frozen rule threshold is modified.",
        ],
        "warning": (
            "This creates a symbol-level external holdout. It does not remove shared market-regime exposure "
            "and does not solve historical point-in-time fundamental limitations."
        )
    }
    audit_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    return universe_file, excluded_file, audit_file, audit

def selftest(here: Path):
    seen = ["AAA","BBB","CCC"]
    raw = pd.DataFrame({
        "Symbol":["AAA","DDD","EEE","EEE"],
        "Company":["A","D","E","E"],
        "Sector":["X","Y","Z","Z"],
        "Source_Index":["SP400","SP400","SP600","SP600"]
    })
    grouped = raw.groupby("Symbol",as_index=False).agg({
        "Company":"first","Sector":"first",
        "Source_Index":lambda s:"+".join(sorted(set(s)))
    })
    grouped["Already_Seen"]=grouped["Symbol"].isin(set(seen))
    holdout=grouped[~grouped.Already_Seen].copy()
    assert sorted(holdout.Symbol.tolist()) == ["DDD","EEE"]
    verify_holdout(holdout,seen)
    assert normalize_symbol("BRK.B")=="BRK-B"
    mini = b"""<html><body><table><tr><th>Symbol</th><th>Security</th></tr><tr><td>XYZ</td><td>Example Corp</td></tr></table></body></html>"""
    parsed = parse_wikipedia_tables(mini, "SELFTEST")
    assert parsed.iloc[0]["Symbol"] == "XYZ"
    print("TradePilot 0.8.12.1 TRUE HOLDOUT UNIVERSE HTML FIX SELFTEST: OK")
    print("Seen-Symbol-Ausschluss: OK")
    print("Duplikat-Bereinigung: OK")
    print("Yahoo-Symbolnormalisierung: OK")
    print("Frozen-Rule-Blindness: OK")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent

    if args.selftest:
        selftest(here)
        return

    print("="*118)
    print("TRADEPILOT 0.8.12.1 TRUE HOLDOUT UNIVERSE HTML FIX")
    print("="*118)
    print("Regelblinder Universumsbau: S&P MidCap 400 + S&P SmallCap 600")
    print("Bereits gesehene Symbole aus 0.8.11 werden zwingend ausgeschlossen.")
    print("Es werden KEINE Renditen, Scores oder Alpha-Werte ausgewertet.")
    print("")

    holdout, excluded, combined, seen, seen_path, source_meta = build_universe()
    verify_holdout(holdout, seen)
    universe_file, excluded_file, audit_file, audit = save_outputs(
        here, holdout, excluded, combined, seen, seen_path, source_meta
    )

    print("")
    print("="*118)
    print("HOLDOUT-UNIVERSUM ERSTELLT")
    print("="*118)
    print(f"Bisher gesehene Symbole:                  {len(seen)}")
    print(f"Externe Indexsymbole vor Ausschluss:      {combined.Symbol.nunique()}")
    print(f"Wegen 0.8.11-Lock ausgeschlossen:         {len(excluded)}")
    print(f"Finale ungesehene Holdout-Symbole:        {len(holdout)}")
    print(f"Overlap mit Seen Symbols:                 0")
    print("")
    print(f"Dauerhaft gespeichert: {universe_file}")
    print(f"Lokale Kopie:          {here / 'TradePilot_True_Holdout_Universe_0.8.12.1.csv'}")
    print(f"Audit:                  {audit_file}")
    print(f"Holdout-Hash:           {audit['holdout_csv_sha256']}")
    print("")
    print("WICHTIG: Ab jetzt darf die Symbolauswahl dieses Holdouts nicht anhand von Testergebnissen verändert werden.")
    print("0.8.12 verändert KEINE Produktions-Scorelogik.")
    print("="*118)

if __name__ == "__main__":
    main()
