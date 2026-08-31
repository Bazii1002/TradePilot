from __future__ import annotations

_LANGUAGE = "de"

T = {
"de": {
"nav.dashboard":"Dashboard","nav.analysis":"Analyse","nav.watchlist":"Watchlist","nav.portfolio":"Portfolio","nav.signals":"Signale","nav.bot":"AutoTrader","nav.history":"Verlauf","nav.settings":"Einstellungen",
"section.workspace":"WORKSPACE","section.system":"SYSTEM","top.search":"Ticker suchen · z. B. AAPL, JPM, XOM, ADBE","top.analyze":"Analyse starten   ▶","top.data":"DATENSTATUS","top.ready":"Bereit",
"settings.title":"Einstellungen","settings.subtitle":"Darstellung, Sprache und lokale App-Einstellungen.","settings.appearance":"Darstellung","settings.appearance_help":"Wähle das Farbschema der gesamten TradePilot-Oberfläche.","settings.theme":"Farbschema","settings.dark":"Dunkel","settings.light":"Hell","settings.language":"Sprache","settings.language_help":"Die Oberfläche wird in der gewählten Sprache neu aufgebaut.","settings.german":"Deutsch","settings.english":"English","settings.info":"Technische Informationen","settings.saved":"Einstellung gespeichert",
"dashboard.subtitle":"Dein persönlicher Überblick über Watchlist, Chancen und Veränderungen.","analysis.start":"Aktie analysieren","watch.add":"☆  Zur Watchlist","watch.in":"★  In Watchlist","price.current":"AKTUELLER KURS","chart.title":"KURSVERLAUF","entry.title":"Einstiegssituation","reasons.title":"Stärken & Warnungen",
"score.company":"Unternehmensscore","score.entry":"Einstiegsscore","score.quality":"Qualität","score.development":"Entwicklung","score.valuation":"Bewertung","score.trap":"Value-Trap-Risiko",
"page.portfolio.sub":"Eigene Positionen, Einstandskurse, Gewinn/Verlust und Risikoübersicht kommen hier hinein.","page.signals.sub":"Neue Einstiege, Score-Verbesserungen und Warnsignale werden hier zentral gesammelt.",
"bot.title":"TradePilot AutoTrader","bot.subtitle":"Strategie- und Risikosteuerung im sicheren Paper-Modus.","bot.paper":"PAPER-MODUS","bot.status":"AUTOTRADER-STATUS","bot.active":"Aktiv","bot.paused":"Pausiert","bot.activate":"AutoTrader aktivieren","bot.pause":"AutoTrader pausieren","bot.profile":"Risikoprofil","bot.capital":"Demo-Kapital","bot.current":"Aktueller Kandidat","bot.no_data":"Analysiere zuerst eine Aktie. TradePilot prüft sie anschließend automatisch mit dem gewählten Risikoprofil.","bot.ready":"Trade vorbereitet","bot.wait":"Auf Bestätigung warten","bot.reject":"Kein Trade","bot.blocked":"Durch Sicherheitsregel gesperrt","bot.confidence":"Bestätigungsgrad","bot.not_probability":"Interner Bestätigungsgrad – keine Gewinnwahrscheinlichkeit.","bot.checks":"Entscheidungskriterien","bot.position":"Risk Manager","bot.position_size":"Max. Positionswert","bot.shares":"Vorgeschlagene Stückzahl","bot.reserve":"Cash-Reserve","bot.max_positions":"Max. offene Positionen","bot.execute_note":"0.9 führt keine Broker-Order aus. Die Berechnung dient ausschließlich der Paper-/Demo-Vorschau.","bot.profile.defensive":"Defensiv","bot.profile.balanced":"Ausgewogen","bot.profile.offensive":"Offensiv","bot.profile.speculative":"Spekulativ","bot.check.company":"Unternehmensscore","bot.check.entry":"Einstiegsscore","bot.check.trap":"Value-Trap","bot.check.quality":"Qualität","bot.check.development":"Entwicklung","bot.check.valuation":"Bewertung","bot.check.trend":"Trend",
"detail.quality":"Unternehmensqualität","detail.development":"Geschäftsentwicklung","detail.valuation":"Bewertung","detail.risk":"Risiko",
"metric.net_margin":"Nettomarge","metric.margin":"Marge","metric.revenue_growth":"Umsatzwachstum","metric.multiyear_score":"Mehrjahres-Score","metric.trend_score":"Trend-Score","metric.pe":"KGV aktuell","metric.forward_pe":"Forward KGV","metric.drawdown_52w":"Drawdown 52W",
"info.company_score":"Unternehmensscore\nGesamtbewertung der fundamentalen Stärke des Unternehmens. TradePilot kombiniert Qualität, Geschäftsentwicklung und Bewertung und berücksichtigt zusätzlich das Value-Trap-Risiko.",
"info.entry_score":"Einstiegsscore\nBewertet, wie attraktiv der aktuelle Zeitpunkt für einen möglichen Einstieg ist. Berücksichtigt Unternehmensscore, Bewertung, Kursrückgang und Trend.",
"info.quality_score":"Qualität\nBewertet fundamentale Merkmale wie Profitabilität, Cashflow, Eigenkapitalrendite und Verschuldung. Höher ist grundsätzlich besser.",
"info.development_score":"Entwicklung\nBewertet die mehrjährige Entwicklung von Umsatz, Ergebnis, Cashflow, Margen und – je nach Modell – Verschuldung.",
"info.valuation_score":"Bewertung\nSchätzt ein, wie teuer oder günstig die Aktie anhand verschiedener Bewertungskennzahlen ist. Die Interpretation ist branchenabhängig.",
"info.trap_score":"Value-Trap-Risiko\nWarnt vor Aktien, die günstig erscheinen, deren Unternehmen sich aber fundamental verschlechtern könnte. Hier ist ein niedriger Wert besser.",
"info.entry_situation":"Einstiegssituation\nFasst Timing, Trend, Momentum und Rücksetzer zusammen. Sie ergänzt die Unternehmensanalyse, ersetzt sie aber nicht.",
"info.roe":"ROE – Return on Equity / Eigenkapitalrendite\nZeigt, wie effizient ein Unternehmen mit dem Eigenkapital seiner Eigentümer Gewinne erwirtschaftet. Ein hoher Wert ist meist positiv, sollte aber zusammen mit der Verschuldung betrachtet werden.",
"info.net_margin":"Nettomarge\nAnteil des Umsatzes, der nach allen Kosten als Gewinn übrig bleibt. Höhere und stabile Margen sind in der Regel positiv.",
"info.fcf_margin":"FCF-Marge – Free-Cash-Flow-Marge\nZeigt, welcher Anteil des Umsatzes als freier Cashflow übrig bleibt. Positiver und stabiler FCF gibt dem Unternehmen finanziellen Spielraum.",
"info.revenue_growth":"Umsatzwachstum\nVeränderung des Umsatzes gegenüber dem Vergleichszeitraum. Wachstum kann auf eine zunehmende Nachfrage oder Expansion hinweisen.",
"info.multiyear_score":"Mehrjahres-Score\nTradePilot bewertet, ob sich wichtige Unternehmenskennzahlen über mehrere Geschäftsjahre verbessern oder verschlechtern.",
"info.trend_score":"Trend-Score\nTechnischer Gesamtwert aus Kurslage, gleitenden Durchschnitten, RSI und Momentum. Er beschreibt den aktuellen Kurstrend, nicht die Qualität des Unternehmens.",
"info.pe":"KGV – Kurs-Gewinn-Verhältnis / P/E\nSetzt den Aktienkurs ins Verhältnis zum Gewinn je Aktie. Ein niedrigeres KGV kann günstiger wirken, muss aber mit Wachstum, Qualität und Branche verglichen werden.",
"info.forward_pe":"Forward KGV – erwartetes Kurs-Gewinn-Verhältnis\nVerwendet erwartete zukünftige Gewinne statt vergangener Gewinne. Da Analystenschätzungen verwendet werden, kann sich dieser Wert deutlich ändern.",
"info.peg":"PEG – Price/Earnings-to-Growth Ratio\nSetzt das KGV ins Verhältnis zum erwarteten Gewinnwachstum. Es versucht Bewertung und Wachstum gemeinsam zu betrachten.",
"info.drawdown":"Drawdown\nZeigt, wie weit der aktuelle Kurs unter einem vorherigen Hoch liegt. Ein größerer negativer Wert bedeutet einen stärkeren Kursrückgang.",
"info.value_trap":"Value Trap – Bewertungsfalle\nEine Aktie kann billig aussehen, weil sich das Geschäft verschlechtert. TradePilot versucht solche Situationen mit dem Value-Trap-Score zu erkennen.",
"info.debt_cash":"Debt/Cash – Schulden im Verhältnis zu Barmitteln\nVergleicht die Finanzschulden mit verfügbaren liquiden Mitteln. Ein hoher Wert kann auf eine stärkere finanzielle Belastung hinweisen.",
"info.confirmation":"Bestätigungsgrad\nZeigt, wie viele Bedingungen des gewählten Risikoprofils aktuell erfüllt sind. Er ist keine Wahrscheinlichkeit für Gewinn oder Kursanstieg.",
"info.risk_manager":"Risk Manager\nBegrenzt eine mögliche Position anhand des Risikoprofils, des verfügbaren Kapitals und festgelegter Sicherheitsregeln. Er entscheidet nicht, ob eine Aktie gut ist.",
"info.position_size":"Maximaler Positionswert\nObergrenze des Kapitals, das der AutoTrader für diesen einzelnen Trade verwenden dürfte.",
"info.shares":"Vorgeschlagene Stückzahl\nAus aktuellem Aktienkurs und maximalem Positionswert berechnete Stückzahl für die Paper-Trading-Vorschau.",
"info.cash_reserve":"Cash-Reserve\nAnteil des Demo-Kapitals, der bewusst nicht in diese Position investiert wird.",
"info.max_positions":"Maximale offene Positionen\nBegrenzt, wie viele Positionen der AutoTrader gleichzeitig halten darf, um das Kapital nicht auf zu viele oder zu wenige Trades zu konzentrieren.",
"common.prepared":"Diese Seite ist in der neuen App-Struktur bereits vorbereitet und wird in den nächsten Versionen funktional ausgebaut.",
},
"en": {
"nav.dashboard":"Dashboard","nav.analysis":"Analysis","nav.watchlist":"Watchlist","nav.portfolio":"Portfolio","nav.signals":"Signals","nav.bot":"AutoTrader","nav.history":"History","nav.settings":"Settings",
"section.workspace":"WORKSPACE","section.system":"SYSTEM","top.search":"Search ticker · e.g. AAPL, JPM, XOM, ADBE","top.analyze":"Start analysis   ▶","top.data":"DATA STATUS","top.ready":"Ready",
"settings.title":"Settings","settings.subtitle":"Appearance, language and local app settings.","settings.appearance":"Appearance","settings.appearance_help":"Choose the color scheme for the entire TradePilot interface.","settings.theme":"Color scheme","settings.dark":"Dark","settings.light":"Light","settings.language":"Language","settings.language_help":"The interface is rebuilt in the selected language.","settings.german":"Deutsch","settings.english":"English","settings.info":"Technical information","settings.saved":"Setting saved",
"dashboard.subtitle":"Your personal overview of watchlist, opportunities and changes.","analysis.start":"Analyze stock","watch.add":"☆  Add to watchlist","watch.in":"★  In watchlist","price.current":"CURRENT PRICE","chart.title":"PRICE HISTORY","entry.title":"Entry situation","reasons.title":"Strengths & warnings",
"score.company":"Company score","score.entry":"Entry score","score.quality":"Quality","score.development":"Development","score.valuation":"Valuation","score.trap":"Value-trap risk",
"page.portfolio.sub":"Your positions, entry prices, profit/loss and risk overview will live here.","page.signals.sub":"New entries, score improvements and warning signals will be collected here.",
"bot.title":"TradePilot AutoTrader","bot.subtitle":"Strategy and risk control in safe paper mode.","bot.paper":"PAPER MODE","bot.status":"AUTOTRADER STATUS","bot.active":"Active","bot.paused":"Paused","bot.activate":"Activate AutoTrader","bot.pause":"Pause AutoTrader","bot.profile":"Risk profile","bot.capital":"Demo capital","bot.current":"Current candidate","bot.no_data":"Analyze a stock first. TradePilot will then automatically evaluate it with the selected risk profile.","bot.ready":"Trade prepared","bot.wait":"Wait for confirmation","bot.reject":"No trade","bot.blocked":"Blocked by safety rule","bot.confidence":"Confirmation score","bot.not_probability":"Internal confirmation score – not a probability of profit.","bot.checks":"Decision criteria","bot.position":"Risk Manager","bot.position_size":"Max. position value","bot.shares":"Suggested shares","bot.reserve":"Cash reserve","bot.max_positions":"Max. open positions","bot.execute_note":"0.9 does not place broker orders. The calculation is only a paper/demo preview.","bot.profile.defensive":"Defensive","bot.profile.balanced":"Balanced","bot.profile.offensive":"Offensive","bot.profile.speculative":"Speculative","bot.check.company":"Company score","bot.check.entry":"Entry score","bot.check.trap":"Value trap","bot.check.quality":"Quality","bot.check.development":"Development","bot.check.valuation":"Valuation","bot.check.trend":"Trend",
"detail.quality":"Company quality","detail.development":"Business development","detail.valuation":"Valuation","detail.risk":"Risk",
"metric.net_margin":"Net margin","metric.margin":"margin","metric.revenue_growth":"Revenue growth","metric.multiyear_score":"Multi-year score","metric.trend_score":"Trend score","metric.pe":"Current P/E","metric.forward_pe":"Forward P/E","metric.drawdown_52w":"52W drawdown",
"info.company_score":"Company score\nOverall assessment of the company's fundamental strength. TradePilot combines quality, business development and valuation while also considering value-trap risk.",
"info.entry_score":"Entry score\nAssesses how attractive the current timing may be for an entry. It considers company score, valuation, pullback and trend.",
"info.quality_score":"Quality\nAssesses fundamentals such as profitability, cash flow, return on equity and debt. Higher is generally better.",
"info.development_score":"Development\nAssesses the multi-year development of revenue, earnings, cash flow, margins and, depending on the model, debt.",
"info.valuation_score":"Valuation\nEstimates how expensive or inexpensive the stock appears using several valuation metrics. Interpretation depends on the industry.",
"info.trap_score":"Value-trap risk\nWarns about stocks that appear cheap while the underlying business may be deteriorating. Lower is better here.",
"info.entry_situation":"Entry situation\nSummarizes timing, trend, momentum and pullback. It complements the company analysis rather than replacing it.",
"info.roe":"ROE – Return on Equity\nShows how efficiently a company generates profit from shareholders' equity. A high value is often positive but should be considered together with debt.",
"info.net_margin":"Net margin\nThe share of revenue remaining as profit after all expenses. Higher and stable margins are generally positive.",
"info.fcf_margin":"FCF margin – Free Cash Flow margin\nShows what share of revenue remains as free cash flow. Positive and stable FCF gives a company financial flexibility.",
"info.revenue_growth":"Revenue growth\nChange in revenue versus the comparison period. Growth may indicate increasing demand or business expansion.",
"info.multiyear_score":"Multi-year score\nTradePilot assesses whether important company metrics have improved or deteriorated over several fiscal years.",
"info.trend_score":"Trend score\nTechnical composite of price position, moving averages, RSI and momentum. It describes the current price trend, not company quality.",
"info.pe":"P/E – Price-to-Earnings ratio\nCompares the share price with earnings per share. A lower P/E can look cheaper, but should be compared with growth, quality and industry peers.",
"info.forward_pe":"Forward P/E – expected Price-to-Earnings ratio\nUses expected future earnings instead of historical earnings. Because it relies on analyst estimates, the value can change substantially.",
"info.peg":"PEG – Price/Earnings-to-Growth ratio\nRelates the P/E ratio to expected earnings growth and attempts to consider valuation and growth together.",
"info.drawdown":"Drawdown\nShows how far the current price is below a previous high. A larger negative value means a deeper price decline.",
"info.value_trap":"Value trap\nA stock can look cheap because its business is deteriorating. TradePilot attempts to flag such situations using the value-trap score.",
"info.debt_cash":"Debt/Cash\nCompares financial debt with available cash. A high ratio can indicate a heavier financial burden.",
"info.confirmation":"Confirmation score\nShows how many conditions of the selected risk profile are currently met. It is not a probability of profit or a price increase.",
"info.risk_manager":"Risk Manager\nLimits a potential position using the risk profile, available capital and fixed safety rules. It does not determine whether a company is good.",
"info.position_size":"Maximum position value\nUpper limit of capital the AutoTrader may allocate to this single trade.",
"info.shares":"Suggested shares\nNumber of shares calculated from the current share price and maximum position value for the paper-trading preview.",
"info.cash_reserve":"Cash reserve\nPart of the demo capital intentionally kept out of this position.",
"info.max_positions":"Maximum open positions\nLimits how many positions AutoTrader may hold at the same time to control portfolio concentration.",
"common.prepared":"This page is already prepared in the new app structure and will be expanded in upcoming versions.",
}}

def set_language(lang: str) -> None:
    global _LANGUAGE
    _LANGUAGE = lang if lang in T else "de"

def language() -> str:
    return _LANGUAGE

def tr(key: str, fallback: str | None = None) -> str:
    return T.get(_LANGUAGE, T["de"]).get(key, fallback if fallback is not None else key)

STATUS_EN = {
    "INTERESSANTER EINSTIEG":"Interesting entry",
    "BEOBACHTEN":"Watch",
    "KEIN BESONDERER EINSTIEG":"No special entry",
    "RISIKOREICHER RÜCKSETZER":"Risky pullback",
    "KEIN EINSTIEG":"No entry",
}
def translate_status(text: str) -> str:
    if _LANGUAGE == "en":
        return STATUS_EN.get(str(text).upper(), str(text))
    return str(text)
