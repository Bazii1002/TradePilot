import json
import os
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QGridLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QMessageBox, QLineEdit, QCheckBox, QScrollArea
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

        self.setWindowTitle("TradePilot Desktop Alpha 0.10.1 · UI Redesign")
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
        self.sidebar.setFixedWidth(238)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 24, 16, 18)
        side.setSpacing(8)
        brand_row = QHBoxLayout()
        logo = QLabel("TP")
        logo.setObjectName("logoMark")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(42, 42)
        brand_box = QVBoxLayout()
        brand = QLabel("TradePilot")
        brand.setObjectName("brand")
        version = QLabel("DESKTOP  ·  ALPHA 0.10.1")
        version.setObjectName("brandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(version)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_box)
        side.addLayout(brand_row)
        side.addSpacing(26)

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
        self.mode_badge = QLabel()
        self.mode_badge.setObjectName("modeBadge")
        side.addWidget(self.mode_badge)

        shell.addWidget(self.sidebar)
        shell.addWidget(self.stack, 1)
        self.set_page(0)

    def page_shell(self, title, subtitle=""):
        outer = QWidget()
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(34, 26, 34, 28)
        lay.setSpacing(20)

        row = QHBoxLayout()
        row.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        h = QLabel(title)
        h.setObjectName("pageTitle")
        title_box.addWidget(h)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("pageSubtitle")
            title_box.addWidget(s)
        row.addLayout(title_box)
        row.addStretch(1)

        self.nyse_pill = QLabel()
        self.nyse_pill.setObjectName("marketPill")
        self.nasdaq_pill = QLabel()
        self.nasdaq_pill.setObjectName("marketPill")
        self.top_mode_pill = QLabel()
        self.top_mode_pill.setObjectName("modeTopPill")
        row.addWidget(self.nyse_pill)
        row.addWidget(self.nasdaq_pill)
        row.addWidget(self.top_mode_pill)
        lay.addLayout(row)
        return outer, lay

    def set_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
        self.refresh_all()

    # ---------- Dashboard ----------
    def _page_dashboard(self):
        w, lay = self.page_shell("Dashboard", "Portfolio, Bot und Marktaktivität auf einen Blick")

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        self.card_cash = Card("Cash Available", subtitle="Available for TradePilot")
        self.card_invested = Card("Invested", subtitle="Open TradePilot positions")
        self.card_value = Card("Portfolio Value", subtitle="TradePilot capital")
        self.card_today = Card("Today", subtitle="Current session")
        for i, c in enumerate([self.card_cash, self.card_invested, self.card_value, self.card_today]):
            grid.addWidget(c, 0, i)
        lay.addLayout(grid)

        lower = QGridLayout()
        lower.setHorizontalSpacing(14)
        lower.setVerticalSpacing(14)

        recent = self.section("Recent Trades", "Latest bot activity")
        self.dashboard_trades = self.table(["Zeit", "Symbol", "Aktion", "Betrag", "Status"])
        recent.layout().addWidget(self.dashboard_trades)
        lower.addWidget(recent, 0, 0, 2, 1)

        overview = self.section("Portfolio Overview", "Open and pending TradePilot positions")
        self.dashboard_positions = self.table(["Symbol", "Stufe", "Status", "Betrag"])
        overview.layout().addWidget(self.dashboard_positions)
        lower.addWidget(overview, 0, 1)

        status = self.section("Bot Status", "Current trading configuration")
        self.dashboard_bot_state = QLabel("Stopped")
        self.dashboard_bot_state.setObjectName("statusHero")
        self.dashboard_strategy = QLabel("Strategy · –")
        self.dashboard_strategy.setObjectName("metricLine")
        self.dashboard_limits = QLabel("Limits · –")
        self.dashboard_limits.setObjectName("metricLine")
        self.dashboard_cycle = QLabel("Cycle · –")
        self.dashboard_cycle.setObjectName("metricLine")
        status.layout().addWidget(self.dashboard_bot_state)
        status.layout().addWidget(self.dashboard_strategy)
        status.layout().addWidget(self.dashboard_limits)
        status.layout().addWidget(self.dashboard_cycle)
        status.layout().addStretch(1)
        lower.addWidget(status, 1, 1)

        lower.setColumnStretch(0, 3)
        lower.setColumnStretch(1, 2)
        lower.setRowStretch(0, 3)
        lower.setRowStretch(1, 2)
        lay.addLayout(lower, 1)
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
        try:
            now = datetime.now(ZoneInfo("America/New_York"))
            weekday = now.weekday() < 5
            minutes = now.hour * 60 + now.minute
            open_now = weekday and (9 * 60 + 30 <= minutes < 16 * 60)
            state = "OPEN" if open_now else "CLOSED"
        except Exception:
            state = "—"
        if hasattr(self, "nyse_pill"):
            self.nyse_pill.setText(f"●  NYSE  {state}")
        if hasattr(self, "nasdaq_pill"):
            self.nasdaq_pill.setText(f"●  NASDAQ  {state}")

    def mode_files(self):
        mode = str(self.config.get("trading_mode", "REAL")).upper()
        if mode == "DEMO":
            return ROOT / "etoro_demo_positions.json", ROOT / "etoro_demo_trades.json"
        return ROOT / "etoro_real_positions.json", ROOT / "etoro_real_trades.json"

    def refresh_all(self):
        mode = str(self.config.get("trading_mode", "REAL")).upper()
        self.mode_badge.setText(f"● {mode}")
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
        self.card_cash.value.setText(f"${available:,.2f}")
        self.card_cash.sub.setText("TradePilot budget available")
        self.card_invested.value.setText(f"${invested:,.2f}")
        self.card_invested.sub.setText(f"Limit ${budget:,.2f}")
        self.card_value.value.setText(f"${budget:,.2f}")
        self.card_value.sub.setText("Configured bot capital")
        snap = load_json(ROOT / "latest_analysis.json", {})
        risk = snap.get("risk_state", {}) if isinstance(snap, dict) else {}
        today_pnl = risk.get("today_total_approx_usd")
        if today_pnl is None:
            self.card_today.value.setText("–")
        else:
            self.card_today.value.setText(f"${float(today_pnl):+,.2f}")
        self.card_today.sub.setText(f"Trades today {self._today_trade_text(trades)}")

        if hasattr(self, "dashboard_bot_state"):
            if self.process and self.process.state() != QProcess.NotRunning:
                self.dashboard_bot_state.setText("● RUNNING")
            elif self.bot_requested:
                self.dashboard_bot_state.setText("● ARMED")
            else:
                self.dashboard_bot_state.setText("● STOPPED")
            level = int(self.config.get("strategy_level", 1))
            self.dashboard_strategy.setText(f"Strategy  ·  {STRATEGIES.get(level, STRATEGIES[1])[0]}")
            self.dashboard_limits.setText(f"Limits  ·  {int(self.config.get('max_trades_per_day',0))} trades/day  ·  ${float(self.config.get('max_invested_usd',0)):,.0f} max")
            self.dashboard_cycle.setText(f"Cycle  ·  every {int(self.config.get('run_interval_minutes',5))} min")

        self._fill_positions(self.dashboard_positions, active, short=True)
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
        self.setStyleSheet(f"""
        QWidget {{ background:{c['bg']}; color:{c['text']}; font-family:'Segoe UI'; font-size:10pt; }}
        QMainWindow {{ background:{c['bg']}; }}
        #sidebar {{ background:{c['sidebar']}; border-right:1px solid {c['border']}; }}
        #logoMark {{ background:{c['accent']}; color:white; border-radius:11px; font-weight:800; font-size:11pt; }}
        #brand {{ font-size:18pt; font-weight:750; letter-spacing:-0.4px; }}
        #brandSub {{ color:{c['muted']}; font-size:7.5pt; font-weight:650; letter-spacing:1.2px; }}
        #pageTitle {{ font-size:24pt; font-weight:750; letter-spacing:-0.6px; }}
        #pageSubtitle, #sectionSubtitle, #muted {{ color:{c['muted']}; }}
        #pageSubtitle {{ font-size:9.5pt; }}
        #section {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:14px; }}
        #card {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:14px; min-height:104px; }}
        #sectionTitle {{ font-size:11.5pt; font-weight:700; }}
        #sectionSubtitle {{ font-size:8.5pt; margin-bottom:2px; }}
        #cardTitle {{ color:{c['muted']}; font-size:8.5pt; font-weight:650; letter-spacing:0.8px; }}
        #cardValue {{ font-size:22pt; font-weight:760; letter-spacing:-0.7px; }}
        #nav {{ text-align:left; padding:12px 15px; border:none; border-radius:10px; color:{c['muted']}; background:transparent; font-weight:550; }}
        #nav:hover {{ background:{c['panel2']}; color:{c['text']}; }}
        #nav:checked {{ background:{c['panel2']}; color:{c['text']}; font-weight:700; border-left:3px solid {c['accent']}; padding-left:12px; }}
        #primary {{ background:{c['accent']}; color:white; border:none; border-radius:9px; padding:11px 18px; font-weight:700; }}
        #primary:hover {{ background:{c['accent2']}; }}
        #danger {{ background:{c['bad']}; color:white; border:none; border-radius:9px; padding:11px 18px; font-weight:700; }}
        #modeBadge {{ background:{c['panel2']}; border:1px solid {c['border']}; border-radius:10px; padding:10px 12px; color:{c['good']}; font-weight:700; }}
        #marketPill {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:13px; padding:8px 12px; color:{c['muted']}; font-size:8.5pt; font-weight:650; }}
        #modeTopPill {{ background:{c['panel2']}; border:1px solid {c['border']}; border-radius:13px; padding:8px 12px; color:{c['accent2']}; font-size:8.5pt; font-weight:750; }}
        #statusBig {{ font-size:13pt; font-weight:750; color:{c['good']}; }}
        #statusHero {{ font-size:17pt; font-weight:750; color:{c['good']}; padding:3px 0 8px 0; }}
        #metricLine {{ background:{c['panel2']}; border:1px solid {c['border']}; border-radius:8px; padding:9px 11px; color:{c['muted']}; }}
        QPushButton {{ background:{c['panel2']}; border:1px solid {c['border']}; border-radius:8px; padding:9px 13px; }}
        QPushButton:hover {{ border-color:{c['accent']}; }}
        QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{ background:{c['panel2']}; border:1px solid {c['border']}; border-radius:8px; padding:8px 10px; min-height:25px; selection-background-color:{c['accent']}; }}
        QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{ border-color:{c['accent']}; }}
        QTextEdit, QTableWidget {{ background:{c['panel']}; border:none; border-radius:9px; gridline-color:{c['border']}; alternate-background-color:{c['panel2']}; }}
        QTableWidget::item {{ padding:8px; border-bottom:1px solid {c['border']}; }}
        QTableWidget::item:selected {{ background:{c['panel3']}; color:{c['text']}; }}
        QHeaderView::section {{ background:{c['panel2']}; color:{c['muted']}; border:none; border-bottom:1px solid {c['border']}; padding:10px 8px; font-weight:700; }}
        QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
        QScrollBar::handle:vertical {{ background:{c['border']}; border-radius:5px; min-height:30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = TradePilotWindow()
    win.show()
    sys.exit(app.exec())
