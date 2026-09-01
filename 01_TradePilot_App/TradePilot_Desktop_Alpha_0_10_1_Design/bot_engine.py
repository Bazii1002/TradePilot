import os
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import requests
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# SINGLE INSTANCE - verhindert parallele Echtgeld-Bot-Läufe
# ============================================================

BOT_MUTEX_HANDLE = None

if os.name == "nt":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    BOT_MUTEX_HANDLE = kernel32.CreateMutexW(
        None,
        False,
        "Global\\TradePilot_eToro_Real_Bot"
    )

    if kernel32.GetLastError() == 183:
        raise SystemExit(
            "Bot läuft bereits. Zweiter Start wurde aus Sicherheitsgründen verhindert."
        )

# ============================================================
# TRADEPILOT TRADING MODE - DEMO / REAL
# 0.6.6.4: Safe Trading Mode Switch
# ============================================================

load_dotenv()

BOT_VERSION = "0.10.0-alpha"
TRADING_MODE = os.getenv("TRADING_MODE", "DEMO").strip().upper()
REAL_TRADING_CONFIRMATION = os.getenv("REAL_TRADING_CONFIRMATION", "").strip().upper()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if TRADING_MODE not in {"DEMO", "REAL"}:
    raise SystemExit("TRADING_MODE ungültig. Erlaubt sind nur DEMO oder REAL.")

# Public/API-Key kann gemeinsam sein. Der User-Key ist bei eToro
# an die jeweilige Umgebung (Virtual/Demo bzw. Real) gebunden.
if TRADING_MODE == "DEMO":
    ETORO_API_KEY = (
        os.getenv("ETORO_DEMO_API_KEY")
        or os.getenv("ETORO_API_KEY")
    )
    ETORO_USER_KEY = os.getenv("ETORO_DEMO_USER_KEY")
else:
    ETORO_API_KEY = (
        os.getenv("ETORO_REAL_API_KEY")
        or os.getenv("ETORO_API_KEY")
    )
    ETORO_USER_KEY = (
        os.getenv("ETORO_REAL_USER_KEY")
        or os.getenv("ETORO_USER_KEY")
    )

if not ETORO_API_KEY:
    raise SystemExit(
        f"Kein eToro API-Key für {TRADING_MODE} gefunden."
    )
if not ETORO_USER_KEY:
    if TRADING_MODE == "DEMO":
        raise SystemExit(
            "ETORO_DEMO_USER_KEY fehlt in .env. "
            "Für DEMO muss bewusst ein Virtual/Demo User-Key hinterlegt werden."
        )
    raise SystemExit(
        "ETORO_REAL_USER_KEY bzw. ETORO_USER_KEY fehlt in .env"
    )
if not OPENAI_API_KEY:
    raise SystemExit("OPENAI_API_KEY fehlt in .env")

# Zweite, unabhängige Echtgeld-Schranke.
if TRADING_MODE == "REAL" and REAL_TRADING_CONFIRMATION != "YES":
    raise SystemExit(
        "REAL TRADING gesperrt. Für Echtgeld sind BEIDE Einstellungen nötig: "
        "TRADING_MODE=REAL und REAL_TRADING_CONFIRMATION=YES"
    )

BASE_V1 = "https://public-api.etoro.com/api/v1"
BASE_V2 = "https://public-api.etoro.com/api/v2"
INSTRUMENT_DIRECTORY_URL = f"{BASE_V1}/market-data/instruments"
_instrument_directory_cache = None

if TRADING_MODE == "DEMO":
    ORDER_URL = f"{BASE_V2}/trading/execution/demo/orders"
    ORDER_LOOKUP_V2 = f"{BASE_V2}/trading/info/demo/orders:lookup"
    PORTFOLIO_URL = f"{BASE_V1}/trading/info/demo/portfolio"
    PNL_URL = f"{BASE_V1}/trading/info/demo/pnl"
    CLOSE_BASE_URL = f"{BASE_V1}/trading/execution/demo/market-close-orders/positions"
else:
    ORDER_URL = f"{BASE_V2}/trading/execution/orders"
    ORDER_LOOKUP_V2 = f"{BASE_V2}/trading/info/orders:lookup"
    PORTFOLIO_URL = f"{BASE_V1}/trading/info/portfolio"
    PNL_URL = f"{BASE_V1}/trading/info/real/pnl"
    CLOSE_BASE_URL = f"{BASE_V1}/trading/execution/market-close-orders/positions"

MODE_LABEL = "DEMO" if TRADING_MODE == "DEMO" else "REAL"

# eToro GET-Anfragen bewusst drosseln.
# 1.30 s Abstand entspricht maximal ca. 46 GETs/Minute.
API_GET_MIN_INTERVAL_SECONDS = 1.30
API_GET_429_MAX_RETRIES = 3
_last_api_get_monotonic = 0.0

VIENNA_TZ = ZoneInfo("Europe/Vienna")
NEW_YORK_TZ = ZoneInfo("America/New_York")

# Für den Start mit ca. 500 EUR bewusst konservativ.
# eToro Orderbetrag wird in USD übergeben.
MAX_STOCK_POSITIONS = 2
STOCK_POSITION_USD = 100.0
MAX_CRYPTO_POSITIONS = 1
CRYPTO_POSITION_USD = 100.0
MAX_TOTAL_POSITIONS = 3

# Frühere Gewinnmitnahme für Aktien
STOCK_EARLY_PROFIT_1 = 2.0
STOCK_EARLY_PROFIT_1_MAX_SCORE = 69
STOCK_EARLY_PROFIT_2 = 3.0
STOCK_EARLY_PROFIT_2_MAX_SCORE = 79

# Engerer Gewinnschutz, sobald eine Aktie bereits gut im Plus war.
STOCK_TRAIL_LEVEL_1_MAX = 4.0
STOCK_TRAIL_LEVEL_1_FLOOR = 2.0
STOCK_TRAIL_LEVEL_2_MAX = 5.0
STOCK_TRAIL_LEVEL_2_FLOOR = 3.0
STOCK_TRAIL_LEVEL_3_MAX = 6.0
STOCK_TRAIL_LEVEL_3_FLOOR = 4.0
STOCK_TRAIL_LEVEL_4_MAX = 7.0
STOCK_TRAIL_LEVEL_4_FLOOR = 5.0

STOCK_STOP_LOSS_PERCENT = -5.0
STOCK_TAKE_PROFIT_PERCENT = 10.0
CRYPTO_STOP_LOSS_PERCENT = -7.0
CRYPTO_TAKE_PROFIT_PERCENT = 14.0
MIN_AI_CONFIDENCE = 70

STOCK_UNIVERSE_FILE = "stock_universe.json"
MAX_AI_STOCK_CANDIDATES = 8
STOCK_AI_PRESELECT_SCORE = 70

# Echtgeld-Sicherheitsgrenzen
DAILY_LOSS_LIMIT_USD = -15.0
MAX_BOT_DRAWDOWN_USD = -50.0

# News-/Event-Risiko
NEWS_MAX_HEADLINES_PER_SYMBOL = 8
NEWS_BLOCK_SCORE = -20
EVENT_BLOCK_HOURS = 2

# Frei zugänglicher US-Makro-Kalender (kein API-Key)
ECONOMIC_CALENDAR_URL = "https://xoomar.com/api/markets/calendar"

INSTRUMENT_CACHE_FILE = "instrument_ids.json"

# DEMO und REAL teilen niemals Positions-/Trade-/State-Dateien.
# So kann ein Testlauf keine Echtgeld-Zustände überschreiben.
if TRADING_MODE == "DEMO":
    STATE_FILE = "demo_bot_state.json"
    BOT_POSITIONS_FILE = "etoro_demo_positions.json"
    BOT_TRADES_FILE = "etoro_demo_trades.json"
    TRADE_LOG_FILE = "demo_trade_log.txt"
    ORDER_DIAGNOSTICS_FILE = "demo_order_diagnostics.log"
    DAILY_CLOSE_STATE_FILE = "demo_daily_close_state.json"
else:
    STATE_FILE = "real_bot_state.json"
    BOT_POSITIONS_FILE = "etoro_real_positions.json"
    BOT_TRADES_FILE = "etoro_real_trades.json"
    TRADE_LOG_FILE = "real_trade_log.txt"
    ORDER_DIAGNOSTICS_FILE = "real_order_diagnostics.log"
    DAILY_CLOSE_STATE_FILE = "real_daily_close_state.json"

DASHBOARD_SNAPSHOT_FILE = "latest_analysis.json"

# ============================================================
# TRADEPILOT DESKTOP APP CONFIG
# ============================================================

APP_CONFIG_FILE = "tradepilot_app_config.json"


def load_app_config():
    defaults = {
        "strategy_level": 1,
        "max_trades_per_day": 5,
        "max_invested_usd": 500.0,
        "position_size_usd": 100.0,
        "max_total_positions": 3,
        "bot_enabled": False,
        "run_interval_minutes": 5,
    }
    try:
        if os.path.exists(APP_CONFIG_FILE):
            with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                defaults.update(raw)
    except Exception as e:
        print("APP CONFIG konnte nicht geladen werden:", e)
    return defaults


APP_CONFIG = load_app_config()
STRATEGY_LEVEL = max(1, min(int(APP_CONFIG.get("strategy_level", 1)), 4))
MAX_TRADES_PER_DAY = max(0, int(APP_CONFIG.get("max_trades_per_day", 5)))
MAX_INVESTED_USD = max(0.0, float(APP_CONFIG.get("max_invested_usd", 500.0)))
POSITION_SIZE_USD = max(1.0, float(APP_CONFIG.get("position_size_usd", 100.0)))
MAX_TOTAL_POSITIONS = max(1, int(APP_CONFIG.get("max_total_positions", MAX_TOTAL_POSITIONS)))
STOCK_POSITION_USD = POSITION_SIZE_USD
CRYPTO_POSITION_USD = POSITION_SIZE_USD

STRATEGY_NAMES = {
    1: "FAST",
    2: "DAY",
    3: "WEEK",
    4: "INVEST",
}


def successful_buys_today(bot_trades):
    today = datetime.now(VIENNA_TZ).date()
    count = 0
    for trade in bot_trades:
        if trade.get("type") not in ["BUY_CONFIRMED", "BUY_REQUEST_PENDING"]:
            continue
        raw_time = str(trade.get("time", ""))
        try:
            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt.astimezone(VIENNA_TZ).date() == today:
                count += 1
        except Exception:
            continue
    return count


def bot_invested_usd(bot_positions):
    total = 0.0
    for position in bot_positions:
        if position.get("status") not in ["OPEN", "PENDING", "CLOSING"]:
            continue
        try:
            total += float(position.get("amount_usd", 0.0) or 0.0)
        except Exception:
            pass
    return total


def app_buy_limits_allow(bot_positions, bot_trades, amount):
    trades_today = successful_buys_today(bot_trades)
    invested = bot_invested_usd(bot_positions)

    if MAX_TRADES_PER_DAY >= 0 and trades_today >= MAX_TRADES_PER_DAY:
        print(
            f"APP LIMIT: Tageslimit erreicht "
            f"({trades_today}/{MAX_TRADES_PER_DAY}) -> BUY blockiert."
        )
        return False

    if invested + float(amount) > MAX_INVESTED_USD + 1e-9:
        print(
            f"APP LIMIT: Kapitalgrenze würde überschritten "
            f"({invested:.2f} + {float(amount):.2f} > {MAX_INVESTED_USD:.2f} USD) "
            "-> BUY blockiert."
        )
        return False

    return True


CRYPTO_WATCHLIST = [
    {"key":"BTC","name":"Bitcoin","market":"CRYPTO","asset_type":"CRYPTO","aliases":["BTC"]},
    {"key":"ETH","name":"Ethereum","market":"CRYPTO","asset_type":"CRYPTO","aliases":["ETH"]},
    {"key":"SOL","name":"Solana","market":"CRYPTO","asset_type":"CRYPTO","aliases":["SOL"]},
]


def load_stock_universe():
    raw = load_json(STOCK_UNIVERSE_FILE, [])
    stocks = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        if item.get("enabled", True) is False:
            continue

        symbol = str(item.get("symbol", "")).strip()
        market = str(item.get("market", "")).strip().upper()

        if not symbol or market not in ["US", "EU"]:
            continue

        aliases = item.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            aliases = [symbol]

        aliases = [
            str(alias).strip()
            for alias in aliases
            if str(alias).strip()
        ]

        if not aliases:
            aliases = [symbol]

        stocks.append({
            "key": symbol,
            "name": str(item.get("name", symbol)).strip(),
            "market": market,
            "asset_type": "STOCK",
            "aliases": aliases,
        })

    return stocks


client = OpenAI(api_key=OPENAI_API_KEY)


def utc_now_string():
    return datetime.now(timezone.utc).isoformat()


def vienna_now_string():
    return datetime.now(VIENNA_TZ).strftime("%d.%m.%Y %H:%M:%S")


def write_trade_log(text):
    line = f"{vienna_now_string()} | {text}"
    with open(TRADE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("TRADE LOG:", line)


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_headers():
    return {
        "x-api-key": ETORO_API_KEY,
        "x-user-key": ETORO_USER_KEY,
        "x-request-id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }


def walk_dicts(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from walk_dicts(value)
    elif isinstance(data, list):
        for item in data:
            yield from walk_dicts(item)


def recursive_value(data, keys):
    for item in walk_dicts(data):
        for key in keys:
            if key in item and item[key] is not None:
                return item[key]
    return None


def api_get(url, params=None, timeout=30):
    global _last_api_get_monotonic

    for attempt in range(API_GET_429_MAX_RETRIES + 1):
        elapsed = (
            time.monotonic()
            - _last_api_get_monotonic
        )

        wait_for = (
            API_GET_MIN_INTERVAL_SECONDS
            - elapsed
        )

        if wait_for > 0:
            time.sleep(wait_for)

        r = requests.get(
            url,
            headers=make_headers(),
            params=params,
            timeout=timeout
        )

        _last_api_get_monotonic = (
            time.monotonic()
        )

        if r.status_code == 429:
            if attempt >= API_GET_429_MAX_RETRIES:
                raise Exception(
                    "eToro Rate Limit HTTP 429 "
                    "nach mehreren Warteversuchen"
                )

            retry_after = r.headers.get(
                "Retry-After"
            )

            try:
                wait_seconds = max(
                    10.0,
                    float(retry_after)
                )
            except Exception:
                wait_seconds = (
                    15.0
                    * (attempt + 1)
                )

            print(
                f"eToro Rate Limit 429 - "
                f"warte {wait_seconds:.0f}s "
                f"und versuche GET erneut..."
            )

            time.sleep(
                wait_seconds
            )
            continue

        if r.status_code != 200:
            raise Exception(
                f"GET {r.status_code}: "
                f"{r.text[:500]}"
            )

        return r.json()

    raise Exception(
        "eToro GET konnte nicht abgeschlossen werden"
    )


def write_order_diagnostic(title, details):
    timestamp = datetime.now(VIENNA_TZ).strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    with open(
        ORDER_DIAGNOSTICS_FILE,
        "a",
        encoding="utf-8"
    ) as f:
        f.write(
            "\n"
            + "=" * 80
            + "\n"
        )
        f.write(
            f"{timestamp} | {title}\n"
        )
        f.write(
            "=" * 80
            + "\n"
        )
        f.write(
            str(details)
            + "\n"
        )


def api_post(url, payload, timeout=30):
    # Execution-POSTs absichtlich NIE automatisch wiederholen.
    # Ein Timeout kann bedeuten, dass eToro die Order trotzdem erhalten hat.
    request_id = str(uuid.uuid4())

    headers = {
        "x-api-key": ETORO_API_KEY,
        "x-user-key": ETORO_USER_KEY,
        "x-request-id": request_id,
        "Content-Type": "application/json",
    }

    safe_payload = dict(payload)

    diagnostic_request = {
        "request_id": request_id,
        "url": url,
        "payload": safe_payload,
    }

    print()
    print("----- ETORO ORDER DIAGNOSE -----")
    print(f"Request-ID: {request_id}")
    print(f"Endpoint:   {url}")
    print(
        "Payload:    "
        + json.dumps(
            safe_payload,
            ensure_ascii=False
        )
    )

    write_order_diagnostic(
        "ORDER REQUEST",
        json.dumps(
            diagnostic_request,
            ensure_ascii=False,
            indent=2
        )
    )

    try:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout
        )
    except requests.Timeout as e:
        msg = (
            "POST TIMEOUT. Orderstatus ist UNBEKANNT. "
            "Aus Sicherheitsgründen erfolgt KEIN automatischer Retry."
        )

        print(msg)

        write_order_diagnostic(
            "ORDER TIMEOUT",
            f"{type(e).__name__}: {e}"
        )

        raise Exception(msg) from e

    except Exception as e:
        write_order_diagnostic(
            "ORDER REQUEST ERROR",
            f"{type(e).__name__}: {e}"
        )
        raise

    response_text = (
        r.text.strip()
        if r.text
        else ""
    )

    print(
        f"HTTP Status: {r.status_code}"
    )
    print(
        "Response: "
        + (
            response_text[:4000]
            if response_text
            else "<leer>"
        )
    )
    print("-------------------------------")

    diagnostic_response = {
        "request_id": request_id,
        "http_status": r.status_code,
        "response_headers": dict(r.headers),
        "response_body": response_text[:10000],
    }

    write_order_diagnostic(
        "ORDER RESPONSE",
        json.dumps(
            diagnostic_response,
            ensure_ascii=False,
            indent=2
        )
    )

    if r.status_code not in (
        200,
        201,
        202
    ):
        raise Exception(
            f"POST {r.status_code}: "
            f"{response_text[:2000]}"
        )

    if not response_text:
        return {
            "_http_status": r.status_code,
            "_request_id": request_id,
            "_empty_response": True,
        }

    try:
        data = r.json()
    except Exception:
        data = {
            "_raw_text": response_text,
        }

    if isinstance(data, dict):
        data.setdefault(
            "_http_status",
            r.status_code
        )
        data.setdefault(
            "_request_id",
            request_id
        )

    return data


def is_market_open_now(market):
    if market == "CRYPTO":
        return True
    if market == "US":
        now = datetime.now(NEW_YORK_TZ)
        if now.weekday() >= 5:
            return False
        m = now.hour * 60 + now.minute
        return 9*60+30 <= m < 16*60
    now = datetime.now(VIENNA_TZ)
    if now.weekday() >= 5:
        return False
    m = now.hour * 60 + now.minute
    return 9*60 <= m < 17*60+30


def get_position_id(item):
    for key in ["positionId","positionID","PositionId","PositionID"]:
        if key in item:
            try:
                return int(item[key])
            except Exception:
                pass
    return None


def get_instrument_id(item):
    for key in ["instrumentId","instrumentID","InstrumentId","InstrumentID","internalInstrumentId"]:
        if key in item:
            try:
                return int(item[key])
            except Exception:
                pass
    return None


def get_real_portfolio_raw():
    return api_get(PORTFOLIO_URL)


def get_real_pnl_raw():
    return api_get(PNL_URL)


def extract_real_positions(data):
    positions, seen = [], set()
    for item in walk_dicts(data):
        pid = get_position_id(item)
        iid = get_instrument_id(item)
        if pid is None or iid is None or pid in seen:
            continue
        seen.add(pid)
        positions.append({"position_id":pid,"instrument_id":iid,"raw":item})
    return positions


def extract_position_pnl_map(data):
    result = {}
    for item in walk_dicts(data):
        pid = get_position_id(item)
        if pid is None:
            continue
        amount = item.get("amount")
        unrealized = item.get("unrealizedPnL")
        if not isinstance(unrealized, dict):
            continue
        pnl = unrealized.get("pnL", unrealized.get("pnl"))
        try:
            amount, pnl = float(amount), float(pnl)
        except Exception:
            continue
        if amount <= 0:
            continue
        result[pid] = {"amount":amount,"pnl_usd":pnl,"pnl_percent":pnl/amount*100}
    return result


def position_asset_type(position):
    if position.get("asset_type"):
        return position["asset_type"]
    return "CRYPTO" if position.get("market") == "CRYPTO" else "STOCK"


def bot_has_position(bot_positions, symbol):
    return any(p.get("symbol") == symbol and p.get("status") in ["OPEN","PENDING","CLOSING"] for p in bot_positions)


def active_position_counts(bot_positions):
    stock = crypto = 0
    for p in bot_positions:
        if p.get("status") not in ["OPEN","PENDING","CLOSING"]:
            continue
        if position_asset_type(p) == "CRYPTO":
            crypto += 1
        else:
            stock += 1
    return stock, crypto


def real_portfolio_has_instrument(instrument_id):
    # Fail closed: wenn Portfolio nicht gelesen werden kann, wird BUY blockiert.
    try:
        return any(int(p["instrument_id"]) == int(instrument_id) for p in extract_real_positions(get_real_portfolio_raw()))
    except Exception as e:
        print("Portfolio-Prüfung fehlgeschlagen -> BUY blockiert:", e)
        return True


def extract_search_symbol(item):
    """
    Liest ein eToro-Symbol aus Search- oder Instrument-Directory-Daten.

    Search liefert typischerweise internalSymbolFull, während das
    Instrument-Directory symbolFull verwenden kann.
    """
    if not isinstance(item, dict):
        return None

    for key in [
        "internalSymbolFull",
        "symbolFull",
        "symbol",
        "symbolName",
        "ticker",
    ]:
        value = item.get(key)
        if value:
            return str(value).strip().upper()
    return None


def search_exact_symbol(symbol):
    """
    Primäre Instrument-Auflösung über /market-data/search.

    Es wird ausschließlich ein exakter Symboltreffer mit positiver
    Instrument-ID akzeptiert. Mehrere unterschiedliche IDs für dasselbe
    Symbol werden aus Sicherheitsgründen nicht automatisch ausgewählt.
    """
    target = str(symbol).strip().upper()
    data = api_get(
        f"{BASE_V1}/market-data/search",
        params={
            "internalSymbolFull": target,
            "fields": (
                "instrumentId,internalInstrumentId,"
                "internalSymbolFull,displayname"
            ),
        },
        timeout=20,
    )

    matches = {}
    for item in walk_dicts(data):
        iid = get_instrument_id(item)
        if (
            extract_search_symbol(item) == target
            and iid is not None
            and iid > 0
        ):
            matches[int(iid)] = {
                "instrument_id": int(iid),
                "etoro_symbol": target,
            }

    if len(matches) == 1:
        return next(iter(matches.values()))

    if len(matches) > 1:
        print(
            f"{target}: SEARCH uneindeutig - "
            f"{len(matches)} verschiedene Instrument-IDs gefunden."
        )

    return None


def load_instrument_directory():
    """
    Lädt das eToro Instrument Directory höchstens einmal pro Bot-Lauf.

    0.6.6.3 Fallback: Der Metadaten-Endpunkt /market-data/instruments
    wird nur benötigt, wenn die normale Search-Auflösung keinen sicheren
    Treffer liefert. Das Ergebnis wird im RAM gehalten, damit mehrere
    Fallbacks nicht jedes Mal einen weiteren großen GET auslösen.
    """
    global _instrument_directory_cache

    if _instrument_directory_cache is not None:
        return _instrument_directory_cache

    print("Instrument Directory Fallback: lade eToro Instrument-Metadaten...")

    try:
        data = api_get(
            INSTRUMENT_DIRECTORY_URL,
            timeout=30,
        )
    except Exception as e:
        print("Instrument Directory nicht verfügbar:", e)
        _instrument_directory_cache = {}
        return _instrument_directory_cache

    if not isinstance(data, (dict, list)):
        print("Instrument Directory: unerwartetes Antwortformat.")
        _instrument_directory_cache = {}
        return _instrument_directory_cache

    _instrument_directory_cache = data
    return _instrument_directory_cache


def search_instrument_directory_exact(symbol):
    """
    Sucht im Instrument Directory nach einem EXAKTEN Symbol.

    Kein Fuzzy Matching und kein Raten: Nur genau ein eindeutiger Treffer
    wird akzeptiert. Das schützt den Echtgeld-Bot vor einer falschen
    Instrument-ID.
    """
    target = str(symbol).strip().upper()
    data = load_instrument_directory()

    matches = {}

    for item in walk_dicts(data):
        iid = get_instrument_id(item)
        item_symbol = extract_search_symbol(item)

        if (
            item_symbol == target
            and iid is not None
            and iid > 0
        ):
            matches[int(iid)] = {
                "instrument_id": int(iid),
                "etoro_symbol": target,
            }

    if len(matches) == 1:
        found = next(iter(matches.values()))
        print(
            f"{target}: Instrument Directory Treffer "
            f"-> ID {found['instrument_id']}"
        )
        return found

    if len(matches) > 1:
        print(
            f"{target}: Instrument Directory uneindeutig - "
            f"{len(matches)} verschiedene Instrument-IDs. "
            "Aus Sicherheitsgründen BLOCKIERT."
        )
    else:
        print(f"{target}: auch im Instrument Directory nicht gefunden.")

    return None


def resolve_instrument(config, cache):
    """
    Instrument-Auflösung 0.6.6.3:

    1. Lokaler Instrument-Cache
    2. Exakte eToro Search-Suche für alle Aliase
    3. Instrument Directory Fallback für alle Aliase
    4. Kein sicherer Treffer -> Instrument wird nicht verwendet
    """
    key = config["key"]

    # 1) CACHE - nur positive Integer-IDs akzeptieren.
    if key in cache:
        cached = cache[key]

        try:
            iid = int(
                cached["instrument_id"]
                if isinstance(cached, dict)
                else cached
            )
        except Exception:
            iid = 0

        if iid > 0:
            return {
                **config,
                "instrument_id": iid,
                "source": "CACHE",
            }

        print(f"{key}: ungültiger Instrument-Cache -> Eintrag wird entfernt.")
        cache.pop(key, None)
        save_json(INSTRUMENT_CACHE_FILE, cache)

    aliases = [
        str(alias).strip().upper()
        for alias in config.get("aliases", [])
        if str(alias).strip()
    ]

    if not aliases:
        aliases = [str(key).strip().upper()]

    # 2) NORMALE SEARCH API
    for alias in aliases:
        found = search_exact_symbol(alias)
        if found:
            cache[key] = found
            save_json(INSTRUMENT_CACHE_FILE, cache)
            return {
                **config,
                "instrument_id": int(found["instrument_id"]),
                "source": "SEARCH",
            }

    # 3) 0.6.6.3 - INSTRUMENT DIRECTORY FALLBACK
    print(f"{key}: Search ohne Treffer -> Instrument Directory Fallback")

    for alias in aliases:
        found = search_instrument_directory_exact(alias)
        if found:
            cache[key] = found
            save_json(INSTRUMENT_CACHE_FILE, cache)
            return {
                **config,
                "instrument_id": int(found["instrument_id"]),
                "source": "DIRECTORY",
            }

    # 4) FAIL CLOSED
    print(
        f"{key}: keine sichere Instrument-ID gefunden "
        "-> Instrument wird übersprungen."
    )
    return None

def get_candles(instrument_id, interval, count):
    url = f"{BASE_V1}/market-data/instruments/{instrument_id}/history/candles/asc/{interval}/{count}"
    data = api_get(url, timeout=20)
    groups = data.get("candles", [])
    if not groups or not groups[0].get("candles"):
        raise Exception("Keine Candles")
    df = pd.DataFrame(groups[0]["candles"])
    df["fromDate"] = pd.to_datetime(df["fromDate"], utc=True)
    return df


def remove_open_candle(df, interval):
    now = pd.Timestamp.now(tz="UTC")
    last = df.iloc[-1]["fromDate"]
    if interval == "OneHour" and last.floor("h") == now.floor("h"):
        return df.iloc[:-1].copy()
    if interval == "OneDay" and last.date() == now.date():
        return df.iloc[:-1].copy()
    return df.copy()


def add_indicators(df):
    df = df.copy()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["EMA200"] = df["close"].ewm(span=200, adjust=False).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))
    return df


def add_market_time(df, market):
    df = df.copy()
    if market == "CRYPTO":
        tz, valid = timezone.utc, list(range(24))
    elif market == "US":
        tz, valid = NEW_YORK_TZ, [10,11,12,13,14,15]
    else:
        tz, valid = VIENNA_TZ, [10,11,12,13,14,15,16]
    df["market_time"] = df["fromDate"].dt.tz_convert(tz)
    df["market_hour"] = df["market_time"].dt.hour
    return df, valid


def score_1h(asset_type, close, e20, e50, e200, rsi, momentum, volume_ratio):
    s = 0
    s += 15 if close > e20 else 0
    s += 15 if close > e50 else 0
    s += 10 if close > e200 else 0
    s += 10 if e50 > e200 else 0
    if asset_type == "CRYPTO":
        s += 15 if 48 <= rsi <= 65 else 8 if 65 < rsi <= 72 else 0
        s += 20 if momentum >= 4 else 15 if momentum >= 2 else 8 if momentum >= 0 else 0
    else:
        s += 15 if 50 <= rsi <= 65 else 8 if 65 < rsi <= 70 else 0
        s += 20 if momentum >= 2 else 15 if momentum >= 1 else 8 if momentum >= 0 else 0
    if volume_ratio is not None:
        s += 15 if volume_ratio >= 1.5 else 10 if volume_ratio >= 1.2 else 5 if volume_ratio >= 0.8 else 0
    return s


def score_daily(asset_type, close, e20, e50, e200, rsi):
    s = 0
    s += 20 if close > e20 else 0
    s += 20 if close > e50 else 0
    s += 20 if close > e200 else 0
    s += 20 if e50 > e200 else 0
    if asset_type == "CRYPTO":
        s += 20 if 45 <= rsi <= 68 else 10 if 68 < rsi <= 75 else 0
    else:
        s += 20 if 45 <= rsi <= 65 else 10 if 65 < rsi <= 70 else 0
    return s


def analyze_instrument(instrument):
    market = instrument["market"]
    asset = instrument["asset_type"]
    iid = int(instrument["instrument_id"])

    h = add_indicators(remove_open_candle(get_candles(iid,"OneHour",500),"OneHour"))
    if len(h) < 210:
        raise Exception("Zu wenige 1H-Candles")
    h, valid_hours = add_market_time(h, market)
    latest = h.iloc[-1]
    close = float(latest["close"])
    momentum = ((close / float(h.iloc[-6]["close"])) - 1) * 100
    current_volume = None
    try:
        if latest.get("volume") is not None:
            current_volume = float(latest.get("volume"))
    except Exception:
        pass
    volume_ratio = None
    if current_volume is not None and "volume" in h.columns:
        refs = h[(h["market_hour"] == int(latest["market_hour"])) & (h["fromDate"] < latest["fromDate"])]["volume"].dropna().tail(10)
        if len(refs) >= 3:
            try:
                med = float(refs.median())
                if pd.notna(med) and med > 0:
                    volume_ratio = current_volume / med
            except Exception:
                pass

    s1 = score_1h(asset, close, float(latest["EMA20"]), float(latest["EMA50"]), float(latest["EMA200"]), float(latest["RSI14"]), momentum, volume_ratio)

    d = add_indicators(remove_open_candle(get_candles(iid,"OneDay",300),"OneDay"))
    if len(d) < 210:
        raise Exception("Zu wenige Daily-Candles")
    day = d.iloc[-1]
    sd = score_daily(asset, float(day["close"]), float(day["EMA20"]), float(day["EMA50"]), float(day["EMA200"]), float(day["RSI14"]))
    total = int(round(s1*0.60 + sd*0.40))
    daily_bullish = float(day["close"]) > float(day["EMA50"]) and float(day["close"]) > float(day["EMA200"])
    market_open = is_market_open_now(market)
    candle_regular = int(latest["market_hour"]) in valid_hours

    if not market_open or not candle_regular or not daily_bullish:
        tech = "NO_TRADE"
    elif total >= 85:
        tech = "STRONG_BUY"
    elif total >= 70:
        tech = "BUY"
    elif total >= 55:
        tech = "WAIT"
    else:
        tech = "NO_TRADE"

    chart_df = h.tail(80).copy()

    chart_data = {
        "time": [str(value) for value in chart_df["fromDate"].tolist()],
        "close": [round(float(value), 6) for value in chart_df["close"].tolist()],
        "ema20": [round(float(value), 6) for value in chart_df["EMA20"].tolist()],
        "ema50": [round(float(value), 6) for value in chart_df["EMA50"].tolist()],
        "ema200": [round(float(value), 6) for value in chart_df["EMA200"].tolist()],
    }

    return {
        "chart_data": chart_data,
        "symbol":instrument["key"],"name":instrument["name"],"market":market,"asset_type":asset,"instrument_id":iid,
        "candle_1h":str(latest["fromDate"]),"market_open_now":market_open,"candle_regular_session":candle_regular,
        "close_1h":round(close,4),"rsi_1h":round(float(latest["RSI14"]),2),"momentum_5h":round(momentum,2),
        "volume_ratio":round(volume_ratio,2) if volume_ratio is not None else None,
        "score_1h":s1,"score_daily":sd,"daily_bullish":daily_bullish,"total_score":total,"technical_signal":tech,
    }



# ============================================================
# NEWS + WIRTSCHAFTSKALENDER
# ============================================================

def fetch_google_news_headlines(query, max_items=8):
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}"
        "&hl=de&gl=AT&ceid=AT:de"
    )
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)

    items = []
    for item in root.findall("./channel/item")[:max_items]:
        title = item.findtext("title", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        source_el = item.find("source")
        source = (
            source_el.text.strip()
            if source_el is not None and source_el.text
            else "-"
        )
        if title:
            items.append({
                "title": title,
                "source": source,
                "pub_date": pub_date,
            })
    return items


def get_macro_events():
    now_utc = datetime.now(timezone.utc)
    start = (now_utc - timedelta(days=1)).date().isoformat()
    end = (now_utc + timedelta(days=2)).date().isoformat()

    try:
        response = requests.get(
            ECONOMIC_CALENDAR_URL,
            params={
                "from": start,
                "to": end,
                "importance": "high",
            },
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            data = payload.get("data", [])
        elif isinstance(payload, list):
            data = payload
        else:
            data = []

        events = []
        for event in data:
            if not isinstance(event, dict):
                continue

            scheduled = (
                event.get("scheduledAt")
                or event.get("scheduled_at")
                or event.get("date")
            )
            if not scheduled:
                continue

            events.append({
                "event_name": (
                    event.get("eventName")
                    or event.get("event_name")
                    or event.get("name")
                    or "-"
                ),
                "importance": (
                    event.get("importance")
                    or event.get("impact")
                    or "-"
                ),
                "scheduled_at": scheduled,
                "source": event.get("source", "-"),
                "actual": event.get("actual"),
                "previous": event.get("previous"),
            })

        return events

    except Exception as e:
        print("Wirtschaftskalender nicht verfügbar:", e)
        return []


def macro_event_risk_for_market(market, macro_events):
    if market != "US":
        return {
            "risk": "LOW",
            "next_event": None,
            "hours_to_event": None,
        }

    now_utc = datetime.now(timezone.utc)
    future = []

    for event in macro_events:
        try:
            raw = str(event["scheduled_at"])
            dt = datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            dt = dt.astimezone(timezone.utc)
            hours = (dt - now_utc).total_seconds() / 3600

            if hours >= 0:
                future.append((hours, event))
        except Exception:
            continue

    if not future:
        return {
            "risk": "LOW",
            "next_event": None,
            "hours_to_event": None,
        }

    future.sort(key=lambda item: item[0])
    hours, event = future[0]

    if hours <= EVENT_BLOCK_HOURS:
        risk = "HIGH"
    elif hours <= 6:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "risk": risk,
        "next_event": event,
        "hours_to_event": round(hours, 2),
    }


def analyze_news_for_result(result, macro_context):
    symbol = result["symbol"]
    name = result["name"]

    queries = [
        f"{symbol} {name} stock earnings company news",
        (
            "Federal Reserve inflation jobs stock market"
            if result["market"] == "US"
            else "ECB inflation Europe stock market economy"
        ),
    ]

    headlines = []

    for query in queries:
        try:
            headlines.extend(
                fetch_google_news_headlines(
                    query,
                    max_items=max(
                        1,
                        NEWS_MAX_HEADLINES_PER_SYMBOL // 2
                    )
                )
            )
        except Exception as e:
            print(f"{symbol}: News-Abfrage Fehler:", e)

    deduped = []
    seen = set()

    for item in headlines:
        key = item["title"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    headlines = deduped[:NEWS_MAX_HEADLINES_PER_SYMBOL]

    if not headlines:
        return {
            "news_score": 0,
            "news_risk": "MEDIUM",
            "news_summary": "Keine aktuellen Newsdaten verfügbar.",
            "news_headlines": [],
        }

    prompt = f"""
Du bist ein konservativer News-Risikofilter für einen Echtgeld-Trading-Bot.

Aktie: {symbol} - {name}
Markt: {result['market']}
Technischer Score: {result['total_score']}
Technisches Signal: {result['technical_signal']}

Makro-Kontext:
{json.dumps(macro_context, ensure_ascii=False, indent=2)}

Aktuelle Schlagzeilen:
{json.dumps(headlines, ensure_ascii=False, indent=2)}

Regeln:
- Positive News dürfen ein technisch schlechtes Setup NICHT zu BUY machen.
- Negative oder unsichere News dürfen einen Kauf blockieren.
- Bei widersprüchlichen Meldungen konservativ bleiben.
- Bewerte nur die gelieferten Schlagzeilen.

Antworte ausschließlich als JSON:
{{
  "news_score": 0,
  "news_risk": "LOW",
  "summary": "kurze Zusammenfassung auf Deutsch"
}}

news_score: -100 bis +100
news_risk: LOW, MEDIUM oder HIGH
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt
        )

        raw = (
            response.output_text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        data = json.loads(raw)

        score = int(data.get("news_score", 0))
        score = max(-100, min(score, 100))

        risk = str(
            data.get("news_risk", "MEDIUM")
        ).upper()

        if risk not in ["LOW", "MEDIUM", "HIGH"]:
            risk = "MEDIUM"

        return {
            "news_score": score,
            "news_risk": risk,
            "news_summary": str(data.get("summary", "")),
            "news_headlines": headlines,
        }

    except Exception as e:
        return {
            "news_score": 0,
            "news_risk": "MEDIUM",
            "news_summary": f"News-Auswertung fehlgeschlagen: {e}",
            "news_headlines": headlines,
        }


# ============================================================
# BOT-PERFORMANCE / RISK GUARD
# ============================================================

def calculate_bot_risk_state(bot_positions, bot_trades):
    open_pnl = 0.0

    try:
        pnl_map = extract_position_pnl_map(
            get_real_pnl_raw()
        )

        for position in bot_positions:
            if position.get("status") != "OPEN":
                continue

            position_id = position.get("position_id")
            pnl = pnl_map.get(position_id)

            if pnl:
                open_pnl += float(
                    pnl.get("pnl_usd", 0)
                )

    except Exception as e:
        print("Risk-Guard P/L konnte nicht gelesen werden:", e)

    realized_approx = 0.0
    today_realized_approx = 0.0
    today = datetime.now(VIENNA_TZ).date()

    for trade in bot_trades:
        if trade.get("type") != "CLOSE_REQUEST":
            continue

        pnl_usd = trade.get("pnl_usd")
        if pnl_usd is None:
            continue

        try:
            pnl_usd = float(pnl_usd)
        except Exception:
            continue

        realized_approx += pnl_usd

        try:
            raw_time = trade.get("time", "")
            dt = datetime.fromisoformat(
                raw_time.replace("Z", "+00:00")
            )

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=VIENNA_TZ)

            dt = dt.astimezone(VIENNA_TZ)

            if dt.date() == today:
                today_realized_approx += pnl_usd
        except Exception:
            pass

    bot_total_approx = realized_approx + open_pnl
    today_total_approx = today_realized_approx + open_pnl

    daily_block = (
        today_total_approx <= DAILY_LOSS_LIMIT_USD
    )
    drawdown_block = (
        bot_total_approx <= MAX_BOT_DRAWDOWN_USD
    )

    return {
        "open_pnl_usd": round(open_pnl, 2),
        "realized_approx_usd": round(realized_approx, 2),
        "today_realized_approx_usd": round(
            today_realized_approx,
            2
        ),
        "today_total_approx_usd": round(
            today_total_approx,
            2
        ),
        "bot_total_approx_usd": round(
            bot_total_approx,
            2
        ),
        "daily_loss_limit_usd": DAILY_LOSS_LIMIT_USD,
        "max_drawdown_usd": MAX_BOT_DRAWDOWN_USD,
        "daily_block": daily_block,
        "drawdown_block": drawdown_block,
        "new_buys_blocked": (
            daily_block or drawdown_block
        ),
    }



def ask_chatgpt(result):
    prompt = f'''Du bist der konservative Risiko- und Qualitätsfilter eines Trading-Bots.
Regeln: BUY nur bei technischem BUY/STRONG_BUY, daily_bullish=true, bei Unsicherheit WAIT, Risiko HIGH darf nie gekauft werden.
Du hast keine aktuellen Nachrichten.
Antworte ausschließlich als JSON: {{"signal":"WAIT","confidence":70,"risk":"MEDIUM","reason":"kurz"}}
Daten:\n{json.dumps(result, ensure_ascii=False, indent=2)}'''
    try:
        r = client.responses.create(model="gpt-5-mini", input=prompt)
        ai = json.loads(r.output_text.replace("```json","").replace("```","").strip())
        signal = str(ai.get("signal","ERROR")).upper()
        risk = str(ai.get("risk","UNKNOWN")).upper()
        conf = max(0,min(int(ai.get("confidence",0)),100))
        if signal not in ["BUY","WAIT","NO_TRADE"]:
            signal = "ERROR"
        if risk not in ["LOW","MEDIUM","HIGH"]:
            risk = "UNKNOWN"
        return {"signal":signal,"confidence":conf,"risk":risk,"reason":str(ai.get("reason",""))}
    except Exception as e:
        return {"signal":"ERROR","confidence":0,"risk":"UNKNOWN","reason":str(e)}


def can_open_position(result, bot_positions):
    stock, crypto = active_position_counts(bot_positions)
    if stock + crypto >= MAX_TOTAL_POSITIONS:
        return False
    return crypto < MAX_CRYPTO_POSITIONS if result["asset_type"] == "CRYPTO" else stock < MAX_STOCK_POSITIONS


def position_amount(result):
    return CRYPTO_POSITION_USD if result["asset_type"] == "CRYPTO" else STOCK_POSITION_USD


def get_order_status(order_id=None, reference_id=None):
    params = {}

    if order_id is not None:
        params["orderId"] = int(order_id)
    elif reference_id:
        params["referenceId"] = reference_id
    else:
        raise ValueError(
            "order_id oder reference_id erforderlich"
        )

    data = api_get(
        ORDER_LOOKUP_V2,
        params=params,
        timeout=30
    )

    status = data.get("status", {}) if isinstance(data, dict) else {}

    return {
        "raw": data,
        "status_id": status.get("id"),
        "status_name": status.get("name"),
        "error_code": status.get("errorCode"),
        "error_message": status.get("errorMessage"),
        "position_executions": data.get("positionExecutions", [])
        if isinstance(data, dict)
        else [],
    }


def extract_position_id_from_order_status(status_info):
    executions = status_info.get(
        "position_executions",
        []
    )

    for execution in executions:
        if not isinstance(execution, dict):
            continue

        for key in [
            "positionId",
            "positionID",
            "PositionId",
            "PositionID",
        ]:
            if key in execution:
                try:
                    return int(
                        execution[key]
                    )
                except Exception:
                    pass

    return None


def real_buy(result, bot_positions, bot_trades):
    symbol = result["symbol"]

    if (
        bot_has_position(
            bot_positions,
            symbol
        )
        or not can_open_position(
            result,
            bot_positions
        )
    ):
        return False

    if real_portfolio_has_instrument(
        result["instrument_id"]
    ):
        print(
            f"{symbol}: bereits im {MODE_LABEL}-Portfolio "
            "-> BUY übersprungen."
        )
        return False

    amount = float(
        position_amount(result)
    )

    if not app_buy_limits_allow(bot_positions, bot_trades, amount):
        return False

    before = extract_real_positions(
        get_real_portfolio_raw()
    )

    before_ids = {
        p["position_id"]
        for p in before
    }

    payload = {
        "action": "open",
        "transaction": "buy",
        "instrumentId": int(
            result["instrument_id"]
        ),
        "orderType": "mkt",
        "amount": amount,
        "orderCurrency": "usd",
        "leverage": 1,
    }

    print(
        f"\n!!! {MODE_LABEL} BUY REQUEST: "
        f"{symbol} | {amount:.2f} USD !!!"
    )

    try:
        data = api_post(
            ORDER_URL,
            payload
        )

    except Exception as e:
        print(
            f"{MODE_LABEL} BUY FEHLER:",
            e
        )
        write_trade_log(
            f"BUY FEHLER | {symbol} | "
            f"{amount:.2f} USD | {e}"
        )
        return False

    order_id = recursive_value(
        data,
        [
            "orderId",
            "orderID",
            "OrderId",
            "OrderID",
        ]
    )

    reference_id = recursive_value(
        data,
        [
            "referenceId",
            "referenceID",
            "token",
        ]
    )

    http_status = (
        data.get("_http_status")
        if isinstance(data, dict)
        else None
    )

    request_id = (
        data.get("_request_id")
        if isinstance(data, dict)
        else None
    )

    print(
        f"{symbol}: Request akzeptiert "
        f"| HTTP {http_status} "
        f"| Order-ID {order_id} "
        f"| Reference-ID {reference_id}"
    )

    # --------------------------------------------------------
    # ORDER-STATUS DIREKT PRÜFEN
    # --------------------------------------------------------

    order_status = None

    for attempt in range(1, 7):
        time.sleep(2)

        try:
            order_status = get_order_status(
                order_id=order_id
            )
        except Exception as e:
            print(
                f"{symbol}: Order-Status "
                f"Prüfung {attempt}/6 fehlgeschlagen: "
                f"{e}"
            )
            continue

        status_name = str(
            order_status.get(
                "status_name"
            )
            or ""
        ).upper()

        error_code = order_status.get(
            "error_code"
        )

        error_message = order_status.get(
            "error_message"
        )

        print(
            f"{symbol}: Order-Status "
            f"{order_status.get('status_name')} "
            f"| Error {error_code} "
            f"| {error_message or '-'}"
        )

        if status_name in [
            "REJECTED",
            "CANCELLED",
            "CANCELED",
            "EXPIRED",
            "FAILED",
        ]:
            bot_trades.append({
                "type": "BUY_REJECTED",
                "symbol": symbol,
                "time": utc_now_string(),
                "order_id": order_id,
                "reference_id": reference_id,
                "request_id": request_id,
                "http_status": http_status,
                "amount_usd": amount,
                "status": status_name,
                "error_code": error_code,
                "error_message": error_message,
            })

            save_json(
                BOT_TRADES_FILE,
                bot_trades
            )

            write_trade_log(
                f"BUY REJECTED | {symbol} | "
                f"{amount:.2f} USD | "
                f"Order-ID {order_id} | "
                f"Error {error_code} | "
                f"{error_message}"
            )

            print(
                f"{symbol}: ORDER ABGELEHNT "
                "-> KEINE Bot-Position angelegt."
            )

            return False

        # Wenn eToro schon eine Position-ID in den
        # Executions liefert, übernehmen wir sie direkt.
        found_pid = (
            extract_position_id_from_order_status(
                order_status
            )
        )

        if found_pid is not None:
            status = "OPEN"

            pos = {
                "symbol": symbol,
                "market": result["market"],
                "asset_type": result["asset_type"],
                "instrument_id": int(
                    result["instrument_id"]
                ),
                "position_id": found_pid,
                "order_id": order_id,
                "reference_id": reference_id,
                "request_id": request_id,
                "http_status": http_status,
                "amount_usd": amount,
                "strategy_level": STRATEGY_LEVEL,
                "entry_time": utc_now_string(),
                "entry_score": result["total_score"],
                "ai_confidence": result["ai_confidence"],
                "ai_risk": result["ai_risk"],
                "status": status,
                "max_pnl_percent": 0.0,
                "portfolio_position_ids_before_order": sorted(
                    before_ids
                ),
            }

            bot_positions.append(
                pos
            )

            bot_trades.append({
                "type": "BUY_CONFIRMED",
                "symbol": symbol,
                "time": utc_now_string(),
                "position_id": found_pid,
                "order_id": order_id,
                "reference_id": reference_id,
                "request_id": request_id,
                "http_status": http_status,
                "amount_usd": amount,
                "status": status,
            })

            save_json(
                BOT_POSITIONS_FILE,
                bot_positions
            )
            save_json(
                BOT_TRADES_FILE,
                bot_trades
            )

            write_trade_log(
                f"{MODE_LABEL} BUY BESTÄTIGT | {symbol} | "
                f"{amount:.2f} USD | "
                f"Position-ID {found_pid} | "
                f"Order-ID {order_id}"
            )

            return True

        # bekannte Statuswerte, die noch laufen können
        if status_name in [
            "PENDING",
            "OPEN",
            "INPROGRESS",
            "IN_PROGRESS",
            "ACCEPTED",
        ]:
            continue

        # Unbekannter Status: weitere kurze Prüfung
        if attempt < 6:
            continue

    # --------------------------------------------------------
    # FALLBACK: PORTFOLIO PRÜFEN
    # --------------------------------------------------------

    found_pid = None

    for _ in range(6):
        time.sleep(2)

        try:
            after = extract_real_positions(
                get_real_portfolio_raw()
            )
        except Exception:
            continue

        matches = [
            p
            for p in after
            if (
                p["position_id"] not in before_ids
                and p["instrument_id"]
                == int(
                    result["instrument_id"]
                )
            )
        ]

        if len(matches) == 1:
            found_pid = matches[0][
                "position_id"
            ]
            break

    if found_pid is not None:
        status = "OPEN"
    else:
        status = "PENDING"

    pos = {
        "symbol": symbol,
        "market": result["market"],
        "asset_type": result["asset_type"],
        "instrument_id": int(
            result["instrument_id"]
        ),
        "position_id": found_pid,
        "order_id": order_id,
        "reference_id": reference_id,
        "request_id": request_id,
        "http_status": http_status,
        "amount_usd": amount,
        "strategy_level": STRATEGY_LEVEL,
        "entry_time": utc_now_string(),
        "entry_score": result["total_score"],
        "ai_confidence": result["ai_confidence"],
        "ai_risk": result["ai_risk"],
        "status": status,
        "max_pnl_percent": 0.0,
        "portfolio_position_ids_before_order": sorted(
            before_ids
        ),
    }

    bot_positions.append(
        pos
    )

    bot_trades.append({
        "type": (
            "BUY_CONFIRMED"
            if found_pid is not None
            else "BUY_REQUEST_PENDING"
        ),
        "symbol": symbol,
        "time": utc_now_string(),
        "position_id": found_pid,
        "order_id": order_id,
        "reference_id": reference_id,
        "request_id": request_id,
        "http_status": http_status,
        "amount_usd": amount,
        "status": status,
    })

    save_json(
        BOT_POSITIONS_FILE,
        bot_positions
    )
    save_json(
        BOT_TRADES_FILE,
        bot_trades
    )

    if found_pid is not None:
        write_trade_log(
            f"{MODE_LABEL} BUY BESTÄTIGT | {symbol} | "
            f"{amount:.2f} USD | "
            f"Position-ID {found_pid}"
        )
    else:
        write_trade_log(
            f"BUY REQUEST PENDING | {symbol} | "
            f"{amount:.2f} USD | "
            f"Order-ID {order_id} | "
            "Orderstatus nach Prüfungen noch unklar"
        )

    return True

def real_close_position(position, bot_positions, bot_trades, reason, pnl_data=None):
    pid = position.get("position_id")
    if pid is None:
        return False
    url = f"{CLOSE_BASE_URL}/{pid}"
    payload = {"InstrumentId":int(position["instrument_id"]),"UnitsToDeduct":None}
    print(f"\n!!! {MODE_LABEL} CLOSE: {position['symbol']} | {reason} !!!")
    try:
        data = api_post(url,payload)
    except Exception as e:
        print(f"{MODE_LABEL} CLOSE FEHLER:",e)
        write_trade_log(f"SELL FEHLER | {position['symbol']} | {reason} | {e}")
        return False
    close_order_id = recursive_value(data,["orderId","orderID","OrderId","OrderID"])
    position.update({"status":"CLOSING","close_order_id":close_order_id,"close_reason":reason,"close_requested_at":utc_now_string()})
    if pnl_data:
        position["close_request_pnl_usd"] = round(pnl_data["pnl_usd"],2)
        position["close_request_pnl_percent"] = round(pnl_data["pnl_percent"],2)
    bot_trades.append({"type":"CLOSE_REQUEST","symbol":position["symbol"],"position_id":pid,"close_order_id":close_order_id,"time":utc_now_string(),"reason":reason})
    save_json(BOT_POSITIONS_FILE,bot_positions); save_json(BOT_TRADES_FILE,bot_trades)
    ptxt = f"{pnl_data['pnl_usd']:+.2f} USD ({pnl_data['pnl_percent']:+.2f}%)" if pnl_data else "P/L unbekannt"
    write_trade_log(f"{MODE_LABEL} SELL ANGEFORDERT | {position['symbol']} | {ptxt} | {reason} | Position-ID {pid}")
    return True


def reconcile_bot_positions(bot_positions, bot_trades):
    real_positions = extract_real_positions(get_real_portfolio_raw())
    real_ids = {p["position_id"] for p in real_positions}
    changed = False
    for pos in bot_positions:
        if pos.get("status") == "PENDING":
            before_ids = set(
                pos.get(
                    "portfolio_position_ids_before_order",
                    []
                )
            )

            candidates = [
                p
                for p in real_positions
                if (
                    p["instrument_id"]
                    == int(pos["instrument_id"])
                    and p["position_id"]
                    not in before_ids
                )
            ]

            if len(candidates) == 1:
                pos["position_id"] = (
                    candidates[0]["position_id"]
                )
                pos["status"] = "OPEN"
                pos["confirmed_at"] = utc_now_string()
                changed = True

                write_trade_log(
                    f"PENDING BESTÄTIGT | "
                    f"{pos['symbol']} | "
                    f"Position-ID "
                    f"{pos['position_id']}"
                )

            elif len(candidates) == 0:
                print(
                    f"{pos['symbol']}: "
                    "PENDING bleibt bestehen - "
                    "noch keine neue Real-Position gefunden. "
                    "KEIN neuer BUY."
                )

            else:
                print(
                    f"{pos['symbol']}: "
                    f"PENDING unklar - "
                    f"{len(candidates)} mögliche "
                    "Portfolio-Positionen gefunden. "
                    "KEIN neuer BUY."
                )
        elif pos.get("status") == "CLOSING" and pos.get("position_id") not in real_ids:
            pos["status"] = "CLOSED"
            pos["closed_at"] = utc_now_string()
            bot_trades.append({"type":"CLOSED","symbol":pos["symbol"],"position_id":pos.get("position_id"),"time":utc_now_string(),"reason":pos.get("close_reason","-")})
            write_trade_log(f"{MODE_LABEL} SELL BESTÄTIGT | {pos['symbol']} | {pos.get('close_request_pnl_percent','?')}% | {pos.get('close_reason','-')}")
            changed = True
    if changed:
        save_json(BOT_POSITIONS_FILE,bot_positions); save_json(BOT_TRADES_FILE,bot_trades)


def exit_limits(position):
    return (CRYPTO_STOP_LOSS_PERCENT,CRYPTO_TAKE_PROFIT_PERCENT) if position_asset_type(position) == "CRYPTO" else (STOCK_STOP_LOSS_PERCENT,STOCK_TAKE_PROFIT_PERCENT)


def trailing_profit_reason(position, current, maxp):
    asset_type = position_asset_type(
        position
    )

    if asset_type == "STOCK":
        # Höchste erreichte Gewinnstufe zuerst prüfen.
        if (
            maxp >= STOCK_TRAIL_LEVEL_4_MAX
            and current <= STOCK_TRAIL_LEVEL_4_FLOOR
        ):
            return (
                "GEWINNSICHERUNG AKTIE "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}% | "
                f"Floor +{STOCK_TRAIL_LEVEL_4_FLOOR:.0f}%)"
            )

        if (
            maxp >= STOCK_TRAIL_LEVEL_3_MAX
            and current <= STOCK_TRAIL_LEVEL_3_FLOOR
        ):
            return (
                "GEWINNSICHERUNG AKTIE "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}% | "
                f"Floor +{STOCK_TRAIL_LEVEL_3_FLOOR:.0f}%)"
            )

        if (
            maxp >= STOCK_TRAIL_LEVEL_2_MAX
            and current <= STOCK_TRAIL_LEVEL_2_FLOOR
        ):
            return (
                "GEWINNSICHERUNG AKTIE "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}% | "
                f"Floor +{STOCK_TRAIL_LEVEL_2_FLOOR:.0f}%)"
            )

        if (
            maxp >= STOCK_TRAIL_LEVEL_1_MAX
            and current <= STOCK_TRAIL_LEVEL_1_FLOOR
        ):
            return (
                "GEWINNSICHERUNG AKTIE "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}% | "
                f"Floor +{STOCK_TRAIL_LEVEL_1_FLOOR:.0f}%)"
            )

        return None

    # Krypto bleibt großzügiger, weil die normale Schwankung höher ist.
    if asset_type == "CRYPTO":
        if maxp >= 10 and current <= 7:
            return (
                "GEWINNSICHERUNG KRYPTO "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}%)"
            )

        if maxp >= 7 and current <= 4:
            return (
                "GEWINNSICHERUNG KRYPTO "
                f"(MAX {maxp:+.2f}% -> {current:+.2f}%)"
            )

    return None


def get_position_age_hours(position):
    try:
        dt = datetime.fromisoformat(position["entry_time"])
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds()/3600
    except Exception:
        return None


def manage_exits(bot_positions, bot_trades, result_map):
    pnl_map = extract_position_pnl_map(get_real_pnl_raw())
    print(f"\n========================================\n       {MODE_LABEL} BOT POSITIONEN / PNL\n========================================")
    changed = False
    for pos in bot_positions:
        if pos.get("status") != "OPEN":
            continue
        pid = pos.get("position_id")
        if pid is None:
            continue
        pnl = pnl_map.get(pid)
        if pnl is None:
            print(f"{pos['symbol']}: kein Real-P/L-Datensatz gefunden.")
            continue

        current = float(pnl["pnl_percent"])
        try:
            maxp = float(pos.get("max_pnl_percent", current))
        except Exception:
            maxp = current
        if current > maxp:
            maxp = current
            pos["max_pnl_percent"] = round(maxp, 4)
            pos["max_pnl_updated_at"] = utc_now_string()
            changed = True

        level = int(pos.get("strategy_level", STRATEGY_LEVEL) or STRATEGY_LEVEL)
        sl, tp = exit_limits(pos)
        print(
            f"{pos['symbol']} | Stufe {level} | {position_asset_type(pos)} | "
            f"P/L {pnl['pnl_usd']:+.2f} USD | {current:+.2f}% | MAX {maxp:+.2f}% | "
            f"SL {sl:.0f}% | TP +{tp:.0f}%"
        )

        # Harte Risiko-Grenzen gelten in allen vier Stufen.
        reason = "STOP LOSS" if current <= sl else "TAKE PROFIT" if current >= tp else None

        # Trailing-Gewinnschutz für Stufe 1-3, nicht für langfristige Stufe 4.
        if reason is None and level in [1, 2, 3]:
            reason = trailing_profit_reason(pos, current, maxp)

        result = result_map.get(pos["symbol"])

        # Stufe 4: langfristig. Nach den harten SL/TP-Regeln keine kurzfristigen
        # Technik-/Momentum-Exits anwenden.
        if reason is None and result and level != 4:
            score = int(result["total_score"])

            if (
                position_asset_type(pos) == "CRYPTO"
                and current >= 4
                and score < 55
            ):
                reason = (
                    "GEWINN + TECHNISCHE VERSCHLECHTERUNG "
                    f"(Score {score})"
                )

            elif position_asset_type(pos) == "STOCK":
                momentum = float(result.get("momentum_5h", 0) or 0)

                # Nur Stufe 1 nimmt kleine Gewinne besonders früh mit.
                if level == 1 and (
                    current >= STOCK_EARLY_PROFIT_2
                    and score <= STOCK_EARLY_PROFIT_2_MAX_SCORE
                ):
                    reason = (
                        "FRÜHE GEWINNMITNAHME STUFE 1 "
                        f"({current:+.2f}% | Score {score})"
                    )

                elif level == 1 and (
                    current >= STOCK_EARLY_PROFIT_1
                    and (
                        score <= STOCK_EARLY_PROFIT_1_MAX_SCORE
                        or momentum < 0
                    )
                ):
                    reason = (
                        "FRÜHE GEWINNMITNAHME STUFE 1 "
                        f"({current:+.2f}% | Score {score} | Mom {momentum:+.2f}%)"
                    )

                elif current >= 3 and score < 55:
                    reason = (
                        "GEWINN + TECHNISCHE VERSCHLECHTERUNG "
                        f"(Score {score})"
                    )

                elif not result["daily_bullish"] and score < 55:
                    reason = "TECHNISCHE VERSCHLECHTERUNG"

            elif not result["daily_bullish"] and score < 55:
                reason = "TECHNISCHE VERSCHLECHTERUNG"

        if (
            reason is None
            and position_asset_type(pos) == "CRYPTO"
            and result
            and level != 4
        ):
            age = get_position_age_hours(pos)
            score = int(result["total_score"])
            mom = float(result.get("momentum_5h", 0))
            if age is not None and age >= 168 and 0 < current < 6 and score < 80 and mom < 3:
                reason = f"TIME EXIT KRYPTO ({age/24:.1f} Tage | P/L {current:+.2f}% | Score {score})"
            elif age is not None and age >= 72 and 1 <= current < 4 and score < 70 and mom < 2:
                reason = f"TIME EXIT KRYPTO ({age/24:.1f} Tage | P/L {current:+.2f}% | Score {score})"

        if reason:
            if real_close_position(pos, bot_positions, bot_trades, reason, pnl):
                changed = True

    if changed:
        save_json(BOT_POSITIONS_FILE, bot_positions)

def get_daily_close_market():
    v = datetime.now(VIENNA_TZ); vm = v.hour*60+v.minute
    if v.weekday() < 5 and 17*60+15 <= vm < 17*60+30: return "EU"
    n = datetime.now(NEW_YORK_TZ); nm = n.hour*60+n.minute
    if n.weekday() < 5 and 15*60+45 <= nm < 16*60: return "US"
    return None


def market_date_string(market):
    tz = NEW_YORK_TZ if market == "US" else VIENNA_TZ
    return datetime.now(tz).strftime("%Y-%m-%d")


def daily_close_profit_exit(bot_positions, bot_trades):
    market = get_daily_close_market()
    if market is None or not is_market_open_now(market): return
    state = load_json(DAILY_CLOSE_STATE_FILE,{})
    today = market_date_string(market)
    if state.get(market) == today:
        print(f"DAILY CLOSE {market}: heute bereits ausgeführt."); return
    pnl_map = extract_position_pnl_map(get_real_pnl_raw())
    candidates = []
    for pos in bot_positions:
        if pos.get("status") != "OPEN" or position_asset_type(pos) != "STOCK" or pos.get("market") != market: continue
        if int(pos.get("strategy_level", STRATEGY_LEVEL) or STRATEGY_LEVEL) != 2: continue
        pnl = pnl_map.get(pos.get("position_id"))
        if pnl and float(pnl["pnl_percent"]) > 0:
            candidates.append((float(pnl["pnl_percent"]),pos,pnl))
    if not candidates:
        print(f"DAILY CLOSE {market}: keine profitable {MODE_LABEL}-Bot-Aktie."); return
    candidates.sort(key=lambda x:x[0], reverse=True)
    pcent,pos,pnl = candidates[0]
    reason = f"DAILY CLOSE PROFIT ({market} | {pcent:+.2f}%)"
    print(f"\n{MODE_LABEL} DAILY CLOSE {market}: {pos['symbol']} {pcent:+.2f}%")
    if real_close_position(pos,bot_positions,bot_trades,reason,pnl):
        state[market] = today; save_json(DAILY_CLOSE_STATE_FILE,state)




def weekly_friday_exit(bot_positions, bot_trades):
    """Stufe 3: spätestens Freitag vor Börsenschluss schließen."""
    now_ny = datetime.now(NEW_YORK_TZ)
    if now_ny.weekday() != 4:
        return

    # Ab 15:40 New York: genug Puffer vor 16:00 Börsenschluss.
    if (now_ny.hour, now_ny.minute) < (15, 40):
        return

    try:
        pnl_map = extract_position_pnl_map(get_real_pnl_raw())
    except Exception as e:
        print("WEEKLY CLOSE P/L konnte nicht gelesen werden:", e)
        return

    for pos in list(bot_positions):
        if pos.get("status") != "OPEN":
            continue
        if position_asset_type(pos) != "STOCK" or pos.get("market") != "US":
            continue
        if int(pos.get("strategy_level", STRATEGY_LEVEL) or STRATEGY_LEVEL) != 3:
            continue
        pnl = pnl_map.get(pos.get("position_id"))
        reason = "WEEKLY FRIDAY CLOSE (Stufe 3)"
        real_close_position(pos, bot_positions, bot_trades, reason, pnl)


# ============================================================
# START
# ============================================================

print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print("        TRADEPILOT TRADING BOT")
print(f"        MODE: {TRADING_MODE}")
if TRADING_MODE == "REAL":
    print("        ECHTES GELD WIRD VERWENDET")
else:
    print("        DEMO / KEIN ECHTES GELD")
print(f"        VERSION {BOT_VERSION}")
print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print(
    "Aktien Gewinnschutz: "
    "+2% bei Schwäche | "
    "+3% bei Score <=79 | "
    "Trail ab +4%"
)
print(
    f"Bot-Stufe: {STRATEGY_LEVEL} ({STRATEGY_NAMES[STRATEGY_LEVEL]}) | "
    f"Max Trades/Tag: {MAX_TRADES_PER_DAY} | "
    f"Max investiert: {MAX_INVESTED_USD:.2f} USD | "
    f"Position: {POSITION_SIZE_USD:.2f} USD"
)

cache = load_json(INSTRUMENT_CACHE_FILE,{})
state = load_json(STATE_FILE,{"last_processed_candles":{}})
state.setdefault("last_processed_candles",{})
bot_positions = load_json(BOT_POSITIONS_FILE,[])
bot_trades = load_json(BOT_TRADES_FILE,[])

# Erst echter Account-Read. Bei Fehler kein Trading.
try:
    get_real_portfolio_raw()
    print(f"{MODE_LABEL}-Portfolio Zugriff: OK")
    reconcile_bot_positions(bot_positions,bot_trades)
except Exception as e:
    raise SystemExit(f"SICHERHEITSABBRUCH {MODE_LABEL}-Portfolio: {e}")

print("\nInstrumente:")

stock_watchlist = load_stock_universe()

print(
    f"Dynamisches Aktienuniversum: "
    f"{len(stock_watchlist)} aktiv"
)

watchlist = stock_watchlist + CRYPTO_WATCHLIST

instruments = []
for config in watchlist:
    try:
        inst = resolve_instrument(config,cache)
        if inst:
            instruments.append(inst)
            print(f"{inst['key']}: ID {inst['instrument_id']} | {inst['market']} | {inst['asset_type']} | {inst['source']}")
        else:
            print(f"{config['key']}: NICHT GEFUNDEN")
    except Exception as e:
        print(config["key"],"Instrument Fehler:",e)

macro_events = get_macro_events()

results = []

# ------------------------------------------------------------
# 1) ALLE Instrumente zuerst nur technisch analysieren
# ------------------------------------------------------------

for inst in instruments:
    symbol = inst["key"]

    # Geschlossene Aktienmärkte werden nicht mit
    # Candle-Abfragen belastet. Das spart API-Aufrufe
    # und verhindert unnötige 429-Fehler.
    if (
        inst["asset_type"] == "STOCK"
        and not is_market_open_now(
            inst["market"]
        )
    ):
        print(
            f"\n{symbol}: "
            f"ÜBERSPRUNGEN - "
            f"{inst['market']} Markt geschlossen"
        )
        continue

    print(
        f"\nAnalysiere {symbol} "
        f"({inst['asset_type']})..."
    )

    try:
        result = analyze_instrument(inst)

        already = (
            state["last_processed_candles"].get(symbol)
            == result["candle_1h"]
        )

        result["already_processed"] = already
        result["ai_signal"] = "PENDING"
        result["ai_confidence"] = 0
        result["ai_risk"] = "-"
        result["ai_reason"] = "-"
        result["final_signal"] = (
            "SKIP_CANDLE"
            if already
            else result["technical_signal"]
        )

        results.append(result)

        print(
            f"{symbol}: "
            f"TOTAL {result['total_score']} "
            f"| TECH {result['technical_signal']} "
            f"| PRELIM {result['final_signal']}"
        )

    except Exception as e:
        print(
            symbol,
            "ANALYSE FEHLER:",
            e
        )


# ------------------------------------------------------------
# 2) Aktien technisch ranken
# ------------------------------------------------------------

stock_ai_candidates = [
    result
    for result in results
    if (
        result["asset_type"] == "STOCK"
        and not result["already_processed"]
        and result["technical_signal"]
        in ["BUY", "STRONG_BUY"]
        and result["total_score"]
        >= STOCK_AI_PRESELECT_SCORE
    )
]

stock_ai_candidates.sort(
    key=lambda result: (
        result["total_score"],
        result["momentum_5h"],
        (
            result["volume_ratio"]
            if result["volume_ratio"] is not None
            else 0
        ),
    ),
    reverse=True
)

stock_ai_candidates = stock_ai_candidates[
    :MAX_AI_STOCK_CANDIDATES
]

stock_ai_symbols = {
    result["symbol"]
    for result in stock_ai_candidates
}

if stock_ai_candidates:
    print()
    print("========================================")
    print("        AKTIEN TECHNIK-RANKING")
    print("========================================")

    for rank, result in enumerate(
        stock_ai_candidates,
        start=1
    ):
        volume_text = (
            f"{result['volume_ratio']:.2f}"
            if result["volume_ratio"] is not None
            else "-"
        )

        print(
            f"{rank:>2}. "
            f"{result['symbol']:<12} "
            f"| Score {result['total_score']:>3} "
            f"| Mom {result['momentum_5h']:+.2f}% "
            f"| Vol {volume_text}"
        )


# ------------------------------------------------------------
# 3) OpenAI nur für Top-Aktien + technisches Krypto-BUY
# ------------------------------------------------------------

for result in results:
    symbol = result["symbol"]

    if result["already_processed"]:
        result["ai_signal"] = "SKIPPED"
        result["ai_confidence"] = 0
        result["ai_risk"] = "-"
        result["ai_reason"] = "Candle bereits verarbeitet."
        result["final_signal"] = "SKIP_CANDLE"
        continue

    should_call_ai = (
        (
            result["asset_type"] == "CRYPTO"
            and result["technical_signal"]
            in ["BUY", "STRONG_BUY"]
        )
        or
        (
            result["asset_type"] == "STOCK"
            and symbol in stock_ai_symbols
        )
    )

    if should_call_ai:
        print(
            f"\nChatGPT Analyse: {symbol}..."
        )

        ai = ask_chatgpt(result)

        result["ai_signal"] = ai["signal"]
        result["ai_confidence"] = ai["confidence"]
        result["ai_risk"] = ai["risk"]
        result["ai_reason"] = ai["reason"]

        result["final_signal"] = (
            "BUY"
            if (
                ai["signal"] == "BUY"
                and ai["confidence"] >= MIN_AI_CONFIDENCE
                and ai["risk"] != "HIGH"
            )
            else "WAIT"
        )

    else:
        result["ai_signal"] = "SKIPPED"
        result["ai_confidence"] = 0
        result["ai_risk"] = "-"
        result["ai_reason"] = (
            "Nicht im AI-Vorfilter."
            if result["asset_type"] == "STOCK"
            else "Kein technisches BUY."
        )

        result["final_signal"] = (
            result["technical_signal"]
        )

        # Nicht gerankte Aktien dürfen kein BUY behalten.
        if (
            result["asset_type"] == "STOCK"
            and result["technical_signal"]
            in ["BUY", "STRONG_BUY"]
            and symbol not in stock_ai_symbols
        ):
            result["final_signal"] = "WAIT"

    print(
        f"{symbol}: "
        f"TECH {result['technical_signal']} "
        f"| AI {result['ai_signal']} "
        f"{result['ai_confidence']}% "
        f"| FINAL {result['final_signal']}"
    )


# ------------------------------------------------------------
# 4) NEWS- / EVENT-FILTER FÜR BESTÄTIGTE AKTIEN-BUYS
# ------------------------------------------------------------

for result in results:
    result["news_score"] = 0
    result["news_risk"] = "-"
    result["news_summary"] = ""
    result["news_headlines"] = []

    macro_context = macro_event_risk_for_market(
        result["market"],
        macro_events
    )

    result["event_risk"] = macro_context["risk"]
    result["next_macro_event"] = macro_context["next_event"]
    result["hours_to_macro_event"] = macro_context["hours_to_event"]

    if (
        result["asset_type"] == "STOCK"
        and result["final_signal"] == "BUY"
    ):
        news = analyze_news_for_result(
            result,
            macro_context
        )

        result.update(news)

        if (
            result["news_score"] <= NEWS_BLOCK_SCORE
            or result["news_risk"] == "HIGH"
            or result["event_risk"] == "HIGH"
        ):
            result["final_signal"] = "WAIT"

            print(
                f"{result['symbol']}: "
                f"BUY durch News/Event-Risiko blockiert "
                f"| News {result['news_score']} "
                f"| NewsRisk {result['news_risk']} "
                f"| EventRisk {result['event_risk']}"
            )


# ------------------------------------------------------------
# 5) Finales Ranking aller bestätigten BUYs
# ------------------------------------------------------------

for result in results:
    if result["final_signal"] == "BUY":
        momentum_bonus = max(
            -5.0,
            min(
                float(result["momentum_5h"]),
                5.0
            )
        )

        result["final_rank_score"] = round(
            (
                result["total_score"] * 0.65
                + result["ai_confidence"] * 0.20
                + (momentum_bonus + 5.0)
                + max(-5.0, min(result.get("news_score", 0) / 10.0, 5.0))
            ),
            2
        )
    else:
        result["final_rank_score"] = 0.0


final_ranked = sorted(
    [
        result
        for result in results
        if result["final_signal"] == "BUY"
    ],
    key=lambda result: result[
        "final_rank_score"
    ],
    reverse=True
)

if final_ranked:
    print()
    print("========================================")
    print("          FINAL BUY RANKING")
    print("========================================")

    for rank, result in enumerate(
        final_ranked,
        start=1
    ):
        print(
            f"{rank:>2}. "
            f"{result['symbol']:<12} "
            f"| Rank {result['final_rank_score']:.2f} "
            f"| Technik {result['total_score']} "
            f"| AI {result['ai_confidence']}%"
        )


result_map = {
    result["symbol"]: result
    for result in results
}

# Fail closed: wenn Real-P/L/Exit-Management nicht funktioniert, keine neuen Käufe.
try:
    manage_exits(bot_positions,bot_trades,result_map)
except Exception as e:
    save_json(BOT_POSITIONS_FILE,bot_positions); save_json(BOT_TRADES_FILE,bot_trades)
    raise SystemExit(f"SICHERHEITSABBRUCH Exit/P-L: {e}")

try:
    daily_close_profit_exit(bot_positions, bot_trades)
    weekly_friday_exit(bot_positions, bot_trades)
except Exception as e:
    print("ZEITBASIERTER CLOSE FEHLER:", e)

risk_state = calculate_bot_risk_state(
    bot_positions,
    bot_trades
)

if risk_state["new_buys_blocked"]:
    print()
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("       NEUE KÄUFE SIND GESPERRT")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(
        f"Heute ca.: {risk_state['today_total_approx_usd']:+.2f} USD "
        f"| Bot gesamt ca.: {risk_state['bot_total_approx_usd']:+.2f} USD"
    )
    buy_candidates = []
else:
    buy_candidates = [
        r for r in results
        if (
            r["final_signal"] == "BUY"
            and not bot_has_position(
                bot_positions,
                r["symbol"]
            )
        )
    ]
buy_candidates.sort(
    key=lambda r: (
        r.get("final_rank_score", 0),
        r["total_score"],
        r["ai_confidence"],
    ),
    reverse=True
)
for candidate in buy_candidates:
    if can_open_position(candidate,bot_positions):
        real_buy(candidate,bot_positions,bot_trades)

for result in results:
    should_mark = result["asset_type"] == "CRYPTO" or (result["market_open_now"] and result["candle_regular_session"])
    if should_mark:
        state["last_processed_candles"][result["symbol"]] = result["candle_1h"]

dashboard_positions = []

try:
    dashboard_pnl_map = extract_position_pnl_map(
        get_real_pnl_raw()
    )
except Exception:
    dashboard_pnl_map = {}

for p in bot_positions:
    if p.get("status") not in ["OPEN", "PENDING", "CLOSING"]:
        continue

    row = dict(p)
    position_id = p.get("position_id")
    pnl_data = dashboard_pnl_map.get(position_id)

    if pnl_data:
        row["current_pnl_usd"] = round(
            pnl_data.get("pnl_usd", 0),
            2
        )
        row["current_pnl_percent"] = round(
            pnl_data.get("pnl_percent", 0),
            2
        )

    dashboard_positions.append(row)

invested_usd = round(
    sum(
        float(p.get("amount_usd", 0) or 0)
        for p in dashboard_positions
    ),
    2
)

dashboard_snapshot = {
    "generated_at": utc_now_string(),
    "results": results,
    "final_ranked": final_ranked,
    "positions": dashboard_positions,
    "macro_events": macro_events,
    "risk_state": risk_state,
    "account_summary": {
        "bot_invested_usd": invested_usd,
        "bot_open_pnl_usd": risk_state["open_pnl_usd"],
        "bot_total_approx_usd": risk_state["bot_total_approx_usd"],
    },
}
save_json(DASHBOARD_SNAPSHOT_FILE, dashboard_snapshot)

save_json(STATE_FILE,state); save_json(BOT_POSITIONS_FILE,bot_positions); save_json(BOT_TRADES_FILE,bot_trades)
stock,crypto = active_position_counts(bot_positions)
print("\n========================================")
print(f"        {MODE_LABEL} BOT-POSITIONEN")
print("========================================")
print(f"Aktien: {stock}/{MAX_STOCK_POSITIONS}")
print(f"Krypto: {crypto}/{MAX_CRYPTO_POSITIONS}")
print(f"Gesamt: {stock+crypto}/{MAX_TOTAL_POSITIONS}\n")
for p in bot_positions:
    if p.get("status") in ["OPEN","PENDING","CLOSING"]:
        print(f"{p['symbol']} | {position_asset_type(p)} | {p['status']} | Position-ID {p.get('position_id')}")
print(f"\nReal Trade-Log: {os.path.abspath(TRADE_LOG_FILE)}")
print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print(f"      {MODE_LABEL} BOT-LAUF BEENDET")
print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
