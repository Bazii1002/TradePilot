from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

VERSION = "0.8.18.1 THIRD HOLDOUT LOCK + UNIVERSE HASH FIX"
DATA_DIR = Path(r"C:\TradePilot\03_Research_Data")
RESEARCH_DIR = Path(r"C:\TradePilot\02_Research")

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

H1_NAME = "H1_BASELINE_061_U70_E70"
H1_COMPANY_MIN = 70
H1_ENTRY_MIN = 70
PRIMARY_ENDPOINT = "FIRST_SIGNAL_PER_STOCK_12M"
TARGET_SAMPLE_SIZE = 1500
SAMPLE_SEED = "TRADEPILOT-0.8.18-THIRD-HOLDOUT"

EXPECTED_DISCOVERY_COUNT = 494
EXPECTED_FIRST_HOLDOUT_COUNT = 999
EXPECTED_SECOND_HOLDOUT_COUNT = 1339
EXPECTED_FIRST_HOLDOUT_HASH = "34b38c903865506f8cfb1d80560a6717abf9b33c73ed8c6a2432c52e16fc310c"
EXPECTED_SECOND_HOLDOUT_HASH = "63e1f6ca1d5a37bf2ef9ca0fe32134b69896bb52ec9c91f0cb6739fe3b458604"

PASS_RULE = {
    "min_first_signal_cases": 30,
    "median_12m_gt": 0.0,
    "median_spy_alpha_gt": 0.0,
    "median_sector_alpha_gt": 0.0,
    "positive_rate_gte_pct": 55.0,
    "loss_le_minus20_rate_lte_pct": 20.0,
}
WATCH_RULE = {
    "min_first_signal_cases": 15,
    "median_spy_alpha_gt": 0.0,
    "median_sector_alpha_gt": 0.0,
}

EXCLUDE_NAME_PATTERNS = (
    " warrant", " warrants", " unit", " units", " right", " rights",
    " preferred", " preference", " depositary preferred", " depositary shares representing preferred",
)


def normalize_symbol(symbol: str) -> str:
    s = str(symbol).strip().upper()
    s = s.replace(".", "-")
    s = re.sub(r"\s+", "", s)
    if not re.fullmatch(r"[A-Z0-9-]{1,15}", s):
        return ""
    return s


def symbol_hash(symbols) -> str:
    clean = sorted(set(normalize_symbol(s) for s in symbols if normalize_symbol(s)))
    payload = "\n".join(clean).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def deterministic_rank(symbol: str) -> str:
    return hashlib.sha256(f"{SAMPLE_SEED}|{symbol}".encode("utf-8")).hexdigest()


def latest_file(patterns: list[str], roots: list[Path]) -> Path:
    hits: list[Path] = []
    for root in roots:
        if root.exists():
            for pat in patterns:
                hits.extend(root.rglob(pat))
    hits = [p for p in hits if p.is_file()]
    if not hits:
        raise FileNotFoundError("Keine passende Datei gefunden fuer: " + ", ".join(patterns))
    return max(hits, key=lambda p: p.stat().st_mtime)


def read_symbols(path: Path) -> list[str]:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    cols = {str(c).strip().lower(): c for c in df.columns}
    for key in ("symbol", "ticker", "aktie"):
        if key in cols:
            col = cols[key]
            return [normalize_symbol(x) for x in df[col].dropna().tolist() if normalize_symbol(x)]
    # Fallback: erste Spalte bei einspaltigen Symbol-CSV
    if len(df.columns) == 1:
        return [normalize_symbol(x) for x in df.iloc[:, 0].dropna().tolist() if normalize_symbol(x)]
    raise ValueError(f"Keine Symbolspalte in {path} gefunden. Spalten: {list(df.columns)}")


def locate_previous_sets():
    roots = [DATA_DIR, RESEARCH_DIR]
    discovery = latest_file(["TradePilot_0_8_11_SEEN_SYMBOLS.csv"], roots)
    first = latest_file(["TradePilot_True_Holdout_Universe_0.8.12.1.csv"], roots)
    second = latest_file(["TradePilot_Second_Holdout_Universe_0.8.14.csv"], roots)
    return discovery, first, second


def download_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 TradePilot Research/0.8.18"}
    r = requests.get(url, timeout=30, headers=headers)
    r.raise_for_status()
    return r.text


def parse_pipe_table(text: str) -> list[dict[str, str]]:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("File Creation Time")]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="|")
    return [dict(row) for row in reader]


def name_allowed(name: str) -> bool:
    low = " " + str(name).strip().lower()
    return not any(p in low for p in EXCLUDE_NAME_PATTERNS)


def build_candidate_pool(nasdaq_rows: list[dict[str, str]], other_rows: list[dict[str, str]]) -> pd.DataFrame:
    out = []

    for r in nasdaq_rows:
        raw = r.get("Symbol", "")
        sym = normalize_symbol(raw)
        name = r.get("Security Name", "")
        if not sym:
            continue
        if str(r.get("Test Issue", "N")).upper() != "N":
            continue
        if str(r.get("ETF", "N")).upper() != "N":
            continue
        if not name_allowed(name):
            continue
        out.append({"Symbol": sym, "Security_Name": name, "Source": "NASDAQ_LISTED", "Exchange": "NASDAQ"})

    exchange_map = {
        "A": "NYSE_AMERICAN", "N": "NYSE", "P": "NYSE_ARCA", "Z": "CBOE_BZX", "V": "IEX"
    }
    for r in other_rows:
        raw = r.get("ACT Symbol", "")
        sym = normalize_symbol(raw)
        name = r.get("Security Name", "")
        if not sym:
            continue
        if str(r.get("Test Issue", "N")).upper() != "N":
            continue
        if str(r.get("ETF", "N")).upper() != "N":
            continue
        if not name_allowed(name):
            continue
        exch_code = str(r.get("Exchange", "")).upper()
        out.append({
            "Symbol": sym,
            "Security_Name": name,
            "Source": "OTHER_LISTED",
            "Exchange": exchange_map.get(exch_code, exch_code or "OTHER"),
        })

    df = pd.DataFrame(out)
    if df.empty:
        return pd.DataFrame(columns=["Symbol", "Security_Name", "Source", "Exchange"])
    df = df.drop_duplicates("Symbol", keep="first").sort_values("Symbol").reset_index(drop=True)
    return df


def choose_sample(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= TARGET_SAMPLE_SIZE:
        return df.sort_values("Symbol").reset_index(drop=True)
    ranked = df.copy()
    ranked["_rank"] = ranked["Symbol"].map(deterministic_rank)
    ranked = ranked.sort_values(["_rank", "Symbol"]).head(TARGET_SAMPLE_SIZE).drop(columns=["_rank"])
    return ranked.sort_values("Symbol").reset_index(drop=True)


def write_outputs(previous_all: set[str], pool: pd.DataFrame, sample: pd.DataFrame, paths: dict[str, Path], source_meta: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({"Symbol": sorted(previous_all)}).to_csv(paths["excluded"], index=False, encoding="utf-8-sig")
    sample.to_csv(paths["universe"], index=False, encoding="utf-8-sig")

    frozen = pd.DataFrame([
        {
            "Hypothesis": H1_NAME,
            "Company_Min": H1_COMPANY_MIN,
            "Entry_Min": H1_ENTRY_MIN,
            "Primary_Endpoint": PRIMARY_ENDPOINT,
            "Min_First_Signal_Cases_PASS": PASS_RULE["min_first_signal_cases"],
            "Median_12M_PASS": ">0",
            "Median_SPY_Alpha_PASS": ">0",
            "Median_Sector_Alpha_PASS": ">0",
            "Positive_Rate_PASS": ">=55%",
            "Loss_Le_Minus20_PASS": "<=20%",
            "No_Alternative_Thresholds": True,
        }
    ])
    frozen.to_csv(paths["hypotheses"], index=False, encoding="utf-8-sig")

    lock = {
        "version": VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": {
            "name": H1_NAME,
            "company_min": H1_COMPANY_MIN,
            "entry_min": H1_ENTRY_MIN,
            "no_alternative_thresholds": True,
        },
        "primary_endpoint": PRIMARY_ENDPOINT,
        "pass_rule": PASS_RULE,
        "watch_rule": WATCH_RULE,
        "secondary_only": ["RAW_H1", "MODEL_SPLITS", "MARKET_REGIME_SPLITS"],
        "universe_method": {
            "sources": [NASDAQ_LISTED_URL, OTHER_LISTED_URL],
            "filters": [
                "Test Issue = N", "ETF = N", "exclude obvious warrants/units/rights/preferred securities",
                "normalize Yahoo symbol", "exclude all previously used symbols",
            ],
            "sample_size_cap": TARGET_SAMPLE_SIZE,
            "sample_method": "SHA256 deterministic rank if eligible unseen pool exceeds cap",
            "sample_seed": SAMPLE_SEED,
        },
        "counts": {
            "previously_used_unique": len(previous_all),
            "eligible_unseen_pool": len(pool),
            "third_holdout_sample": len(sample),
            "overlap_with_previous": len(set(sample["Symbol"]) & previous_all),
        },
        "hashes": {
            "third_holdout_symbol_hash": symbol_hash(sample["Symbol"]),
            "eligible_pool_symbol_hash": symbol_hash(pool["Symbol"]),
        },
        "source_metadata": source_meta,
        "warning": "0.8.18 contains no return/alpha evaluation. Do not alter H1, endpoint or universe after seeing 0.8.19 results.",
    }
    paths["lock"].write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    return lock


def selftest():
    assert normalize_symbol("brk.b") == "BRK-B"
    assert normalize_symbol("ABC") == "ABC"
    assert normalize_symbol("A/B") == ""
    assert symbol_hash(["B", "A", "A"]) == symbol_hash(["A", "B"])
    assert deterministic_rank("ABC") == deterministic_rank("ABC")
    assert H1_COMPANY_MIN == 70 and H1_ENTRY_MIN == 70
    assert PRIMARY_ENDPOINT == "FIRST_SIGNAL_PER_STOCK_12M"
    assert PASS_RULE["min_first_signal_cases"] == 30

    nasdaq_text = "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nABC|ABC Corp|Q|N|N|100|N|N\nETF1|ETF Fund|Q|N|N|100|Y|N\nWRT|Foo Warrant|Q|N|N|100|N|N\nFile Creation Time: 123\n"
    other_text = "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nXYZ|XYZ Inc|N|XYZ|N|100|N|XYZ\nPREF|Foo Preferred Stock|A|PREF|N|100|N|PREF\n"
    pool = build_candidate_pool(parse_pipe_table(nasdaq_text), parse_pipe_table(other_text))
    assert set(pool["Symbol"]) == {"ABC", "XYZ"}

    fake = pd.DataFrame({
        "Symbol": [f"S{i:04d}" for i in range(1600)],
        "Security_Name": ["X"] * 1600,
        "Source": ["T"] * 1600,
        "Exchange": ["T"] * 1600,
    })
    a = choose_sample(fake)
    b = choose_sample(fake.sample(frac=1, random_state=1))
    assert len(a) == TARGET_SAMPLE_SIZE
    assert list(a["Symbol"]) == list(b["Symbol"])

    print("TradePilot 0.8.18 THIRD HOLDOUT LOCK + UNIVERSE SELFTEST: OK")
    print("Frozen H1 U>=70/E>=70: OK")
    print("Primary endpoint FIRST_SIGNAL_PER_STOCK_12M: OK")
    print("PASS/WATCH rules frozen: OK")
    print("NASDAQ Trader parsing/filtering: OK")
    print("Deterministic SHA256 sample: OK")
    print("No return/alpha evaluation in 0.8.18: OK")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return

    print("=" * 120)
    print("TRADEPILOT 0.8.18 THIRD HOLDOUT LOCK + UNIVERSE")
    print("=" * 120)
    print("Dieser Schritt sieht KEINE neuen Renditen oder Alpha-Werte an.")
    print(f"H1 eingefroren: Unternehmensscore >={H1_COMPANY_MIN} UND Einstiegsscore >={H1_ENTRY_MIN}")
    print(f"Primaerer spaeterer Endpunkt: {PRIMARY_ENDPOINT}")
    print("Keine alternative Score-Schwelle wird getestet.\n")

    discovery_path, first_path, second_path = locate_previous_sets()
    discovery = set(read_symbols(discovery_path))
    first = set(read_symbols(first_path))
    second = set(read_symbols(second_path))

    print(f"Discovery-Symbole:                    {len(discovery)}")
    print(f"First-Holdout-Symbole:                {len(first)}")
    print(f"Second-Holdout-Symbole:               {len(second)}")

    if len(discovery) != EXPECTED_DISCOVERY_COUNT:
        raise RuntimeError(f"STOP: Discovery-Anzahl {len(discovery)} != erwartet {EXPECTED_DISCOVERY_COUNT}")
    if len(first) != EXPECTED_FIRST_HOLDOUT_COUNT:
        raise RuntimeError(f"STOP: First-Holdout-Anzahl {len(first)} != erwartet {EXPECTED_FIRST_HOLDOUT_COUNT}")
    if len(second) != EXPECTED_SECOND_HOLDOUT_COUNT:
        raise RuntimeError(f"STOP: Second-Holdout-Anzahl {len(second)} != erwartet {EXPECTED_SECOND_HOLDOUT_COUNT}")
    # Die historischen 0.8.12.1/0.8.14 Referenz-Hashes sind SHA256 der CSV-Dateien,
    # nicht Hashes einer normalisierten Symbolliste. Deshalb muessen hier die
    # Originaldateien bytegenau geprueft werden.
    first_file_hash = sha256_file(first_path)
    second_file_hash = sha256_file(second_path)
    if first_file_hash != EXPECTED_FIRST_HOLDOUT_HASH:
        raise RuntimeError(
            f"STOP: First-Holdout-Dateihash stimmt nicht mit 0.8.12.1 ueberein.\n"
            f"Ist:      {first_file_hash}\nErwartet: {EXPECTED_FIRST_HOLDOUT_HASH}"
        )
    if second_file_hash != EXPECTED_SECOND_HOLDOUT_HASH:
        raise RuntimeError(
            f"STOP: Second-Holdout-Dateihash stimmt nicht mit 0.8.14 ueberein.\n"
            f"Ist:      {second_file_hash}\nErwartet: {EXPECTED_SECOND_HOLDOUT_HASH}"
        )

    previous_all = discovery | first | second
    print(f"Einzigartige bereits verwendete:     {len(previous_all)}")
    print("First-/Second-Holdout-Dateihashes:     OK")
    print(f"First-Holdout-Symbolhash (Info):       {symbol_hash(first)}")
    print(f"Second-Holdout-Symbolhash (Info):      {symbol_hash(second)}\n")

    print("Lade offizielle NASDAQ Trader Symbol Directory Dateien ...")
    nasdaq_text = download_text(NASDAQ_LISTED_URL)
    other_text = download_text(OTHER_LISTED_URL)
    nasdaq_rows = parse_pipe_table(nasdaq_text)
    other_rows = parse_pipe_table(other_text)
    print(f"NASDAQ Listed Rohzeilen:              {len(nasdaq_rows)}")
    print(f"Other Listed Rohzeilen:               {len(other_rows)}")

    all_eligible = build_candidate_pool(nasdaq_rows, other_rows)
    unseen_pool = all_eligible[~all_eligible["Symbol"].isin(previous_all)].copy().reset_index(drop=True)
    sample = choose_sample(unseen_pool)
    overlap = set(sample["Symbol"]) & previous_all

    if overlap:
        raise RuntimeError(f"STOP: Third-Holdout hat Overlap mit bereits verwendeten Symbolen: {sorted(overlap)[:20]}")
    if len(sample) < 300:
        raise RuntimeError(f"STOP: Zu wenige neue Symbole ({len(sample)}). Quelle/Filter pruefen.")

    paths = {
        "universe": DATA_DIR / "TradePilot_Third_Holdout_Universe_0.8.18.csv",
        "excluded": Path(__file__).resolve().parent / "TradePilot_0_8_18_EXCLUDED_PREVIOUSLY_USED.csv",
        "hypotheses": Path(__file__).resolve().parent / "TradePilot_0_8_18_FROZEN_HYPOTHESES.csv",
        "lock": Path(__file__).resolve().parent / "TradePilot_0_8_18_THIRD_HOLDOUT_LOCK.json",
    }
    source_meta = {
        "nasdaq_listed_bytes": len(nasdaq_text.encode("utf-8")),
        "other_listed_bytes": len(other_text.encode("utf-8")),
        "nasdaq_listed_sha256": hashlib.sha256(nasdaq_text.encode("utf-8")).hexdigest(),
        "other_listed_sha256": hashlib.sha256(other_text.encode("utf-8")).hexdigest(),
    }
    lock = write_outputs(previous_all, unseen_pool, sample, paths, source_meta)

    print("\n" + "=" * 120)
    print("THIRD HOLDOUT ERFOLGREICH EINGEFROREN")
    print("=" * 120)
    print(f"Boersenlistings nach Security-Filtern:   {len(all_eligible)}")
    print(f"Davon bereits verwendet ausgeschlossen: {len(all_eligible) - len(unseen_pool)}")
    print(f"Eligible ungesehener Pool:               {len(unseen_pool)}")
    print(f"Finale Third-Holdout-Symbole:            {len(sample)}")
    print(f"Overlap mit ALLEN bisherigen Symbolen:   {len(overlap)}")
    print(f"Third-Holdout-Hash:                      {lock['hashes']['third_holdout_symbol_hash']}")
    print(f"Eligible-Pool-Hash:                      {lock['hashes']['eligible_pool_symbol_hash']}")
    print(f"Universum gespeichert:                   {paths['universe']}")
    print(f"Lock/Audit:                              {paths['lock']}")
    print(f"Frozen Hypothesis:                       {paths['hypotheses']}")
    print("\nVOR 0.8.19 EINGEFROREN:")
    print("- H1 bleibt U>=70 / E>=70.")
    print("- Primaerer Endpunkt ist FIRST_SIGNAL_PER_STOCK_12M.")
    print("- PASS/WATCH/FAIL-Regeln duerfen nach Einsicht in 0.8.19 nicht geaendert werden.")
    print("- Raw-H1, Modelle und Regime sind nur sekundaer/diagnostisch.")
    print("- 0.8.18 hat KEINE Produktions-Scorelogik veraendert.")
    print("=" * 120)


if __name__ == "__main__":
    main()
