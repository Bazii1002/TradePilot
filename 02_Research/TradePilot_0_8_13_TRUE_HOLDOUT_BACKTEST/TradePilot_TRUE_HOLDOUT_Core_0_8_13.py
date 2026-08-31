import yfinance as yf
import pandas as pd
import math
import statistics
import time
import os
import pickle
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from universe_large import UNIVERSES, universe_count


# ============================================================
# TRADEPILOT BACKTEST 0.8.3 TURBO - KERNLOGIK 0.6.1
#
# Ziele:
# 1. Größeres Testuniversum
# 2. Value-Trap-Gründe protokollieren
# 3. Cluster / Extremwerte automatisch erkennen
# 4. Unternehmensscore und Einstiegsscore getrennt testen
# ============================================================


# ============================================================
# TESTUNIVERSUM
# ============================================================

TEST_AKTIEN = {
    "STANDARD": [
        "AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "AMD", "ADBE",
        "ORCL", "CRM", "INTC", "IBM", "CSCO", "QCOM", "TXN", "MU",
        "KO", "PEP", "WMT", "COST", "MCD", "NKE", "SBUX", "PG", "TGT",
        "HD", "LOW", "DIS", "NFLX",
        "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "GILD", "AMGN",
        "CAT", "DE", "HON", "UPS", "FDX", "GE", "MMM", "BA",
        "V", "MA"
    ],

    "BANK": [
        "JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "FITB", "KEY",
        "HBAN", "CFG", "RF", "ZION", "FHN"
    ],

    "CAPITAL_MARKETS": [
        "GS", "MS", "SCHW", "IBKR", "RJF", "LPLA", "MKTX", "CME", "ICE"
    ],

    "ENERGY": [
        "XOM", "CVX", "SHEL", "COP", "EOG", "OXY", "DVN", "FANG", "APA",
        "MPC", "VLO", "PSX", "HAL", "SLB", "BKR"
    ]
}


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def wert(info, name, standard=None):
    try:
        ergebnis = info.get(name, standard)
        if ergebnis is None:
            return standard
        if isinstance(ergebnis, float) and math.isnan(ergebnis):
            return standard
        return ergebnis
    except Exception:
        return standard


def score_begrenzen(score):
    return max(0, min(100, round(score)))


def zeile_finden(tabelle, namen):
    if tabelle is None or tabelle.empty:
        return None
    for name in namen:
        if name in tabelle.index:
            return tabelle.loc[name]
    return None


def finanzwerte_sortieren(daten):
    if daten is None:
        return []
    werte = []
    try:
        daten = daten.sort_index()
        for datum, zahl in daten.items():
            if zahl is None:
                continue
            try:
                zahl = float(zahl)
                if math.isnan(zahl):
                    continue
                werte.append((datum, zahl))
            except Exception:
                continue
    except Exception:
        return []
    return werte


def veraenderung_prozent(alt, neu):
    if alt is None or neu is None or alt == 0:
        return None
    return ((neu - alt) / abs(alt)) * 100


def gewichteter_score(teile):
    gesamt = 0
    gewicht_summe = 0
    for score, gewicht, verfuegbar in teile:
        if not verfuegbar:
            continue
        gesamt += score * gewicht
        gewicht_summe += gewicht
    if gewicht_summe == 0:
        return 50
    return score_begrenzen(gesamt / gewicht_summe)


def text_liste(liste):
    if not liste:
        return "-"
    return " | ".join(liste)


# ============================================================
# MODELLERKENNUNG
# ============================================================

def modell_erkennen(info):
    sektor = str(wert(info, "sector", "")).lower()
    branche = str(wert(info, "industry", "")).lower()

    bank_begriffe = [
        "banks - diversified",
        "banks - regional",
        "regional banks",
        "diversified banks",
        "banking services"
    ]
    if any(begriff in branche for begriff in bank_begriffe):
        return "BANK"

    capital_markets_begriffe = [
        "capital markets",
        "investment banking",
        "brokerage",
        "financial data",
        "financial exchanges",
        "asset management"
    ]
    if "financial services" in sektor and any(
        begriff in branche for begriff in capital_markets_begriffe
    ):
        return "CAPITAL_MARKETS"

    if "energy" in sektor:
        return "ENERGY"

    return "STANDARD"


# ============================================================
# FINANZTRENDS
# ============================================================

def finanztrend_score(daten, positiv_ist_gut=True):
    werte = finanzwerte_sortieren(daten)
    if len(werte) < 2:
        return {"score": 50, "veraenderung": None, "verfuegbar": False}

    erster_wert = werte[0][1]
    letzter_wert = werte[-1][1]
    veraenderung = veraenderung_prozent(erster_wert, letzter_wert)

    steigend = 0
    fallend = 0
    for i in range(1, len(werte)):
        vorher = werte[i - 1][1]
        aktuell = werte[i][1]
        if aktuell > vorher:
            steigend += 1
        elif aktuell < vorher:
            fallend += 1

    score = 50
    if veraenderung is not None:
        if positiv_ist_gut:
            if veraenderung >= 30:
                score += 30
            elif veraenderung >= 15:
                score += 22
            elif veraenderung >= 5:
                score += 12
            elif veraenderung >= -5:
                score += 2
            elif veraenderung >= -15:
                score -= 12
            elif veraenderung >= -30:
                score -= 22
            else:
                score -= 30
        else:
            if veraenderung <= -30:
                score += 30
            elif veraenderung <= -15:
                score += 22
            elif veraenderung <= -5:
                score += 12
            elif veraenderung <= 5:
                score += 2
            elif veraenderung <= 15:
                score -= 12
            elif veraenderung <= 30:
                score -= 22
            else:
                score -= 30

    if positiv_ist_gut:
        score += steigend * 5
        score -= fallend * 4
    else:
        score += fallend * 5
        score -= steigend * 4

    return {
        "score": score_begrenzen(score),
        "veraenderung": veraenderung,
        "verfuegbar": True
    }


def zyklischer_finanztrend_score(daten):
    werte = finanzwerte_sortieren(daten)
    if len(werte) < 3:
        return finanztrend_score(daten, True)

    letzter_wert = werte[-1][1]
    alte_werte = [zahl for _, zahl in werte[:-1]]
    median_alt = statistics.median(alte_werte)
    veraenderung = veraenderung_prozent(median_alt, letzter_wert)

    score = 55
    if veraenderung is not None:
        if veraenderung >= 30:
            score += 25
        elif veraenderung >= 10:
            score += 15
        elif veraenderung >= -10:
            score += 5
        elif veraenderung >= -25:
            score -= 5
        elif veraenderung >= -40:
            score -= 15
        else:
            score -= 25

    vorjahr = werte[-2][1]
    if letzter_wert > vorjahr:
        score += 8
    elif letzter_wert < vorjahr:
        score -= 5

    return {
        "score": score_begrenzen(score),
        "veraenderung": veraenderung,
        "verfuegbar": True
    }


# ============================================================
# MARGENTREND
# ============================================================

def margen_daten_berechnen(umsatz_daten, gewinn_daten):
    umsatz = finanzwerte_sortieren(umsatz_daten)
    gewinn = finanzwerte_sortieren(gewinn_daten)
    if not umsatz or not gewinn:
        return []

    umsatz_dict = {datum: zahl for datum, zahl in umsatz}
    gewinn_dict = {datum: zahl for datum, zahl in gewinn}
    gemeinsame_daten = sorted(set(umsatz_dict.keys()) & set(gewinn_dict.keys()))

    margen = []
    for datum in gemeinsame_daten:
        umsatzwert = umsatz_dict[datum]
        gewinnwert = gewinn_dict[datum]
        if umsatzwert == 0:
            continue
        margen.append((datum, (gewinnwert / umsatzwert) * 100))
    return margen


def margen_trend_score(umsatz_daten, gewinn_daten):
    margen = margen_daten_berechnen(umsatz_daten, gewinn_daten)
    if len(margen) < 2:
        return {"score": 50, "veraenderung": None, "verfuegbar": False}

    erste_marge = margen[0][1]
    letzte_marge = margen[-1][1]
    veraenderung = letzte_marge - erste_marge

    steigend = 0
    fallend = 0
    for i in range(1, len(margen)):
        if margen[i][1] > margen[i - 1][1]:
            steigend += 1
        elif margen[i][1] < margen[i - 1][1]:
            fallend += 1

    score = 50
    if veraenderung >= 5:
        score += 30
    elif veraenderung >= 2:
        score += 20
    elif veraenderung >= 0.5:
        score += 10
    elif veraenderung > -0.5:
        score += 2
    elif veraenderung > -2:
        score -= 10
    elif veraenderung > -5:
        score -= 20
    else:
        score -= 30

    score += steigend * 4
    score -= fallend * 4

    return {
        "score": score_begrenzen(score),
        "veraenderung": veraenderung,
        "verfuegbar": True
    }


# ============================================================
# JAHRESDATEN
# ============================================================

def jahresdaten_ermitteln(income, cashflow, balance):
    return {
        "umsatz": zeile_finden(income, ["TotalRevenue", "OperatingRevenue"]),
        "gewinn": zeile_finden(income, [
            "NetIncome",
            "NetIncomeCommonStockholders",
            "NetIncomeIncludingNoncontrollingInterests"
        ]),
        "operativ": zeile_finden(income, [
            "OperatingIncome",
            "TotalOperatingIncomeAsReported"
        ]),
        "fcf": zeile_finden(cashflow, ["FreeCashFlow"]),
        "schulden": zeile_finden(balance, ["TotalDebt"])
    }


# ============================================================
# ENTWICKLUNG
# ============================================================

def entwicklung_berechnen(modell, income, cashflow, balance):
    daten = jahresdaten_ermitteln(income, cashflow, balance)
    marge = margen_trend_score(daten["umsatz"], daten["gewinn"])

    if modell in ["BANK", "CAPITAL_MARKETS"]:
        umsatz = finanztrend_score(daten["umsatz"], True)
        gewinn = finanztrend_score(daten["gewinn"], True)
        operativ = finanztrend_score(daten["operativ"], True)
        score = gewichteter_score([
            (umsatz["score"], 0.30, umsatz["verfuegbar"]),
            (gewinn["score"], 0.40, gewinn["verfuegbar"]),
            (operativ["score"], 0.10, operativ["verfuegbar"]),
            (marge["score"], 0.20, marge["verfuegbar"])
        ])
        return score, marge["score"]

    if modell == "ENERGY":
        umsatz = zyklischer_finanztrend_score(daten["umsatz"])
        gewinn = zyklischer_finanztrend_score(daten["gewinn"])
        operativ = zyklischer_finanztrend_score(daten["operativ"])
        fcf = zyklischer_finanztrend_score(daten["fcf"])
        schulden = finanztrend_score(daten["schulden"], False)
        score = gewichteter_score([
            (umsatz["score"], 0.15, umsatz["verfuegbar"]),
            (gewinn["score"], 0.20, gewinn["verfuegbar"]),
            (operativ["score"], 0.15, operativ["verfuegbar"]),
            (fcf["score"], 0.20, fcf["verfuegbar"]),
            (marge["score"], 0.15, marge["verfuegbar"]),
            (schulden["score"], 0.15, schulden["verfuegbar"])
        ])
        return score, marge["score"]

    umsatz = finanztrend_score(daten["umsatz"], True)
    gewinn = finanztrend_score(daten["gewinn"], True)
    operativ = finanztrend_score(daten["operativ"], True)
    fcf = finanztrend_score(daten["fcf"], True)
    schulden = finanztrend_score(daten["schulden"], False)
    score = gewichteter_score([
        (umsatz["score"], 0.20, umsatz["verfuegbar"]),
        (gewinn["score"], 0.20, gewinn["verfuegbar"]),
        (operativ["score"], 0.15, operativ["verfuegbar"]),
        (fcf["score"], 0.15, fcf["verfuegbar"]),
        (marge["score"], 0.20, marge["verfuegbar"]),
        (schulden["score"], 0.10, schulden["verfuegbar"])
    ])
    return score, marge["score"]


# ============================================================
# QUALITÄT
# ============================================================

def qualitaet_standard(info):
    score = 50
    growth = wert(info, "revenueGrowth")
    marge = wert(info, "profitMargins")
    fcf = wert(info, "freeCashflow")
    roe = wert(info, "returnOnEquity")
    debt = wert(info, "totalDebt")
    cash = wert(info, "totalCash")

    if growth is not None:
        if growth >= 0.15:
            score += 12
        elif growth >= 0.05:
            score += 7
        elif growth >= 0:
            score += 2
        elif growth >= -0.10:
            score -= 6
        else:
            score -= 15

    if marge is not None:
        if marge >= 0.20:
            score += 10
        elif marge >= 0.10:
            score += 6
        elif marge > 0:
            score += 2
        else:
            score -= 15

    if fcf is not None:
        if fcf > 0:
            score += 10
        else:
            score -= 15

    if roe is not None:
        if roe >= 0.20:
            score += 8
        elif roe >= 0.10:
            score += 4
        elif roe < 0:
            score -= 10

    if debt is not None and cash is not None:
        if debt == 0:
            score += 7
        elif cash >= debt:
            score += 6
        elif cash >= debt * 0.5:
            score += 2
        elif cash > 0 and debt > cash * 4:
            score -= 8

    return score_begrenzen(score)


def qualitaet_finanz(info):
    score = 50
    growth = wert(info, "revenueGrowth")
    marge = wert(info, "profitMargins")
    roe = wert(info, "returnOnEquity")
    pb = wert(info, "priceToBook")

    if growth is not None:
        if growth >= 0.20:
            score += 12
        elif growth >= 0.10:
            score += 8
        elif growth >= 0:
            score += 3
        elif growth < -0.10:
            score -= 10

    if marge is not None:
        if marge >= 0.30:
            score += 12
        elif marge >= 0.20:
            score += 8
        elif marge >= 0.10:
            score += 4
        elif marge <= 0:
            score -= 18

    if roe is not None:
        if roe >= 0.18:
            score += 15
        elif roe >= 0.14:
            score += 12
        elif roe >= 0.10:
            score += 7
        elif roe >= 0.07:
            score += 2
        else:
            score -= 10

    if pb is not None and pb > 0:
        if pb < 1:
            score += 8
        elif pb < 1.5:
            score += 6
        elif pb < 2:
            score += 3
        elif pb > 4:
            score -= 8

    return score_begrenzen(score)


def qualitaet_energy(info):
    score = 50
    umsatz = wert(info, "totalRevenue")
    growth = wert(info, "revenueGrowth")
    marge = wert(info, "profitMargins")
    fcf = wert(info, "freeCashflow")
    roe = wert(info, "returnOnEquity")
    debt = wert(info, "totalDebt")
    cash = wert(info, "totalCash")

    if growth is not None:
        if growth >= 0.20:
            score += 4
        elif growth >= 0.05:
            score += 2
        elif growth < -0.20:
            score -= 5

    if marge is not None:
        if marge >= 0.20:
            score += 15
        elif marge >= 0.15:
            score += 12
        elif marge >= 0.10:
            score += 8
        elif marge >= 0.05:
            score += 4
        elif marge > 0:
            score += 1
        else:
            score -= 18

    if fcf is not None and umsatz is not None and umsatz > 0:
        fcf_marge = fcf / umsatz
        if fcf_marge >= 0.15:
            score += 16
        elif fcf_marge >= 0.10:
            score += 13
        elif fcf_marge >= 0.05:
            score += 9
        elif fcf_marge > 0:
            score += 4
        else:
            score -= 18
    elif fcf is not None:
        if fcf > 0:
            score += 6
        else:
            score -= 18

    if roe is not None:
        if roe >= 0.20:
            score += 12
        elif roe >= 0.15:
            score += 9
        elif roe >= 0.10:
            score += 6
        elif roe >= 0.05:
            score += 2
        elif roe < 0:
            score -= 10

    if debt is not None and cash is not None and cash > 0:
        debt_cash = debt / cash
        if debt_cash <= 1:
            score += 10
        elif debt_cash <= 2:
            score += 7
        elif debt_cash <= 3:
            score += 3
        elif debt_cash <= 4:
            score += 0
        elif debt_cash <= 6:
            score -= 5
        else:
            score -= 10

    return score_begrenzen(score)


def qualitaet_berechnen(modell, info):
    if modell in ["BANK", "CAPITAL_MARKETS"]:
        return qualitaet_finanz(info)
    if modell == "ENERGY":
        return qualitaet_energy(info)
    return qualitaet_standard(info)


# ============================================================
# BEWERTUNG
# ============================================================

def bewertung_standard(info):
    score = 50
    pe = wert(info, "trailingPE")
    forward_pe = wert(info, "forwardPE")
    peg = wert(info, "pegRatio")
    ps = wert(info, "priceToSalesTrailing12Months")

    if pe is not None and pe > 0:
        if pe < 15:
            score += 15
        elif pe < 25:
            score += 8
        elif pe < 35:
            score += 0
        elif pe < 50:
            score -= 10
        else:
            score -= 18

    if forward_pe is not None and forward_pe > 0:
        if forward_pe < 15:
            score += 10
        elif forward_pe < 25:
            score += 5
        elif forward_pe > 40:
            score -= 10

    if peg is not None and peg > 0:
        if peg < 1:
            score += 10
        elif peg <= 2:
            score += 3
        elif peg > 3:
            score -= 8

    if ps is not None and ps > 0:
        if ps < 2:
            score += 7
        elif ps > 10:
            score -= 10

    return score_begrenzen(score)


def bewertung_finanz(info):
    score = 50
    pe = wert(info, "trailingPE")
    forward_pe = wert(info, "forwardPE")
    pb = wert(info, "priceToBook")

    if pe is not None and pe > 0:
        if pe < 10:
            score += 15
        elif pe < 15:
            score += 10
        elif pe < 20:
            score += 4
        elif pe > 30:
            score -= 12

    if forward_pe is not None and forward_pe > 0:
        if forward_pe < 12:
            score += 10
        elif forward_pe < 18:
            score += 5
        elif forward_pe > 30:
            score -= 10

    if pb is not None and pb > 0:
        if pb < 1:
            score += 15
        elif pb < 1.5:
            score += 8
        elif pb < 2.5:
            score += 2
        elif pb > 4:
            score -= 12

    return score_begrenzen(score)


def bewertung_energy(info):
    score = 50
    pe = wert(info, "trailingPE")
    forward_pe = wert(info, "forwardPE")
    ps = wert(info, "priceToSalesTrailing12Months")

    if pe is not None and pe > 0:
        if pe < 10:
            score += 15
        elif pe < 18:
            score += 10
        elif pe < 25:
            score += 4
        elif pe > 35:
            score -= 12

    if forward_pe is not None and forward_pe > 0:
        if forward_pe < 12:
            score += 10
        elif forward_pe < 20:
            score += 5
        elif forward_pe > 35:
            score -= 10

    if ps is not None and ps > 0:
        if ps < 1.5:
            score += 10
        elif ps < 3:
            score += 5
        elif ps > 6:
            score -= 10

    return score_begrenzen(score)


def bewertung_berechnen(modell, info):
    if modell in ["BANK", "CAPITAL_MARKETS"]:
        return bewertung_finanz(info)
    if modell == "ENERGY":
        return bewertung_energy(info)
    return bewertung_standard(info)


# ============================================================
# TREND
# ============================================================

def rsi_berechnen(close, periode=14):
    if close is None or len(close) < periode + 1:
        return None

    differenz = close.diff()
    gewinne = differenz.clip(lower=0)
    verluste = -differenz.clip(upper=0)
    durchschnitt_gewinn = gewinne.rolling(periode).mean()
    durchschnitt_verlust = verluste.rolling(periode).mean()
    letzter_verlust = durchschnitt_verlust.iloc[-1]
    letzter_gewinn = durchschnitt_gewinn.iloc[-1]

    if letzter_verlust == 0:
        if letzter_gewinn > 0:
            return 100
        return 50

    rs = letzter_gewinn / letzter_verlust
    return 100 - (100 / (1 + rs))


def trend_analyse(historie):
    """
    Historische Trendanalyse am jeweiligen Stichtag.

    WICHTIG 0.7.2:
    Die Funktion gibt Kurs UND trend_score zurück. In 0.7.1 wurden
    zwar beide Werte intern berechnet, aber der Kurs nicht zurückgegeben
    und der Trendscore unter dem falschen Schlüssel "score" abgelegt.
    Dadurch wurden gültige Beobachtungen fälschlich verworfen.
    """
    if historie is None or historie.empty:
        return {
            "kurs": None,
            "hoch_52w": None,
            "drawdown": None,
            "ma50": None,
            "ma200": None,
            "rsi": None,
            "momentum_3m": None,
            "trend_score": 50,
        }

    close = historie["Close"].dropna()
    if close.empty:
        return {
            "kurs": None,
            "hoch_52w": None,
            "drawdown": None,
            "ma50": None,
            "ma200": None,
            "rsi": None,
            "momentum_3m": None,
            "trend_score": 50,
        }

    kurs = float(close.iloc[-1])
    hoch = float(close.tail(min(252, len(close))).max())
    drawdown = ((kurs - hoch) / hoch) * 100 if hoch else None

    ma50 = float(close.tail(50).mean()) if len(close) >= 50 else None
    ma200 = float(close.tail(200).mean()) if len(close) >= 200 else None
    rsi = rsi_berechnen(close)
    momentum_3m = None

    if len(close) > 63:
        momentum_3m = ((kurs / float(close.iloc[-64])) - 1) * 100

    score = 50
    if ma50 is not None:
        score += 12 if kurs > ma50 else -8
    if ma200 is not None:
        score += 15 if kurs > ma200 else -12
    if rsi is not None:
        if 40 <= rsi <= 65:
            score += 8
        elif rsi < 30:
            score -= 5
        elif rsi > 75:
            score -= 8
    if momentum_3m is not None:
        if momentum_3m > 10:
            score += 8
        elif momentum_3m > 0:
            score += 4
        elif momentum_3m < -15:
            score -= 10

    return {
        "kurs": kurs,
        "hoch_52w": hoch,
        "drawdown": drawdown,
        "ma50": ma50,
        "ma200": ma200,
        "rsi": rsi,
        "momentum_3m": momentum_3m,
        "trend_score": score_begrenzen(score),
    }


# ============================================================
# DRAWDOWN
# ============================================================

def drawdown_score_berechnen(drawdown):
    if drawdown is None:
        return 50
    if drawdown > -5:
        return 35
    elif drawdown > -10:
        return 40
    elif drawdown > -20:
        return 50
    elif drawdown > -30:
        return 60
    elif drawdown > -40:
        return 78
    elif drawdown > -50:
        return 85
    return 75


# ============================================================
# VALUE TRAP - SCORE + PROTOKOLL
# ============================================================

def value_trap_risiko(modell, info, fundamental_score, entwicklungs_score, margen_score, drawdown):
    risiko = 0
    gruende = []

    def add(punkte, grund):
        nonlocal risiko
        risiko += punkte
        gruende.append(f"+{punkte} {grund}")

    marge = wert(info, "profitMargins")
    fcf = wert(info, "freeCashflow")
    growth = wert(info, "revenueGrowth")

    if fundamental_score < 50:
        add(30, "Unternehmensqualität < 50")
    elif fundamental_score < 65:
        add(15, "Unternehmensqualität < 65")

    if modell in ["BANK", "CAPITAL_MARKETS"]:
        if entwicklungs_score < 35:
            add(30, "Finanz-Entwicklung < 35")
        elif entwicklungs_score < 50:
            add(15, "Finanz-Entwicklung < 50")
        if marge is not None and marge < 0:
            add(25, "negative Gewinnmarge")

    elif modell == "ENERGY":
        if entwicklungs_score < 30:
            add(25, "Energy-Entwicklung < 30")
        elif entwicklungs_score < 40:
            add(10, "Energy-Entwicklung < 40")
        if marge is not None and marge < 0:
            add(25, "negative Gewinnmarge")
        if fcf is not None and fcf < 0:
            add(25, "negativer Free Cashflow")

    else:
        if entwicklungs_score < 35:
            add(30, "Mehrjahresentwicklung < 35")
        elif entwicklungs_score < 50:
            add(18, "Mehrjahresentwicklung < 50")
        elif entwicklungs_score < 60:
            add(8, "Mehrjahresentwicklung < 60")

        if margen_score is not None:
            if margen_score < 30:
                add(20, "Margentrend < 30")
            elif margen_score < 45:
                add(10, "Margentrend < 45")

        if growth is not None:
            if growth < -0.15:
                add(25, "aktuelles Umsatzwachstum < -15 %")
            elif growth < 0:
                add(10, "aktuelles Umsatzwachstum negativ")

        if marge is not None and marge < 0:
            add(20, "negative Gewinnmarge")

        if fcf is not None and fcf < 0:
            add(20, "negativer Free Cashflow")

        debt = wert(info, "totalDebt")
        cash = wert(info, "totalCash")
        if debt is not None and cash is not None and cash > 0 and debt > cash * 5:
            add(15, "Schulden > 5x Cash")

    if drawdown is not None:
        if drawdown <= -50:
            add(15, "Drawdown <= -50 %")
        elif drawdown <= -30:
            add(5, "Drawdown <= -30 %")

    rohscore = risiko
    return score_begrenzen(risiko), rohscore, gruende


# ============================================================
# TRADEPILOT 0.6 - GETRENNTE SCORES
# ============================================================

def unternehmens_score(fundamental_score, entwicklungs_score, bewertungs_score, trap_score):
    """
    Misst das Unternehmen unabhängig vom aktuellen Kursrücksetzer.

    Arbeitsgewichte 0.6:
    - Qualität: 40 %
    - Entwicklung: 35 %
    - Bewertung: 25 %
    - Value-Trap-Abzug: 35 % des Trap-Scores
    """
    score = (
        fundamental_score * 0.40
        + entwicklungs_score * 0.35
        + bewertungs_score * 0.25
    )
    score -= trap_score * 0.35
    return score_begrenzen(score)


def einstiegs_score(company_score, bewertungs_score, drawdown_score, trend_score):
    """
    Rohwert für die Attraktivität des Einstiegs JETZT.

    Arbeitsgewichte 0.6 bleiben unverändert:
    - Unternehmensscore: 25 %
    - Bewertung: 20 %
    - Drawdown-Chance: 40 %
    - Trend: 15 %

    In 0.6.1 wird dieser Rohwert anschließend durch ein Sicherheits-Gate
    begrenzt. So kann ein starker Kurssturz fundamentale Risiken nicht
    überdecken.
    """
    score = (
        company_score * 0.25
        + bewertungs_score * 0.20
        + drawdown_score * 0.40
        + trend_score * 0.15
    )
    return score_begrenzen(score)




# ============================================================
# 0.8.5 SCORE AUDIT - 0.6.1 VS. 0.6.2-KANDIDATEN
# ============================================================
# WICHTIG:
# - BASELINE_061 entspricht exakt der produktiven 0.6.1-Gewichtung.
# - Kandidaten ändern NUR die Aggregationsgewichte.
# - Komponenten (Qualität, Entwicklung, Bewertung, Trap, Drawdown, Trend)
#   und das 0.6.1-Sicherheits-Gate bleiben unverändert.
# - Erst der große Backtest entscheidet, ob ein Kandidat übernommen wird.

SCORE_VARIANTEN = {
    "BASELINE_061": {
        "company": (0.40, 0.35, 0.25, 0.35),
        "entry": (0.25, 0.20, 0.40, 0.15),
        "beschreibung": "Original 0.6.1",
    },
    "CANDIDATE_062_BALANCED": {
        "company": (0.45, 0.40, 0.15, 0.30),
        "entry": (0.35, 0.10, 0.30, 0.25),
        "beschreibung": "Mehr Qualität/Entwicklung, weniger doppelte Bewertung/Drawdown",
    },
    "CANDIDATE_062_QUALITY": {
        "company": (0.50, 0.40, 0.10, 0.30),
        "entry": (0.40, 0.05, 0.25, 0.30),
        "beschreibung": "Konservativer Qualitäts-/Trend-Fokus",
    },
}

def score_variante_berechnen(variant_name, qualitaet, entwicklung, bewertung, trap, dd_score, trend_score):
    cfg = SCORE_VARIANTEN[variant_name]
    wq, we, wb, trap_factor = cfg["company"]
    company = score_begrenzen(
        qualitaet * wq + entwicklung * we + bewertung * wb - trap * trap_factor
    )
    wc, wb2, wdd, wt = cfg["entry"]
    entry_raw = score_begrenzen(
        company * wc + bewertung * wb2 + dd_score * wdd + trend_score * wt
    )
    entry, status, gate = einstiegs_gate(company, trap, entry_raw)
    return company, entry_raw, entry, status, gate

def einstiegs_gate(company_score, trap_score, rohscore):
    """
    Sicherheits-Gate 0.6.1.

    Es verändert NICHT die zugrunde liegenden Qualitäts-, Entwicklungs-,
    Bewertungs- oder Drawdown-Regeln. Es verhindert nur, dass ein großer
    Kursrückgang ein fundamental schwaches/riskantes Unternehmen zu einer
    positiven Einstiegslage hochzieht.

    Priorität:
    1. Hohes Value-Trap-Risiko
    2. Mittleres Value-Trap-Risiko
    3. Schwacher Unternehmensscore
    4. Sonst Rohscore unverändert
    """
    limit = 100
    gruende = []

    if trap_score >= 60:
        limit = min(limit, 39)
        gruende.append("Value-Trap >= 60: positiver Einstieg gesperrt")
    elif trap_score >= 40:
        limit = min(limit, 54)
        gruende.append("Value-Trap 40-59: maximal Beobachten")

    if company_score < 40:
        limit = min(limit, 39)
        gruende.append("Unternehmensscore < 40: positiver Einstieg gesperrt")
    elif company_score < 55:
        limit = min(limit, 54)
        gruende.append("Unternehmensscore 40-54: maximal Beobachten")
    elif company_score < 70:
        limit = min(limit, 69)
        gruende.append("Unternehmensscore 55-69: Einstieg nach oben begrenzt")

    final = min(rohscore, limit)

    if trap_score >= 60:
        status = "RISIKOREICHER RÜCKSETZER"
    elif trap_score >= 40:
        status = "BEOBACHTEN"
    elif company_score < 40:
        status = "KEIN EINSTIEG"
    elif final >= 70:
        status = "INTERESSANTER EINSTIEG"
    elif final >= 55:
        status = "BEOBACHTEN"
    else:
        status = "KEIN BESONDERER EINSTIEG"

    if not gruende:
        gruende.append("kein Sicherheits-Limit aktiv")

    return score_begrenzen(final), status, " | ".join(gruende)


# ============================================================
# DATEN LADEN MIT RETRY
# ============================================================


# ============================================================
# TRADEPILOT BACKTEST 0.8
# ============================================================
# WICHTIG:
# - Die Score-Logik entspricht TradePilot 0.6.1.
# - Historische Fundamentaldaten werden nur verwendet, wenn das
#   Geschäftsjahr mindestens FUNDAMENT_LAG_TAGE zurückliegt.
# - Das ist konservativer Schutz gegen Look-ahead-Bias, aber KEIN
#   vollständig revisionssicheres Point-in-Time-Datenarchiv.
# - Historisches Forward-KGV und PEG sind aus den kostenlosen Yahoo-
#   Daten nicht zuverlässig rekonstruierbar und bleiben deshalb leer.
# - 12-Monats-Ergebnisse überlappen bei quartalsweisen Signalen.
# ============================================================

FUNDAMENT_LAG_TAGE = 120
START_DATUM = "2022-01-01"
MARKT_BENCHMARK = "SPY"
SEKTOR_BENCHMARKS = {
    "STANDARD": "SPY",
    "BANK": "XLF",
    "CAPITAL_MARKETS": "XLF",
    "ENERGY": "XLE",
}
MAX_ALTER_ABSCHLUSS_TAGE = 550

# ============================================================
# PERFORMANCE / CACHE - 0.8.2 FAST
# ============================================================
# WICHTIG: Diese Werte beschleunigen nur Laden und Verarbeitung.
# Die Score-, Gate- und Auswertungslogik bleibt unverändert zu 0.8.1.
PERFORMANCE_VERSION = "0.8.4 LARGE"
CACHE_FORMAT_VERSION = 1
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "backtest_cache"
DEFAULT_BATCH_SIZE = 25
DEFAULT_WORKERS = min(8, max(2, os.cpu_count() or 4))
PRICE_CACHE_TTL_STUNDEN = 12
FUNDAMENT_CACHE_TTL_STUNDEN = 168

# Laufzeitwerte; werden in main() aus den Kommandozeilenargumenten gesetzt.
CACHE_DIR = DEFAULT_CACHE_DIR
CACHE_AKTIV = True
CACHE_FORCE_REFRESH = False


def naive_ts(x):
    t = pd.Timestamp(x)
    if t.tzinfo is not None:
        t = t.tz_localize(None)
    return t


def tabelle_bis_stichtag(tabelle, stichtag):
    """
    Gibt nur Geschäftsjahre frei, deren Periodenende plus Sicherheits-Lag
    am historischen Stichtag bereits erreicht war.
    """
    if tabelle is None or tabelle.empty:
        return pd.DataFrame()

    stichtag = naive_ts(stichtag).normalize()
    cols = []

    for c in tabelle.columns:
        try:
            period_end = pd.to_datetime(c, errors="coerce")
            if pd.isna(period_end):
                continue
            period_end = naive_ts(period_end).normalize()
            verfuegbar_ab = period_end + pd.Timedelta(days=FUNDAMENT_LAG_TAGE)
            if verfuegbar_ab <= stichtag:
                cols.append(c)
        except Exception:
            continue

    if not cols:
        return pd.DataFrame(index=tabelle.index)

    return tabelle.loc[:, cols].copy()


def letzte_zahl(tabelle, namen):
    serie = zeile_finden(tabelle, namen)
    werte = finanzwerte_sortieren(serie)
    return werte[-1][1] if werte else None


def letzte_zwei(tabelle, namen):
    serie = zeile_finden(tabelle, namen)
    werte = finanzwerte_sortieren(serie)
    if len(werte) < 2:
        return None, None
    return werte[-2][1], werte[-1][1]


def letzter_abschluss_stichtag(*tabellen):
    daten = []
    for t in tabellen:
        if t is None or t.empty:
            continue
        for c in t.columns:
            try:
                daten.append(naive_ts(c))
            except Exception:
                pass
    return max(daten) if daten else None


def historische_info_bauen(modell, income, cashflow, balance, kurs):
    umsatz_alt, umsatz = letzte_zwei(income, ["TotalRevenue", "OperatingRevenue"])
    gewinn = letzte_zahl(income, [
        "NetIncome", "NetIncomeCommonStockholders",
        "NetIncomeIncludingNoncontrollingInterests"
    ])
    fcf = letzte_zahl(cashflow, ["FreeCashFlow"])
    debt = letzte_zahl(balance, ["TotalDebt"])
    cash = letzte_zahl(balance, [
        "CashCashEquivalentsAndShortTermInvestments",
        "CashAndCashEquivalents", "CashFinancial"
    ])
    equity = letzte_zahl(balance, [
        "StockholdersEquity", "CommonStockEquity", "TotalEquityGrossMinorityInterest"
    ])
    shares = letzte_zahl(income, [
        "DilutedAverageShares", "BasicAverageShares"
    ])
    eps = letzte_zahl(income, ["DilutedEPS", "BasicEPS"])

    growth = None
    if umsatz_alt is not None and umsatz is not None and umsatz_alt != 0:
        growth = (umsatz - umsatz_alt) / abs(umsatz_alt)

    margin = None
    if umsatz not in (None, 0) and gewinn is not None:
        margin = gewinn / umsatz

    roe = None
    if equity not in (None, 0) and gewinn is not None:
        roe = gewinn / equity

    market_cap = None
    if shares is not None and shares > 0 and kurs is not None:
        market_cap = shares * kurs

    pe = None
    if eps is not None and eps > 0 and kurs is not None:
        pe = kurs / eps
    elif gewinn is not None and gewinn > 0 and market_cap is not None:
        pe = market_cap / gewinn

    ps = None
    if market_cap is not None and umsatz is not None and umsatz > 0:
        ps = market_cap / umsatz

    pb = None
    if market_cap is not None and equity is not None and equity > 0:
        pb = market_cap / equity

    return {
        "totalRevenue": umsatz,
        "revenueGrowth": growth,
        "profitMargins": margin,
        "freeCashflow": fcf,
        "returnOnEquity": roe,
        "totalDebt": debt,
        "totalCash": cash,
        "trailingPE": pe,
        "forwardPE": None,   # historisch nicht belastbar verfügbar
        "pegRatio": None,    # historisch nicht belastbar verfügbar
        "priceToSalesTrailing12Months": ps,
        "priceToBook": pb,
    }


def preis_am_oder_nachher(historie, datum, toleranz_tage=10):
    if historie is None or historie.empty:
        return None
    d = naive_ts(datum)
    idx = pd.DatetimeIndex([naive_ts(x) for x in historie.index])
    h = historie.copy()
    h.index = idx
    teil = h.loc[(h.index >= d) & (h.index <= d + pd.Timedelta(days=toleranz_tage))]
    if teil.empty:
        return None
    return float(teil["Close"].iloc[0])


def rendite_vorwaerts(historie, stichtag, monate):
    start = preis_am_oder_nachher(historie, stichtag, 5)
    ziel_datum = naive_ts(stichtag) + pd.DateOffset(months=monate)
    ziel = preis_am_oder_nachher(historie, ziel_datum, 10)
    if start is None or ziel is None or start == 0:
        return None
    return (ziel / start - 1) * 100


def quartals_stichtage(historie):
    if historie is None or historie.empty:
        return []
    h = historie.copy()
    h.index = pd.DatetimeIndex([naive_ts(x) for x in h.index])
    h = h.loc[h.index >= pd.Timestamp(START_DATUM)]
    if h.empty:
        return []
    # Letzter Handelstag jedes Quartals
    return list(h.groupby(h.index.to_period("Q")).apply(lambda x: x.index[-1]))


def eine_beobachtung(symbol, modell, stichtag, historie, income_all, cashflow_all, balance_all, benchmark_historien, diagnose=None):
    def verworfen(grund):
        if diagnose is not None:
            diagnose[grund] += 1
        return None

    h_bis = historie.loc[[naive_ts(x) <= naive_ts(stichtag) for x in historie.index]].copy()
    if len(h_bis) < 252:
        return verworfen("weniger als 252 Kurstage vor Stichtag")

    income = tabelle_bis_stichtag(income_all, stichtag)
    cashflow = tabelle_bis_stichtag(cashflow_all, stichtag)
    balance = tabelle_bis_stichtag(balance_all, stichtag)

    if income.empty:
        return verworfen("noch kein Jahresabschluss nach 120-Tage-Lag freigegeben")

    # Mindestens zwei Umsatzjahre für einen sinnvollen Entwicklungsscore.
    revenue_series = zeile_finden(income, ["TotalRevenue", "OperatingRevenue"])
    anzahl_umsatzjahre = len(finanzwerte_sortieren(revenue_series))
    if anzahl_umsatzjahre < 2:
        return verworfen("weniger als 2 freigegebene Umsatzjahre")

    letzter_abschluss = letzter_abschluss_stichtag(income, cashflow, balance)
    if letzter_abschluss is None:
        return verworfen("kein datierbarer Jahresabschluss")

    alter = (naive_ts(stichtag) - letzter_abschluss).days
    if alter > MAX_ALTER_ABSCHLUSS_TAGE:
        return verworfen("letzter freigegebener Abschluss älter als 550 Tage")

    trend = trend_analyse(h_bis.tail(520))
    kurs = trend.get("kurs")
    if kurs is None:
        return verworfen("Trend/Kurs am Stichtag nicht berechenbar")

    info = historische_info_bauen(modell, income, cashflow, balance, kurs)
    qualitaet = qualitaet_berechnen(modell, info)
    entwicklung, margen_score = entwicklung_berechnen(modell, income, cashflow, balance)
    bewertung = bewertung_berechnen(modell, info)
    dd = trend.get("drawdown")
    dd_score = drawdown_score_berechnen(dd)
    trap, trap_roh, trap_gruende = value_trap_risiko(
        modell, info, qualitaet, entwicklung, margen_score, dd
    )
    u = unternehmens_score(qualitaet, entwicklung, bewertung, trap)
    einstieg_roh = einstiegs_score(u, bewertung, dd_score, trend["trend_score"])
    einstieg, status, gate = einstiegs_gate(u, trap, einstieg_roh)

    varianten = {}
    for varianten_name in SCORE_VARIANTEN:
        vu, vroh, ve, vstatus, vgate = score_variante_berechnen(
            varianten_name, qualitaet, entwicklung, bewertung, trap, dd_score, trend["trend_score"]
        )
        varianten[varianten_name] = (vu, vroh, ve, vstatus, vgate)

    result = {
        "Symbol": symbol,
        "Modell": modell,
        "Stichtag": naive_ts(stichtag).date().isoformat(),
        "Abschluss_bis": letzter_abschluss.date().isoformat(),
        "Qualitaet": qualitaet,
        "Entwicklung": entwicklung,
        "Bewertung": bewertung,
        "Unternehmensscore": u,
        "Value_Trap": trap,
        "Value_Trap_Roh": trap_roh,
        "Trap_Gruende": text_liste(trap_gruende),
        "Drawdown": round(dd, 1) if dd is not None else None,
        "Drawdown_Score": dd_score,
        "Trend": trend["trend_score"],
        "Einstieg_Roh": einstieg_roh,
        "Einstiegsscore": einstieg,
        "Status": status,
        "Gate": gate,
    }

    for varianten_name, (vu, vroh, ve, vstatus, vgate) in varianten.items():
        kurz = {
            "BASELINE_061": "B061",
            "CANDIDATE_062_BALANCED": "C062B",
            "CANDIDATE_062_QUALITY": "C062Q",
        }[varianten_name]
        result[f"{kurz}_Unternehmensscore"] = vu
        result[f"{kurz}_Einstieg_Roh"] = vroh
        result[f"{kurz}_Einstiegsscore"] = ve
        result[f"{kurz}_Status"] = vstatus
        result[f"{kurz}_Gate"] = vgate

    sektor_ticker = SEKTOR_BENCHMARKS.get(modell, MARKT_BENCHMARK)
    result["Sektor_Benchmark"] = sektor_ticker

    markt_hist = benchmark_historien.get(MARKT_BENCHMARK)
    sektor_hist = benchmark_historien.get(sektor_ticker)

    for monate in (3, 6, 12):
        r = rendite_vorwaerts(historie, stichtag, monate)
        markt = rendite_vorwaerts(markt_hist, stichtag, monate)
        sektor = rendite_vorwaerts(sektor_hist, stichtag, monate)

        result[f"Rendite_{monate}M"] = round(r, 2) if r is not None else None
        result[f"SPY_{monate}M"] = round(markt, 2) if markt is not None else None
        result[f"Alpha_{monate}M"] = (
            round(r - markt, 2) if r is not None and markt is not None else None
        )
        result[f"Sektor_{monate}M"] = round(sektor, 2) if sektor is not None else None
        result[f"Sektor_Alpha_{monate}M"] = (
            round(r - sektor, 2) if r is not None and sektor is not None else None
        )

    return result


def _sicherer_dateiname(symbol):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in str(symbol))


def _cache_pfad(kind, symbol):
    return CACHE_DIR / kind / f"{_sicherer_dateiname(symbol)}.pkl"


def _cache_ist_gueltig(pfad, ttl_stunden):
    if not pfad.exists():
        return False
    alter_stunden = (time.time() - pfad.stat().st_mtime) / 3600.0
    return alter_stunden <= ttl_stunden


def cache_laden(kind, symbol, ttl_stunden):
    if not CACHE_AKTIV or CACHE_FORCE_REFRESH:
        return None
    pfad = _cache_pfad(kind, symbol)
    if not _cache_ist_gueltig(pfad, ttl_stunden):
        return None
    try:
        with pfad.open("rb") as f:
            payload = pickle.load(f)
        if payload.get("cache_format") != CACHE_FORMAT_VERSION:
            return None
        return payload.get("data")
    except Exception:
        return None


def cache_speichern(kind, symbol, daten):
    if not CACHE_AKTIV:
        return
    pfad = _cache_pfad(kind, symbol)
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = pfad.with_suffix(".tmp")
        with tmp.open("wb") as f:
            pickle.dump(
                {
                    "cache_format": CACHE_FORMAT_VERSION,
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "data": daten,
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        tmp.replace(pfad)
    except Exception as e:
        print(f"  ! Cache konnte für {symbol}/{kind} nicht gespeichert werden: {e}")


def normalisiere_historie(hist):
    if hist is None or hist.empty:
        return pd.DataFrame()
    h = hist.copy()
    h.index = pd.DatetimeIndex([naive_ts(x) for x in h.index])
    h = h.sort_index()
    h = h.loc[h.index >= pd.Timestamp("2019-01-01")]
    if "Close" in h.columns:
        h = h.loc[h["Close"].notna()]
    return h


def _batch_hist_extrahieren(download, symbol, batch):
    if download is None or download.empty:
        return pd.DataFrame()

    try:
        if isinstance(download.columns, pd.MultiIndex):
            level0 = set(map(str, download.columns.get_level_values(0)))
            level1 = set(map(str, download.columns.get_level_values(1)))

            if symbol in level0:
                hist = download[symbol].copy()
            elif symbol in level1:
                hist = download.xs(symbol, axis=1, level=1).copy()
            else:
                return pd.DataFrame()
        else:
            if len(batch) != 1:
                return pd.DataFrame()
            hist = download.copy()
    except Exception:
        return pd.DataFrame()

    return normalisiere_historie(hist)


def _kurs_einzeln_laden(symbol, versuche=3):
    """Robuster Einzel-Fallback für Batch-Ausreißer.

    Erst Ticker.history, danach ein nicht-paralleler yf.download-Versuch.
    Das reduziert temporäre yfinance/SQLite-Probleme wie 'database is locked'.
    """
    fehler = None
    for i in range(versuche):
        # Methode 1: Ticker.history
        try:
            hist = yf.Ticker(symbol).history(period="max", auto_adjust=True)
            hist = normalisiere_historie(hist)
            if not hist.empty and len(hist) >= 252:
                return hist
            if hist.empty:
                fehler = ValueError("keine Kurshistorie")
            else:
                fehler = ValueError(f"Kurshistorie zu kurz: nur {len(hist)} Handelstage")
        except Exception as e:
            fehler = e

        # Methode 2: bewusst threads=False, um yfinance-DB-Locks zu umgehen
        try:
            dl = yf.download(
                tickers=symbol, period="max", auto_adjust=True,
                progress=False, actions=False, threads=False,
            )
            hist2 = normalisiere_historie(dl)
            if not hist2.empty and len(hist2) >= 252:
                return hist2
            if not hist2.empty:
                fehler = ValueError(f"Kurshistorie zu kurz: nur {len(hist2)} Handelstage")
        except Exception as e:
            fehler = e

        if i < versuche - 1:
            time.sleep(1.5 * (i + 1))
    raise fehler or ValueError("keine Kurshistorie")


def lade_kurshistorien_gebuendelt(symbole, batch_size=DEFAULT_BATCH_SIZE):
    """Lädt Kurshistorien aus Cache und fehlende Titel in Yahoo-Batches."""
    symbole = list(dict.fromkeys(symbole))
    ergebnis = {}
    fehlend = []
    cache_hits = 0

    for symbol in symbole:
        cached = cache_laden("prices", symbol, PRICE_CACHE_TTL_STUNDEN)
        if cached is not None:
            hist = normalisiere_historie(cached)
            if len(hist) >= 252:
                ergebnis[symbol] = hist
                cache_hits += 1
                continue
        fehlend.append(symbol)

    print(f"Kursdaten: {cache_hits} Cache-Treffer | {len(fehlend)} neu zu laden")

    for pos in range(0, len(fehlend), max(1, batch_size)):
        batch = fehlend[pos:pos + max(1, batch_size)]
        print(
            f"  Kurs-Batch {pos // max(1, batch_size) + 1}: "
            f"{len(batch)} Titel ({', '.join(batch[:5])}{' ...' if len(batch) > 5 else ''})"
        )
        download = None
        try:
            download = yf.download(
                tickers=batch,
                period="max",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
                actions=False,
            )
        except Exception as e:
            print(f"  ! Batch-Download fehlgeschlagen ({e}); Einzel-Fallback wird verwendet.")

        for symbol in batch:
            hist = _batch_hist_extrahieren(download, symbol, batch)
            if hist.empty or len(hist) < 252:
                try:
                    hist = _kurs_einzeln_laden(symbol)
                except Exception as e:
                    print(f"  ! Kursdaten {symbol}: {e}")
                    continue
            ergebnis[symbol] = hist
            cache_speichern("prices", symbol, hist)

    return ergebnis


def _fundamental_einzeln_laden(symbol, versuche=3):
    fehler = None
    for i in range(versuche):
        try:
            t = yf.Ticker(symbol)
            income = t.get_income_stmt(freq="yearly")
            cashflow = t.get_cash_flow(freq="yearly")
            balance = t.get_balance_sheet(freq="yearly")
            return income, cashflow, balance
        except Exception as e:
            fehler = e
            if i < versuche - 1:
                time.sleep(1.25 * (i + 1))
    raise fehler


def lade_fundamentaldaten_parallel(symbole, workers=DEFAULT_WORKERS):
    """Lädt Jahresabschlüsse aus Cache; Cache-Misses parallel per yfinance."""
    symbole = list(dict.fromkeys(symbole))
    ergebnis = {}
    fehlend = []
    cache_hits = 0

    for symbol in symbole:
        cached = cache_laden("fundamentals", symbol, FUNDAMENT_CACHE_TTL_STUNDEN)
        if cached is not None and isinstance(cached, tuple) and len(cached) == 3:
            ergebnis[symbol] = cached
            cache_hits += 1
        else:
            fehlend.append(symbol)

    print(f"Fundamentaldaten: {cache_hits} Cache-Treffer | {len(fehlend)} neu zu laden")
    if not fehlend:
        return ergebnis, {}

    fehler = {}
    max_workers = max(1, min(int(workers), len(fehlend)))
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tp-fund") as pool:
        futures = {pool.submit(_fundamental_einzeln_laden, s): s for s in fehlend}
        fertig = 0
        for future in as_completed(futures):
            symbol = futures[future]
            fertig += 1
            try:
                daten = future.result()
                ergebnis[symbol] = daten
                cache_speichern("fundamentals", symbol, daten)
                print(f"  Fundamental [{fertig:03}/{len(fehlend)}] {symbol:<6} OK")
            except Exception as e:
                fehler[symbol] = str(e)
                print(f"  Fundamental [{fertig:03}/{len(fehlend)}] {symbol:<6} FEHLER | {e}")

    return ergebnis, fehler




def _historie_vorbereiten(historie):
    """Normalisiert den DatetimeIndex genau einmal und hält Close als NumPy-Array bereit."""
    if historie is None or historie.empty:
        return None
    h = historie.copy()
    if not isinstance(h.index, pd.DatetimeIndex) or h.index.tz is not None:
        h.index = pd.DatetimeIndex([naive_ts(x) for x in h.index])
    else:
        h.index = h.index.tz_localize(None) if h.index.tz is not None else h.index
    # Yahoo liefert chronologisch; falls Cache/Quelle abweicht, einmalig sortieren.
    if not h.index.is_monotonic_increasing:
        h = h.sort_index()
    return {
        "df": h,
        "index": h.index,
        "close": h["Close"].to_numpy(copy=False),
    }


def _statement_vorbereiten(tabelle):
    """Berechnet die Freigabedaten der Jahresabschluss-Spalten nur einmal."""
    if tabelle is None or tabelle.empty:
        return {"df": pd.DataFrame(), "release": []}
    release = []
    for c in tabelle.columns:
        try:
            period_end = pd.to_datetime(c, errors="coerce")
            if pd.isna(period_end):
                continue
            period_end = naive_ts(period_end).normalize()
            release.append((c, period_end + pd.Timedelta(days=FUNDAMENT_LAG_TAGE), period_end))
        except Exception:
            continue
    return {"df": tabelle, "release": release}


def _statement_bis_stichtag_fast(prepared, stichtag):
    tabelle = prepared["df"]
    if tabelle is None or tabelle.empty:
        return pd.DataFrame()
    d = naive_ts(stichtag).normalize()
    cols = [c for c, verfuegbar_ab, _ in prepared["release"] if verfuegbar_ab <= d]
    if not cols:
        return pd.DataFrame(index=tabelle.index)
    # Kein .copy(): die nachfolgenden Kernfunktionen lesen diese Tabelle nur.
    return tabelle.loc[:, cols]


def _preis_am_oder_nachher_fast(prepared_hist, datum, toleranz_tage=10):
    if not prepared_hist:
        return None
    idx = prepared_hist["index"]
    if len(idx) == 0:
        return None
    d = naive_ts(datum)
    pos = int(idx.searchsorted(d, side="left"))
    if pos >= len(idx):
        return None
    if idx[pos] > d + pd.Timedelta(days=toleranz_tage):
        return None
    try:
        return float(prepared_hist["close"][pos])
    except Exception:
        return None


def _rendite_vorwaerts_fast(prepared_hist, stichtag, monate):
    start = _preis_am_oder_nachher_fast(prepared_hist, stichtag, 5)
    ziel_datum = naive_ts(stichtag) + pd.DateOffset(months=monate)
    ziel = _preis_am_oder_nachher_fast(prepared_hist, ziel_datum, 10)
    if start is None or ziel is None or start == 0:
        return None
    return (ziel / start - 1) * 100


def _quartals_stichtage_fast(prepared_hist):
    if not prepared_hist:
        return []
    idx = prepared_hist["index"]
    idx = idx[idx >= pd.Timestamp(START_DATUM)]
    if len(idx) == 0:
        return []
    # Gleiche Semantik wie groupby(...).apply(lambda x: x.index[-1]), ohne DataFrame-Kopien.
    periods = idx.to_period("Q")
    result = []
    for i in range(len(idx)):
        if i == len(idx) - 1 or periods[i] != periods[i + 1]:
            result.append(idx[i])
    return result


def eine_beobachtung_turbo(symbol, modell, stichtag, prepared_hist, income_p, cashflow_p, balance_p,
                            benchmark_prepared, diagnose=None):
    """Output-kompatible 0.8.1-Beobachtung, aber ohne wiederholtes Index-/DataFrame-Rebuilding."""
    def verworfen(grund):
        if diagnose is not None:
            diagnose[grund] += 1
        return None

    d = naive_ts(stichtag)
    hist_df = prepared_hist["df"]
    idx = prepared_hist["index"]
    ende = int(idx.searchsorted(d, side="right"))
    if ende < 252:
        return verworfen("weniger als 252 Kurstage vor Stichtag")
    h_bis = hist_df.iloc[:ende]

    income = _statement_bis_stichtag_fast(income_p, stichtag)
    cashflow = _statement_bis_stichtag_fast(cashflow_p, stichtag)
    balance = _statement_bis_stichtag_fast(balance_p, stichtag)

    if income.empty:
        return verworfen("noch kein Jahresabschluss nach 120-Tage-Lag freigegeben")

    revenue_series = zeile_finden(income, ["TotalRevenue", "OperatingRevenue"])
    anzahl_umsatzjahre = len(finanzwerte_sortieren(revenue_series))
    if anzahl_umsatzjahre < 2:
        return verworfen("weniger als 2 freigegebene Umsatzjahre")

    letzter_abschluss = letzter_abschluss_stichtag(income, cashflow, balance)
    if letzter_abschluss is None:
        return verworfen("kein datierbarer Jahresabschluss")

    alter = (d - letzter_abschluss).days
    if alter > MAX_ALTER_ABSCHLUSS_TAGE:
        return verworfen("letzter freigegebener Abschluss älter als 550 Tage")

    trend = trend_analyse(h_bis.tail(520))
    kurs = trend.get("kurs")
    if kurs is None:
        return verworfen("Trend/Kurs am Stichtag nicht berechenbar")

    info = historische_info_bauen(modell, income, cashflow, balance, kurs)
    qualitaet = qualitaet_berechnen(modell, info)
    entwicklung, margen_score = entwicklung_berechnen(modell, income, cashflow, balance)
    bewertung = bewertung_berechnen(modell, info)
    dd = trend.get("drawdown")
    dd_score = drawdown_score_berechnen(dd)
    trap, trap_roh, trap_gruende = value_trap_risiko(
        modell, info, qualitaet, entwicklung, margen_score, dd
    )
    u = unternehmens_score(qualitaet, entwicklung, bewertung, trap)
    einstieg_roh = einstiegs_score(u, bewertung, dd_score, trend["trend_score"])
    einstieg, status, gate = einstiegs_gate(u, trap, einstieg_roh)

    result = {
        "Symbol": symbol,
        "Modell": modell,
        "Stichtag": d.date().isoformat(),
        "Abschluss_bis": letzter_abschluss.date().isoformat(),
        "Qualitaet": qualitaet,
        "Entwicklung": entwicklung,
        "Bewertung": bewertung,
        "Unternehmensscore": u,
        "Value_Trap": trap,
        "Value_Trap_Roh": trap_roh,
        "Trap_Gruende": text_liste(trap_gruende),
        "Drawdown": round(dd, 1) if dd is not None else None,
        "Drawdown_Score": dd_score,
        "Trend": trend["trend_score"],
        "Einstieg_Roh": einstieg_roh,
        "Einstiegsscore": einstieg,
        "Status": status,
        "Gate": gate,
    }

    # 0.8.5.1 FIX: Der TURBO-Pfad muss dieselben Audit-Spalten erzeugen
    # wie der klassische Pfad. In 0.8.5 fehlten diese Spalten nur hier.
    for varianten_name in SCORE_VARIANTEN:
        vu, vroh, ve, vstatus, vgate = score_variante_berechnen(
            varianten_name, qualitaet, entwicklung, bewertung, trap, dd_score, trend["trend_score"]
        )
        kurz = {
            "BASELINE_061": "B061",
            "CANDIDATE_062_BALANCED": "C062B",
            "CANDIDATE_062_QUALITY": "C062Q",
        }[varianten_name]
        result[f"{kurz}_Unternehmensscore"] = vu
        result[f"{kurz}_Einstieg_Roh"] = vroh
        result[f"{kurz}_Einstiegsscore"] = ve
        result[f"{kurz}_Status"] = vstatus
        result[f"{kurz}_Gate"] = vgate

    sektor_ticker = SEKTOR_BENCHMARKS.get(modell, MARKT_BENCHMARK)
    result["Sektor_Benchmark"] = sektor_ticker
    markt_p = benchmark_prepared.get(MARKT_BENCHMARK)
    sektor_p = benchmark_prepared.get(sektor_ticker)

    for monate in (3, 6, 12):
        r = _rendite_vorwaerts_fast(prepared_hist, stichtag, monate)
        markt = _rendite_vorwaerts_fast(markt_p, stichtag, monate)
        sektor = _rendite_vorwaerts_fast(sektor_p, stichtag, monate)
        result[f"Rendite_{monate}M"] = round(r, 2) if r is not None else None
        result[f"SPY_{monate}M"] = round(markt, 2) if markt is not None else None
        result[f"Alpha_{monate}M"] = round(r - markt, 2) if r is not None and markt is not None else None
        result[f"Sektor_{monate}M"] = round(sektor, 2) if sektor is not None else None
        result[f"Sektor_Alpha_{monate}M"] = round(r - sektor, 2) if r is not None and sektor is not None else None

    return result

def verarbeite_symbol_parallel(job_index, symbol, modell, historie, fundamentals, benchmark_historien):
    """TURBO: berechnet alle Stichtage mit einmalig vorbereiteten Indizes/Statements."""
    start = time.perf_counter()
    diagnose = Counter()
    beobachtungen = []

    if historie is None or historie.empty:
        raise ValueError("keine Kurshistorie vorbereitet")
    if fundamentals is None:
        raise ValueError("keine Fundamentaldaten vorbereitet")

    income, cashflow, balance = fundamentals
    prepared_hist = _historie_vorbereiten(historie)
    income_p = _statement_vorbereiten(income)
    cashflow_p = _statement_vorbereiten(cashflow)
    balance_p = _statement_vorbereiten(balance)
    benchmark_prepared = {k: _historie_vorbereiten(v) for k, v in benchmark_historien.items()}
    stichtage = _quartals_stichtage_fast(prepared_hist)

    for stichtag in stichtage:
        obs = eine_beobachtung_turbo(
            symbol, modell, stichtag, prepared_hist,
            income_p, cashflow_p, balance_p, benchmark_prepared, diagnose,
        )
        if obs is not None:
            beobachtungen.append(obs)

    return {
        "job_index": job_index,
        "symbol": symbol,
        "modell": modell,
        "beobachtungen": beobachtungen,
        "diagnose": diagnose,
        "sekunden": time.perf_counter() - start,
    }


def lade_marktdaten(symbol, versuche=3):
    """Kompatibilitätsfunktion für Einzeltests; Hauptlauf nutzt Batch/Cache."""
    hist = cache_laden("prices", symbol, PRICE_CACHE_TTL_STUNDEN)
    if hist is None:
        hist = _kurs_einzeln_laden(symbol, versuche=versuche)
        cache_speichern("prices", symbol, hist)
    else:
        hist = normalisiere_historie(hist)

    fund = cache_laden("fundamentals", symbol, FUNDAMENT_CACHE_TTL_STUNDEN)
    if fund is None:
        fund = _fundamental_einzeln_laden(symbol, versuche=versuche)
        cache_speichern("fundamentals", symbol, fund)

    income, cashflow, balance = fund
    return hist, income, cashflow, balance


def zahlenreihe(df, spalte):
    if spalte not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[spalte], errors="coerce").dropna()


def mittelwert(df, spalte):
    x = zahlenreihe(df, spalte)
    return x.mean() if not x.empty else float("nan")


def medianwert(df, spalte):
    x = zahlenreihe(df, spalte)
    return x.median() if not x.empty else float("nan")


def anteil_bedingung(df, spalte, funktion):
    x = zahlenreihe(df, spalte)
    if x.empty:
        return float("nan")
    return funktion(x).mean() * 100


def horizon_statistik(df, monate):
    r_spalte = f"Rendite_{monate}M"
    b_spalte = f"SPY_{monate}M"
    a_spalte = f"Alpha_{monate}M"
    s_spalte = f"Sektor_{monate}M"
    sa_spalte = f"Sektor_Alpha_{monate}M"

    if r_spalte not in df.columns or b_spalte not in df.columns:
        return None

    r = pd.to_numeric(df[r_spalte], errors="coerce")
    b = pd.to_numeric(df[b_spalte], errors="coerce")
    a = pd.to_numeric(df[a_spalte], errors="coerce")

    gueltig = r.notna() & b.notna()
    if not gueltig.any():
        return None

    r2 = r[gueltig]
    b2 = b[gueltig]
    a2 = a[gueltig]

    ergebnis = {
        "n": int(len(r2)),
        "rendite_avg": float(r2.mean()),
        "rendite_median": float(r2.median()),
        "alpha_avg": float(a2.mean()),
        "alpha_median": float(a2.median()),
        "spy_geschlagen": float((a2 > 0).mean() * 100),
        "positiv": float((r2 > 0).mean() * 100),
        "verlust_10": float((r2 <= -10).mean() * 100),
        "verlust_20": float((r2 <= -20).mean() * 100),
        "best": float(r2.max()),
        "worst": float(r2.min()),
        "sektor_n": 0,
        "sektor_alpha_avg": float("nan"),
        "sektor_alpha_median": float("nan"),
        "sektor_geschlagen": float("nan"),
    }

    if s_spalte in df.columns and sa_spalte in df.columns:
        sektor = pd.to_numeric(df[s_spalte], errors="coerce")
        sektor_alpha = pd.to_numeric(df[sa_spalte], errors="coerce")
        sg = r.notna() & sektor.notna() & sektor_alpha.notna()
        if sg.any():
            sa = sektor_alpha[sg]
            ergebnis["sektor_n"] = int(len(sa))
            ergebnis["sektor_alpha_avg"] = float(sa.mean())
            ergebnis["sektor_alpha_median"] = float(sa.median())
            ergebnis["sektor_geschlagen"] = float((sa > 0).mean() * 100)

    return ergebnis

def gruppe_zeigen(name, teil, kompakt=False):
    print(f"{name:<31} Signale={len(teil):>4}")

    for m in (3, 6, 12):
        st = horizon_statistik(teil, m)
        if st is None:
            print(f"   {m:>2}M: n=   0 | keine vollständigen Vorwärtsdaten")
            continue

        print(
            f"   {m:>2}M: n={st['n']:>4} | "
            f"Ø {st['rendite_avg']:+6.1f}% | Med {st['rendite_median']:+6.1f}% | "
            f"Alpha Ø {st['alpha_avg']:+6.1f} | Med {st['alpha_median']:+6.1f} | "
            f"SPY geschl. {st['spy_geschlagen']:5.1f}% | "
            f"Sektor Alpha Med {st['sektor_alpha_median']:+6.1f} | "
            f"Sektor geschl. {st['sektor_geschlagen']:5.1f}% | "
            f"Positiv {st['positiv']:5.1f}% | <=-20% {st['verlust_20']:5.1f}%"
        )

        if not kompakt and m == 12:
            print(
                f"       12M-Spanne: schlechtester Fall {st['worst']:+.1f}% | "
                f"bester Fall {st['best']:+.1f}%"
            )


def score_band(df, spalte, lo, hi):
    if lo is None:
        return df[df[spalte] <= hi]
    if hi is None:
        return df[df[spalte] >= lo]
    return df[(df[spalte] >= lo) & (df[spalte] <= hi)]


def gueltige_horizon_daten(df, monate=12):
    r_spalte = f"Rendite_{monate}M"
    b_spalte = f"SPY_{monate}M"
    a_spalte = f"Alpha_{monate}M"

    x = df.copy()
    x[r_spalte] = pd.to_numeric(x[r_spalte], errors="coerce")
    x[b_spalte] = pd.to_numeric(x[b_spalte], errors="coerce")
    x[a_spalte] = pd.to_numeric(x[a_spalte], errors="coerce")
    return x.dropna(subset=[r_spalte, b_spalte, a_spalte])


def gueltige_sektor_horizon_daten(df, monate=12):
    r_spalte = f"Rendite_{monate}M"
    s_spalte = f"Sektor_{monate}M"
    a_spalte = f"Sektor_Alpha_{monate}M"
    x = df.copy()
    for sp in (r_spalte, s_spalte, a_spalte):
        if sp not in x.columns:
            return x.iloc[0:0].copy()
        x[sp] = pd.to_numeric(x[sp], errors="coerce")
    return x.dropna(subset=[r_spalte, s_spalte, a_spalte])


def signal_episoden(df, max_abstand_tage=130):
    """
    Aufeinanderfolgende qualifizierende Quartalssignale derselben Aktie
    zählen als eine Episode, solange zwischen zwei Signalen höchstens
    max_abstand_tage liegen. Repräsentant der Episode ist das erste Signal.
    """
    if df.empty:
        return df.copy()

    x = df.copy()
    x["_Datum"] = pd.to_datetime(x["Stichtag"], errors="coerce")
    x = x.dropna(subset=["_Datum"]).sort_values(["Symbol", "_Datum"])

    rep_indices = []
    for symbol, gruppe in x.groupby("Symbol", sort=False):
        letzter = None
        for idx, row in gruppe.iterrows():
            datum = row["_Datum"]
            if letzter is None or (datum - letzter).days > max_abstand_tage:
                rep_indices.append(idx)
            letzter = datum

    return x.loc[rep_indices].drop(columns=["_Datum"])


def getrimmter_mittelwert(serie, anteil=0.10):
    s = pd.to_numeric(serie, errors="coerce").dropna().sort_values()
    if s.empty:
        return float("nan")
    k = int(len(s) * anteil)
    if k == 0 or len(s) <= 2 * k:
        return float(s.mean())
    return float(s.iloc[k:len(s)-k].mean())


def robustheits_kennzahlen(df, monate=12):
    x = gueltige_horizon_daten(df, monate)
    if x.empty:
        return None

    r_col = f"Rendite_{monate}M"
    a_col = f"Alpha_{monate}M"
    r = x[r_col].sort_values()
    a = x[a_col]

    ohne_best1 = r.iloc[:-1] if len(r) > 1 else r.iloc[0:0]
    ohne_best3 = r.iloc[:-3] if len(r) > 3 else r.iloc[0:0]

    agg_dict = {
        "Rendite": (r_col, "mean"),
        "Alpha": (a_col, "mean"),
    }
    sektor_alpha_col = f"Sektor_Alpha_{monate}M"
    if sektor_alpha_col in x.columns:
        agg_dict["SektorAlpha"] = (sektor_alpha_col, "mean")

    pro_aktie = x.groupby("Symbol", as_index=False).agg(**agg_dict)

    episoden = signal_episoden(x)

    return {
        "n": len(x),
        "aktien": int(x["Symbol"].nunique()),
        "episoden": int(len(episoden)),
        "avg": float(r.mean()),
        "median": float(r.median()),
        "ohne_best1": float(ohne_best1.mean()) if not ohne_best1.empty else float("nan"),
        "ohne_best3": float(ohne_best3.mean()) if not ohne_best3.empty else float("nan"),
        "trim10": getrimmter_mittelwert(r, 0.10),
        "aktiengew_avg": float(pro_aktie["Rendite"].mean()),
        "aktiengew_median": float(pro_aktie["Rendite"].median()),
        "aktiengew_alpha": float(pro_aktie["Alpha"].mean()),
        "aktiengew_sektor_alpha": (
            float(pro_aktie["SektorAlpha"].mean())
            if "SektorAlpha" in pro_aktie.columns else float("nan")
        ),
    }


def schwellen_matrix(df):
    print()
    print("SCHWELLENWERT-MATRIX: UNTERNEHMENSSCORE + EINSTIEGSSCORE")
    print("-" * 158)
    print(
        f"{'Filter':<26} {'Signale':>7} {'12M n':>6} {'Aktien':>7} {'Epis.':>6} "
        f"{'12M Ø':>8} {'12M Med':>9} {'Alpha Ø':>9} {'Alpha Med':>10} "
        f"{'SPY%':>7} {'Sekt A Med':>10} {'Sekt%':>7} {'Positiv%':>9} {'<=-20%':>8}"
    )
    print("-" * 158)

    kombis = [
        (60, 60),
        (65, 60),
        (65, 65),
        (70, 60),
        (70, 65),
        (70, 70),
        (75, 65),
        (75, 70),
    ]

    matrix = []
    for u_grenze, e_grenze in kombis:
        teil = df[
            (df["Unternehmensscore"] >= u_grenze)
            & (df["Einstiegsscore"] >= e_grenze)
        ]
        st = horizon_statistik(teil, 12)
        gueltig12 = gueltige_horizon_daten(teil, 12)
        episoden12 = signal_episoden(gueltig12)
        zeile = {
            "U": u_grenze,
            "E": e_grenze,
            "Signale": len(teil),
            "N12": 0 if st is None else st["n"],
            "Aktien12": int(gueltig12["Symbol"].nunique()) if not gueltig12.empty else 0,
            "Episoden12": int(len(episoden12)),
            "R12": float("nan") if st is None else st["rendite_avg"],
            "Med12": float("nan") if st is None else st["rendite_median"],
            "A12": float("nan") if st is None else st["alpha_avg"],
            "AMed12": float("nan") if st is None else st["alpha_median"],
            "SPY": float("nan") if st is None else st["spy_geschlagen"],
            "SektorAMed": float("nan") if st is None else st["sektor_alpha_median"],
            "SektorBeat": float("nan") if st is None else st["sektor_geschlagen"],
            "Pos": float("nan") if st is None else st["positiv"],
            "Loss20": float("nan") if st is None else st["verlust_20"],
        }
        matrix.append(zeile)

        def fmt(v, suffix=""):
            return "   --   " if pd.isna(v) else f"{v:+7.1f}{suffix}"

        spy_txt = "--" if pd.isna(zeile["SPY"]) else f"{zeile['SPY']:.1f}%"
        sekt_a_txt = "--" if pd.isna(zeile["SektorAMed"]) else f"{zeile['SektorAMed']:+.1f}"
        sekt_b_txt = "--" if pd.isna(zeile["SektorBeat"]) else f"{zeile['SektorBeat']:.1f}%"
        pos_txt = "--" if pd.isna(zeile["Pos"]) else f"{zeile['Pos']:.1f}%"
        loss20_txt = "--" if pd.isna(zeile["Loss20"]) else f"{zeile['Loss20']:.1f}%"

        print(
            f"U>={u_grenze} & E>={e_grenze:<3}"
            f"{len(teil):>9} {zeile['N12']:>6} {zeile['Aktien12']:>7} {zeile['Episoden12']:>6} "
            f"{fmt(zeile['R12'], '%'):>8} {fmt(zeile['Med12'], '%'):>9} "
            f"{fmt(zeile['A12']):>9} {fmt(zeile['AMed12']):>10} "
            f"{spy_txt:>7} {sekt_a_txt:>10} {sekt_b_txt:>7} {pos_txt:>9} {loss20_txt:>8}"
        )

    print()
    print("Aktien = verschiedene Aktien mit vollständigem 12M-Ergebnis.")
    print("Epis.  = unabhängiger angenäherte Signal-Episoden (Folgequartale derselben Aktie zusammengefasst).")
    print("Kleine Gruppen bleiben Hinweise, keine belastbare Evidenz.")
    return pd.DataFrame(matrix)

def signal_liste(df):
    print()
    print("KONKRETE KERNSIGNALE: U>=70 & EINSTIEG>=70")
    print("-" * 150)

    sig = df[
        (df["Unternehmensscore"] >= 70)
        & (df["Einstiegsscore"] >= 70)
    ].copy()

    if sig.empty:
        print("Keine Kernsignale gefunden.")
        return

    sig["Stichtag_dt"] = pd.to_datetime(sig["Stichtag"], errors="coerce")
    sig = sig.sort_values(["Stichtag_dt", "Symbol"])

    kopf = (
        f"{'Datum':<12} {'Aktie':<6} {'Modell':<16} {'U':>3} {'Einst':>6} "
        f"{'Trap':>5} {'DD':>7} {'3M':>8} {'6M':>8} {'12M':>8} {'12M Alpha':>11}"
    )
    print(kopf)
    print("-" * 150)

    def p(v):
        if v is None or pd.isna(v):
            return "      --"
        return f"{float(v):+7.1f}%"

    for _, r in sig.iterrows():
        dd = r.get("Drawdown")
        dd_txt = "   --" if pd.isna(dd) else f"{float(dd):+6.1f}%"
        print(
            f"{str(r['Stichtag']):<12} {str(r['Symbol']):<6} {str(r['Modell']):<16} "
            f"{int(r['Unternehmensscore']):>3} {int(r['Einstiegsscore']):>6} "
            f"{int(r['Value_Trap']):>5} {dd_txt:>7} "
            f"{p(r.get('Rendite_3M')):>8} {p(r.get('Rendite_6M')):>8} "
            f"{p(r.get('Rendite_12M')):>8} {p(r.get('Alpha_12M')):>11}"
        )


def extremfaelle(df):
    print()
    print("EXTREMFÄLLE 12M: WAS TREIBT DIE DURCHSCHNITTE?")
    print("-" * 120)

    x = df.copy()
    x["Rendite_12M_num"] = pd.to_numeric(x["Rendite_12M"], errors="coerce")
    x["Alpha_12M_num"] = pd.to_numeric(x["Alpha_12M"], errors="coerce")
    x = x.dropna(subset=["Rendite_12M_num"])

    if x.empty:
        print("Noch keine vollständigen 12M-Fälle.")
        return

    for titel, teil in [
        ("Beste 8 Renditen", x.nlargest(8, "Rendite_12M_num")),
        ("Schlechteste 8 Renditen", x.nsmallest(8, "Rendite_12M_num")),
    ]:
        print(titel)
        for _, r in teil.iterrows():
            print(
                f"  {r['Stichtag']} {r['Symbol']:<6} | U {int(r['Unternehmensscore']):>3} | "
                f"E {int(r['Einstiegsscore']):>3} | Trap {int(r['Value_Trap']):>3} | "
                f"12M {r['Rendite_12M_num']:+6.1f}% | Alpha {r['Alpha_12M_num']:+6.1f}"
            )
        print()



def episoden_detail(df, u_grenze, e_grenze, titel):
    print()
    print(titel)
    print("-" * 135)
    teil = df[
        (df["Unternehmensscore"] >= u_grenze)
        & (df["Einstiegsscore"] >= e_grenze)
    ].copy()
    gueltig = gueltige_horizon_daten(teil, 12)
    episoden = signal_episoden(gueltig)

    print(
        f"Filter U>={u_grenze} & Einstieg>={e_grenze}: "
        f"{len(teil)} Signale | {len(gueltig)} vollständige 12M-Fälle | "
        f"{gueltig['Symbol'].nunique() if not gueltig.empty else 0} verschiedene Aktien | "
        f"{len(episoden)} Signal-Episoden"
    )

    if episoden.empty:
        print("Keine vollständigen Episoden verfügbar.")
        return

    print(
        f"{'Start':<12} {'Aktie':<6} {'Modell':<16} {'U':>3} {'E':>3} "
        f"{'Trap':>5} {'DD':>7} {'12M':>8} {'SPY A':>8} {'Sekt A':>8} {'Bench':>6}"
    )
    for _, r in episoden.sort_values(["Stichtag", "Symbol"]).iterrows():
        dd = r.get("Drawdown")
        dd_txt = "--" if pd.isna(dd) else f"{float(dd):+.1f}%"
        print(
            f"{r['Stichtag']:<12} {r['Symbol']:<6} {r['Modell']:<16} "
            f"{int(r['Unternehmensscore']):>3} {int(r['Einstiegsscore']):>3} "
            f"{int(r['Value_Trap']):>5} {dd_txt:>7} "
            f"{float(r['Rendite_12M']):+7.1f}% {float(r['Alpha_12M']):+7.1f} "
            f"{float(r['Sektor_Alpha_12M']):+7.1f} {str(r['Sektor_Benchmark']):>6}"
        )


def robustheitstabelle(df):
    print()
    print("ROBUSTHEIT 12M: EXTREMWERTE, AKTIENGEWICHTUNG UND EPISODEN")
    print("-" * 166)
    print(
        f"{'Gruppe':<29} {'n':>5} {'Aktien':>7} {'Epis.':>6} {'Ø':>8} {'Median':>8} "
        f"{'ohne Top1':>11} {'ohne Top3':>11} {'Trim10':>8} "
        f"{'Aktien-Ø':>10} {'Aktien-Med':>11} {'Aktien Alpha':>12} {'Sektor Alpha':>13}"
    )
    print("-" * 166)

    gruppen = [
        ("Alle Beobachtungen", df),
        ("U>=70 & E>=65", df[(df["Unternehmensscore"] >= 70) & (df["Einstiegsscore"] >= 65)]),
        ("U>=70 & E>=70", df[(df["Unternehmensscore"] >= 70) & (df["Einstiegsscore"] >= 70)]),
        ("Einstieg 0-39", df[df["Einstiegsscore"] <= 39]),
        ("Value-Trap >=60", df[df["Value_Trap"] >= 60]),
        ("Value-Trap <20", df[df["Value_Trap"] < 20]),
    ]

    for name, teil in gruppen:
        k = robustheits_kennzahlen(teil, 12)
        if k is None:
            print(f"{name:<29} keine vollständigen 12M-Fälle")
            continue

        def f(v):
            return "    --" if pd.isna(v) else f"{v:+7.1f}%"

        print(
            f"{name:<29} {k['n']:>5} {k['aktien']:>7} {k['episoden']:>6} "
            f"{f(k['avg']):>8} {f(k['median']):>8} {f(k['ohne_best1']):>11} "
            f"{f(k['ohne_best3']):>11} {f(k['trim10']):>8} "
            f"{f(k['aktiengew_avg']):>10} {f(k['aktiengew_median']):>11} "
            f"{f(k['aktiengew_alpha']):>12} {f(k['aktiengew_sektor_alpha']):>13}"
        )

    print()
    print("Aktien-Ø: zuerst Mittelwert je Aktie, danach alle Aktien gleich gewichtet.")
    print("Trim10: 10 % der höchsten und niedrigsten 12M-Renditen abgeschnitten.")
    print("Episoden: Folgequartale derselben Aktie innerhalb von 130 Tagen als eine Episode gezählt.")


def episode_vs_rohsignale(df):
    print()
    print("KERNSIGNALE: ROHSIGNALE VS. SIGNAL-EPISODEN")
    print("-" * 125)
    for u, e in [(70, 65), (70, 70)]:
        teil = df[(df["Unternehmensscore"] >= u) & (df["Einstiegsscore"] >= e)]
        raw = horizon_statistik(teil, 12)
        epis = signal_episoden(gueltige_horizon_daten(teil, 12))
        epi_stat = horizon_statistik(epis, 12)

        print(f"U>={u} & Einstieg>={e}")
        if raw is None:
            print("  Rohsignale: keine vollständigen 12M-Fälle")
        else:
            print(
                f"  Rohsignale: n={raw['n']} | Ø {raw['rendite_avg']:+.1f}% | "
                f"Med {raw['rendite_median']:+.1f}% | Alpha Med {raw['alpha_median']:+.1f} | "
                f"SPY {raw['spy_geschlagen']:.1f}%"
            )
        if epi_stat is None:
            print("  Episoden:   keine vollständigen 12M-Fälle")
        else:
            print(
                f"  Episoden:   n={epi_stat['n']} | Ø {epi_stat['rendite_avg']:+.1f}% | "
                f"Med {epi_stat['rendite_median']:+.1f}% | Alpha Med {epi_stat['alpha_median']:+.1f} | "
                f"SPY {epi_stat['spy_geschlagen']:.1f}%"
            )



def modell_score_wirkung(df):
    """
    Prüft Unternehmens- und Einstiegsscore innerhalb jedes Modells separat.
    Dadurch wird vermieden, dass Unterschiede zwischen Branchen/Modellen
    fälschlich als Score-Wirkung interpretiert werden.
    """
    print()
    print("SCORE-WIRKUNG INNERHALB JEDES MODELLS (12M)")
    print("-" * 154)
    print(
        f"{'Modell / Scoreband':<36} {'Signale':>7} {'12M n':>6} {'Aktien':>7} {'Epis.':>6} "
        f"{'12M Med':>9} {'SPY A Med':>10} {'Sekt A Med':>11} {'Sekt%':>7} {'Positiv%':>9} {'<=-20%':>8}"
    )
    print("-" * 154)

    score_tests = [
        (
            "Unternehmensscore",
            [
                (None, 54, "U 0-54"),
                (55, 69, "U 55-69"),
                (70, None, "U 70-100"),
            ],
        ),
        (
            "Einstiegsscore",
            [
                (None, 54, "E 0-54"),
                (55, 64, "E 55-64"),
                (65, None, "E 65-100"),
            ],
        ),
    ]

    for modell in sorted(df["Modell"].dropna().unique()):
        modell_df = df[df["Modell"] == modell]
        benchmark = SEKTOR_BENCHMARKS.get(modell, MARKT_BENCHMARK)
        print(f"\n{modell} | Vergleichsbenchmark: {benchmark}")

        for spalte, baender in score_tests:
            for lo, hi, label in baender:
                teil = score_band(modell_df, spalte, lo, hi)
                st = horizon_statistik(teil, 12)
                gueltig = gueltige_horizon_daten(teil, 12)
                epis = signal_episoden(gueltig)

                if st is None:
                    print(f"  {label:<20} {len(teil):>7} {0:>6} {0:>7} {0:>6} | keine vollständigen 12M-Daten")
                    continue

                print(
                    f"  {label:<20} {len(teil):>7} {st['n']:>6} "
                    f"{int(gueltig['Symbol'].nunique()):>7} {len(epis):>6} "
                    f"{st['rendite_median']:+8.1f}% {st['alpha_median']:+9.1f} "
                    f"{st['sektor_alpha_median']:+10.1f} {st['sektor_geschlagen']:>6.1f}% "
                    f"{st['positiv']:>8.1f}% {st['verlust_20']:>7.1f}%"
                )

        print("  Hinweis: Entscheidend ist, ob höhere Scorebänder innerhalb desselben Modells konsistent besser werden.")


def leave_one_stock_out_70_65(df):
    """
    Robustheitstest für den derzeit interessantesten Filter U>=70 & Einstieg>=65.
    Verwendet 12M-Signal-Episoden und entfernt nacheinander jede Aktie vollständig.
    """
    print()
    print("LEAVE-ONE-STOCK-OUT: U>=70 & EINSTIEG>=65 (12M-EPISODEN)")
    print("-" * 142)

    teil = df[
        (df["Unternehmensscore"] >= 70)
        & (df["Einstiegsscore"] >= 65)
    ].copy()
    gueltig = gueltige_horizon_daten(teil, 12)
    epis = signal_episoden(gueltig)

    if epis.empty:
        print("Keine vollständigen 12M-Episoden verfügbar.")
        return

    print(
        f"Ausgangslage: {len(epis)} Episoden | {epis['Symbol'].nunique()} Aktien. "
        "Danach wird jeweils eine Aktie mit allen ihren Episoden entfernt."
    )
    print()
    print(
        f"{'Variante':<30} {'Epis.':>6} {'Aktien':>7} {'12M Ø':>9} {'12M Med':>9} "
        f"{'SPY A Med':>10} {'Sekt A Med':>11} {'SPY%':>7} {'Sekt%':>7} {'<=-20%':>8}"
    )
    print("-" * 142)

    def zeile(name, x):
        st = horizon_statistik(x, 12)
        if st is None:
            print(f"{name:<30} keine Daten")
            return
        print(
            f"{name:<30} {st['n']:>6} {int(x['Symbol'].nunique()):>7} "
            f"{st['rendite_avg']:+8.1f}% {st['rendite_median']:+8.1f}% "
            f"{st['alpha_median']:+9.1f} {st['sektor_alpha_median']:+10.1f} "
            f"{st['spy_geschlagen']:>6.1f}% {st['sektor_geschlagen']:>6.1f}% "
            f"{st['verlust_20']:>7.1f}%"
        )

    zeile("ALLE EPISODEN", epis)

    for symbol in sorted(epis["Symbol"].dropna().unique()):
        rest = epis[epis["Symbol"] != symbol]
        zeile(f"ohne {symbol}", rest)

    print()
    print("Interpretation: Bleibt das Ergebnis nach Entfernen jeder einzelnen Aktie ähnlich, ist der Effekt robuster.")
    print("Bricht Median/Alpha bei einer Aktie stark ein, hängt das Ergebnis noch zu stark von diesem Einzelwert ab.")

def auswertung(df):
    print()
    print("=" * 110)
    print("TRADEPILOT BACKTEST 0.8.1 - AUSWERTUNG")
    print("=" * 110)
    print(f"Beobachtungen / Signale insgesamt: {len(df)}")
    print(f"Aktien: {df['Symbol'].nunique()}")
    print(f"Zeitraum: {df['Stichtag'].min()} bis {df['Stichtag'].max()}")

    print()
    print("VERFÜGBARE VORWÄRTSERGEBNISSE")
    print("-" * 110)
    for m in (3, 6, 12):
        st = horizon_statistik(df, m)
        if st:
            print(
                f"{m:>2} Monate: {st['n']:>4}/{len(df)} Signale vollständig auswertbar "
                f"({st['n'] / len(df) * 100:.1f} %)"
            )

    print()
    print("EINSTIEGSSTATUS")
    print("-" * 110)
    for status in [
        "INTERESSANTER EINSTIEG",
        "BEOBACHTEN",
        "KEIN BESONDERER EINSTIEG",
        "RISIKOREICHER RÜCKSETZER",
        "KEIN EINSTIEG",
    ]:
        teil = df[df["Status"] == status]
        if not teil.empty:
            gruppe_zeigen(status, teil)

    print()
    print("EINSTIEGSSCORE-BÄNDER")
    print("-" * 110)
    for lo, hi, label in [
        (None, 39, "0-39"),
        (40, 54, "40-54"),
        (55, 69, "55-69"),
        (70, None, "70-100"),
    ]:
        teil = score_band(df, "Einstiegsscore", lo, hi)
        if not teil.empty:
            gruppe_zeigen(label, teil)

    print()
    print("UNTERNEHMENSSCORE-BÄNDER")
    print("-" * 110)
    for lo, hi, label in [
        (None, 39, "0-39"),
        (40, 54, "40-54"),
        (55, 69, "55-69"),
        (70, None, "70-100"),
    ]:
        teil = score_band(df, "Unternehmensscore", lo, hi)
        if not teil.empty:
            gruppe_zeigen(label, teil)

    print()
    print("MODELLVERGLEICH")
    print("-" * 110)
    for modell in sorted(df["Modell"].dropna().unique()):
        gruppe_zeigen(modell, df[df["Modell"] == modell])

    print()
    print("MODELLVERGLEICH: SPY VS. SEKTOR-BENCHMARK")
    print("-" * 125)
    for modell in sorted(df["Modell"].dropna().unique()):
        teil = df[df["Modell"] == modell]
        benchmark = SEKTOR_BENCHMARKS.get(modell, MARKT_BENCHMARK)
        print(f"{modell} | Sektor-Benchmark: {benchmark}")
        for m in (3, 6, 12):
            st = horizon_statistik(teil, m)
            if st is None:
                print(f"   {m:>2}M: keine vollständigen Daten")
                continue
            print(
                f"   {m:>2}M n={st['n']:>3} | SPY Alpha Med {st['alpha_median']:+6.1f} | "
                f"SPY geschl. {st['spy_geschlagen']:5.1f}% | "
                f"{benchmark} Alpha Med {st['sektor_alpha_median']:+6.1f} | "
                f"{benchmark} geschl. {st['sektor_geschlagen']:5.1f}%"
            )

    print()
    print("KERNTEST: GUTES UNTERNEHMEN + GUTER EINSTIEG")
    print("-" * 110)
    gut = df[
        (df["Unternehmensscore"] >= 70)
        & (df["Einstiegsscore"] >= 70)
    ]
    gruppe_zeigen("U>=70 & Einstieg>=70", gut)
    vergleich = df.drop(index=gut.index)
    gruppe_zeigen("alle anderen", vergleich)

    print()
    print("RISIKOTEST")
    print("-" * 110)
    gruppe_zeigen("Value-Trap >= 60", df[df["Value_Trap"] >= 60])
    gruppe_zeigen("Value-Trap < 20", df[df["Value_Trap"] < 20])

    matrix_df = schwellen_matrix(df)
    signal_liste(df)
    extremfaelle(df)
    robustheitstabelle(df)
    episode_vs_rohsignale(df)
    episoden_detail(df, 70, 65, "SIGNAL-EPISODEN IM DETAIL: U>=70 & EINSTIEG>=65")
    episoden_detail(df, 70, 70, "SIGNAL-EPISODEN IM DETAIL: U>=70 & EINSTIEG>=70")
    modell_score_wirkung(df)
    leave_one_stock_out_70_65(df)

    print()
    print("WICHTIGE METHODENGRENZEN")
    print("-" * 110)
    print("! Historische Jahresdaten werden mit 120 Tagen Sicherheitsabstand freigegeben.")
    print("! Yahoo liefert kein revisionssicheres Point-in-Time-Archiv; spätere Restatements sind möglich.")
    print("! Historisches Forward-KGV und PEG fehlen und werden NICHT erfunden.")
    print("! Quartalsweise Signale derselben Aktie sind keine vollständig unabhängigen Beobachtungen.")
    print("! 0.8.1 zeigt zusätzlich Signal-Episoden mit maximal 130 Tagen Folgeabstand.")
    print("! Aktiengewichtete Statistiken verhindern, dass häufige Signale einer Aktie überproportional zählen.")
    print("! 6M- und 12M-Ergebnisse überlappen bei aufeinanderfolgenden Quartalssignalen teilweise.")
    print("! Das Aktienuniversum enthält überwiegend heute existierende Firmen -> Survivorship Bias bleibt.")
    print("! Kleine Teilgruppen (insbesondere hohe Einstiegsscores) nicht überinterpretieren.")
    print("! Sektor-Benchmarks: BANK/CAPITAL_MARKETS=XLF, ENERGY=XLE, STANDARD=SPY.")
    print("! 0.8.4 LARGE nutzt dieselbe Score-/Modellauswertung wie 0.8.1 und den TURBO-Datenpfad; geändert wurde nur das skalierbare Aktienuniversum.")
    print("! Leave-one-stock-out nutzt 12M-Signal-Episoden und entfernt jeweils eine Aktie vollständig.")
    print("! Dieser Test ist Forschungsstufe 0.8.4 LARGE, noch keine wissenschaftliche Validierung.")

    return matrix_df




def _audit_episode_count(df):
    if df.empty:
        return 0
    try:
        return len(signal_episoden(df))
    except Exception:
        return 0

def _audit_row(df, variant, u_col, e_col, u_min, e_min, modell="ALLE"):
    basis = df.copy()
    if modell != "ALLE":
        basis = basis[basis["Modell"] == modell]
    sel = basis[(pd.to_numeric(basis[u_col], errors="coerce") >= u_min) &
                (pd.to_numeric(basis[e_col], errors="coerce") >= e_min)].copy()
    voll = sel[pd.to_numeric(sel["Rendite_12M"], errors="coerce").notna()].copy()
    r = pd.to_numeric(voll["Rendite_12M"], errors="coerce")
    a = pd.to_numeric(voll["Alpha_12M"], errors="coerce")
    sa = pd.to_numeric(voll["Sektor_Alpha_12M"], errors="coerce")
    return {
        "Variante": variant, "Modell": modell, "U_min": u_min, "E_min": e_min,
        "Signale": len(sel), "12M_n": len(voll),
        "Aktien": int(voll["Symbol"].nunique()) if not voll.empty else 0,
        "Episoden": _audit_episode_count(voll),
        "12M_Median": float(r.median()) if not r.empty else float("nan"),
        "12M_Mittel": float(r.mean()) if not r.empty else float("nan"),
        "Alpha_Median": float(a.median()) if not a.empty else float("nan"),
        "SektorAlpha_Median": float(sa.median()) if not sa.empty else float("nan"),
        "Positiv_pct": float((r > 0).mean() * 100) if not r.empty else float("nan"),
        "Minus20_pct": float((r <= -20).mean() * 100) if not r.empty else float("nan"),
    }

def score_audit_auswertung(df):
    print()
    print("=" * 118)
    print("SCORE AUDIT 0.8.5: 0.6.1 VS. 0.6.2-KANDIDATEN")
    print("=" * 118)
    print("Komponenten und Safety-Gate sind identisch; verglichen werden nur Aggregationsgewichte.")
    print()

    # 0.8.5.1 FIX: defensive Rekonstruktion. Damit kann auch eine CSV/
    # Beobachtung aus einem älteren 0.8.5-Lauf ausgewertet werden, selbst
    # wenn die Audit-Spalten damals im TURBO-Pfad nicht mitgeschrieben wurden.
    benoetigt = ["Qualitaet", "Entwicklung", "Bewertung", "Value_Trap", "Drawdown_Score", "Trend"]
    fehlende_basis = [c for c in benoetigt if c not in df.columns]
    if fehlende_basis:
        raise ValueError(f"Score-Audit: Basis-Komponenten fehlen: {', '.join(fehlende_basis)}")

    for varianten_name, kurz in (("BASELINE_061", "B061"),
                                 ("CANDIDATE_062_BALANCED", "C062B"),
                                 ("CANDIDATE_062_QUALITY", "C062Q")):
        u_col = f"{kurz}_Unternehmensscore"
        e_col = f"{kurz}_Einstiegsscore"
        if u_col not in df.columns or e_col not in df.columns:
            werte = df.apply(
                lambda r: score_variante_berechnen(
                    varianten_name,
                    float(r["Qualitaet"]), float(r["Entwicklung"]), float(r["Bewertung"]),
                    float(r["Value_Trap"]), float(r["Drawdown_Score"]), float(r["Trend"]),
                ),
                axis=1,
            )
            df[u_col] = [x[0] for x in werte]
            df[f"{kurz}_Einstieg_Roh"] = [x[1] for x in werte]
            df[e_col] = [x[2] for x in werte]
            df[f"{kurz}_Status"] = [x[3] for x in werte]
            df[f"{kurz}_Gate"] = [x[4] for x in werte]

    mapping = {
        "BASELINE_061": ("B061_Unternehmensscore", "B061_Einstiegsscore"),
        "CANDIDATE_062_BALANCED": ("C062B_Unternehmensscore", "C062B_Einstiegsscore"),
        "CANDIDATE_062_QUALITY": ("C062Q_Unternehmensscore", "C062Q_Einstiegsscore"),
    }
    rows=[]
    thresholds=[(60,60),(65,60),(65,65),(70,60),(70,65),(70,70),(75,65),(75,70)]
    modelle=["ALLE"] + sorted(df["Modell"].dropna().unique().tolist())
    for v,(uc,ec) in mapping.items():
        for modell in modelle:
            for umin,emin in thresholds:
                rows.append(_audit_row(df,v,uc,ec,umin,emin,modell))
    out=pd.DataFrame(rows)

    # Vergleichsübersicht: bewusst keine automatische "Sieger"-Kür ohne Mindeststichprobe.
    print("KERNVERGLEICH U>=70 & E>=65 (12M)")
    print("-" * 118)
    kern=out[(out["Modell"]=="ALLE") & (out["U_min"]==70) & (out["E_min"]==65)]
    for _,r in kern.iterrows():
        print(f"{r['Variante']:<28} n={int(r['12M_n']):4} | Aktien={int(r['Aktien']):3} | Epis={int(r['Episoden']):3} | "
              f"12M Med {r['12M_Median']:+6.1f}% | Alpha Med {r['Alpha_Median']:+6.1f} | "
              f"Sektor A Med {r['SektorAlpha_Median']:+6.1f} | Positiv {r['Positiv_pct']:5.1f}% | <=-20 {r['Minus20_pct']:4.1f}%")

    print()
    print("ENTSCHEIDUNGSREGEL FÜR MONTAG")
    print("-" * 118)
    print("Ein 0.6.2-Kandidat wird NICHT wegen des höchsten Durchschnitts gewählt.")
    print("Bevorzugt wird nur ein Kandidat, wenn er bei ausreichendem n/Aktien/Episoden")
    print("Median + Benchmark-Alpha verbessert, ohne die Verlustquote deutlich zu verschlechtern,")
    print("und der Effekt in mehreren Modellen statt nur in einer Einzelgruppe sichtbar bleibt.")
    return out

def argumente_lesen():
    parser = argparse.ArgumentParser(
        description="TradePilot Backtest 0.8.4 LARGE - TURBO-Datenpfad mit skalierbarem Aktienuniversum"
    )
    parser.add_argument(
        "--universe",
        choices=sorted(UNIVERSES.keys()),
        default="sp500-250",
        help="Aktienuniversum: core85, sp500-250, sp500-350 oder sp500-full (Standard: sp500-250)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallele Worker für Fundamentals/Tests (Standard: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Titel pro Yahoo-Kursbatch (Standard: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Vorhandenen Cache ignorieren und Daten neu laden.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Cache vor dem Lauf vollständig löschen.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Cache weder lesen noch schreiben.",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=str(DEFAULT_CACHE_DIR),
        help="Pfad zum Backtest-Cache.",
    )
    return parser.parse_args()


def main():
    global CACHE_DIR, CACHE_AKTIV, CACHE_FORCE_REFRESH

    args = argumente_lesen()
    CACHE_DIR = Path(args.cache_dir).expanduser().resolve()
    CACHE_AKTIV = not args.no_cache
    CACHE_FORCE_REFRESH = bool(args.refresh_cache)
    workers = max(1, int(args.workers))
    batch_size = max(1, int(args.batch_size))

    if args.clear_cache and CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"Cache gelöscht: {CACHE_DIR}")

    gesamt_start = time.perf_counter()

    print()
    print("=" * 100)
    print("TRADEPILOT BACKTEST 0.8.13 TRUE HOLDOUT RAW")
    print("=" * 100)
    print("Historischer Forschungs-Backtest der unveränderten 0.6.1-Scorelogik")
    print("Basis-Auswertung: 0.8.1 | LARGE: TURBO-Engine + auswählbares Aktienuniversum")
    print(f"Fundamentaldaten-Lag: {FUNDAMENT_LAG_TAGE} Tage")
    print(f"Markt-Benchmark: {MARKT_BENCHMARK}")
    print("Sektor-Benchmarks: STANDARD=SPY | BANK=XLF | CAPITAL_MARKETS=XLF | ENERGY=XLE")
    selected_universe = UNIVERSES[args.universe]
    print(f"Universum: {args.universe} | {universe_count(selected_universe)} Listings")
    print(f"Modellmix: " + " | ".join(f"{k}={len(v)}" for k, v in selected_universe.items()))
    print(f"Worker: {workers} | Kurs-Batchgröße: {batch_size}")
    print(f"Cache: {'AN' if CACHE_AKTIV else 'AUS'} | Pfad: {CACHE_DIR}")
    if CACHE_FORCE_REFRESH:
        print("Cache-Modus: REFRESH (vorhandene Einträge werden ignoriert)")
    print()

    jobs = []
    for modell, symbole in selected_universe.items():
        for symbol in symbole:
            jobs.append((len(jobs), symbol, modell))

    aktien_symbole = [symbol for _, symbol, _ in jobs]
    benchmark_ticker = sorted(set([MARKT_BENCHMARK] + list(SEKTOR_BENCHMARKS.values())))
    alle_kurs_symbole = list(dict.fromkeys(aktien_symbole + benchmark_ticker))

    # 1) KURSE: Cache + gebündelter Download
    t0 = time.perf_counter()
    print("[1/3] KURSHISTORIEN: Cache + Batch-Download")
    kurshistorien = lade_kurshistorien_gebuendelt(alle_kurs_symbole, batch_size=batch_size)
    print(f"Kursphase fertig in {time.perf_counter() - t0:.1f}s | {len(kurshistorien)}/{len(alle_kurs_symbole)} verfügbar")
    print()

    benchmark_historien = {}
    for ticker in benchmark_ticker:
        hist_b = kurshistorien.get(ticker)
        if hist_b is None or hist_b.empty:
            raise RuntimeError(f"Benchmark {ticker} konnte nicht geladen werden.")
        benchmark_historien[ticker] = hist_b

    # 2) FUNDAMENTALS: Cache + parallele Einzelabrufe (Yahoo bietet hierfür keinen sauberen Multi-Ticker-Batch)
    t1 = time.perf_counter()
    print("[2/3] FUNDAMENTALDATEN: Cache + parallele Abrufe")
    fundamentals, fund_fehler = lade_fundamentaldaten_parallel(aktien_symbole, workers=workers)
    print(f"Fundamentalphase fertig in {time.perf_counter() - t1:.1f}s | {len(fundamentals)}/{len(aktien_symbole)} verfügbar")
    print()

    # 3) BACKTEST: alle Titel ohne Netzwerkzugriff parallel berechnen
    t2 = time.perf_counter()
    print("[3/3] BACKTEST: parallele Symbolverarbeitung")
    results_by_index = {}
    fehler = []

    ausführbare_jobs = []
    for job_index, symbol, modell in jobs:
        hist = kurshistorien.get(symbol)
        fund = fundamentals.get(symbol)
        if hist is None or hist.empty:
            fehler.append((symbol, "Kurshistorie fehlt"))
            print(f"[{job_index + 1:03}/{len(jobs)}] {symbol:<6} {modell:<15} FEHLER | Kurshistorie fehlt")
            continue
        if fund is None:
            grund = fund_fehler.get(symbol, "Fundamentaldaten fehlen")
            fehler.append((symbol, grund))
            print(f"[{job_index + 1:03}/{len(jobs)}] {symbol:<6} {modell:<15} FEHLER | {grund}")
            continue
        ausführbare_jobs.append((job_index, symbol, modell, hist, fund))

    max_workers = max(1, min(workers, len(ausführbare_jobs) or 1))
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tp-test") as pool:
        futures = {
            pool.submit(
                verarbeite_symbol_parallel,
                job_index,
                symbol,
                modell,
                hist,
                fund,
                benchmark_historien,
            ): (job_index, symbol, modell)
            for job_index, symbol, modell, hist, fund in ausführbare_jobs
        }

        fertig = 0
        for future in as_completed(futures):
            job_index, symbol, modell = futures[future]
            fertig += 1
            try:
                res = future.result()
                results_by_index[job_index] = res
                count = len(res["beobachtungen"])
                msg = f"[{fertig:03}/{len(ausführbare_jobs)}] {symbol:<6} {modell:<15} OK | {count} Stichtage | {res['sekunden']:.2f}s"
                if count == 0 and res["diagnose"]:
                    häufig = ", ".join(
                        f"{grund}: {anzahl}" for grund, anzahl in res["diagnose"].most_common(3)
                    )
                    msg += f" | Diagnose: {häufig}"
                print(msg)
            except Exception as e:
                fehler.append((symbol, str(e)))
                print(f"[{fertig:03}/{len(ausführbare_jobs)}] {symbol:<6} {modell:<15} FEHLER | {e}")

    # Ursprüngliche Reihenfolge beibehalten, obwohl parallel gerechnet wurde.
    alle = []
    for job_index, _, _ in jobs:
        res = results_by_index.get(job_index)
        if res:
            alle.extend(res["beobachtungen"])

    print(f"Backtestphase fertig in {time.perf_counter() - t2:.1f}s")
    print()

    if not alle:
        raise RuntimeError("Keine historischen Beobachtungen erzeugt.")

    df = pd.DataFrame(alle)
    stempel = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    datei = f"TradePilot_Backtest_0.8.13_TRUE_HOLDOUT_RAW_{stempel}.csv"
    df.to_csv(datei, index=False, encoding="utf-8-sig")

    matrix_df = auswertung(df)

    matrix_datei = f"TradePilot_Schwellenmatrix_0.8.13_TRUE_HOLDOUT_RAW_{stempel}.csv"
    matrix_df.to_csv(matrix_datei, index=False, encoding="utf-8-sig")

    audit_df = score_audit_auswertung(df)
    audit_datei = f"TradePilot_ScoreAudit_0.8.13_{stempel}.csv"
    audit_df.to_csv(audit_datei, index=False, encoding="utf-8-sig")

    dauer = time.perf_counter() - gesamt_start
    print()
    print("=" * 100)
    print(f"Beobachtungs-CSV gespeichert: {datei}")
    print(f"Schwellenmatrix gespeichert: {matrix_datei}")
    print(f"Score-Audit gespeichert: {audit_datei}")
    print(f"Gesamtlaufzeit: {dauer:.1f}s ({dauer / 60:.1f} min)")
    if CACHE_AKTIV:
        print(f"Cache bleibt erhalten: {CACHE_DIR}")
        print("Nächster Lauf mit denselben Daten sollte deutlich weniger Netzwerkabrufe benötigen.")
    if fehler:
        print(f"Fehlerhafte Aktien: {len(fehler)}")
        for symbol, fehlertext in fehler:
            print(f"! {symbol}: {fehlertext}")
    else:
        print("Alle Aktien ohne Lade-/Verarbeitungsfehler verarbeitet.")
    print("=" * 100)
    print("Backtest 0.8.13 TRUE HOLDOUT RAW beendet.")


if __name__ == "__main__":
    main()
