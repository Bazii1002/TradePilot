import json
import os
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QProcess, QTimer, QRectF, QPointF
from PySide6.QtGui import QFont, QTextCursor, QPainter, QPen, QColor, QBrush, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QGridLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QMessageBox, QLineEdit, QCheckBox, QScrollArea, QSizePolicy
)

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "tradepilot_app_config.json"
ENGINE_FILE = ROOT / "bot_engine.py"

DEFAULTS = {
    "strategy_level": 1,
    "max_trades_per_day": 5,
    "max_invested_usd": 500.0,
    "position_size_usd": 100.0,
    "max_total_positions": 3,
    "bot_enabled": False,
    "run_interval_minutes": 5,
    "trading_mode": "REAL",
    "theme": "dark",
}

STRATEGIES = {
    1: ("Stufe 1 · Fast", "Schnelle Trades, kleine Gewinne früh sichern."),
    2: ("Stufe 2 · Day", "Länger halten; profitable Aktien am Tagesende schließen."),
    3: ("Stufe 3 · Week", "Mehrere Tage halten; spätestens Freitag vor US-Börsenschluss schließen."),
    4: ("Stufe 4 · Invest", "Langfristig; keine Tages-/Wochen- und keine kurzfristigen Technik-Exits."),
}

DARK = {
    "bg": "#070B12", "sidebar": "#0A1019", "panel": "#0D1420", "panel2": "#121C2A", "panel3": "#162235",
    "border": "#1D2B3D", "text": "#F6F8FC", "muted": "#7F91A8", "accent": "#4A7DFF",
    "accent2": "#6D9BFF", "good": "#31C48D", "warn": "#F5B942", "bad": "#F05B68"
}
LIGHT = {
    "bg": "#F5F7FB", "sidebar": "#FFFFFF", "panel": "#FFFFFF", "panel2": "#F4F7FB", "panel3": "#EBF0F7",
    "border": "#E1E7F0", "text": "#162033", "muted": "#738196", "accent": "#356DF3",
    "accent2": "#5D87F5", "good": "#159B6C", "warn": "#B87918", "bad": "#D34F5C"
}


def load_json(path, default):
    try:
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return default


def save_json(path, data):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


class Card(QFrame):
    def __init__(self, title, value="–", subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(6)
        t = QLabel(title.upper())
        t.setObjectName("cardTitle")
        self.value = QLabel(value)
        self.value.setObjectName("cardValue")
        self.sub = QLabel(subtitle)
        self.sub.setObjectName("muted")
        lay.addWidget(t)
        lay.addWidget(self.value)
        lay.addWidget(self.sub)



class MarketStatus(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setObjectName("marketStatus")
        self.setFixedSize(185, 66)
        l = QVBoxLayout(self)
        l.setContentsMargins(15, 8, 12, 7)
        l.setSpacing(0)
        self.name = QLabel(f"●   {name}")
        self.name.setObjectName("marketName")
        self.state = QLabel("Closed")
        self.state.setObjectName("marketClosed")
        self.detail = QLabel("öffnet später")
        self.detail.setObjectName("marketDetail")
        l.addWidget(self.name); l.addWidget(self.state); l.addWidget(self.detail)


class KpiCard(QFrame):
    def __init__(self, title, icon, accent, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.accent = accent
        self.setMinimumHeight(172)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 16, 20, 0)
        outer.setSpacing(5)
        top = QHBoxLayout()
        title_l = QLabel(title); title_l.setObjectName("kpiTitle")
        icon_l = QLabel(icon); icon_l.setAlignment(Qt.AlignCenter); icon_l.setObjectName("kpiIcon")
        icon_l.setProperty("accent", accent); icon_l.setFixedSize(54,54)
        top.addWidget(title_l); top.addStretch(1); top.addWidget(icon_l)
        self.value = QLabel("—"); self.value.setObjectName("kpiValue")
        subrow = QHBoxLayout()
        self.sub_left = QLabel("—"); self.sub_left.setObjectName("kpiSub")
        self.sub_right = QLabel("—"); self.sub_right.setObjectName("kpiSub")
        subrow.addWidget(self.sub_left); subrow.addStretch(1); subrow.addWidget(self.sub_right)
        outer.addLayout(top); outer.addWidget(self.value); outer.addStretch(1); outer.addLayout(subrow)
        self.accent_bar = QFrame(); self.accent_bar.setFixedHeight(3); self.accent_bar.setStyleSheet(f"background:{accent}; border:none;")
        outer.addWidget(self.accent_bar)


class PortfolioChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0.0
        self.setMinimumHeight(255)
    def set_value(self, value):
        self.value=float(value or 0); self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); left,top,right,bottom=8,20,54,48
        plot=QRectF(left,top,max(10,w-left-right),max(10,h-top-bottom))
        grid=QColor('#13293A'); text=QColor('#6F8BA5'); line=QColor('#5B7CFF')
        p.setPen(QPen(grid,1))
        for i in range(5):
            y=plot.top()+plot.height()*i/4; p.drawLine(QPointF(plot.left(),y),QPointF(plot.right(),y))
        for i in range(5):
            x=plot.left()+plot.width()*i/4; p.drawLine(QPointF(x,plot.top()),QPointF(x,plot.bottom()))
        y=plot.top()+plot.height()*0.52
        path=QPainterPath(); path.moveTo(plot.left(),y)
        for i in range(1,21):
            x=plot.left()+plot.width()*i/20
            yy=y + (2 if i%3==0 else -1 if i%4==0 else 0)
            path.lineTo(x,yy)
        fill=QPainterPath(path); fill.lineTo(plot.right(),plot.bottom()); fill.lineTo(plot.left(),plot.bottom()); fill.closeSubpath()
        p.fillPath(fill,QColor(40,84,185,55)); p.setPen(QPen(line,2)); p.drawPath(path)
        p.setPen(text); f=p.font(); f.setPointSize(8); p.setFont(f)
        p.drawText(QRectF(plot.left(),plot.bottom()+8,plot.width(),20),Qt.AlignLeft,'09:30 AM        11:00 AM        12:30 PM        02:00 PM        04:00 PM')
        p.drawText(QRectF(plot.left(),plot.top()+plot.height()*0.45,plot.width(),22),Qt.AlignCenter,'Portfolio-Verlauf wird ab jetzt lokal aufgezeichnet')


class BotOrb(QWidget):
    def __init__(self,parent=None): super().__init__(parent); self.setFixedSize(105,105)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); c=self.rect().center()
        p.setPen(QPen(QColor('#0A5B3D'),7)); p.drawEllipse(c,43,43)
        p.setPen(QPen(QColor('#16E67E'),2)); p.drawEllipse(c,34,34)
        p.setBrush(QBrush(QColor('#EAF7FF'))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(c.x()-22, c.y()-14, 44, 31), 12, 12)
        p.setBrush(QColor('#102436'))
        p.drawRoundedRect(QRectF(c.x()-15, c.y()-8, 30, 17), 8, 8)
        p.setBrush(QColor('#16E67E')); p.drawEllipse(c.x()-9,c.y()-2,5,5); p.drawEllipse(c.x()+4,c.y()-2,5,5)
        p.setPen(QPen(QColor('#EAF7FF'),3)); p.drawLine(c.x(),c.y()-15,c.x(),c.y()-25); p.drawEllipse(c.x()-3,c.y()-29,6,6)


class TradePilotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = DEFAULTS.copy()
        self.config.update(load_json(CONFIG_FILE, {}))
        self.process = None
        self.bot_requested = bool(self.config.get("bot_enabled", False))
        self.next_timer = QTimer(self)
        self.next_timer.setSingleShot(True)
        self.next_timer.timeout.connect(self._run_cycle)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_all)
        self.refresh_timer.start(3000)

        self.setWindowTitle("TradePilot Desktop Alpha 0.10.2.1 · Exact Dashboard Design Fix")
        self.resize(1540, 960)
        self.setMinimumSize(1180, 760)
        self._build_ui()
        self.apply_theme()
        self.refresh_all()
        if self.bot_requested:
            QTimer.singleShot(1200, self._run_cycle)

    # ---------- UI shell ----------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(276)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(10, 28, 12, 18)
        side.setSpacing(8)
        brand_row = QHBoxLayout()
        logo = QLabel("TP")
        logo.setText("TP")
        logo.setObjectName("logoMark")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(58, 44)
        brand_box = QVBoxLayout()
        brand = QLabel("TradePilot")
        brand.setObjectName("brand")
        version = QLabel("1.0 · UI Prototype 0.10.2.1")
        version.setObjectName("brandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(version)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_box)
        side.addLayout(brand_row)
        side.addSpacing(34)

        self.stack = QStackedWidget()
        pages = [
            ("▦   Dashboard", self._page_dashboard),
            ("◉   Bot", self._page_bot),
            ("◇   Portfolio", self._page_portfolio),
            ("⌁   Markets", self._page_markets),
            ("◫   News", self._page_news),
            ("↗   Backtest", self._page_backtest),
            ("⇄   Trades", self._page_trades),
            ("⚙   Settings", self._page_settings),
        ]
        self.nav_buttons = []
        for idx, (name, factory) in enumerate(pages):
            b = QPushButton(name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, i=idx: self.set_page(i))
            side.addWidget(b)
            self.nav_buttons.append(b)
            self.stack.addWidget(factory())
        side.addStretch(1)
        self.market_clock_box = QFrame(); self.market_clock_box.setObjectName("marketClockBox")
        mc=QVBoxLayout(self.market_clock_box); mc.setContentsMargins(16,13,16,13); mc.setSpacing(3)
        mct=QLabel("◉  Market Time (ET)"); mct.setObjectName("marketClockTitle")
        self.market_clock=QLabel("--:--:--"); self.market_clock.setObjectName("marketClock")
        self.market_date=QLabel("—"); self.market_date.setObjectName("marketDate")
        online=QLabel("●  System Status: Online"); online.setObjectName("onlineText")
        mc.addWidget(mct); mc.addWidget(self.market_clock); mc.addWidget(self.market_date); mc.addWidget(online)
        side.addWidget(self.market_clock_box)
        self.mode_badge = QLabel()
        self.mode_badge.setObjectName("modeBadge")
        self.mode_badge.setAlignment(Qt.AlignCenter)
        side.addSpacing(12); side.addWidget(self.mode_badge)
        footer=QLabel("Live Dashboard · eToro READ ONLY"); footer.setObjectName("sideFooter"); footer.setAlignment(Qt.AlignCenter)
        side.addSpacing(10); side.addWidget(footer)

        shell.addWidget(self.sidebar)
        shell.addWidget(self.stack, 1)
        self.set_page(0)

    def topbar(self, include_title=None, subtitle=""):
        bar=QFrame(); bar.setObjectName("topbar"); bar.setFixedHeight(112)
        row=QHBoxLayout(bar); row.setContentsMargins(28,16,28,16); row.setSpacing(12)
        if include_title:
            tb=QVBoxLayout(); h=QLabel(include_title); h.setObjectName("pageTitle"); tb.addWidget(h)
            if subtitle:
                st=QLabel(subtitle); st.setObjectName("pageSubtitle"); tb.addWidget(st)
            row.addLayout(tb)
        row.addStretch(1)
        self.market_cards=[]
        for name in ["NYSE","NASDAQ","XETRA"]:
            card=MarketStatus(name); self.market_cards.append(card); row.addWidget(card)
        bell=QLabel("♧"); bell.setObjectName("topIcon"); bell.setAlignment(Qt.AlignCenter); bell.setFixedSize(54,54)
        user=QLabel("○"); user.setObjectName("profileIcon"); user.setAlignment(Qt.AlignCenter); user.setFixedSize(62,62)
        row.addSpacing(12); row.addWidget(bell); row.addWidget(user)
        return bar

    def page_shell(self, title, subtitle=""):
        outer=QWidget(); lay=QVBoxLayout(outer); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        lay.addWidget(self.topbar(title,subtitle))
        body=QVBoxLayout(); body.setContentsMargins(26,22,26,24); body.setSpacing(16)
        holder=QWidget(); holder.setLayout(body); lay.addWidget(holder,1)
        return outer, body

    def set_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
        self.refresh_all()

    # ---------- Dashboard ----------
    def _page_dashboard(self):
        w=QWidget(); root=QVBoxLayout(w); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self.topbar())
        body=QVBoxLayout(); body.setContentsMargins(26,20,26,22); body.setSpacing(16)
        host=QWidget(); host.setLayout(body); root.addWidget(host,1)

        kpis=QHBoxLayout(); kpis.setSpacing(16)
        self.card_cash=KpiCard("Cash Available","▣","#19A9F5")
        self.card_invested=KpiCard("Invested","◔","#18D47A")
        self.card_value=KpiCard("Portfolio Value","⌁","#8A5CF6")
        self.card_today=KpiCard("Today","↗","#1AAAF4")
        for x in [self.card_cash,self.card_invested,self.card_value,self.card_today]: kpis.addWidget(x,1)
        body.addLayout(kpis)

        lower=QHBoxLayout(); lower.setSpacing(16)
        open_box=self.section("Open Positions")
        open_head=QHBoxLayout(); open_head.addStretch(1); va=QLabel("View All  ›"); va.setObjectName("viewAll"); open_box.layout().insertLayout(1,open_head)
        self.dashboard_positions=self.table(["Symbol","Side","Amount","Time"]); self.dashboard_positions.setObjectName("openPositionsTable")
        open_box.layout().addWidget(self.dashboard_positions,1)
        foot=QLabel("Alle Zeiten in ET"); foot.setObjectName("tinyMuted"); open_box.layout().addWidget(foot)
        lower.addWidget(open_box,28)

        portfolio=self.section("Portfolio Overview")
        top=QHBoxLayout(); self.portfolio_value_big=QLabel("$0.00"); self.portfolio_value_big.setObjectName("portfolioBig")
        day=QLabel("Today P/L: —"); day.setObjectName("goodText")
        tl=QVBoxLayout(); tl.addWidget(self.portfolio_value_big); tl.addWidget(day); top.addLayout(tl); top.addStretch(1)
        period=QPushButton("1D ⌄"); period.setObjectName("periodBtn"); top.addWidget(period); portfolio.layout().insertLayout(1,top)
        self.portfolio_chart=PortfolioChart(); portfolio.layout().addWidget(self.portfolio_chart,1)
        tabs=QHBoxLayout()
        for text in ["1D","1W","1M","3M","YTD","1Y","All"]:
            b=QPushButton(text); b.setObjectName("chartTab"); tabs.addWidget(b)
        tabs.addStretch(1); portfolio.layout().addLayout(tabs)
        stats=QHBoxLayout();
        self.portfolio_invested=QLabel("●  Invested\n    $0.00\n    0.0%"); self.portfolio_invested.setObjectName("portfolioStat")
        self.portfolio_positions=QLabel("●  Positions\n    0 offene Positionen\n    READ ONLY"); self.portfolio_positions.setObjectName("portfolioStatPurple")
        self.portfolio_cash=QLabel("●  Cash\n    $0.00\n    100.0%"); self.portfolio_cash.setObjectName("portfolioStatCyan")
        stats.addWidget(self.portfolio_invested); stats.addWidget(self.portfolio_positions); stats.addWidget(self.portfolio_cash)
        portfolio.layout().addLayout(stats)
        allocation=QFrame(); allocation.setObjectName("allocationBar"); allocation.setFixedHeight(15); portfolio.layout().addWidget(allocation)
        lower.addWidget(portfolio,34)

        right=QVBoxLayout(); right.setSpacing(16)
        news=self.section("International Market News · Preview")
        nh=QHBoxLayout(); nh.addStretch(1); nva=QLabel("View All  ›"); nva.setObjectName("viewAll"); nh.addWidget(nva); news.layout().insertLayout(1,nh)
        self.news_preview=QVBoxLayout(); news.layout().addLayout(self.news_preview)
        for badge,title,desc in [
            ("FED","Fed / macro news","News-Preview wird mit aktuellen Daten befüllt."),
            ("NASDAQ","US Tech","Markt- und Unternehmensmeldungen erscheinen hier."),
            ("BTC","Crypto","Relevante Krypto-Meldungen aus dem Bot-Snapshot."),
            ("EUROPE","Europe","Europäische Markt- und Zentralbankmeldungen."),
        ]:
            row=QFrame(); row.setObjectName("newsRow"); rl=QHBoxLayout(row); rl.setContentsMargins(0,8,0,8)
            thumb=QLabel(badge[:2]); thumb.setObjectName("newsThumb"); thumb.setAlignment(Qt.AlignCenter); thumb.setFixedSize(86,52)
            tx=QVBoxLayout(); tt=QLabel(title); tt.setObjectName("newsTitle"); dd=QLabel(desc); dd.setObjectName("newsDesc"); dd.setWordWrap(True); tx.addWidget(tt); tx.addWidget(dd)
            bg=QLabel(badge); bg.setObjectName("newsBadge"); bg.setAlignment(Qt.AlignCenter); bg.setFixedWidth(65)
            rl.addWidget(thumb); rl.addLayout(tx,1); rl.addWidget(bg); self.news_preview.addWidget(row)
        right.addWidget(news,3)

        bot=self.section("Bot Status"); bot.setObjectName("botStatusCard")
        br=QHBoxLayout(); orb=BotOrb(); br.addWidget(orb)
        info=QVBoxLayout(); self.dashboard_bot_state=QLabel("●  eToro REAL · LIVE"); self.dashboard_bot_state.setObjectName("liveBadge")
        self.dashboard_strategy=QLabel("🔒  AutoTrader → REAL gesperrt"); self.dashboard_strategy.setObjectName("botLine")
        self.dashboard_limits=QLabel("Strategie:  Research Engine 0.6.1"); self.dashboard_limits.setObjectName("botLine")
        self.dashboard_cycle=QLabel("◷  LIVE · wartet auf nächsten Zyklus"); self.dashboard_cycle.setObjectName("botLine")
        info.addWidget(self.dashboard_bot_state); info.addWidget(self.dashboard_strategy); info.addWidget(self.dashboard_limits); info.addWidget(self.dashboard_cycle)
        br.addLayout(info,1); view=QPushButton("View Bot  ›"); view.setObjectName("viewBot"); view.clicked.connect(lambda:self.set_page(1)); br.addWidget(view)
        bot.layout().addLayout(br); right.addWidget(bot,2)
        lower.addLayout(right,36)
        body.addLayout(lower,1)
        disclaimer=QLabel("ⓘ Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse."); disclaimer.setObjectName("disclaimer")
        body.addWidget(disclaimer)
        return w

    # ---------- Bot ----------
    def _page_bot(self):
        w, lay = self.page_shell("Bot", "Strategie, Kapitalgrenzen und echter Trading-Betrieb")
        top = QHBoxLayout()
        self.bot_status = QLabel("● STOPPED")
        self.bot_status.setObjectName("statusBig")
        top.addWidget(self.bot_status)
        top.addStretch(1)
        self.start_btn = QPushButton("BOT STARTEN")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_bot)
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        lay.addLayout(top)

        strategy_box = self.section("Handelsstufe")
        sl = strategy_box.layout()
        self.strategy_combo = QComboBox()
        for level in range(1, 5):
            self.strategy_combo.addItem(STRATEGIES[level][0], level)
        self.strategy_combo.setCurrentIndex(int(self.config["strategy_level"]) - 1)
        self.strategy_combo.currentIndexChanged.connect(self._strategy_changed)
        self.strategy_desc = QLabel()
        self.strategy_desc.setWordWrap(True)
        self.strategy_desc.setObjectName("muted")
        sl.addWidget(self.strategy_combo)
        sl.addWidget(self.strategy_desc)
        self._strategy_changed()
        lay.addWidget(strategy_box)

        limits = self.section("Kapital & Limits")
        g = QGridLayout()
        limits.layout().addLayout(g)
        self.max_capital = self.money_spin(0, 1_000_000, self.config["max_invested_usd"])
        self.position_size = self.money_spin(1, 1_000_000, self.config["position_size_usd"])
        self.max_trades = QSpinBox(); self.max_trades.setRange(0, 1000); self.max_trades.setValue(int(self.config["max_trades_per_day"]))
        self.max_positions = QSpinBox(); self.max_positions.setRange(1, 100); self.max_positions.setValue(int(self.config["max_total_positions"]))
        self.interval = QSpinBox(); self.interval.setRange(1, 120); self.interval.setValue(int(self.config["run_interval_minutes"])); self.interval.setSuffix(" min")
        fields = [
            ("Maximal investiertes Kapital", self.max_capital),
            ("Betrag pro Position", self.position_size),
            ("Maximale Trades pro Tag", self.max_trades),
            ("Maximal offene Positionen", self.max_positions),
            ("Analyse-Intervall", self.interval),
        ]
        for r, (label, widget) in enumerate(fields):
            g.addWidget(QLabel(label), r, 0)
            g.addWidget(widget, r, 1)
        save = QPushButton("Einstellungen speichern")
        save.setObjectName("primary")
        save.clicked.connect(self.save_bot_settings)
        g.addWidget(save, len(fields), 1)
        lay.addWidget(limits)

        activity = self.section("Current Activity")
        self.activity = QTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMinimumHeight(260)
        activity.layout().addWidget(self.activity)
        lay.addWidget(activity, 1)
        return w

    # ---------- Portfolio ----------
    def _page_portfolio(self):
        w, lay = self.page_shell("Portfolio", "Nur von TradePilot verwaltete Positionen werden hier markiert")
        self.portfolio_table = self.table(["Symbol", "Markt", "Typ", "Stufe", "Status", "Betrag USD", "Position-ID"])
        lay.addWidget(self.portfolio_table, 1)
        return w

    # ---------- Markets ----------
    def _page_markets(self):
        w, lay = self.page_shell("Markets", "Letzter Analyse-Snapshot der Trading Engine")
        self.markets_table = self.table(["Symbol", "Markt", "Typ", "Score", "Technik", "AI", "Final"])
        lay.addWidget(self.markets_table, 1)
        return w

    # ---------- News ----------
    def _page_news(self):
        w, lay = self.page_shell("News", "News-/Risikoauswertung aus dem letzten Bot-Lauf")
        self.news_text = QTextEdit(); self.news_text.setReadOnly(True)
        lay.addWidget(self.news_text, 1)
        return w

    # ---------- Backtest ----------
    def _page_backtest(self):
        w, lay = self.page_shell("Backtest", "Forschungsbereich – vom Echtgeld-Bot getrennt")
        box = self.section("Backtest Center")
        txt = QLabel(
            "Die bestehende TradePilot-Backtest-Forschung bleibt bewusst getrennt vom Echtgeld-Bot. "
            "In der nächsten Dev-Ausbaustufe binden wir die vorhandenen Backtest-Skripte hier als auswählbare Läufe ein."
        )
        txt.setWordWrap(True); txt.setObjectName("muted")
        box.layout().addWidget(txt)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    # ---------- Trades ----------
    def _page_trades(self):
        w, lay = self.page_shell("Trades", "Lokaler TradePilot-Tradeverlauf")
        self.trades_table = self.table(["Zeit", "Typ", "Symbol", "Betrag USD", "Status", "Grund"])
        lay.addWidget(self.trades_table, 1)
        return w

    # ---------- Settings ----------
    def _page_settings(self):
        w, lay = self.page_shell("Settings", "Trading-Modus, Darstellung und Sicherheitsstatus")
        broker = self.section("Broker")
        g = QGridLayout(); broker.layout().addLayout(g)
        g.addWidget(QLabel("eToro Trading Mode"), 0, 0)
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["REAL", "DEMO"])
        self.mode_combo.setCurrentText(str(self.config.get("trading_mode", "REAL")).upper())
        g.addWidget(self.mode_combo, 0, 1)
        self.connection_label = QLabel("Nicht getestet")
        self.connection_label.setObjectName("muted")
        g.addWidget(QLabel("Connection"), 1, 0); g.addWidget(self.connection_label, 1, 1)
        test = QPushButton("Verbindung beim nächsten Bot-Lauf prüfen")
        test.clicked.connect(lambda: self.activity.append("Connection wird beim nächsten Engine-Lauf geprüft."))
        g.addWidget(test, 2, 1)
        lay.addWidget(broker)

        appearance = self.section("Appearance")
        ag = QGridLayout(); appearance.layout().addLayout(ag)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(str(self.config.get("theme", "dark")))
        ag.addWidget(QLabel("Theme"), 0, 0); ag.addWidget(self.theme_combo, 0, 1)
        save = QPushButton("Settings speichern"); save.setObjectName("primary"); save.clicked.connect(self.save_settings)
        ag.addWidget(save, 1, 1)
        lay.addWidget(appearance)

        sec = self.section("Echtgeld-Sicherheit")
        note = QLabel(
            "REAL führt echte eToro-Orders aus. Zusätzlich verlangt die Engine weiterhin REAL_TRADING_CONFIRMATION=YES in der .env. "
            "STOP beendet keine bereits laufende Order-Anfrage abrupt; der aktuelle Zyklus darf sicher fertiglaufen."
        )
        note.setWordWrap(True); note.setObjectName("muted")
        sec.layout().addWidget(note)
        lay.addWidget(sec)
        lay.addStretch(1)
        return w

    # ---------- helpers ----------
    def section(self, title, subtitle=""):
        f = QFrame(); f.setObjectName("section")
        l = QVBoxLayout(f); l.setContentsMargins(20, 18, 20, 20); l.setSpacing(12)
        h = QLabel(title); h.setObjectName("sectionTitle"); l.addWidget(h)
        if subtitle:
            sh = QLabel(subtitle); sh.setObjectName("sectionSubtitle"); l.addWidget(sh)
        return f

    def table(self, columns):
        t = QTableWidget(0, len(columns))
        t.setHorizontalHeaderLabels(columns)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        return t

    def money_spin(self, lo, hi, value):
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setDecimals(2); s.setValue(float(value)); s.setSuffix(" USD"); s.setSingleStep(25.0)
        return s

    def _strategy_changed(self):
        level = int(self.strategy_combo.currentData()) if hasattr(self, "strategy_combo") else 1
        self.strategy_desc.setText(STRATEGIES[level][1])

    def save_bot_settings(self):
        self.config.update({
            "strategy_level": int(self.strategy_combo.currentData()),
            "max_invested_usd": float(self.max_capital.value()),
            "position_size_usd": float(self.position_size.value()),
            "max_trades_per_day": int(self.max_trades.value()),
            "max_total_positions": int(self.max_positions.value()),
            "run_interval_minutes": int(self.interval.value()),
        })
        if self.config["position_size_usd"] > self.config["max_invested_usd"] and self.config["max_invested_usd"] > 0:
            QMessageBox.warning(self, "TradePilot", "Der Betrag pro Position ist größer als das maximale Bot-Kapital. Neue Käufe wären dadurch blockiert.")
        save_json(CONFIG_FILE, self.config)
        self.activity.append("Bot-Einstellungen gespeichert.")
        self.refresh_all()

    def save_settings(self):
        self.config["trading_mode"] = self.mode_combo.currentText()
        self.config["theme"] = self.theme_combo.currentText()
        save_json(CONFIG_FILE, self.config)
        self.apply_theme()
        self.refresh_all()

    # ---------- Bot lifecycle ----------
    def start_bot(self):
        self.save_bot_settings()
        self.config["trading_mode"] = self.mode_combo.currentText() if hasattr(self, "mode_combo") else self.config.get("trading_mode", "REAL")
        mode = str(self.config["trading_mode"]).upper()
        if mode == "REAL":
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Echtgeld bestätigen")
            msg.setText("TradePilot wird im REAL-Modus gestartet. Echte eToro-Orders sind möglich.")
            msg.setInformativeText(
                f"Stufe {self.config['strategy_level']} · Max {self.config['max_trades_per_day']} Trades/Tag · "
                f"Max {self.config['max_invested_usd']:.2f} USD investiert · {self.config['position_size_usd']:.2f} USD je Position"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            msg.setDefaultButton(QMessageBox.Cancel)
            if msg.exec() != QMessageBox.Yes:
                return
        self.bot_requested = True
        self.config["bot_enabled"] = True
        save_json(CONFIG_FILE, self.config)
        self._update_bot_state()
        self._run_cycle()

    def stop_bot(self):
        self.bot_requested = False
        self.config["bot_enabled"] = False
        save_json(CONFIG_FILE, self.config)
        self.next_timer.stop()
        if self.process and self.process.state() != QProcess.NotRunning:
            self.activity.append("STOP angefordert: aktueller Trading-Zyklus läuft aus Sicherheitsgründen noch fertig. Kein neuer Zyklus wird gestartet.")
        self._update_bot_state()

    def _run_cycle(self):
        if not self.bot_requested:
            return
        if self.process and self.process.state() != QProcess.NotRunning:
            return
        if not ENGINE_FILE.exists():
            self.activity.append("FEHLER: bot_engine.py fehlt.")
            self.stop_bot(); return
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        env = self.process.processEnvironment()
        # QProcessEnvironment() may be empty in some bindings; use system env when needed.
        from PySide6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("TRADING_MODE", str(self.config.get("trading_mode", "REAL")).upper())
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._cycle_finished)
        self.activity.append("\n" + "=" * 72)
        self.activity.append(f"Bot-Zyklus gestartet · {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        self.process.start(sys.executable, [str(ENGINE_FILE)])
        self._update_bot_state(running=True)

    def _read_stdout(self):
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.activity.moveCursor(QTextCursor.End)
            self.activity.insertPlainText(data)
            if "Portfolio Zugriff: OK" in data:
                self.connection_label.setText("● Connected")

    def _read_stderr(self):
        data = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self.activity.append("\n[ENGINE STDERR]\n" + data)

    def _cycle_finished(self, code, status):
        self.activity.append(f"\nBot-Zyklus beendet · Exit-Code {code}")
        self.refresh_all()
        self._update_bot_state(running=False)
        if self.bot_requested:
            minutes = max(1, int(self.config.get("run_interval_minutes", 5)))
            self.activity.append(f"Nächster Zyklus in {minutes} Minute(n).")
            self.next_timer.start(minutes * 60 * 1000)

    def _update_bot_state(self, running=None):
        if running is None:
            running = bool(self.process and self.process.state() != QProcess.NotRunning)
        if running:
            self.bot_status.setText("● RUNNING")
        elif self.bot_requested:
            self.bot_status.setText("● ARMED · wartet auf nächsten Zyklus")
        else:
            self.bot_status.setText("● STOPPED")

    # ---------- data refresh ----------
    def _refresh_market_pills(self):
        now_et=datetime.now(ZoneInfo("America/New_York")); now_v=datetime.now(ZoneInfo("Europe/Vienna"))
        def state(market):
            if market in ("NYSE","NASDAQ"):
                opened=now_et.weekday()<5 and (now_et.hour*60+now_et.minute)>=570 and (now_et.hour*60+now_et.minute)<960
                return opened, "Open" if opened else "Closed", "US market session"
            opened=now_v.weekday()<5 and (now_v.hour*60+now_v.minute)>=540 and (now_v.hour*60+now_v.minute)<1050
            return opened, "Open" if opened else "Closed", "European session"
        for card,name in zip(getattr(self,"market_cards",[]),["NYSE","NASDAQ","XETRA"]):
            op,txt,detail=state(name); card.state.setText(txt); card.state.setObjectName("marketOpen" if op else "marketClosed"); card.detail.setText(detail); card.style().unpolish(card.state); card.style().polish(card.state)

    def mode_files(self):
        mode = str(self.config.get("trading_mode", "REAL")).upper()
        if mode == "DEMO":
            return ROOT / "etoro_demo_positions.json", ROOT / "etoro_demo_trades.json"
        return ROOT / "etoro_real_positions.json", ROOT / "etoro_real_trades.json"

    def refresh_all(self):
        mode = str(self.config.get("trading_mode", "REAL")).upper()
        self.mode_badge.setText(f"● {mode}")
        if hasattr(self,"market_clock"):
            try:
                et=datetime.now(ZoneInfo("America/New_York")); self.market_clock.setText(et.strftime("%-I:%M:%S %p") if os.name != "nt" else et.strftime("%I:%M:%S %p").lstrip("0")); self.market_date.setText(et.strftime("%b %d, %Y"))
            except Exception: pass
        if hasattr(self, "top_mode_pill"):
            self.top_mode_pill.setText(f"●  {mode} MODE")
        self._refresh_market_pills()
        pos_file, trades_file = self.mode_files()
        positions = load_json(pos_file, [])
        trades = load_json(trades_file, [])
        active = [p for p in positions if p.get("status") in ["OPEN", "PENDING", "CLOSING"]]
        invested = sum(float(p.get("amount_usd", 0) or 0) for p in active)
        budget = float(self.config.get("max_invested_usd", 0) or 0)
        available = max(0.0, budget - invested)
        snap = load_json(ROOT / "latest_analysis.json", {})
        acct = snap.get("account_summary", {}) if isinstance(snap, dict) else {}
        broker_cash = acct.get("broker_cash_usd")
        display_cash = float(broker_cash) if broker_cash is not None else available
        portfolio_total = display_cash + invested
        self.card_cash.value.setText(f"${display_cash:,.2f}")
        self.card_cash.sub_left.setText("Buying Power")
        self.card_cash.sub_right.setText(f"${display_cash:,.2f}")
        self.card_invested.value.setText(f"${invested:,.2f}")
        self.card_invested.sub_left.setText(f"{len(active)} offene Positionen")
        self.card_invested.sub_right.setText(f"{(invested/portfolio_total*100 if portfolio_total else 0):.1f}% of Portfolio")
        self.card_value.value.setText(f"${portfolio_total:,.2f}")
        self.card_value.sub_left.setText(f"eToro {mode} · LIVE")
        self.card_value.sub_right.setText(f"${portfolio_total:,.2f}")
        risk = snap.get("risk_state", {}) if isinstance(snap, dict) else {}
        today_pnl = risk.get("today_total_approx_usd")
        if today_pnl is None:
            self.card_today.value.setText("—")
        else:
            self.card_today.value.setText(f"${float(today_pnl):+,.2f}")
        self.card_today.sub_left.setText("—" if today_pnl is None else "Today P/L")
        self.card_today.sub_right.setText("")
        if hasattr(self,"portfolio_value_big"):
            self.portfolio_value_big.setText(f"${portfolio_total:,.2f}")
            self.portfolio_chart.set_value(portfolio_total)
            pct=(invested/portfolio_total*100 if portfolio_total else 0)
            self.portfolio_invested.setText(f"●  Invested\n    ${invested:,.2f}\n    {pct:.1f}%")
            self.portfolio_positions.setText(f"●  Positions\n    {len(active)} offene Positionen\n    READ ONLY")
            self.portfolio_cash.setText(f"●  Cash\n    ${display_cash:,.2f}\n    {(display_cash/portfolio_total*100 if portfolio_total else 0):.1f}%")

        if hasattr(self, "dashboard_bot_state"):
            if self.process and self.process.state() != QProcess.NotRunning:
                state_txt="RUNNING"
            elif self.bot_requested:
                state_txt="ARMED"
            else:
                state_txt="STOPPED"
            self.dashboard_bot_state.setText(f"●  eToro {mode} · LIVE")
            level = int(self.config.get("strategy_level", 1))
            self.dashboard_strategy.setText(f"🔒  AutoTrader → {state_txt}")
            self.dashboard_limits.setText(f"Strategie:  {STRATEGIES.get(level, STRATEGIES[1])[0]}")
            self.dashboard_cycle.setText(f"◷  {int(self.config.get('run_interval_minutes',5))} Min. Zyklus · {int(self.config.get('max_trades_per_day',0))} Trades/Tag · ${float(self.config.get('max_invested_usd',0)):,.0f} max")

        self._fill_open_positions_dashboard(self.dashboard_positions, active)
        self._fill_positions(self.portfolio_table, positions, short=False)
        self._fill_trades(self.dashboard_trades, trades[-8:], short=True)
        self._fill_trades(self.trades_table, trades[-200:], short=False)
        self._refresh_snapshot()
        self._update_bot_state()

    def _today_trade_text(self, trades):
        today = datetime.now().date().isoformat()
        n = 0
        for t in trades:
            if t.get("type") not in ["BUY_CONFIRMED", "BUY_REQUEST_PENDING"]:
                continue
            if str(t.get("time", ""))[:10] == today:
                n += 1
        return f"{n} / {int(self.config.get('max_trades_per_day', 0))}"

    def _fill_open_positions_dashboard(self, table, positions):
        rows=list(reversed(positions[-100:])); table.setRowCount(len(rows))
        if not rows:
            table.setRowCount(1); table.setSpan(0,0,1,4); item=QTableWidgetItem("Keine offenen eToro-Positionen."); item.setFlags(Qt.ItemIsEnabled); table.setItem(0,0,item); return
        for r,p in enumerate(rows):
            vals=[p.get("symbol","-"), "BUY", f"${float(p.get('amount_usd',0) or 0):.2f}", str(p.get("entry_time","-"))[11:19]]
            for c,v in enumerate(vals): table.setItem(r,c,QTableWidgetItem(str(v)))

    def _fill_positions(self, table, positions, short=False):
        rows = list(reversed(positions[-100:]))
        table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            if short:
                vals = [p.get("symbol", "-"), str(p.get("strategy_level", "-")), p.get("status", "-"), f"${float(p.get('amount_usd',0) or 0):.2f}"]
            else:
                vals = [p.get("symbol","-"), p.get("market","-"), p.get("asset_type","-"), str(p.get("strategy_level","-")), p.get("status","-"), f"{float(p.get('amount_usd',0) or 0):.2f}", str(p.get("position_id","-"))]
            for c, v in enumerate(vals): table.setItem(r, c, QTableWidgetItem(str(v)))

    def _fill_trades(self, table, trades, short=False):
        rows = list(reversed(trades))
        table.setRowCount(len(rows))
        for r, t in enumerate(rows):
            if short:
                vals = [str(t.get("time","-"))[:19], t.get("symbol","-"), t.get("type","-"), f"{float(t.get('amount_usd',0) or 0):.2f}" if t.get("amount_usd") is not None else "-", t.get("status","-")]
            else:
                vals = [str(t.get("time","-"))[:19], t.get("type","-"), t.get("symbol","-"), f"{float(t.get('amount_usd',0) or 0):.2f}" if t.get("amount_usd") is not None else "-", t.get("status","-"), t.get("reason", t.get("error_message","-"))]
            for c, v in enumerate(vals): table.setItem(r, c, QTableWidgetItem(str(v)))

    def _refresh_snapshot(self):
        snap = load_json(ROOT / "latest_analysis.json", {})
        results = snap.get("results", snap.get("analysis", [])) if isinstance(snap, dict) else []
        if not isinstance(results, list): results = []
        self.markets_table.setRowCount(len(results))
        news_lines = []
        for r, x in enumerate(results):
            vals = [x.get("symbol","-"), x.get("market","-"), x.get("asset_type","-"), x.get("total_score","-"), x.get("technical_signal","-"), f"{x.get('ai_signal','-')} {x.get('ai_confidence',0)}%", x.get("final_signal","-")]
            for c, v in enumerate(vals): self.markets_table.setItem(r, c, QTableWidgetItem(str(v)))
            if x.get("news_summary") or x.get("news_risk"):
                news_lines.append(f"{x.get('symbol','-')} · Risk {x.get('news_risk','-')} · Score {x.get('news_score','-')}\n{x.get('news_summary','')}\n")
        self.news_text.setPlainText("\n".join(news_lines) if news_lines else "Noch keine News-Auswertung im aktuellen Snapshot vorhanden.")

    # ---------- theme ----------
    def apply_theme(self):
        c = DARK if self.config.get("theme", "dark") == "dark" else LIGHT
        # The exact dashboard reference is dark-first. Light uses the same geometry/components.
        self.setStyleSheet(f"""
        QWidget {{ background:{c['bg']}; color:{c['text']}; font-family:'Segoe UI'; font-size:10pt; }}
        QMainWindow {{ background:{c['bg']}; }}
        #sidebar {{ background:#03101A; border-right:1px solid #183246; }}
        #logoMark {{ color:#7C67FF; background:transparent; font-size:20pt; font-weight:900; font-style:italic; }}
        #brand {{ font-size:18pt; font-weight:750; }}
        #brandSub {{ color:#5F86A6; font-size:7.5pt; }}
        #topbar {{ background:#020D17; border-bottom:1px solid #183246; }}
        #pageTitle {{ font-size:22pt; font-weight:750; }} #pageSubtitle {{ color:#7290A9; }}
        #marketStatus {{ background:#071522; border:1px solid #7C2533; border-radius:13px; }}
        #marketName {{ font-size:9pt; font-weight:700; color:#F0F4FA; }}
        #marketName::first-letter {{ color:#EF476F; }}
        #marketClosed {{ color:#FF526D; font-weight:700; font-size:8pt; }} #marketOpen {{ color:#1FE083; font-weight:700; font-size:8pt; }}
        #marketDetail {{ color:#55728C; font-size:7pt; }}
        #topIcon {{ color:#A8BED0; font-size:27pt; background:transparent; }}
        #profileIcon {{ color:#A8BED0; font-size:37pt; border:1px solid #31526B; border-radius:31px; background:#071522; }}
        #nav {{ text-align:left; padding:14px 20px; min-height:34px; border:none; border-radius:12px; color:#ADC1D2; background:transparent; font-size:10.5pt; }}
        #nav:hover {{ background:#081B2A; color:white; }}
        #nav:checked {{ background:#0B2A40; color:white; border:1px solid #1F6C9E; border-left:5px solid #1BAAF5; font-weight:650; }}
        #marketClockBox {{ background:#071724; border:1px solid #1D4A67; border-radius:14px; }} #marketClockTitle,#marketDate {{ color:#7290A9; font-size:8pt; }}
        #marketClock {{ font-size:17pt; font-weight:650; }} #onlineText {{ color:#19D77D; font-size:7pt; }} #sideFooter {{ color:#42617A; font-size:7pt; }}
        #modeBadge {{ background:transparent; border:none; color:#19D77D; font-size:8pt; }}
        #kpiCard,#section {{ background:#071723; border:1px solid #20445E; border-radius:15px; }}
        #kpiTitle {{ font-size:11pt; color:#F1F5F9; }} #kpiValue {{ font-size:23pt; font-weight:700; }} #kpiSub {{ color:#76A0BD; font-size:8pt; }}
        #kpiIcon {{ background:#09263A; border:1px solid #14567E; border-radius:13px; color:#23AAF3; font-size:19pt; font-weight:700; }}
        #sectionTitle {{ font-size:11.5pt; font-weight:700; }} #sectionSubtitle,#muted,#tinyMuted {{ color:#64829A; }} #tinyMuted {{font-size:7pt;}}
        #viewAll {{ color:#32A9FF; font-size:8pt; }}
        #portfolioBig {{ font-size:20pt; font-weight:650; }} #goodText {{ color:#1FDF80; font-size:8pt; }}
        #periodBtn,#chartTab {{ background:#071723; border:1px solid #20445E; border-radius:8px; color:#A9BED0; padding:7px 13px; font-size:8pt; }} #chartTab:hover,#periodBtn:hover {{ border-color:#1BAAF5; }}
        #portfolioStat,#portfolioStatPurple,#portfolioStatCyan {{ color:#A9BED0; font-size:8.5pt; line-height:1.5; }} #portfolioStat {{ color:#80AACA; }} #portfolioStatPurple {{ color:#B39BFF; }} #portfolioStatCyan {{ color:#6DDDE4; }}
        #allocationBar {{ background:#2EC6CE; border-radius:5px; }}
        #newsRow {{ border-bottom:1px solid #173247; }} #newsThumb {{ background:#12334A; color:#59C4FF; border-radius:3px; font-weight:800; font-size:12pt; }}
        #newsTitle {{ font-weight:650; font-size:8.5pt; }} #newsDesc {{ color:#7593AA; font-size:7pt; }} #newsBadge {{ background:#0B5790; border-radius:7px; padding:4px; color:white; font-size:7pt; font-weight:700; }}
        #botStatusCard {{ background:#06221E; border:1px solid #126A4B; border-radius:15px; border-bottom:3px solid #15D978; }}
        #liveBadge {{ background:#084C38; border:1px solid #16905E; border-radius:9px; color:#24E98A; padding:9px 12px; font-weight:700; }} #botLine {{ color:#82A0B6; font-size:8pt; }}
        #viewBot {{ background:#071D2C; border:1px solid #2B6688; border-radius:9px; padding:10px 16px; color:#D7E4ED; }}
        #disclaimer {{ color:#4C6A82; font-size:7pt; }}
        QPushButton {{ background:#0C1D2B; border:1px solid #234056; border-radius:8px; padding:9px 13px; }} QPushButton:hover {{ border-color:#1BAAF5; }}
        #primary {{ background:#1E73E8; color:white; border:none; font-weight:700; }} #danger {{ background:#A83244; color:white; border:none; font-weight:700; }}
        QComboBox,QSpinBox,QDoubleSpinBox,QLineEdit {{ background:#0C1D2B; border:1px solid #234056; border-radius:8px; padding:8px 10px; min-height:25px; }}
        QTextEdit,QTableWidget {{ background:transparent; border:none; gridline-color:#173247; }}
        QTableWidget::item {{ padding:8px; border-bottom:1px solid #173247; color:#9BB6C9; }} QTableWidget::item:selected {{ background:#0A2A40; color:white; }}
        QHeaderView::section {{ background:transparent; color:#7899B2; border:none; border-bottom:1px solid #21455E; padding:9px 5px; font-size:8pt; }}
        QScrollBar:vertical {{ background:transparent; width:9px; }} QScrollBar::handle:vertical {{ background:#1D3C51; border-radius:4px; min-height:30px; }}
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = TradePilotWindow()
    win.show()
    sys.exit(app.exec())
