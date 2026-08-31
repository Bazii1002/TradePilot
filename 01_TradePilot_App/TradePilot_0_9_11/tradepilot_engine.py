import yfinance as yf
import math
import statistics


# ============================================================
# TRADEPILOT 0.7.2
#
# Modelle:
# - STANDARD
# - BANK
# - CAPITAL_MARKETS
# - ENERGY
# ============================================================


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


def prozent(wert):
    if wert is None:
        return "keine Daten"

    return f"{wert * 100:.1f} %"


def zahl_prozent(wert):
    if wert is None:
        return "keine Daten"

    return f"{wert:+.1f} %"


def geld(wert):
    if wert is None:
        return "keine Daten"

    if abs(wert) >= 1_000_000_000:
        return f"{wert / 1_000_000_000:.1f} Mrd."

    if abs(wert) >= 1_000_000:
        return f"{wert / 1_000_000:.1f} Mio."

    return f"{wert:,.0f}"


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

    return score_begrenzen(
        gesamt / gewicht_summe
    )


# ============================================================
# MODELLERKENNUNG
# ============================================================

def modell_erkennen(info):

    sektor = str(
        wert(info, "sector", "")
    ).lower()

    branche = str(
        wert(info, "industry", "")
    ).lower()

    # Klassische Banken
    bank_begriffe = [
        "banks - diversified",
        "banks - regional",
        "regional banks",
        "diversified banks",
        "banking services"
    ]

    if any(
        begriff in branche
        for begriff in bank_begriffe
    ):
        return "BANK"

    # Investmentbanken / Broker / Capital Markets
    capital_markets_begriffe = [
        "capital markets",
        "investment banking",
        "brokerage",
        "financial data",
        "financial exchanges",
        "asset management"
    ]

    if (
        "financial services" in sektor
        and any(
            begriff in branche
            for begriff in capital_markets_begriffe
        )
    ):
        return "CAPITAL_MARKETS"

    # Energie
    if "energy" in sektor:
        return "ENERGY"

    return "STANDARD"


def modell_text(modell):

    if modell == "BANK":
        return "BANKMODELL"

    if modell == "CAPITAL_MARKETS":
        return "CAPITAL-MARKETS-MODELL"

    if modell == "ENERGY":
        return "ENERGIEMODELL (ZYKLISCH)"

    return "STANDARDMODELL"


# ============================================================
# FINANZTREND
# ============================================================

def finanztrend_score(daten, positiv_ist_gut=True):

    werte = finanzwerte_sortieren(daten)

    if len(werte) < 2:
        return {
            "score": 50,
            "veraenderung": None,
            "richtung": "keine Daten",
            "werte": werte,
            "verfuegbar": False
        }

    erster_wert = werte[0][1]
    letzter_wert = werte[-1][1]

    veraenderung = veraenderung_prozent(
        erster_wert,
        letzter_wert
    )

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

    score = score_begrenzen(score)

    if veraenderung is None:
        richtung = "keine Daten"

    elif positiv_ist_gut:

        if veraenderung >= 10:
            richtung = "deutlich steigend"

        elif veraenderung >= 3:
            richtung = "steigend"

        elif veraenderung > -3:
            richtung = "stabil"

        elif veraenderung > -10:
            richtung = "fallend"

        else:
            richtung = "deutlich fallend"

    else:

        if veraenderung <= -10:
            richtung = "deutlich verbessert"

        elif veraenderung <= -3:
            richtung = "verbessert"

        elif veraenderung < 3:
            richtung = "stabil"

        elif veraenderung < 10:
            richtung = "verschlechtert"

        else:
            richtung = "deutlich verschlechtert"

    return {
        "score": score,
        "veraenderung": veraenderung,
        "richtung": richtung,
        "werte": werte,
        "verfuegbar": True
    }


# ============================================================
# ZYKLISCHER ENERGY-TREND
# ============================================================

def zyklischer_finanztrend_score(daten):

    werte = finanzwerte_sortieren(daten)

    if len(werte) < 3:
        return finanztrend_score(daten, True)

    letzter_wert = werte[-1][1]

    alte_werte = [
        zahl
        for _, zahl in werte[:-1]
    ]

    median_alt = statistics.median(
        alte_werte
    )

    veraenderung = veraenderung_prozent(
        median_alt,
        letzter_wert
    )

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

    # Aktuelle Richtung zusätzlich berücksichtigen
    vorjahr = werte[-2][1]

    if letzter_wert > vorjahr:
        score += 8

    elif letzter_wert < vorjahr:
        score -= 5

    score = score_begrenzen(score)

    if veraenderung is None:
        richtung = "keine Daten"

    elif veraenderung >= 15:
        richtung = "über Mehrjahresniveau"

    elif veraenderung >= -15:
        richtung = "nahe Mehrjahresniveau"

    elif veraenderung >= -35:
        richtung = "unter Mehrjahresniveau"

    else:
        richtung = "deutlich unter Mehrjahresniveau"

    return {
        "score": score,
        "veraenderung": veraenderung,
        "richtung": richtung,
        "werte": werte,
        "verfuegbar": True
    }


# ============================================================
# MARGENTREND
# ============================================================

def margen_daten_berechnen(
    umsatz_daten,
    gewinn_daten
):

    umsatz = finanzwerte_sortieren(
        umsatz_daten
    )

    gewinn = finanzwerte_sortieren(
        gewinn_daten
    )

    if not umsatz or not gewinn:
        return []

    umsatz_dict = {
        datum: zahl
        for datum, zahl in umsatz
    }

    gewinn_dict = {
        datum: zahl
        for datum, zahl in gewinn
    }

    gemeinsame_daten = sorted(
        set(umsatz_dict.keys())
        &
        set(gewinn_dict.keys())
    )

    margen = []

    for datum in gemeinsame_daten:

        umsatzwert = umsatz_dict[datum]
        gewinnwert = gewinn_dict[datum]

        if umsatzwert == 0:
            continue

        marge = (
            gewinnwert
            / umsatzwert
        ) * 100

        margen.append(
            (datum, marge)
        )

    return margen


def margen_trend_score(
    umsatz_daten,
    gewinn_daten
):

    margen = margen_daten_berechnen(
        umsatz_daten,
        gewinn_daten
    )

    if len(margen) < 2:

        return {
            "score": 50,
            "veraenderung": None,
            "richtung": "keine Daten",
            "werte": margen,
            "erste_marge": None,
            "letzte_marge": None,
            "verfuegbar": False
        }

    erste_marge = margen[0][1]
    letzte_marge = margen[-1][1]

    veraenderung = (
        letzte_marge
        - erste_marge
    )

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

    score = score_begrenzen(score)

    if veraenderung >= 2:
        richtung = "deutlich verbessert"

    elif veraenderung >= 0.5:
        richtung = "verbessert"

    elif veraenderung > -0.5:
        richtung = "stabil"

    elif veraenderung > -2:
        richtung = "verschlechtert"

    else:
        richtung = "deutlich verschlechtert"

    return {
        "score": score,
        "veraenderung": veraenderung,
        "richtung": richtung,
        "werte": margen,
        "erste_marge": erste_marge,
        "letzte_marge": letzte_marge,
        "verfuegbar": True
    }


# ============================================================
# JAHRESDATEN
# ============================================================

def jahresdaten_ermitteln(
    income,
    cashflow,
    balance
):

    return {

        "umsatz": zeile_finden(
            income,
            [
                "TotalRevenue",
                "OperatingRevenue"
            ]
        ),

        "gewinn": zeile_finden(
            income,
            [
                "NetIncome",
                "NetIncomeCommonStockholders",
                "NetIncomeIncludingNoncontrollingInterests"
            ]
        ),

        "operativ": zeile_finden(
            income,
            [
                "OperatingIncome",
                "TotalOperatingIncomeAsReported"
            ]
        ),

        "fcf": zeile_finden(
            cashflow,
            [
                "FreeCashFlow"
            ]
        ),

        "schulden": zeile_finden(
            balance,
            [
                "TotalDebt"
            ]
        )
    }


# ============================================================
# ENTWICKLUNG
# ============================================================

def entwicklung_standard(
    income,
    cashflow,
    balance
):

    daten = jahresdaten_ermitteln(
        income,
        cashflow,
        balance
    )

    umsatz = finanztrend_score(
        daten["umsatz"],
        True
    )

    gewinn = finanztrend_score(
        daten["gewinn"],
        True
    )

    operativ = finanztrend_score(
        daten["operativ"],
        True
    )

    fcf = finanztrend_score(
        daten["fcf"],
        True
    )

    schulden = finanztrend_score(
        daten["schulden"],
        False
    )

    marge = margen_trend_score(
        daten["umsatz"],
        daten["gewinn"]
    )

    score = gewichteter_score([
        (
            umsatz["score"],
            0.20,
            umsatz["verfuegbar"]
        ),
        (
            gewinn["score"],
            0.20,
            gewinn["verfuegbar"]
        ),
        (
            operativ["score"],
            0.15,
            operativ["verfuegbar"]
        ),
        (
            fcf["score"],
            0.15,
            fcf["verfuegbar"]
        ),
        (
            marge["score"],
            0.20,
            marge["verfuegbar"]
        ),
        (
            schulden["score"],
            0.10,
            schulden["verfuegbar"]
        )
    ])

    return entwicklung_ergebnis(
        score,
        umsatz,
        gewinn,
        operativ,
        fcf,
        marge,
        schulden
    )


def entwicklung_finanz(
    income,
    cashflow,
    balance
):

    daten = jahresdaten_ermitteln(
        income,
        cashflow,
        balance
    )

    umsatz = finanztrend_score(
        daten["umsatz"],
        True
    )

    gewinn = finanztrend_score(
        daten["gewinn"],
        True
    )

    operativ = finanztrend_score(
        daten["operativ"],
        True
    )

    marge = margen_trend_score(
        daten["umsatz"],
        daten["gewinn"]
    )

    # FCF und normale Verschuldung werden
    # für Banken/Capital Markets nicht verwendet.
    fcf = {
        "score": None,
        "veraenderung": None,
        "richtung": "im Finanzmodell nicht verwendet",
        "werte": [],
        "verfuegbar": False
    }

    schulden = {
        "score": None,
        "veraenderung": None,
        "richtung": "im Finanzmodell nicht verwendet",
        "werte": [],
        "verfuegbar": False
    }

    score = gewichteter_score([
        (
            umsatz["score"],
            0.30,
            umsatz["verfuegbar"]
        ),
        (
            gewinn["score"],
            0.40,
            gewinn["verfuegbar"]
        ),
        (
            operativ["score"],
            0.10,
            operativ["verfuegbar"]
        ),
        (
            marge["score"],
            0.20,
            marge["verfuegbar"]
        )
    ])

    return entwicklung_ergebnis(
        score,
        umsatz,
        gewinn,
        operativ,
        fcf,
        marge,
        schulden
    )


def entwicklung_energy(
    income,
    cashflow,
    balance
):

    daten = jahresdaten_ermitteln(
        income,
        cashflow,
        balance
    )

    umsatz = zyklischer_finanztrend_score(
        daten["umsatz"]
    )

    gewinn = zyklischer_finanztrend_score(
        daten["gewinn"]
    )

    operativ = zyklischer_finanztrend_score(
        daten["operativ"]
    )

    fcf = zyklischer_finanztrend_score(
        daten["fcf"]
    )

    marge = margen_trend_score(
        daten["umsatz"],
        daten["gewinn"]
    )

    schulden = finanztrend_score(
        daten["schulden"],
        False
    )

    score = gewichteter_score([
        (
            umsatz["score"],
            0.15,
            umsatz["verfuegbar"]
        ),
        (
            gewinn["score"],
            0.20,
            gewinn["verfuegbar"]
        ),
        (
            operativ["score"],
            0.15,
            operativ["verfuegbar"]
        ),
        (
            fcf["score"],
            0.20,
            fcf["verfuegbar"]
        ),
        (
            marge["score"],
            0.15,
            marge["verfuegbar"]
        ),
        (
            schulden["score"],
            0.15,
            schulden["verfuegbar"]
        )
    ])

    return entwicklung_ergebnis(
        score,
        umsatz,
        gewinn,
        operativ,
        fcf,
        marge,
        schulden
    )


def entwicklung_ergebnis(
    score,
    umsatz,
    gewinn,
    operativ,
    fcf,
    marge,
    schulden
):

    gruende = []
    warnungen = []

    pruefungen = [
        (
            umsatz,
            "positive Umsatzentwicklung",
            "schwache Umsatzentwicklung"
        ),
        (
            gewinn,
            "positive Gewinnentwicklung",
            "schwache Gewinnentwicklung"
        ),
        (
            operativ,
            "operatives Ergebnis verbessert sich",
            "operatives Ergebnis unter Druck"
        ),
        (
            fcf,
            "positive Free-Cashflow-Entwicklung",
            "Free Cashflow entwickelt sich schwach"
        ),
        (
            marge,
            "Gewinnmarge verbessert sich",
            "Gewinnmarge verschlechtert sich"
        ),
        (
            schulden,
            "Verschuldung verbessert sich",
            "Verschuldung entwickelt sich ungünstig"
        )
    ]

    for trend, plus_text, warn_text in pruefungen:

        if not trend.get(
            "verfuegbar",
            False
        ):
            continue

        trend_score = trend.get(
            "score"
        )

        if trend_score is None:
            continue

        if trend_score >= 65:
            gruende.append(
                plus_text
            )

        elif trend_score <= 40:
            warnungen.append(
                warn_text
            )

    return {
        "score": score,
        "umsatz": umsatz,
        "gewinn": gewinn,
        "operativ": operativ,
        "fcf": fcf,
        "marge": marge,
        "schulden": schulden,
        "gruende": gruende,
        "warnungen": warnungen
    }


def unternehmensentwicklung(
    modell,
    income,
    cashflow,
    balance
):

    if modell in [
        "BANK",
        "CAPITAL_MARKETS"
    ]:
        return entwicklung_finanz(
            income,
            cashflow,
            balance
        )

    if modell == "ENERGY":
        return entwicklung_energy(
            income,
            cashflow,
            balance
        )

    return entwicklung_standard(
        income,
        cashflow,
        balance
    )


# ============================================================
# QUALITÄT STANDARD
# ============================================================

def qualitaet_standard(info):

    score = 50
    gruende = []
    warnungen = []

    growth = wert(
        info,
        "revenueGrowth"
    )

    marge = wert(
        info,
        "profitMargins"
    )

    fcf = wert(
        info,
        "freeCashflow"
    )

    roe = wert(
        info,
        "returnOnEquity"
    )

    debt = wert(
        info,
        "totalDebt"
    )

    cash = wert(
        info,
        "totalCash"
    )

    if growth is not None:

        if growth >= 0.15:
            score += 12
            gruende.append(
                "starkes Umsatzwachstum"
            )

        elif growth >= 0.05:
            score += 7
            gruende.append(
                "positives Umsatzwachstum"
            )

        elif growth >= 0:
            score += 2

        elif growth >= -0.10:
            score -= 6
            warnungen.append(
                "Umsatz aktuell rückläufig"
            )

        else:
            score -= 15
            warnungen.append(
                "starker aktueller Umsatzrückgang"
            )

    if marge is not None:

        if marge >= 0.20:
            score += 10
            gruende.append(
                "sehr hohe Gewinnmarge"
            )

        elif marge >= 0.10:
            score += 6
            gruende.append(
                "gute Gewinnmarge"
            )

        elif marge > 0:
            score += 2

        else:
            score -= 15
            warnungen.append(
                "Unternehmen schreibt Verluste"
            )

    if fcf is not None:

        if fcf > 0:
            score += 10
            gruende.append(
                "positiver Free Cashflow"
            )

        else:
            score -= 15
            warnungen.append(
                "negativer Free Cashflow"
            )

    if roe is not None:

        if roe >= 0.20:
            score += 8
            gruende.append(
                "hohe Eigenkapitalrendite"
            )

        elif roe >= 0.10:
            score += 4

        elif roe < 0:
            score -= 10
            warnungen.append(
                "negative Eigenkapitalrendite"
            )

    if (
        debt is not None
        and cash is not None
    ):

        if debt == 0:
            score += 7

        elif cash >= debt:
            score += 6
            gruende.append(
                "starke Liquiditätsposition"
            )

        elif cash >= debt * 0.5:
            score += 2

        elif (
            cash > 0
            and debt > cash * 4
        ):
            score -= 8
            warnungen.append(
                "hohe Verschuldung relativ zum Cash"
            )

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


# ============================================================
# QUALITÄT FINANZUNTERNEHMEN
# ============================================================

def qualitaet_finanz(info):

    score = 50
    gruende = []
    warnungen = []

    growth = wert(
        info,
        "revenueGrowth"
    )

    marge = wert(
        info,
        "profitMargins"
    )

    roe = wert(
        info,
        "returnOnEquity"
    )

    pb = wert(
        info,
        "priceToBook"
    )

    if growth is not None:

        if growth >= 0.20:
            score += 12
            gruende.append(
                "starkes Umsatzwachstum"
            )

        elif growth >= 0.10:
            score += 8
            gruende.append(
                "gutes Umsatzwachstum"
            )

        elif growth >= 0:
            score += 3

        elif growth < -0.10:
            score -= 10
            warnungen.append(
                "deutlicher Umsatzrückgang"
            )

    if marge is not None:

        if marge >= 0.30:
            score += 12
            gruende.append(
                "sehr hohe Gewinnmarge"
            )

        elif marge >= 0.20:
            score += 8
            gruende.append(
                "hohe Gewinnmarge"
            )

        elif marge >= 0.10:
            score += 4

        elif marge <= 0:
            score -= 18
            warnungen.append(
                "Finanzunternehmen schreibt Verluste"
            )

    if roe is not None:

        if roe >= 0.18:
            score += 15
            gruende.append(
                "sehr starke Eigenkapitalrendite"
            )

        elif roe >= 0.14:
            score += 12
            gruende.append(
                "starke Eigenkapitalrendite"
            )

        elif roe >= 0.10:
            score += 7

        elif roe >= 0.07:
            score += 2

        else:
            score -= 10
            warnungen.append(
                "schwache Eigenkapitalrendite"
            )

    if pb is not None and pb > 0:

        if pb < 1:
            score += 8
            gruende.append(
                "unter Buchwert bewertet"
            )

        elif pb < 1.5:
            score += 6

        elif pb < 2:
            score += 3

        elif pb > 4:
            score -= 8
            warnungen.append(
                "sehr hohe Bewertung zum Buchwert"
            )

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


# ============================================================
# QUALITÄT ENERGY 0.4.1
# ============================================================

def qualitaet_energy(info):

    score = 50
    gruende = []
    warnungen = []

    umsatz = wert(
        info,
        "totalRevenue"
    )

    growth = wert(
        info,
        "revenueGrowth"
    )

    marge = wert(
        info,
        "profitMargins"
    )

    fcf = wert(
        info,
        "freeCashflow"
    )

    roe = wert(
        info,
        "returnOnEquity"
    )

    debt = wert(
        info,
        "totalDebt"
    )

    cash = wert(
        info,
        "totalCash"
    )

    # Umsatzwachstum bewusst gering gewichtet,
    # weil Energie stark zyklisch ist.
    if growth is not None:

        if growth >= 0.20:
            score += 4

        elif growth >= 0.05:
            score += 2

        elif growth < -0.20:
            score -= 5

    # Gewinnmarge feiner abstufen
    if marge is not None:

        if marge >= 0.20:
            score += 15
            gruende.append(
                "sehr hohe Gewinnmarge"
            )

        elif marge >= 0.15:
            score += 12
            gruende.append(
                "starke Gewinnmarge"
            )

        elif marge >= 0.10:
            score += 8
            gruende.append(
                "solide Gewinnmarge"
            )

        elif marge >= 0.05:
            score += 4

        elif marge > 0:
            score += 1

        else:
            score -= 18
            warnungen.append(
                "Unternehmen schreibt Verluste"
            )

    # Free-Cashflow nicht nur positiv/negativ,
    # sondern relativ zum Umsatz.
    if (
        fcf is not None
        and umsatz is not None
        and umsatz > 0
    ):

        fcf_marge = fcf / umsatz

        if fcf_marge >= 0.15:
            score += 16
            gruende.append(
                "sehr starke Free-Cashflow-Marge"
            )

        elif fcf_marge >= 0.10:
            score += 13
            gruende.append(
                "starke Free-Cashflow-Marge"
            )

        elif fcf_marge >= 0.05:
            score += 9
            gruende.append(
                "solider Free Cashflow"
            )

        elif fcf_marge > 0:
            score += 4

        else:
            score -= 18
            warnungen.append(
                "negativer Free Cashflow"
            )

    elif fcf is not None:

        if fcf > 0:
            score += 6

        else:
            score -= 18

    # ROE feiner
    if roe is not None:

        if roe >= 0.20:
            score += 12
            gruende.append(
                "hohe Eigenkapitalrendite"
            )

        elif roe >= 0.15:
            score += 9

        elif roe >= 0.10:
            score += 6

        elif roe >= 0.05:
            score += 2

        elif roe < 0:
            score -= 10

    # Verschuldung / Cash feiner
    if (
        debt is not None
        and cash is not None
        and cash > 0
    ):

        debt_cash = debt / cash

        if debt_cash <= 1:
            score += 10
            gruende.append(
                "sehr starke Liquiditätsposition"
            )

        elif debt_cash <= 2:
            score += 7
            gruende.append(
                "solide Liquiditätsposition"
            )

        elif debt_cash <= 3:
            score += 3

        elif debt_cash <= 4:
            score += 0

        elif debt_cash <= 6:
            score -= 5
            warnungen.append(
                "erhöhte Verschuldung relativ zum Cash"
            )

        else:
            score -= 10
            warnungen.append(
                "hohe Verschuldung relativ zum Cash"
            )

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


def fundamental_score_berechnen(
    modell,
    info
):

    if modell in [
        "BANK",
        "CAPITAL_MARKETS"
    ]:
        return qualitaet_finanz(info)

    if modell == "ENERGY":
        return qualitaet_energy(info)

    return qualitaet_standard(info)


# ============================================================
# BEWERTUNG
# ============================================================

def bewertung_standard(info):

    score = 50
    gruende = []
    warnungen = []

    pe = wert(
        info,
        "trailingPE"
    )

    forward_pe = wert(
        info,
        "forwardPE"
    )

    peg = wert(
        info,
        "pegRatio"
    )

    ps = wert(
        info,
        "priceToSalesTrailing12Months"
    )

    if pe is not None and pe > 0:

        if pe < 15:
            score += 15
            gruende.append(
                "niedriges KGV"
            )

        elif pe < 25:
            score += 8

        elif pe < 35:
            score += 0

        elif pe < 50:
            score -= 10
            warnungen.append(
                "hohes KGV"
            )

        else:
            score -= 18
            warnungen.append(
                "sehr hohes KGV"
            )

    if (
        forward_pe is not None
        and forward_pe > 0
    ):

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

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


def bewertung_finanz(info):

    score = 50
    gruende = []
    warnungen = []

    pe = wert(
        info,
        "trailingPE"
    )

    forward_pe = wert(
        info,
        "forwardPE"
    )

    pb = wert(
        info,
        "priceToBook"
    )

    if pe is not None and pe > 0:

        if pe < 10:
            score += 15

        elif pe < 15:
            score += 10

        elif pe < 20:
            score += 4

        elif pe > 30:
            score -= 12

    if (
        forward_pe is not None
        and forward_pe > 0
    ):

        if forward_pe < 12:
            score += 10

        elif forward_pe < 18:
            score += 5

        elif forward_pe > 30:
            score -= 10

    if pb is not None and pb > 0:

        if pb < 1:
            score += 15
            gruende.append(
                "unter Buchwert bewertet"
            )

        elif pb < 1.5:
            score += 8

        elif pb < 2.5:
            score += 2

        elif pb > 4:
            score -= 12
            warnungen.append(
                "hohes Kurs-Buchwert-Verhältnis"
            )

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


def bewertung_energy(info):

    score = 50
    gruende = []
    warnungen = []

    pe = wert(
        info,
        "trailingPE"
    )

    forward_pe = wert(
        info,
        "forwardPE"
    )

    ps = wert(
        info,
        "priceToSalesTrailing12Months"
    )

    if pe is not None and pe > 0:

        if pe < 10:
            score += 15

        elif pe < 18:
            score += 10

        elif pe < 25:
            score += 4

        elif pe > 35:
            score -= 12

    if (
        forward_pe is not None
        and forward_pe > 0
    ):

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

    return (
        score_begrenzen(score),
        gruende,
        warnungen
    )


def bewertungs_score_berechnen(
    modell,
    info
):

    if modell in [
        "BANK",
        "CAPITAL_MARKETS"
    ]:
        return bewertung_finanz(info)

    if modell == "ENERGY":
        return bewertung_energy(info)

    return bewertung_standard(info)


# ============================================================
# RSI / TREND
# ============================================================

def rsi_berechnen(
    close,
    periode=14
):

    if (
        close is None
        or len(close) < periode + 1
    ):
        return None

    differenz = close.diff()

    gewinne = differenz.clip(
        lower=0
    )

    verluste = -differenz.clip(
        upper=0
    )

    durchschnitt_gewinn = (
        gewinne
        .rolling(periode)
        .mean()
    )

    durchschnitt_verlust = (
        verluste
        .rolling(periode)
        .mean()
    )

    letzter_verlust = (
        durchschnitt_verlust.iloc[-1]
    )

    letzter_gewinn = (
        durchschnitt_gewinn.iloc[-1]
    )

    if letzter_verlust == 0:

        if letzter_gewinn > 0:
            return 100

        return 50

    rs = (
        letzter_gewinn
        / letzter_verlust
    )

    return float(
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )


def trend_analyse(historie):

    ergebnis = {
        "kurs": None,
        "hoch_52w": None,
        "drawdown": None,
        "ma50": None,
        "ma200": None,
        "rsi": None,
        "momentum_1m": None,
        "momentum_3m": None,
        "trend_score": 50
    }

    if historie is None or historie.empty:
        return ergebnis

    try:
        close = historie["Close"].dropna()
        close = close[close.apply(lambda x: math.isfinite(float(x)) and float(x) > 0)]
    except Exception:
        return ergebnis

    if close.empty:
        return ergebnis

    kurs = float(close.iloc[-1])

    ergebnis["kurs"] = kurs

    letzte_252 = close.tail(
        min(252, len(close))
    )

    hoch = float(
        letzte_252.max()
    )

    ergebnis["hoch_52w"] = hoch

    ergebnis["drawdown"] = (
        (
            kurs - hoch
        )
        / hoch
    ) * 100

    if len(close) >= 50:
        ergebnis["ma50"] = float(
            close.tail(50).mean()
        )

    if len(close) >= 200:
        ergebnis["ma200"] = float(
            close.tail(200).mean()
        )

    ergebnis["rsi"] = rsi_berechnen(
        close
    )

    if len(close) > 21:

        ergebnis["momentum_1m"] = (
            (
                kurs
                / float(
                    close.iloc[-22]
                )
            )
            - 1
        ) * 100

    if len(close) > 63:

        ergebnis["momentum_3m"] = (
            (
                kurs
                / float(
                    close.iloc[-64]
                )
            )
            - 1
        ) * 100

    score = 50

    if ergebnis["ma50"] is not None:

        if kurs > ergebnis["ma50"]:
            score += 12

        else:
            score -= 8

    if ergebnis["ma200"] is not None:

        if kurs > ergebnis["ma200"]:
            score += 15

        else:
            score -= 12

    rsi = ergebnis["rsi"]

    if rsi is not None:

        if 40 <= rsi <= 65:
            score += 8

        elif rsi < 30:
            score -= 5

        elif rsi > 75:
            score -= 8

    momentum = ergebnis[
        "momentum_3m"
    ]

    if momentum is not None:

        if momentum > 10:
            score += 8

        elif momentum > 0:
            score += 4

        elif momentum < -15:
            score -= 10

    ergebnis["trend_score"] = (
        score_begrenzen(score)
    )

    return ergebnis


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
# VALUE TRAP
# ============================================================

def value_trap_risiko(
    modell,
    info,
    fundamental_score,
    entwicklungs_score,
    margen_score,
    drawdown
):

    risiko = 0
    gruende = []

    marge = wert(
        info,
        "profitMargins"
    )

    fcf = wert(
        info,
        "freeCashflow"
    )

    growth = wert(
        info,
        "revenueGrowth"
    )

    if fundamental_score < 50:

        risiko += 30
        gruende.append(
            "schwache Unternehmensqualität"
        )

    elif fundamental_score < 65:
        risiko += 15

    # Finanzunternehmen
    if modell in [
        "BANK",
        "CAPITAL_MARKETS"
    ]:

        if entwicklungs_score < 35:

            risiko += 30
            gruende.append(
                "deutlich negative Mehrjahresentwicklung"
            )

        elif entwicklungs_score < 50:

            risiko += 15
            gruende.append(
                "schwache Mehrjahresentwicklung"
            )

        if marge is not None and marge < 0:

            risiko += 25
            gruende.append(
                "Finanzunternehmen schreibt Verluste"
            )

    # Energie
    elif modell == "ENERGY":

        if entwicklungs_score < 30:

            risiko += 25
            gruende.append(
                "schwache Entwicklung trotz Zyklusbereinigung"
            )

        elif entwicklungs_score < 40:

            risiko += 10

        if marge is not None and marge < 0:

            risiko += 25
            gruende.append(
                "negative Gewinnmarge"
            )

        if fcf is not None and fcf < 0:

            risiko += 25
            gruende.append(
                "negativer Free Cashflow"
            )

    # Standard
    else:

        if entwicklungs_score < 35:

            risiko += 30
            gruende.append(
                "deutlich negative Mehrjahresentwicklung"
            )

        elif entwicklungs_score < 50:

            risiko += 18
            gruende.append(
                "schwache Mehrjahresentwicklung"
            )

        elif entwicklungs_score < 60:
            risiko += 8

        if margen_score is not None:

            if margen_score < 30:

                risiko += 20
                gruende.append(
                    "Gewinnmarge langfristig stark verschlechtert"
                )

            elif margen_score < 45:

                risiko += 10
                gruende.append(
                    "Gewinnmarge langfristig rückläufig"
                )

        if growth is not None:

            if growth < -0.15:

                risiko += 25
                gruende.append(
                    "starker aktueller Umsatzrückgang"
                )

            elif growth < 0:

                risiko += 10
                gruende.append(
                    "Umsatz aktuell rückläufig"
                )

        if marge is not None and marge < 0:

            risiko += 20
            gruende.append(
                "negative Gewinnmarge"
            )

        if fcf is not None and fcf < 0:

            risiko += 20
            gruende.append(
                "negativer Free Cashflow"
            )

        debt = wert(
            info,
            "totalDebt"
        )

        cash = wert(
            info,
            "totalCash"
        )

        if (
            debt is not None
            and cash is not None
            and cash > 0
            and debt > cash * 5
        ):

            risiko += 15
            gruende.append(
                "hohe Verschuldung"
            )

    if drawdown is not None:

        if drawdown <= -50:

            risiko += 15
            gruende.append(
                "extremer Kursverlust über 50 %"
            )

        elif drawdown <= -30:
            risiko += 5

    return (
        score_begrenzen(risiko),
        gruende
    )


# ============================================================
# UNTERNEHMENS- UND EINSTIEGSSCORE 0.6.1
# ============================================================

def unternehmensscore_berechnen(
    fundamental_score,
    entwicklungs_score,
    bewertungs_score,
    trap_score
):

    score = (
        fundamental_score * 0.40
        + entwicklungs_score * 0.35
        + bewertungs_score * 0.25
    )

    score -= trap_score * 0.35

    return score_begrenzen(score)


def einstiegsscore_berechnen(
    unternehmensscore,
    bewertungs_score,
    drawdown_score,
    trend_score
):

    score = (
        unternehmensscore * 0.25
        + bewertungs_score * 0.20
        + drawdown_score * 0.40
        + trend_score * 0.15
    )

    return score_begrenzen(score)


def einstieg_sicherheits_gate(
    einstieg_roh,
    unternehmensscore,
    trap_score
):

    final = einstieg_roh
    gruende = []

    if unternehmensscore < 40:
        if final > 39:
            final = 39
            gruende.append(
                "Unternehmensscore unter 40 begrenzt den Einstieg"
            )

    elif unternehmensscore < 55:
        if final > 54:
            final = 54
            gruende.append(
                "Unternehmensscore unter 55 begrenzt den Einstieg"
            )

    elif unternehmensscore < 70:
        if final > 69:
            final = 69
            gruende.append(
                "Unternehmensscore unter 70 begrenzt den Einstieg"
            )

    if trap_score >= 60:
        if final > 39:
            final = 39
            gruende.append(
                "Hohes Value-Trap-Risiko begrenzt den Einstieg"
            )

    elif trap_score >= 40:
        if final > 54:
            final = 54
            gruende.append(
                "Erhöhtes Value-Trap-Risiko begrenzt den Einstieg"
            )

    return score_begrenzen(final), gruende


# ============================================================
# STATUSLOGIK 0.6.1
# ============================================================

def qualitaets_status(score):

    if score >= 80:
        return (
            "🟢 HOHE QUALITÄT",
            "Die aktuellen Unternehmenskennzahlen sind insgesamt stark."
        )

    if score >= 65:
        return (
            "🟡 SOLIDE QUALITÄT",
            "Die Unternehmensqualität ist insgesamt ordentlich."
        )

    if score >= 50:
        return (
            "🟠 DURCHSCHNITTLICHE QUALITÄT",
            "Die Unternehmensqualität zeigt mehrere Schwachpunkte."
        )

    return (
        "🔴 SCHWACHE QUALITÄT",
        "Die aktuellen Unternehmenskennzahlen zeigen deutliche Probleme."
    )


def entwicklungs_status(
    modell,
    score
):

    # Bei zyklischen Unternehmen neutralere Sprache
    if modell == "ENERGY":

        if score >= 70:
            return (
                "🟢 STARKE ZYKLISCHE ENTWICKLUNG",
                "Die Geschäftsentwicklung liegt insgesamt auf einem starken Niveau."
            )

        if score >= 50:
            return (
                "🟡 STABILE ZYKLISCHE ENTWICKLUNG",
                "Die Geschäftsentwicklung liegt ungefähr im normalen Mehrjahresbereich."
            )

        if score >= 30:
            return (
                "🟠 UNTER MEHRJAHRESNIVEAU",
                "Gewinn, Cashflow oder Margen liegen unter früheren Mehrjahreswerten."
            )

        return (
            "🔴 DEUTLICH UNTER MEHRJAHRESNIVEAU",
            "Die zyklusbereinigte Geschäftsentwicklung ist deutlich schwach."
        )

    if score >= 70:
        return (
            "🟢 STARKE ENTWICKLUNG",
            "Die Mehrjahresentwicklung des Unternehmens ist überzeugend."
        )

    if score >= 55:
        return (
            "🟡 SOLIDE ENTWICKLUNG",
            "Die Mehrjahresentwicklung ist insgesamt positiv bis stabil."
        )

    if score >= 40:
        return (
            "🟠 SCHWACHE ENTWICKLUNG",
            "Mehrere langfristige Unternehmenskennzahlen entwickeln sich schwach."
        )

    return (
        "🔴 DEUTLICH SCHWACHE ENTWICKLUNG",
        "Die Mehrjahresentwicklung zeigt deutliche fundamentale Verschlechterungen."
    )


def risiko_status(score):

    if score < 20:
        return (
            "🟢 NIEDRIG",
            "Aktuell werden keine größeren Value-Trap-Warnsignale erkannt."
        )

    if score < 40:
        return (
            "🟡 MODERAT",
            "Einzelne fundamentale Risiken sind vorhanden."
        )

    if score < 60:
        return (
            "🟠 ERHÖHT",
            "Mehrere fundamentale Warnsignale sollten genauer geprüft werden."
        )

    return (
        "🔴 HOCH",
        "Es bestehen deutliche fundamentale Value-Trap-Risiken."
    )


def einstiegslage(
    einstieg_score,
    unternehmensscore,
    drawdown,
    trap_score
):

    if drawdown is None:
        return (
            "⚪ NICHT GENUG DATEN",
            "Die Einstiegssituation konnte nicht bestimmt werden."
        )

    if trap_score >= 60 and drawdown <= -10:
        return (
            "🔴 RISIKOREICHER RÜCKSETZER",
            "Der Kurs ist deutlich gefallen, gleichzeitig bestehen hohe fundamentale Value-Trap-Risiken."
        )

    if einstieg_score >= 70 and drawdown <= -10 and unternehmensscore >= 55:
        return (
            "🟢 INTERESSANTER EINSTIEG",
            "Unternehmensdaten und Kurssituation ergeben aktuell eine interessante Kombination."
        )

    if einstieg_score >= 55:
        return (
            "🟡 BEOBACHTEN",
            "Die Aktie ist grundsätzlich interessant, die Einstiegslage ist aber noch nicht eindeutig stark genug."
        )

    if drawdown > -10:
        return (
            "⚪ KEIN BESONDERER EINSTIEG",
            "Die Aktie befindet sich relativ nahe am 52-Wochen-Hoch; aktuell liegt kein ausgeprägter Rücksetzer vor."
        )

    return (
        "🟠 BEOBACHTEN",
        "Ein Rücksetzer ist vorhanden, die Kombination aus Unternehmen, Bewertung und Risiko überzeugt aber noch nicht vollständig."
    )


# ============================================================
# AUSGABEFUNKTIONEN
# ============================================================

def trend_ausgeben(
    name,
    trend
):

    score = trend.get("score")

    if score is None:
        score_text = "   --  "

    else:
        score_text = f"{score:>3}/100"

    print(
        f"{name:<25}",
        score_text,
        "|",
        trend.get(
            "richtung",
            "keine Daten"
        ),
        "|",
        zahl_prozent(
            trend.get(
                "veraenderung"
            )
        )
    )


def margen_trend_ausgeben(trend):

    score = trend.get("score")

    if score is None:
        score_text = "   --  "

    else:
        score_text = f"{score:>3}/100"

    print(
        f"{'Gewinnmarge:':<25}",
        score_text,
        "|",
        trend.get(
            "richtung",
            "keine Daten"
        ),
        "|",
        (
            f"{trend['veraenderung']:+.1f} Prozentpunkte"
            if trend.get("veraenderung") is not None
            else "keine Daten"
        )
    )

    if (
        trend.get("erste_marge") is not None
        and trend.get("letzte_marge") is not None
    ):

        print(
            f"{'':<25}",
            f"{trend['erste_marge']:.1f}%"
            " → "
            f"{trend['letzte_marge']:.1f}%"
        )


# ============================================================
# HAUPTANALYSE
# ============================================================


# ============================================================
# TRADEPILOT 0.7.2 - DATENANALYSE FÜR DIE DESKTOP-APP
# ============================================================

def performance_aus_historie(historie):
    ergebnis = {
        "heute": None,
        "1m": None,
        "3m": None,
        "1j": None,
    }

    if historie is None or historie.empty or "Close" not in historie:
        return ergebnis

    try:
        close = historie["Close"].dropna()
    except Exception:
        return ergebnis

    if len(close) < 2:
        return ergebnis

    letzter = float(close.iloc[-1])

    def rendite_vor_tagen(handelstage):
        if len(close) <= handelstage:
            return None
        basis = float(close.iloc[-(handelstage + 1)])
        if basis == 0:
            return None
        return ((letzter / basis) - 1) * 100

    ergebnis["heute"] = rendite_vor_tagen(1)
    ergebnis["1m"] = rendite_vor_tagen(21)
    ergebnis["3m"] = rendite_vor_tagen(63)
    ergebnis["1j"] = rendite_vor_tagen(252)
    return ergebnis


def analyse_daten(symbol):
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Bitte ein Aktien-Symbol eingeben.")

    try:
        aktie = yf.Ticker(symbol)
        info = aktie.info
        historie = aktie.history(period="2y", auto_adjust=True)
        income = aktie.get_income_stmt(freq="yearly")
        cashflow = aktie.get_cash_flow(freq="yearly")
        balance = aktie.get_balance_sheet(freq="yearly")
    except Exception as fehler:
        raise RuntimeError(f"Fehler beim Laden der Daten: {fehler}") from fehler

    if not info:
        raise RuntimeError("Keine Unternehmensdaten gefunden.")

    # 0.9.7 data-quality guard: Yahoo can sometimes return a metadata shell or
    # a final NaN placeholder row. Such data must never become an apparent
    # investment decision. The research formulas stay unchanged; we only clean
    # unusable market-data rows and reject symbols without a valid price history.
    try:
        if historie is None or historie.empty or "Close" not in historie.columns:
            raise RuntimeError(f"Ticker {symbol} nicht gefunden oder keine Kursdaten verfügbar.")
        historie = historie.dropna(subset=["Close"]).copy()
        historie = historie[historie["Close"].apply(lambda x: math.isfinite(float(x)) and float(x) > 0)]
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Kursdaten für {symbol} sind ungültig: {exc}") from exc

    if historie.empty:
        raise RuntimeError(f"Ticker {symbol} nicht gefunden oder keine gültigen Kursdaten verfügbar.")

    quote_type = str(wert(info, "quoteType", "") or "").upper()
    has_identity = bool(wert(info, "longName") or wert(info, "shortName"))
    if not has_identity and quote_type not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
        raise RuntimeError(f"Ticker {symbol} konnte nicht eindeutig als Wertpapier erkannt werden.")

    name = wert(info, "longName", wert(info, "shortName", symbol))
    sektor = wert(info, "sector", "unbekannt")
    branche = wert(info, "industry", "unbekannt")
    waehrung = wert(info, "currency", "")
    modell = modell_erkennen(info)

    fundamental_score, fundamental_plus, fundamental_warnungen = fundamental_score_berechnen(
        modell, info
    )

    entwicklung = unternehmensentwicklung(modell, income, cashflow, balance)
    entwicklungs_score = entwicklung["score"]
    margen_score = entwicklung["marge"].get("score")

    bewertungs_score, bewertung_plus, bewertung_warnungen = bewertungs_score_berechnen(
        modell, info
    )

    trend = trend_analyse(historie)
    drawdown = trend["drawdown"]
    drawdown_score = drawdown_score_berechnen(drawdown)

    trap_score, trap_gruende = value_trap_risiko(
        modell,
        info,
        fundamental_score,
        entwicklungs_score,
        margen_score,
        drawdown,
    )

    unternehmensscore = unternehmensscore_berechnen(
        fundamental_score,
        entwicklungs_score,
        bewertungs_score,
        trap_score,
    )

    einstieg_roh = einstiegsscore_berechnen(
        unternehmensscore,
        bewertungs_score,
        drawdown_score,
        trend["trend_score"],
    )

    einstieg_score, gate_gruende = einstieg_sicherheits_gate(
        einstieg_roh,
        unternehmensscore,
        trap_score,
    )

    q_status, q_text = qualitaets_status(fundamental_score)
    e_status, e_text = entwicklungs_status(modell, entwicklungs_score)
    r_status, r_text = risiko_status(trap_score)
    i_status, i_text = einstiegslage(
        einstieg_score,
        unternehmensscore,
        drawdown,
        trap_score,
    )

    staerken = fundamental_plus + entwicklung["gruende"] + bewertung_plus
    warnungen = fundamental_warnungen + entwicklung["warnungen"] + bewertung_warnungen

    # Doppelte Texte entfernen, Reihenfolge beibehalten.
    staerken = list(dict.fromkeys(staerken))
    warnungen = list(dict.fromkeys(warnungen))
    trap_gruende = list(dict.fromkeys(trap_gruende))
    gate_gruende = list(dict.fromkeys(gate_gruende))

    fcf = wert(info, "freeCashflow")
    umsatz = wert(info, "totalRevenue")
    fcf_marge = None
    if fcf is not None and umsatz not in (None, 0):
        try:
            fcf_marge = fcf / umsatz
        except Exception:
            fcf_marge = None

    debt_cash = None
    debt = wert(info, "totalDebt")
    cash = wert(info, "totalCash")
    if debt is not None and cash not in (None, 0):
        try:
            debt_cash = debt / cash
        except Exception:
            debt_cash = None

    return {
        "symbol": symbol,
        "name": name,
        "sektor": sektor,
        "branche": branche,
        "waehrung": waehrung,
        "modell": modell,
        "modell_text": modell_text(modell),
        "info": info,
        "historie": historie,
        "performance": performance_aus_historie(historie),
        "entwicklung": entwicklung,
        "trend": trend,
        "fundamental_score": fundamental_score,
        "entwicklungs_score": entwicklungs_score,
        "bewertungs_score": bewertungs_score,
        "drawdown_score": drawdown_score,
        "trap_score": trap_score,
        "unternehmensscore": unternehmensscore,
        "einstieg_roh": einstieg_roh,
        "einstieg_score": einstieg_score,
        "q_status": q_status,
        "q_text": q_text,
        "e_status": e_status,
        "e_text": e_text,
        "r_status": r_status,
        "r_text": r_text,
        "i_status": i_status,
        "i_text": i_text,
        "staerken": staerken,
        "warnungen": warnungen,
        "trap_gruende": trap_gruende,
        "gate_gruende": gate_gruende,
        "fcf_marge": fcf_marge,
        "debt_cash": debt_cash,
    }


# ============================================================
# TRADEPILOT 0.7.3 - DESKTOP-OBERFLÄCHE
# ============================================================

