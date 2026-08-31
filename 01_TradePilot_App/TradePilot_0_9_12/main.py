from __future__ import annotations

import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tradepilot_engine import analyse_daten, wert
from app_config import load_config, save_config
from i18n import tr, set_language, translate_status, language
from themes import set_theme, c, build_qss
from strategy_engine import evaluate_strategy
from risk_manager import calculate_position, RISK_LIMITS
from paper_broker import PaperBroker
from etoro_broker import EtoroLiveBroker, EtoroError
from exit_engine import evaluate_exit, EXIT_RULES
from autotrader_universe import universe_symbols
from market_regime import get_market_regime, market_profile_filter
from earnings_guard import get_earnings_info, earnings_profile_filter
from portfolio_guard import evaluate_portfolio_guard
from autotrader_log import AutoTraderLog
from market_data import get_latest_quote
from order_engine import validate_pending_execution, quote_is_executable
from portfolio_guard import LIMITS as PORTFOLIO_LIMITS
from performance_engine import performance_metrics, risk_overview, position_rows, sector_exposure, candidate_position_plan
from exchange_status import all_exchange_statuses, format_countdown

from tradepilot_storage import (
    load_watchlist,
    merge_analysis,
    save_watchlist,
    watchlist_path,
)


VERSION = "0.9.12"
APP_DIR = Path(__file__).resolve().parent


def migrate_persistent_state(app_dir: Path) -> None:
    """Carry local settings/paper state forward from the previous project folder.

    Every development version lives in its own folder. Without migration, a new
    version would appear to have an empty paper account. Only local state files
    are copied; application source code is never mixed between versions.
    """
    candidates = [
        "TradePilot_0_9_10",
        "TradePilot_0_9_9",
        "TradePilot_0_9_8",
        "TradePilot_0_9_7_1",
        "TradePilot_0_9_7",
        "TradePilot_0_9_6",
        "TradePilot_0_9_4",
    ]
    files = [
        "tradepilot_settings.json",
        "tradepilot_paper_portfolio.json",
        "tradepilot_autotrader_log.jsonl",
    ]
    for filename in files:
        target = app_dir / filename
        if target.exists():
            continue
        for folder in candidates:
            source = app_dir.parent / folder / filename
            if source.exists():
                try:
                    shutil.copy2(source, target)
                except Exception:
                    pass
                break


migrate_persistent_state(APP_DIR)
INITIAL_CONFIG = load_config(APP_DIR)
set_theme(INITIAL_CONFIG.get("theme", "dark"))
set_language(INITIAL_CONFIG.get("language", "de"))

# -----------------------------------------------------------------------------
# Designsystem
# -----------------------------------------------------------------------------
BLUE = "#2678ff"
BLUE_2 = "#4e98ff"
GREEN = "#38d98a"
YELLOW = "#f1b83f"
ORANGE = "#ff9b37"
RED = "#ff5f66"

def refresh_theme_tokens():
    global BG, SIDEBAR, SURFACE, SURFACE_2, SURFACE_3, BORDER, BORDER_SOFT, TEXT, TEXT_2, TEXT_3, QSS
    BG = c("bg")
    SIDEBAR = c("sidebar")
    SURFACE = c("surface")
    SURFACE_2 = c("surface2")
    SURFACE_3 = c("surface3")
    BORDER = c("border")
    BORDER_SOFT = c("border")
    TEXT = c("text")
    TEXT_2 = c("muted")
    TEXT_3 = c("subtle")
    QSS = build_qss(BLUE, BLUE_2, GREEN, RED)

refresh_theme_tokens()

def score_color(score: int | float | None, inverse: bool = False) -> str:
    if score is None:
        return TEXT_2
    try:
        s = float(score)
    except Exception:
        return TEXT_2
    if inverse:
        if s < 20: return GREEN
        if s < 40: return YELLOW
        if s < 60: return ORANGE
        return RED
    if s >= 80: return GREEN
    if s >= 65: return "#5fd592"
    if s >= 50: return YELLOW
    if s >= 35: return ORANGE
    return RED

def status_color(status: str) -> str:
    s = (status or "").upper()
    if "INTERESSANT" in s or "INTERESTING" in s: return GREEN
    if "BEOBACHTEN" in s or s == "WATCH": return YELLOW
    if "RISIK" in s or "RISKY" in s or "KEIN EINSTIEG" in s or "NO ENTRY" in s: return RED
    return TEXT_2

def pct(value, digits=1, signed=False) -> str:
    if value is None: return "—"
    try:
        value = float(value)
        if math.isnan(value): return "—"
    except Exception:
        return "—"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.{digits}f}%"

def _finite(value, default=None):
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default

def ratio_percent(value, digits=1) -> str:
    value = _finite(value)
    if value is None: return "—"
    return f"{value * 100:.{digits}f}%"

def number(value, digits=1) -> str:
    value = _finite(value)
    if value is None: return "—"
    return f"{value:.{digits}f}"

def loc(de: str, en: str) -> str:
    return en if language() == "en" else de

def valid_price(data: dict | None):
    data = data or {}
    price = _finite((data.get("trend") or {}).get("kurs"))
    if price is not None and price > 0:
        return price
    try:
        close = data.get("historie")["Close"].dropna()
        for value in reversed(close.tolist()):
            price = _finite(value)
            if price is not None and price > 0:
                return price
    except Exception:
        pass
    return None

def price_text(data: dict) -> str:
    kurs = valid_price(data)
    if kurs is None:
        return loc("Kurs nicht verfügbar", "Price unavailable")
    raw = f"{kurs:,.2f}"
    if language() == "de":
        raw = raw.replace(",", "X").replace(".", ",").replace("X", ".")
    currency = str(data.get("waehrung", "") or "").strip()
    return f"{raw} {currency}".strip()


def order_reason_text(code: str) -> str:
    de={
        "WAITING_FOR_FRESH_MARKET_QUOTE":"Wartet auf frischen Marktkurs", "MARKET_CLOSED":"Markt geschlossen",
        "STALE_QUOTE":"Kurs nicht frisch genug", "PRICE_GAP_TOO_LARGE":"Kursabweichung zu groß – neuer Scan nötig",
        "ORDER_EXPIRED":"Order abgelaufen", "CASH_RESERVE":"Cashreserve würde unterschritten",
        "MAX_SECTOR_EXPOSURE":"Sektorlimit erreicht", "MAX_PORTFOLIO_INVESTMENT":"Investitionslimit erreicht",
        "MAX_POSITIONS":"Maximale Positionen erreicht", "NOT_ENOUGH_CASH":"Nicht genug Cash", "MAX_TRADE_VALUE":"Maximalbetrag pro Trade erreicht",
        "SIGNAL_NO_LONGER_READY":"Signal nicht mehr freigegeben", "POSITION_EXISTS":"Position bereits offen",
        "NO_POSITION":"Keine offene Position", "FILLED":"Ausgeführt",
    }
    en={
        "WAITING_FOR_FRESH_MARKET_QUOTE":"Waiting for fresh market quote", "MARKET_CLOSED":"Market closed",
        "STALE_QUOTE":"Quote not fresh enough", "PRICE_GAP_TOO_LARGE":"Price gap too large – new scan required",
        "ORDER_EXPIRED":"Order expired", "CASH_RESERVE":"Cash reserve would be breached",
        "MAX_SECTOR_EXPOSURE":"Sector limit reached", "MAX_PORTFOLIO_INVESTMENT":"Investment limit reached",
        "MAX_POSITIONS":"Maximum positions reached", "NOT_ENOUGH_CASH":"Not enough cash", "MAX_TRADE_VALUE":"Max trade value reached",
        "SIGNAL_NO_LONGER_READY":"Signal no longer ready", "POSITION_EXISTS":"Position already open",
        "NO_POSITION":"No open position", "FILLED":"Filled",
    }
    return (en if language()=="en" else de).get(str(code or ""), str(code or "—"))


def strategy_reason_text(result: dict) -> str:
    """Human-readable reason for WAIT/REJECT/BLOCKED without changing strategy logic."""
    if not result:
        return loc("Keine Strategiedaten", "No strategy data")
    hard = list(result.get("hard_blocks", []) or [])
    hard_map_de = {"EXTREME_TRAP":"extremes Value-Trap-Risiko", "VERY_WEAK_COMPANY":"Unternehmensscore zu schwach", "VERY_LOW_QUALITY":"Qualität zu niedrig"}
    hard_map_en = {"EXTREME_TRAP":"extreme value-trap risk", "VERY_WEAK_COMPANY":"company score too weak", "VERY_LOW_QUALITY":"quality too low"}
    if hard:
        mapping = hard_map_en if language() == "en" else hard_map_de
        return " · ".join(mapping.get(x, x) for x in hard[:2])

    names_de = {"company":"U-Score", "entry":"Einstieg", "trap":"Value-Trap", "quality":"Qualität", "development":"Entwicklung", "valuation":"Bewertung", "trend":"Trend"}
    names_en = {"company":"Company", "entry":"Entry", "trap":"Value trap", "quality":"Quality", "development":"Development", "valuation":"Valuation", "trend":"Trend"}
    names = names_en if language() == "en" else names_de
    missing = []
    for check in result.get("checks", []) or []:
        if check.get("ok"):
            continue
        key = check.get("key", "")
        value = _finite(check.get("value"), 0) or 0
        target = _finite(check.get("target"), 0) or 0
        if check.get("mode") == "max":
            missing.append(f"{names.get(key,key)} {value:.0f} ≥ {target:.0f}")
        else:
            missing.append(f"{names.get(key,key)} {value:.0f} < {target:.0f}")
    if missing:
        return " · ".join(missing[:3])
    return loc("Strategiekriterien noch nicht erfüllt", "Strategy criteria not met")

# -----------------------------------------------------------------------------
# Hintergrundarbeit
# -----------------------------------------------------------------------------
class AnalysisThread(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol

    def run(self):
        try:
            self.result.emit(analyse_daten(self.symbol))
        except Exception as exc:
            self.error.emit(str(exc))


class WatchlistRefreshThread(QThread):
    item_ready = Signal(object)
    progress = Signal(str)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, symbols: list[str]):
        super().__init__()
        self.symbols = symbols

    def run(self):
        total = len(self.symbols)
        for idx, symbol in enumerate(self.symbols, start=1):
            self.progress.emit(f"Watchlist wird aktualisiert · {idx}/{total} · {symbol}")
            try:
                self.item_ready.emit(analyse_daten(symbol))
            except Exception as exc:
                self.failed.emit(symbol, str(exc))
        self.done.emit()


class QuoteRefreshThread(QThread):
    quote_ready = Signal(str, object)
    failed = Signal(str, str)
    done = Signal(int, int)

    def __init__(self, symbols: list[str]):
        super().__init__()
        self.symbols = [str(x).upper() for x in symbols if str(x).strip()]
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        ok = 0
        failed = 0
        for symbol in self.symbols:
            if self._stop_requested:
                break
            try:
                quote = get_latest_quote(symbol)
                ok += 1
                self.quote_ready.emit(symbol, quote)
            except Exception as exc:
                failed += 1
                self.failed.emit(symbol, str(exc))
        self.done.emit(ok, failed)


class AutoTraderScanThread(QThread):
    item_ready = Signal(object)
    failed = Signal(str, str)
    progress = Signal(int, int, str)
    market_ready = Signal(object)
    done = Signal()

    def __init__(self, symbols: list[str], profile: str = "balanced"):
        super().__init__()
        self.symbols = list(symbols)
        self.profile = profile
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        # One broad-market check per scan. Failure is returned as UNKNOWN and
        # never silently treated as bullish.
        try:
            self.market_ready.emit(get_market_regime("SPY"))
        except Exception as exc:
            self.market_ready.emit({"regime": "UNKNOWN", "score": 50, "error": str(exc)})

        total = len(self.symbols)
        for idx, symbol in enumerate(self.symbols, start=1):
            if self._stop:
                break
            self.progress.emit(idx, total, symbol)
            try:
                data = analyse_daten(symbol)
                base = evaluate_strategy(data, self.profile)
                # Earnings calls are relatively expensive. We query them only
                # for candidates close enough to a trade to matter.
                earnings = {"symbol": symbol, "status": "SKIPPED", "days": None, "next_earnings": None}
                if base.get("decision") in {"READY", "WAIT"}:
                    earnings = get_earnings_info(symbol)
                execution_quote = None
                if base.get("decision") == "READY":
                    try:
                        execution_quote = get_latest_quote(symbol)
                    except Exception:
                        execution_quote = None
                self.item_ready.emit({"data": data, "earnings": earnings, "execution_quote": execution_quote})
            except Exception as exc:
                self.failed.emit(symbol, str(exc))
        self.done.emit()


# -----------------------------------------------------------------------------
# Wiederverwendbare Widgets
# -----------------------------------------------------------------------------
class InfoIcon(QLabel):
    """Kleines Hover-Info-Symbol. Qt blendet den Tooltip automatisch wieder aus."""
    def __init__(self, tooltip: str, parent=None):
        super().__init__("ⓘ", parent)
        self.setObjectName("InfoIcon")
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(18, 18)


def info_title(text: str, tooltip: str, object_name: str = "SectionTitle") -> QWidget:
    box = QWidget()
    box.setObjectName("InfoTitleBox")
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    label = QLabel(text)
    label.setObjectName(object_name)
    layout.addWidget(label)
    layout.addWidget(InfoIcon(tooltip))
    layout.addStretch(1)
    return box


class MetricList(QWidget):
    """Liste aus Kennzahl, Info-Hover und aktuellem Wert."""
    def __init__(self, metrics: list[tuple[str, str, str]], parent=None):
        super().__init__(parent)
        self.values = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for idx, (key, label_text, tooltip) in enumerate(metrics):
            row = QHBoxLayout()
            row.setContentsMargins(0, 9, 0, 9)
            row.setSpacing(6)
            label = QLabel(label_text)
            label.setObjectName("Muted")
            row.addWidget(label)
            row.addWidget(InfoIcon(tooltip))
            row.addStretch(1)
            value = QLabel("—")
            value.setStyleSheet("font-weight:700;")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(value)
            self.values[key] = value
            layout.addLayout(row)
            if idx < len(metrics) - 1:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setObjectName("MetricSeparator")
                layout.addWidget(sep)
        layout.addStretch(1)

    def set_values(self, values: dict[str, str]):
        for key, widget in self.values.items():
            widget.setText(str(values.get(key, "—")))


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")


class ScoreCard(Card):
    def __init__(self, title: str, inverse: bool = False, info: str = "", parent=None):
        super().__init__(parent)
        self.inverse = inverse
        self.setMinimumHeight(126)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.title = QLabel(title)
        self.title.setObjectName("Muted")
        title_row.addWidget(self.title)
        if info:
            title_row.addWidget(InfoIcon(info))
        title_row.addStretch(1)
        self.value = QLabel("—/100")
        self.value.setStyleSheet("font-size: 30px; font-weight: 700;")
        self.caption = QLabel("Noch keine Analyse")
        self.caption.setObjectName("Subtle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setValue(0)

        layout.addLayout(title_row)
        layout.addWidget(self.value)
        layout.addWidget(self.caption)
        layout.addStretch(1)
        layout.addWidget(self.progress)

    def set_score(self, score, caption: str = ""):
        if score is None:
            self.value.setText("—/100")
            self.value.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {TEXT_2};")
            self.progress.setValue(0)
            self.progress.setStyleSheet(
                f"QProgressBar::chunk {{background:{BORDER}; border-radius:3px;}}"
            )
            self.caption.setText(caption or loc("Keine Daten", "No data"))
            self.caption.setStyleSheet(f"color:{TEXT_2};")
            return
        s = int(round(float(score)))
        color = score_color(s, self.inverse)
        self.value.setText(f"{s}/100")
        self.value.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {color};")
        self.progress.setValue(s)
        self.progress.setStyleSheet(
            f"QProgressBar::chunk {{background:{color}; border-radius:3px;}}"
        )
        self.caption.setText(caption or "")
        self.caption.setStyleSheet(f"color:{color};")


class PriceChart(Card):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = None
        self.days = 252
        self.period_label = "1 Jahr"
        self.setMinimumHeight(350)

    def set_history(self, history):
        self.history = history
        self.update()

    def set_period(self, days: int | None, label: str):
        self.days = days
        self.period_label = label
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(20, 16, -20, -16)

        p.setPen(QColor(TEXT_2))
        f = QFont("Segoe UI", 11)
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect.left(), rect.top() + 8, f"Kursentwicklung · {self.period_label}")

        plot = QRectF(rect.left(), rect.top() + 40, rect.width(), rect.height() - 66)
        p.setPen(QPen(QColor("#173049"), 1))
        for i in range(5):
            y = plot.top() + i * plot.height() / 4
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        for i in range(6):
            x = plot.left() + i * plot.width() / 5
            p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        if self.history is None:
            p.setPen(QColor(TEXT_3))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "Nach einer Analyse erscheint hier der Kursverlauf.")
            return
        try:
            close = self.history["Close"].dropna()
            if self.days:
                close = close.tail(self.days)
            if len(close) < 2:
                raise ValueError
            vals = [float(v) for v in close]
        except Exception:
            p.setPen(QColor(TEXT_3))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "Keine Kursdaten verfügbar.")
            return

        lo, hi = min(vals), max(vals)
        pad = max((hi - lo) * 0.08, abs(hi) * 0.01, 1)
        lo -= pad
        hi += pad

        path = QPainterPath()
        points = []
        for i, v in enumerate(vals):
            x = plot.left() + i / (len(vals) - 1) * plot.width()
            y = plot.bottom() - (v - lo) / (hi - lo) * plot.height()
            points.append(QPointF(x, y))
        path.moveTo(points[0])
        for pt in points[1:]:
            path.lineTo(pt)

        p.setPen(QPen(QColor(GREEN), 2.2))
        p.drawPath(path)

        area = QPainterPath(path)
        area.lineTo(points[-1].x(), plot.bottom())
        area.lineTo(points[0].x(), plot.bottom())
        area.closeSubpath()
        fill = QColor(GREEN)
        fill.setAlpha(24)
        p.fillPath(area, fill)

        p.setPen(QColor(TEXT_3))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(int(plot.right() - 70), int(plot.top() + 10), 66, 14, Qt.AlignmentFlag.AlignRight, f"{hi:.0f}")
        p.drawText(int(plot.right() - 70), int(plot.bottom() - 5), 66, 14, Qt.AlignmentFlag.AlignRight, f"{lo:.0f}")

        last = vals[-1]
        last_pt = points[-1]
        p.setBrush(QColor(GREEN))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(last_pt, 4, 4)
        p.setPen(QColor(GREEN))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.drawText(int(plot.right() - 90), int(last_pt.y() - 18), 86, 16, Qt.AlignmentFlag.AlignRight, f"{last:.2f}")


class GaugeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.score = 0
        self.label = "—"
        self.setMinimumSize(180, 150)

    def set_value(self, score: int, label: str):
        self.score = int(max(0, min(100, score)))
        self.label = label
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(22, 20, self.width() - 44, self.height() - 55)
        pen_bg = QPen(QColor("#31465e"), 9)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(rect, 20 * 16, 140 * 16)

        pen = QPen(QColor(score_color(self.score)), 9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 20 * 16, int(140 * 16 * self.score / 100))

        p.setPen(QColor(score_color(self.score)))
        f = QFont("Segoe UI", 27)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 54, self.width(), 42), Qt.AlignmentFlag.AlignCenter, str(self.score))
        p.setPen(QColor(TEXT_2))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(0, 96, self.width(), 24), Qt.AlignmentFlag.AlignCenter, self.label)


class EmptyPage(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        sub.setWordWrap(True)
        card = Card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        msg = QLabel(tr("common.prepared"))
        msg.setObjectName("Muted")
        msg.setWordWrap(True)
        cl.addWidget(msg)
        cl.addStretch(1)
        layout.addWidget(title_lbl)
        layout.addWidget(sub)
        layout.addSpacing(12)
        layout.addWidget(card, 1)


# -----------------------------------------------------------------------------
# AutoTrader / Strategy / Paper Trading
# -----------------------------------------------------------------------------
class BotPage(QWidget):
    setting_changed = Signal(str, object)
    portfolio_changed = Signal()
    candidates_changed = Signal(object)
    status_changed = Signal(str)
    open_symbol = Signal(str)

    def __init__(self, config: dict, broker: PaperBroker, parent=None):
        super().__init__(parent)
        self.config = dict(config)
        self.broker = broker
        self.etoro = EtoroLiveBroker(APP_DIR)
        self.watchlist: dict[str, dict] = {}
        self.data = None
        self.profile = self.config.get("bot_profile", "balanced")
        self.enabled = bool(self.config.get("bot_enabled", False))
        self.demo_capital = float(self.config.get("demo_capital", 10000.0))
        self.scan_source = self.config.get("scan_source", "watchlist")
        self.slippage_bps = float(self.config.get("paper_slippage_bps", 5.0) or 5.0)
        self.pending_max_age_hours = float(self.config.get("pending_order_max_age_hours", 96) or 96)
        self.pending_max_gap_pct = float(self.config.get("pending_order_max_gap_pct", 3.0) or 3.0)
        self.max_trade_value = float(self.config.get("max_trade_value", 1000.0) or 1000.0)
        self.scan_thread = None
        self.candidates: dict[str, dict] = {}
        self.log_lines: list[str] = []
        self.market_regime = {"regime": "UNKNOWN", "score": 50, "error": None}
        self.decision_logger = AutoTraderLog(APP_DIR / "tradepilot_autotrader_log.jsonl")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget(); page.setObjectName("PageSurface")
        root = QVBoxLayout(page); root.setContentsMargins(30,24,30,30); root.setSpacing(16)

        head = QHBoxLayout()
        left = QVBoxLayout()
        title = QLabel(loc("TradePilot AutoTrader", "TradePilot AutoTrader")); title.setObjectName("PageTitle")
        sub = QLabel(loc("Automatische Kandidatensuche, Strategie, Risk Manager und lokales Paper-Trading.",
                         "Automatic candidate scan, strategy, risk manager and local paper trading."))
        sub.setObjectName("Muted")
        left.addWidget(title); left.addWidget(sub)
        head.addLayout(left); head.addStretch(1)
        paper = QLabel(loc("PAPER TRADING · KEINE ECHTEN ORDERS", "PAPER TRADING · NO REAL ORDERS"))
        paper.setStyleSheet(f"color:{YELLOW};border:1px solid {YELLOW};border-radius:8px;padding:6px 10px;font-weight:750;")
        head.addWidget(paper)
        root.addLayout(head)

        controls = Card(); cl = QHBoxLayout(controls); cl.setContentsMargins(20,16,20,16); cl.setSpacing(14)
        st = QVBoxLayout(); a=QLabel(loc("AUTOTRADER STATUS","AUTOTRADER STATUS")); a.setObjectName("Eyebrow")
        self.status_label=QLabel(); st.addWidget(a); st.addWidget(self.status_label); cl.addLayout(st)

        pb=QVBoxLayout(); x=QLabel(loc("RISIKOPROFIL","RISK PROFILE")); x.setObjectName("Eyebrow")
        self.profile_combo=QComboBox()
        for text,key in [(loc("Defensiv","Defensive"),"defensive"),(loc("Ausgewogen","Balanced"),"balanced"),(loc("Offensiv","Offensive"),"offensive"),(loc("Spekulativ","Speculative"),"speculative")]:
            self.profile_combo.addItem(text,key)
        self.profile_combo.setCurrentIndex(max(0,self.profile_combo.findData(self.profile)))
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        pb.addWidget(x); pb.addWidget(self.profile_combo); cl.addLayout(pb)

        sb=QVBoxLayout(); x=QLabel(loc("SCAN-QUELLE","SCAN SOURCE")); x.setObjectName("Eyebrow")
        self.source_combo=QComboBox()
        self.source_combo.addItem(loc("Watchlist","Watchlist"),"watchlist")
        self.source_combo.addItem(loc("TradePilot Core 30","TradePilot Core 30"),"core30")
        self.source_combo.addItem(loc("Watchlist + Core 30","Watchlist + Core 30"),"combined")
        self.source_combo.setCurrentIndex(max(0,self.source_combo.findData(self.scan_source)))
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        sb.addWidget(x); sb.addWidget(self.source_combo); cl.addLayout(sb)

        cb=QVBoxLayout(); x=QLabel(loc("STARTKAPITAL","START CAPITAL")); x.setObjectName("Eyebrow")
        self.capital_input=QLineEdit(f"{self.demo_capital:.2f}"); self.capital_input.setFixedWidth(120); self.capital_input.editingFinished.connect(self._capital_changed)
        cb.addWidget(x); cb.addWidget(self.capital_input); cl.addLayout(cb)

        mb=QVBoxLayout(); x=info_title(loc("MARKTREGIME","MARKET REGIME"), loc("Bewertet den breiten US-Markt über SPY, MA50/MA200, 3-Monats-Momentum und Drawdown. Der AutoTrader verwendet das Marktregime nur als zusätzlichen Filter.", "Rates the broad US market using SPY, MA50/MA200, 3-month momentum and drawdown. AutoTrader uses it only as an additional filter."), "Eyebrow")
        self.market_label=QLabel(loc("Noch nicht geprüft","Not checked yet")); self.market_label.setObjectName("Muted")
        mb.addWidget(x); mb.addWidget(self.market_label); cl.addLayout(mb)
        cl.addStretch(1)
        self.scan_btn=QPushButton(loc("Scan starten","Start scan")); self.scan_btn.setObjectName("Primary"); self.scan_btn.clicked.connect(self.start_scan)
        self.stop_btn=QPushButton(loc("Stoppen","Stop")); self.stop_btn.setEnabled(False); self.stop_btn.clicked.connect(self.stop_scan)
        self.toggle_btn=QPushButton(); self.toggle_btn.clicked.connect(self._toggle)
        cl.addWidget(self.scan_btn); cl.addWidget(self.stop_btn); cl.addWidget(self.toggle_btn)
        root.addWidget(controls)

        self.scan_progress=QProgressBar(); self.scan_progress.setRange(0,100); self.scan_progress.setValue(0); self.scan_progress.setTextVisible(True)
        root.addWidget(self.scan_progress)

        # Account summary
        summary=QHBoxLayout(); summary.setSpacing(12)
        self.account_labels={}
        for key,title_txt in [("equity",loc("Paper-Portfolio","Paper portfolio")),("cash",loc("Cash","Cash")),("invested",loc("Investiert","Invested")),("pnl",loc("Gesamt P/L","Total P/L")),("positions",loc("Offene Positionen","Open positions")),("pending",loc("Vorgemerkte Orders","Pending orders"))]:
            card=Card(); lay=QVBoxLayout(card); lay.setContentsMargins(16,13,16,13)
            t=QLabel(title_txt); t.setObjectName("Eyebrow"); v=QLabel("—"); v.setStyleSheet("font-size:22px;font-weight:760;")
            lay.addWidget(t); lay.addWidget(v); summary.addWidget(card,1); self.account_labels[key]=v
        root.addLayout(summary)

        # Current manual candidate
        cur=Card(); cur_l=QHBoxLayout(cur); cur_l.setContentsMargins(18,14,18,14)
        cur_left=QVBoxLayout(); ct=QLabel(loc("AKTUELL ANALYSIERTER TITEL","CURRENTLY ANALYZED STOCK")); ct.setObjectName("Eyebrow")
        self.company_label=QLabel("—"); self.company_label.setStyleSheet("font-size:19px;font-weight:720;")
        self.company_meta=QLabel(loc("Analysiere eine Aktie oder starte den AutoTrader-Scan.","Analyze a stock or start the AutoTrader scan.")); self.company_meta.setObjectName("Muted")
        cur_left.addWidget(ct); cur_left.addWidget(self.company_label); cur_left.addWidget(self.company_meta); cur_l.addLayout(cur_left); cur_l.addStretch(1)
        right_cur=QVBoxLayout(); right_cur.setSpacing(7)
        self.manual_decision=QLabel("—"); self.manual_decision.setAlignment(Qt.AlignmentFlag.AlignRight); self.manual_decision.setStyleSheet("font-size:18px;font-weight:750;"); right_cur.addWidget(self.manual_decision)
        manual_actions=QHBoxLayout(); manual_actions.setSpacing(7)
        self.manual_buy_btn=QPushButton(loc("Paper-Testorder","Paper test order")); self.manual_buy_btn.setToolTip(loc("Manuelle Paper-Order zum Testen. Bei geschlossenem Markt wird sie vorgemerkt und erst mit frischem Kurs ausgeführt. Umgeht die Strategieentscheidung, aber nicht die Risiko- und Portfoliolimits.","Manual paper order for testing. If the market is closed it remains pending until a fresh quote is available. It bypasses the strategy decision but still respects risk, cash and portfolio limits.")); self.manual_buy_btn.clicked.connect(self._manual_paper_buy)
        self.manual_sell_btn=QPushButton(loc("Position schließen","Close position")); self.manual_sell_btn.clicked.connect(self._manual_paper_sell)
        manual_actions.addWidget(self.manual_buy_btn); manual_actions.addWidget(self.manual_sell_btn); right_cur.addLayout(manual_actions)
        cur_l.addLayout(right_cur)
        root.addWidget(cur)

        # Pending paper orders (Order Engine)
        pending_card=Card(); pdl=QVBoxLayout(pending_card); pdl.setContentsMargins(18,16,18,16); pdl.setSpacing(9)
        ph=QHBoxLayout(); ptitle=info_title(loc("Vorgemerkte Paper-Orders","Pending paper orders"),
            loc("Ein freigegebenes Signal wird außerhalb der regulären US-Handelszeit nicht sofort gekauft. Die Order wartet auf einen frischen Kurs bei geöffnetem Markt und wird vor der Ausführung erneut auf Risiko, Cash und Portfolio-Limits geprüft.",
                "A ready signal is not filled immediately outside regular US trading hours. The order waits for a fresh open-market quote and is rechecked against risk, cash and portfolio limits before execution."), "SectionTitle")
        ph.addWidget(ptitle); ph.addStretch(1); self.pending_summary=QLabel("0"); self.pending_summary.setObjectName("Muted"); ph.addWidget(self.pending_summary); pdl.addLayout(ph)
        self.pending_table=QTableWidget(0,7); self.pending_table.setHorizontalHeaderLabels(["SYMBOL",loc("SEITE","SIDE"),loc("STÜCK","SHARES"),loc("REFERENZ","REFERENCE"),loc("STATUS","STATUS"),loc("ERSTELLT","CREATED"),loc("GRUND","REASON")])
        self.pending_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents); self.pending_table.horizontalHeader().setSectionResizeMode(6,QHeaderView.ResizeMode.Stretch)
        self.pending_table.verticalHeader().setVisible(False); self.pending_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.pending_table.setMinimumHeight(120); self.pending_table.setMaximumHeight(210)
        pdl.addWidget(self.pending_table); root.addWidget(pending_card)

        # Candidate ranking
        cand=Card(); cdl=QVBoxLayout(cand); cdl.setContentsMargins(18,16,18,16); cdl.setSpacing(10)
        row=QHBoxLayout(); tt=info_title(loc("Kandidaten-Ranking","Candidate ranking"), tr("info.confirmation"), "SectionTitle")
        row.addWidget(tt); row.addStretch(1); self.scan_state=QLabel(loc("Noch kein Scan","No scan yet")); self.scan_state.setObjectName("Muted"); row.addWidget(self.scan_state); cdl.addLayout(row)
        self.candidate_table=QTableWidget(0,12)
        self.candidate_table.setHorizontalHeaderLabels(["SYMBOL",loc("UNTERNEHMEN","COMPANY"),"U","E",loc("TRAP","TRAP"),loc("BESTÄTIGUNG","CONFIRMATION"),loc("MARKT","MARKET"),loc("EARNINGS","EARNINGS"),loc("ENTSCHEIDUNG","DECISION"),loc("ORDER","ORDER"),loc("FILTER","FILTERS"),loc("AKTION","ACTION")])
        self.candidate_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.candidate_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.candidate_table.horizontalHeader().setSectionResizeMode(10,QHeaderView.ResizeMode.Stretch)
        for col in [2,3,4,5,6,7,8,9,11]: self.candidate_table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
        self.candidate_table.verticalHeader().setVisible(False); self.candidate_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.candidate_table.setMinimumHeight(290)
        self.candidate_table.cellDoubleClicked.connect(self._candidate_double_clicked)
        cdl.addWidget(self.candidate_table); root.addWidget(cand)

        lower=QHBoxLayout(); lower.setSpacing(14)
        pos=Card(); pl=QVBoxLayout(pos); pl.setContentsMargins(18,16,18,16); pl.setSpacing(9)
        ph=QHBoxLayout(); ptitle=QLabel(loc("Offene Paper-Positionen","Open paper positions")); ptitle.setObjectName("SectionTitle"); ph.addWidget(ptitle); ph.addStretch(1)
        reset=QPushButton(loc("Paper-Konto zurücksetzen","Reset paper account")); reset.clicked.connect(self._reset_paper); ph.addWidget(reset); pl.addLayout(ph)
        self.position_table=QTableWidget(0,6); self.position_table.setHorizontalHeaderLabels(["SYMBOL",loc("STÜCK","SHARES"),loc("EINSTIEG","ENTRY"),loc("AKTUELL","LAST"),"P/L",loc("PROFIL","PROFILE")])
        self.position_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for col in range(1,6): self.position_table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
        self.position_table.verticalHeader().setVisible(False); self.position_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.position_table.setMinimumHeight(220)
        pl.addWidget(self.position_table); lower.addWidget(pos,3)

        log=Card(); ll=QVBoxLayout(log); ll.setContentsMargins(18,16,18,16)
        lt=QLabel(loc("AutoTrader-Protokoll","AutoTrader log")); lt.setObjectName("SectionTitle"); ll.addWidget(lt)
        self.log_table=QTableWidget(0,3); self.log_table.setHorizontalHeaderLabels([loc("ZEIT","TIME"),"SYMBOL",loc("EREIGNIS","EVENT")])
        self.log_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.log_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.log_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False); self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.log_table.setMinimumHeight(220)
        ll.addWidget(self.log_table); lower.addWidget(log,2)
        root.addLayout(lower)

        note=QLabel(loc("Hinweis: Der Bestätigungsgrad ist keine Gewinnwahrscheinlichkeit. 0.9.10 handelt ausschließlich im lokalen Paper-Konto. Orders werden bei geschlossenem Markt vorgemerkt und nur mit frischen regulären Marktkursen ausgeführt.",
                        "Note: The confirmation score is not a probability of profit. 0.9.10 trades only in the local paper account. Orders are queued while the market is closed and filled only from fresh regular-session quotes."))
        note.setObjectName("Subtle"); note.setWordWrap(True); root.addWidget(note); root.addStretch(1)
        scroll.setWidget(page); outer.addWidget(scroll)
        self._refresh_controls(); self._refresh_manual(); self.refresh_portfolio()

    def set_watchlist(self, watchlist: dict[str,dict]):
        self.watchlist = watchlist or {}

    def _refresh_controls(self):
        self.status_label.setText(("●  "+loc("Aktiv","Active")) if self.enabled else ("●  "+loc("Pausiert","Paused")))
        self.status_label.setStyleSheet(f"font-size:18px;font-weight:750;color:{GREEN if self.enabled else YELLOW};")
        self.toggle_btn.setText(loc("AutoTrader pausieren","Pause AutoTrader") if self.enabled else loc("AutoTrader aktivieren","Activate AutoTrader"))
        self.toggle_btn.setObjectName("Danger" if self.enabled else "Primary")
        self.toggle_btn.style().unpolish(self.toggle_btn); self.toggle_btn.style().polish(self.toggle_btn)

    def _toggle(self):
        self.enabled=not self.enabled; self.config["bot_enabled"]=self.enabled; self.setting_changed.emit("bot_enabled",self.enabled); self._refresh_controls()
        self._log("—",loc("AutoTrader aktiviert" if self.enabled else "AutoTrader pausiert", "AutoTrader activated" if self.enabled else "AutoTrader paused"))

    def _profile_changed(self):
        v=self.profile_combo.currentData()
        if v:
            self.profile=v; self.config["bot_profile"]=v; self.setting_changed.emit("bot_profile",v); self._refresh_manual()

    def _source_changed(self):
        v=self.source_combo.currentData()
        if v:
            self.scan_source=v; self.config["scan_source"]=v; self.setting_changed.emit("scan_source",v)

    def _capital_changed(self):
        try:
            value=max(100.0,float(self.capital_input.text().replace(" ","").replace(",",".")))
        except Exception:
            value=self.demo_capital
        self.demo_capital=value; self.capital_input.setText(f"{value:.2f}"); self.config["demo_capital"]=value; self.setting_changed.emit("demo_capital",value)
        self.capital_input.setToolTip(loc("Das Startkapital wird beim nächsten Zurücksetzen des Paper-Kontos verwendet.","The start capital is applied the next time the paper account is reset."))

    def set_analysis(self, data: dict|None):
        self.data=data; self._refresh_manual()

    def _refresh_manual(self):
        r=evaluate_strategy(self.data,self.profile)
        if not self.data:
            self.company_label.setText("—"); self.company_meta.setText(loc("Analysiere eine Aktie oder starte den AutoTrader-Scan.","Analyze a stock or start the AutoTrader scan.")); self.manual_decision.setText("—"); return
        symbol=self.data.get("symbol",""); self.company_label.setText(f"{self.data.get('name',symbol)} · {symbol}")
        self.company_meta.setText(f"{price_text(self.data)} · {r.get('confidence',0)}/100")
        d=r.get("decision","NO_DATA"); dm={"READY":loc("FREIGEGEBEN","READY"),"WAIT":loc("BEOBACHTEN","WAIT"),"REJECT":loc("ABGELEHNT","REJECT"),"BLOCKED":loc("GESPERRT","BLOCKED"),"NO_DATA":"—"}; colors={"READY":GREEN,"WAIT":YELLOW,"REJECT":ORANGE,"BLOCKED":RED,"NO_DATA":TEXT_2}
        self.manual_decision.setText(dm.get(d,d)); self.manual_decision.setStyleSheet(f"font-size:18px;font-weight:750;color:{colors.get(d,TEXT_2)};")

    def _pending_reserved_value(self) -> float:
        total = 0.0
        for order in self.broker.pending_orders("BUY"):
            try:
                total += float(order.get("shares", 0) or 0) * float(order.get("reference_price", 0) or 0)
            except Exception:
                pass
        return max(0.0, total)

    def _execution_text(self, code: str) -> str:
        de = {
            "PENDING": "Vorgemerkt", "FILLED": "Ausgeführt", "SIGNAL_ONLY": "Nur Signal",
            "POSITION": "Position offen", "REJECTED": "Order abgelehnt", "CANCELLED": "Order verworfen",
            "MARKET_CLOSED": "Wartet auf Marktöffnung", "STALE_QUOTE": "Wartet auf frischen Kurs",
        }
        en = {
            "PENDING": "Pending", "FILLED": "Filled", "SIGNAL_ONLY": "Signal only",
            "POSITION": "Position open", "REJECTED": "Order rejected", "CANCELLED": "Order cancelled",
            "MARKET_CLOSED": "Waiting for market open", "STALE_QUOTE": "Waiting for fresh quote",
        }
        return (en if language()=="en" else de).get(code, code or "—")

    def _queue_or_execute_buy(self, data: dict, risk: dict, quote: dict | None, reason: str = "AUTO_READY", requires_autotrader: bool = True) -> str:
        symbol = str(data.get("symbol", "") or "").upper()
        if self.broker.has_position(symbol):
            return "POSITION"
        if self.broker.has_pending_order(symbol, "BUY"):
            return "PENDING"
        price = valid_price(data)
        shares = int(risk.get("shares", 0) or 0)
        if not symbol or price is None or shares < 1:
            return "REJECTED"
        ok, code, order_id = self.broker.queue_buy(
            symbol, data.get("name", symbol), shares, float(price), self.profile, data, reason,
            requires_autotrader=requires_autotrader,
        )
        if not ok or not order_id:
            return "PENDING" if code == "ORDER_EXISTS" else "REJECTED"

        if not quote:
            self._log(symbol, loc(f"Paper-Order vorgemerkt · {shares} Stk. · wartet auf frischen Marktkurs",
                                  f"Paper order queued · {shares} shares · waiting for fresh market quote"), persist=True)
            return "PENDING"

        check = validate_pending_execution(
            self.broker, self.broker._order(order_id), quote, slippage_bps=self.slippage_bps,
            max_order_age_hours=self.pending_max_age_hours, max_gap_pct=self.pending_max_gap_pct,
            max_trade_value=self.max_trade_value,
        )
        if check.get("allowed"):
            ok2, code2, _ = self.broker.execute_pending(
                order_id, check["fill_price"], market_price=check.get("market_price"),
                quote_time=quote.get("quote_time"), quote_source=quote.get("provider"),
                slippage_bps=self.slippage_bps,
            )
            if ok2:
                self._log(symbol, loc(
                    f"Paper-Kauf ausgeführt · {shares} Stk. zu {check['fill_price']:.2f} · Slippage {self.slippage_bps:.1f} bp",
                    f"Paper buy filled · {shares} shares at {check['fill_price']:.2f} · slippage {self.slippage_bps:.1f} bps"), persist=True)
                return "FILLED"
            self.broker.mark_order(order_id, "REJECTED", code2)
            return "REJECTED"

        blocks = list(check.get("blocks", []))
        waiting = [x for x in blocks if x in {"MARKET_CLOSED", "STALE_QUOTE"}]
        hard = [x for x in blocks if x not in {"MARKET_CLOSED", "STALE_QUOTE"}]
        if hard:
            self.broker.mark_order(order_id, "REJECTED", hard[0])
            self._log(symbol, loc(f"Paper-Order verworfen · {hard[0]}", f"Paper order rejected · {hard[0]}"), persist=True)
            return "REJECTED"
        reason_code = waiting[0] if waiting else "PENDING"
        order=self.broker._order(order_id)
        if order:
            order["status_reason"]=reason_code
            order["updated"]=datetime.now().astimezone().isoformat(timespec="seconds")
            self.broker.save()
        self._log(symbol, loc(
            "Paper-Order vorgemerkt · wartet auf Marktöffnung" if reason_code == "MARKET_CLOSED" else "Paper-Order vorgemerkt · wartet auf frischen Kurs",
            "Paper order queued · waiting for market open" if reason_code == "MARKET_CLOSED" else "Paper order queued · waiting for fresh quote"), persist=True)
        return reason_code

    def _queue_sell(self, symbol: str, reason: str, requires_autotrader: bool = True) -> str:
        symbol = str(symbol or "").upper()
        if not self.broker.has_position(symbol):
            return "CANCELLED"
        if self.broker.has_pending_order(symbol, "SELL"):
            return "PENDING"
        ok, code, _ = self.broker.queue_sell(symbol, reason, requires_autotrader=requires_autotrader)
        if ok:
            self._log(symbol, loc(f"Paper-Verkaufsorder vorgemerkt · {reason}", f"Paper sell order queued · {reason}"), persist=True)
            return "PENDING"
        return "REJECTED"

    def start_scan(self):
        if self.scan_thread and self.scan_thread.isRunning(): return
        symbols=universe_symbols(self.scan_source,self.watchlist)
        # Open positions and pending orders are always monitored even if removed
        # from the selected universe.
        pending_symbols={str(o.get("symbol","")).upper() for o in self.broker.pending_orders() if str(o.get("symbol","")).strip()}
        symbols=sorted(set(symbols)|set(self.broker.positions.keys())|pending_symbols)
        if not symbols:
            QMessageBox.information(self,"TradePilot",loc("Die Watchlist ist leer. Füge Aktien hinzu oder wähle TradePilot Core 30.","The watchlist is empty. Add stocks or choose TradePilot Core 30.")); return
        self.candidates={}; self.candidate_table.setRowCount(0); self.scan_progress.setValue(0); self.scan_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.scan_state.setText(loc(f"Scan gestartet · {len(symbols)} Aktien",f"Scan started · {len(symbols)} stocks")); self._log("—",loc(f"Scan gestartet ({len(symbols)} Aktien)",f"Scan started ({len(symbols)} stocks)"))
        self.scan_thread=AutoTraderScanThread(symbols,self.profile); self.scan_thread.item_ready.connect(self._scan_item); self.scan_thread.failed.connect(self._scan_failed); self.scan_thread.progress.connect(self._scan_progress); self.scan_thread.market_ready.connect(self._market_ready); self.scan_thread.done.connect(self._scan_done); self.scan_thread.start()

    def stop_scan(self):
        if self.scan_thread and self.scan_thread.isRunning(): self.scan_thread.stop(); self.scan_state.setText(loc("Scan wird beendet …","Stopping scan …"))

    def _scan_progress(self,idx,total,symbol):
        self.scan_progress.setValue(round(idx/total*100) if total else 0); self.scan_progress.setFormat(f"{idx}/{total} · {symbol}"); self.status_changed.emit(loc(f"AutoTrader scannt {symbol} · {idx}/{total}",f"AutoTrader scanning {symbol} · {idx}/{total}"))

    def _market_ready(self, regime: dict):
        self.market_regime = regime or {"regime": "UNKNOWN", "score": 50}
        r = self.market_regime.get("regime", "UNKNOWN")
        score = int(self.market_regime.get("score", 50) or 50)
        labels = {"BULLISH": loc("Bullish", "Bullish"), "NEUTRAL": loc("Neutral", "Neutral"), "BEARISH": loc("Bearish", "Bearish"), "UNKNOWN": loc("Unbekannt", "Unknown")}
        colors = {"BULLISH": GREEN, "NEUTRAL": YELLOW, "BEARISH": RED, "UNKNOWN": TEXT_2}
        self.market_label.setText(f"● {labels.get(r, r)} · {score}/100")
        self.market_label.setStyleSheet(f"font-weight:750;color:{colors.get(r,TEXT_2)};")
        self._log("SPY", loc(f"Marktregime {labels.get(r,r)} · {score}/100", f"Market regime {labels.get(r,r)} · {score}/100"), persist=True)

    def _scan_failed(self,symbol,error):
        self._log(symbol,loc("Analyse fehlgeschlagen","Analysis failed"), persist=True)
        self.candidates[symbol]={"symbol":symbol,"name":symbol,"decision":"ERROR","confidence":0,"company":0,"entry":0,"trap":0,"market":"UNKNOWN","earnings_days":None,"filter_text":loc("Analysefehler","Analysis error"),"error":error}
        self._rebuild_candidate_table(); self.candidates_changed.emit(dict(self.candidates))

    def _context_decision(self, base: dict, earnings: dict) -> tuple[str, list[str]]:
        decision = base.get("decision", "NO_DATA")
        notes: list[str] = []
        if decision != "READY":
            return decision, notes

        mf = market_profile_filter(self.market_regime, self.profile, base.get("confidence", 0))
        ef = earnings_profile_filter(earnings, self.profile)
        notes.extend(mf.get("warnings", []))
        if ef.get("warning"):
            notes.append(ef["warning"])

        if mf.get("block") or ef.get("block"):
            return "BLOCKED", notes
        if mf.get("downgrade"):
            return "WAIT", notes
        return decision, notes

    def _filter_text(self, notes: list[str], portfolio: dict | None = None, risk: dict | None = None) -> str:
        codes = list(notes or [])
        if portfolio:
            codes += list(portfolio.get("blocks", [])) + list(portfolio.get("warnings", []))
        if risk:
            codes += list(risk.get("blocks", []))
        de = {
            "MARKET_BEARISH":"Markt bearish", "MARKET_DATA_UNKNOWN":"Marktdaten fehlen", "MARKET_NEUTRAL_NEEDS_CONFIRMATION":"Neutraler Markt: mehr Bestätigung nötig",
            "EARNINGS_TOO_CLOSE":"Earnings zu nah", "EARNINGS_SOON":"Earnings bald", "EARNINGS_DATA_UNKNOWN":"Earnings unbekannt",
            "MAX_SECTOR_EXPOSURE":"Sektorlimit", "MAX_PORTFOLIO_INVESTMENT":"Investitionslimit", "SECTOR_UNKNOWN":"Sektor unbekannt",
            "MAX_POSITIONS":"Max. Positionen", "NO_PRICE":"Kein Kurs", "CAPITAL_TOO_LOW":"Kapital zu niedrig", "MAX_TRADE_VALUE":"Maximalbetrag pro Trade erreicht",
        }
        en = {
            "MARKET_BEARISH":"Bearish market", "MARKET_DATA_UNKNOWN":"Market data missing", "MARKET_NEUTRAL_NEEDS_CONFIRMATION":"Neutral market: more confirmation needed",
            "EARNINGS_TOO_CLOSE":"Earnings too close", "EARNINGS_SOON":"Earnings soon", "EARNINGS_DATA_UNKNOWN":"Earnings unknown",
            "MAX_SECTOR_EXPOSURE":"Sector limit", "MAX_PORTFOLIO_INVESTMENT":"Investment limit", "SECTOR_UNKNOWN":"Sector unknown",
            "MAX_POSITIONS":"Max positions", "NO_PRICE":"No price", "CAPITAL_TOO_LOW":"Capital too low", "MAX_TRADE_VALUE":"Max trade value reached",
        }
        mapping = en if language()=="en" else de
        clean=[]
        for code in codes:
            text=mapping.get(code,code)
            if text not in clean: clean.append(text)
        return " · ".join(clean[:3]) if clean else loc("Alle Filter erfüllt","All filters passed")

    def _scan_item(self,payload:dict):
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        earnings = payload.get("earnings", {}) if isinstance(payload, dict) else {}
        execution_quote = payload.get("execution_quote") if isinstance(payload, dict) else None
        symbol=str(data.get("symbol","")).upper()
        base=evaluate_strategy(data,self.profile)
        decision, context_notes = self._context_decision(base, earnings)
        price=valid_price(data)

        # Pending BUY orders reserve capacity conceptually so one scan cannot
        # queue an unlimited number of positions while the market is closed.
        pending_buys=list(self.broker.pending_orders("BUY"))
        own_pending=next((o for o in pending_buys if str(o.get("symbol","")).upper()==symbol),None)
        reserved = self._pending_reserved_value()
        if own_pending:
            reserved=max(0.0,reserved-float(own_pending.get("shares",0) or 0)*float(own_pending.get("reference_price",0) or 0))
        effective_cash = max(0.0, self.broker.cash - reserved)
        effective_open = self.broker.open_count() + len(pending_buys) - (1 if own_pending else 0)
        risk = calculate_position(data,self.profile,self.broker.equity(),effective_open,effective_cash,max_trade_value=self.max_trade_value)
        portfolio = evaluate_portfolio_guard(self.broker, data, self.profile, risk.get("planned_value",0)) if price is not None else {"allowed":False,"blocks":[],"warnings":[]}
        execution_blocks = list(risk.get("blocks", [])) + list(portfolio.get("blocks", []))

        display_decision = decision
        if decision == "READY" and execution_blocks:
            display_decision = "BLOCKED"

        # If a previously queued BUY no longer has a valid READY signal, cancel
        # it. The next scan must deliberately create a new order.
        if self.broker.has_pending_order(symbol, "BUY") and display_decision != "READY":
            cancelled = 0
            for pending_order in list(self.broker.pending_orders("BUY")):
                if str(pending_order.get("symbol","")).upper()==symbol and bool(pending_order.get("requires_autotrader",True)):
                    if self.broker.mark_order(pending_order.get("order_id"), "CANCELLED", "SIGNAL_NO_LONGER_READY"):
                        cancelled += 1
            if cancelled:
                self._log(symbol, loc("Vorgemerkte AutoTrader-Kauforder verworfen · Signal nicht mehr freigegeben",
                                      "Pending AutoTrader buy order cancelled · signal no longer ready"), persist=True)

        earnings_days = earnings.get("days")
        order_status = "POSITION" if self.broker.has_position(symbol) else ("PENDING" if self.broker.has_pending_order(symbol,"BUY") else "SIGNAL_ONLY")
        self.candidates[symbol]={
            "symbol":symbol,"name":data.get("name",symbol),"decision":display_decision,
            "strategy_decision":decision,"confidence":base.get("confidence",0),
            "company":data.get("unternehmensscore",0),"entry":data.get("einstieg_score",0),"trap":data.get("trap_score",0),
            "market":self.market_regime.get("regime","UNKNOWN"),"market_score":self.market_regime.get("score",50),
            "earnings_days":earnings_days,"earnings_status":earnings.get("status","UNKNOWN"),
            "filter_text":"","order_status":order_status,"data":data,
        }

        if base.get("decision") != "READY":
            filter_text = strategy_reason_text(base)
        elif decision != "READY":
            filter_text = self._filter_text(context_notes)
        else:
            filter_text = self._filter_text(context_notes,portfolio,risk)
        self.candidates[symbol]["filter_text"] = filter_text

        self.decision_logger.append("DECISION", symbol,
            profile=self.profile, decision=display_decision, strategy_decision=decision,
            confidence=base.get("confidence",0), company=data.get("unternehmensscore"), entry=data.get("einstieg_score"), trap=data.get("trap_score"),
            market=self.market_regime.get("regime"), market_score=self.market_regime.get("score"), earnings_days=earnings_days,
            filters=filter_text)

        # Existing positions: the scan may request fundamental/time exits, but
        # actual execution is routed through a pending SELL order. Price-based
        # exits are handled only by fresh intraday quote refreshes.
        if self.broker.has_position(symbol) and price:
            pos=self.broker.positions.get(symbol,{})
            exit_result=evaluate_exit(pos,data,pos.get("profile",self.profile))
            non_price_reasons=[r for r in exit_result.get("reasons",[]) if r in {"MAX_HOLDING_TIME","TRAP_DETERIORATION","COMPANY_DETERIORATION"}]
            if non_price_reasons:
                if self.enabled:
                    status=self._queue_sell(symbol,non_price_reasons[0],requires_autotrader=True)
                    self.candidates[symbol]["order_status"]=status
                else:
                    self._log(symbol,loc(f"Ausstiegssignal {non_price_reasons[0]} · AutoTrader pausiert",f"Exit signal {non_price_reasons[0]} · AutoTrader paused"), persist=True)
            else:
                self.candidates[symbol]["order_status"]="POSITION"

        elif self.enabled and display_decision=="READY" and price:
            if risk.get("allowed") and portfolio.get("allowed") and risk.get("shares",0)>=1:
                status=self._queue_or_execute_buy(data,risk,execution_quote,reason="AUTO_READY",requires_autotrader=True)
                self.candidates[symbol]["order_status"]=status
        elif display_decision=="READY":
            self.candidates[symbol]["order_status"]="SIGNAL_ONLY"

        self._rebuild_candidate_table(); self.refresh_portfolio(); self.portfolio_changed.emit(); self.candidates_changed.emit(dict(self.candidates))

    def _scan_done(self):
        self.scan_btn.setEnabled(True); self.stop_btn.setEnabled(False); self.scan_progress.setValue(100 if self.candidates else 0)
        ready=sum(1 for x in self.candidates.values() if x.get("decision")=="READY")
        wait=sum(1 for x in self.candidates.values() if x.get("decision")=="WAIT")
        blocked=sum(1 for x in self.candidates.values() if x.get("decision")=="BLOCKED")
        rejected=sum(1 for x in self.candidates.values() if x.get("decision")=="REJECT")
        errors=sum(1 for x in self.candidates.values() if x.get("decision")=="ERROR")
        pending=self.broker.pending_count()
        self.scan_state.setText(loc(f"Scan fertig · {len(self.candidates)} analysiert · {ready} freigegeben · {pending} vorgemerkt · {wait} beobachten · {blocked} blockiert · {errors} Fehler",f"Scan complete · {len(self.candidates)} analyzed · {ready} ready · {pending} pending · {wait} watching · {blocked} blocked · {errors} errors"))
        self._log("—",loc(f"Scan abgeschlossen · {ready} freigegeben · {wait} beobachten · {rejected} abgelehnt · {blocked} blockiert · {errors} Fehler",f"Scan complete · {ready} ready · {wait} watching · {rejected} rejected · {blocked} blocked · {errors} errors"), persist=True)
        self.candidates_changed.emit(dict(self.candidates))
        self.status_changed.emit(loc("AutoTrader-Scan abgeschlossen","AutoTrader scan complete"))
        if self.scan_thread: self.scan_thread.deleteLater(); self.scan_thread=None

    def _rebuild_candidate_table(self):
        order={"READY":0,"WAIT":1,"REJECT":2,"BLOCKED":3,"ERROR":4,None:5}
        rows=sorted(self.candidates.values(),key=lambda x:(order.get(x.get("decision"),5),-float(x.get("confidence",0)),-float(x.get("entry",0))))
        self.candidate_table.setRowCount(len(rows))
        dm={"READY":loc("Freigegeben","Ready"),"WAIT":loc("Beobachten","Wait"),"REJECT":loc("Abgelehnt","Reject"),"BLOCKED":loc("Gesperrt","Blocked"),"ERROR":loc("Fehler","Error")}
        colors={"READY":GREEN,"WAIT":YELLOW,"REJECT":ORANGE,"BLOCKED":RED,"ERROR":RED}
        market_labels={"BULLISH":loc("Bullish","Bullish"),"NEUTRAL":loc("Neutral","Neutral"),"BEARISH":loc("Bearish","Bearish"),"UNKNOWN":loc("Unbekannt","Unknown")}
        for r,item in enumerate(rows):
            ed=item.get("earnings_days")
            if ed is None:
                earn = "—" if item.get("earnings_status") in {"SKIPPED","NO_DATE"} else loc("?","?")
            else:
                earn = loc(f"in {int(ed)} T.",f"{int(ed)}d")
            order_code=item.get("order_status", "SIGNAL_ONLY")
            order_text=self._execution_text(order_code)
            vals=[item.get("symbol",""),item.get("name",""),str(round(float(item.get("company",0)))),str(round(float(item.get("entry",0)))),str(round(float(item.get("trap",0)))),f"{int(item.get('confidence',0))}/100",market_labels.get(item.get("market"),"?"),earn,dm.get(item.get("decision"),"—"),order_text,item.get("filter_text",""),loc("Doppelklick: Analyse","Double-click: analysis")]
            for col,val in enumerate(vals):
                cell=QTableWidgetItem(val); cell.setData(Qt.ItemDataRole.UserRole,item.get("symbol"))
                if col==8: cell.setForeground(QColor(colors.get(item.get("decision"),TEXT_2)))
                if col==9:
                    oc={"FILLED":GREEN,"POSITION":GREEN,"PENDING":YELLOW,"MARKET_CLOSED":YELLOW,"STALE_QUOTE":YELLOW,"REJECTED":RED,"CANCELLED":RED}.get(order_code,TEXT_2); cell.setForeground(QColor(oc))
                if col==6:
                    mc={"BULLISH":GREEN,"NEUTRAL":YELLOW,"BEARISH":RED}.get(item.get("market"),TEXT_2); cell.setForeground(QColor(mc))
                self.candidate_table.setItem(r,col,cell)

    def _candidate_double_clicked(self,row,col):
        item=self.candidate_table.item(row,0)
        if item: self.open_symbol.emit(item.text())

    def refresh_portfolio(self):
        eq=self.broker.equity(); invested=self.broker.market_value(); pnl=eq-float(self.broker.state.get("initial_cash",self.demo_capital)); cur=self.broker.state.get("currency","USD")
        self.account_labels["equity"].setText(f"{eq:,.2f} {cur}"); self.account_labels["cash"].setText(f"{self.broker.cash:,.2f} {cur}"); self.account_labels["invested"].setText(f"{invested:,.2f} {cur}"); self.account_labels["pnl"].setText(f"{pnl:+,.2f} {cur}"); self.account_labels["pnl"].setStyleSheet(f"font-size:22px;font-weight:760;color:{GREEN if pnl>=0 else RED};"); self.account_labels["positions"].setText(str(self.broker.open_count())); self.account_labels["pending"].setText(str(self.broker.pending_count()))
        positions=list(self.broker.positions.values()); self.position_table.setRowCount(len(positions))
        for r,p in enumerate(positions):
            entry=float(p.get("entry_price",0)); last=float(p.get("last_price",entry)); perf=((last/entry)-1)*100 if entry else 0
            vals=[p.get("symbol",""),str(p.get("shares",0)),f"{entry:.2f}",f"{last:.2f}",f"{perf:+.1f}%",p.get("profile","")]
            for c_,v in enumerate(vals):
                cell=QTableWidgetItem(v)
                if c_==4: cell.setForeground(QColor(GREEN if perf>=0 else RED))
                self.position_table.setItem(r,c_,cell)

        pending=self.broker.pending_orders(); self.pending_table.setRowCount(len(pending)); self.pending_summary.setText(loc(f"{len(pending)} wartet",f"{len(pending)} waiting"))
        for r,o in enumerate(pending):
            created=str(o.get("created", ""))[:16].replace("T"," ")
            reason=order_reason_text(str(o.get("status_reason") or o.get("reason") or ""))
            status=loc("Wartet auf Ausführung","Waiting for fill")
            vals=[o.get("symbol",""),o.get("side",""),str(o.get("shares",0)),f"{float(o.get('reference_price',0) or 0):.2f}",status,created,reason]
            for c_,v in enumerate(vals):
                cell=QTableWidgetItem(str(v))
                if c_==4: cell.setForeground(QColor(YELLOW))
                self.pending_table.setItem(r,c_,cell)
        self._refresh_trade_log()

    def _refresh_trade_log(self):
        combined=[]
        for rec in self.decision_logger.recent(60):
            if rec.get("event") == "DECISION":
                dmap={"READY":loc("Freigegeben","Ready"),"WAIT":loc("Beobachten","Wait"),"REJECT":loc("Abgelehnt","Reject"),"BLOCKED":loc("Gesperrt","Blocked")}
                event = f"{dmap.get(rec.get('decision'),rec.get('decision',''))} · {int(rec.get('confidence',0) or 0)}/100 · {rec.get('filters','')}"
            else:
                event = rec.get("message") or rec.get("event", "")
            combined.append((str(rec.get("time",""))[:16].replace("T"," "),rec.get("symbol",""),event))
        combined=combined[-60:][::-1]; self.log_table.setRowCount(len(combined))
        for r,row in enumerate(combined):
            for c_,v in enumerate(row): self.log_table.setItem(r,c_,QTableWidgetItem(str(v)))

    def _log(self,symbol,event,persist: bool = True):
        from datetime import datetime
        self.log_lines.append(f"{datetime.now().strftime('%H:%M:%S')}|{symbol}|{event}")
        if persist:
            self.decision_logger.append("INFO", symbol, message=str(event))
        self._refresh_trade_log()

    def _manual_paper_buy(self):
        if not self.data:
            QMessageBox.information(self, "TradePilot", loc("Bitte zuerst eine Aktie analysieren.", "Please analyze a stock first."))
            return
        symbol = str(self.data.get("symbol", "") or "").upper()
        price = valid_price(self.data)
        if not symbol or price is None:
            QMessageBox.warning(self, "TradePilot", loc("Für diesen Titel ist kein gültiger Kurs verfügbar.", "No valid price is available for this stock."))
            return
        if self.broker.has_position(symbol) or self.broker.has_pending_order(symbol, "BUY"):
            QMessageBox.information(self, "TradePilot", loc(f"Für {symbol} besteht bereits eine Position oder vorgemerkte Kauforder.", f"A position or pending buy order for {symbol} already exists."))
            return
        reserved=self._pending_reserved_value(); effective_cash=max(0.0,self.broker.cash-reserved); effective_open=self.broker.open_count()+len(self.broker.pending_orders("BUY"))
        risk = calculate_position(self.data, self.profile, self.broker.equity(), effective_open, effective_cash, max_trade_value=self.max_trade_value)
        portfolio = evaluate_portfolio_guard(self.broker, self.data, self.profile, risk.get("planned_value", 0))
        blocks = list(risk.get("blocks", [])) + list(portfolio.get("blocks", []))
        if blocks or risk.get("shares", 0) < 1:
            reason = self._filter_text([], portfolio, risk)
            QMessageBox.warning(self, "TradePilot", loc(f"Paper-Testorder nicht möglich\n{reason}", f"Paper test order not possible\n{reason}"))
            return
        shares = int(risk.get("shares", 0)); value = shares * price
        ans = QMessageBox.question(self, "TradePilot", loc(
            f"Paper-Testorder erstellen?\n\n{symbol} · {shares} Stk. · Referenz ca. {value:.2f} USD\n\nBei geschlossenem Markt bleibt die Order vorgemerkt und wird erst mit frischem regulären Marktkurs ausgeführt.",
            f"Create paper test order?\n\n{symbol} · {shares} shares · reference approx. {value:.2f} USD\n\nIf the market is closed the order remains pending until a fresh regular-session quote is available."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            quote=get_latest_quote(symbol)
        except Exception:
            quote=None
        status=self._queue_or_execute_buy(self.data,risk,quote,reason="MANUAL_TEST",requires_autotrader=False)
        self._log(symbol,loc(f"Paper-Testorder · {self._execution_text(status)}",f"Paper test order · {self._execution_text(status)}"),persist=True)
        self.refresh_portfolio(); self.portfolio_changed.emit()

    def _manual_paper_sell(self):
        if not self.data:
            QMessageBox.information(self, "TradePilot", loc("Bitte zuerst die Aktie der offenen Position analysieren.", "Please analyze the stock of the open position first."))
            return
        symbol=str(self.data.get("symbol","") or "").upper()
        if not self.broker.has_position(symbol):
            QMessageBox.information(self,"TradePilot",loc(f"Für {symbol} besteht keine offene Paper-Position.",f"There is no open paper position for {symbol}."))
            return
        ans=QMessageBox.question(self,"TradePilot",loc(
            f"Paper-Position {symbol} schließen?\n\nBei geschlossenem Markt wird eine Verkaufsorder vorgemerkt und erst mit frischem regulären Marktkurs ausgeführt.",
            f"Close paper position {symbol}?\n\nIf the market is closed, a sell order will remain pending until a fresh regular-session quote is available."),
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans!=QMessageBox.StandardButton.Yes:
            return
        status=self._queue_sell(symbol,"MANUAL_TEST_CLOSE",requires_autotrader=False)
        try:
            quote=get_latest_quote(symbol)
        except Exception:
            quote=None
        if quote and self.broker.has_pending_order(symbol,"SELL"):
            order=next((o for o in self.broker.pending_orders("SELL") if o.get("symbol")==symbol),None)
            if order:
                check=validate_pending_execution(self.broker,order,quote,slippage_bps=self.slippage_bps,max_order_age_hours=self.pending_max_age_hours,max_gap_pct=self.pending_max_gap_pct,max_trade_value=self.max_trade_value)
                if check.get("allowed"):
                    ok,_,pnl=self.broker.execute_pending(order.get("order_id"),check.get("fill_price"),market_price=check.get("market_price"),quote_time=quote.get("quote_time"),quote_source=quote.get("provider"),slippage_bps=self.slippage_bps)
                    if ok:
                        status="FILLED"; self._log(symbol,loc(f"Manueller Paper-Verkauf ausgeführt · P/L {pnl:+.2f}",f"Manual paper sell filled · P/L {pnl:+.2f}"),persist=True)
        self.refresh_portfolio(); self.portfolio_changed.emit()

    def _reset_paper(self):
        ans=QMessageBox.question(self,"TradePilot",loc("Paper-Konto wirklich zurücksetzen? Alle simulierten Positionen und Trades werden gelöscht.","Really reset the paper account? All simulated positions and trades will be deleted."),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans!=QMessageBox.StandardButton.Yes: return
        self.broker.reset(self.demo_capital); self.candidates={}; self._rebuild_candidate_table(); self._log("—",loc("Paper-Konto zurückgesetzt","Paper account reset")); self.refresh_portfolio(); self.portfolio_changed.emit(); self.candidates_changed.emit({})


class PaperPortfolioPage(QWidget):
    refresh_requested = Signal()

    def __init__(self, broker: PaperBroker, parent=None):
        super().__init__(parent); self.broker=broker
        root=QVBoxLayout(self); root.setContentsMargins(30,24,30,30); root.setSpacing(16)
        title=QLabel(loc("Paper-Portfolio","Paper portfolio")); title.setObjectName("PageTitle")
        sub=QLabel(loc("Offene simulierte Positionen und abgeschlossene AutoTrader-Trades.","Open simulated positions and completed AutoTrader trades.")); sub.setObjectName("Muted")
        self.refresh_state = QLabel(loc("Auto-Refresh wartet auf den nächsten Kursabruf.", "Auto refresh is waiting for the next price poll."))
        self.refresh_state.setObjectName("Subtle")
        head = QHBoxLayout()
        head_left = QVBoxLayout()
        head_left.addWidget(title); head_left.addWidget(sub); head_left.addWidget(self.refresh_state)
        head.addLayout(head_left); head.addStretch(1)
        self.refresh_prices_btn = QPushButton(loc("Kurse jetzt aktualisieren", "Refresh prices now"))
        self.refresh_prices_btn.setObjectName("Primary")
        self.refresh_prices_btn.clicked.connect(self.refresh_requested.emit)
        head.addWidget(self.refresh_prices_btn)
        root.addLayout(head)
        summary=QHBoxLayout(); self.labels={}
        for key,text in [("equity",loc("Portfoliowert","Portfolio value")),("cash","Cash"),("unrealized",loc("Offenes P/L","Unrealized P/L")),("realized",loc("Realisiertes P/L","Realized P/L"))]:
            card=Card(); l=QVBoxLayout(card); l.setContentsMargins(18,14,18,14); t=QLabel(text); t.setObjectName("Eyebrow"); v=QLabel("—"); v.setStyleSheet("font-size:23px;font-weight:760;"); l.addWidget(t); l.addWidget(v); summary.addWidget(card,1); self.labels[key]=v
        root.addLayout(summary)
        pending=Card(); pendl=QVBoxLayout(pending); pendl.setContentsMargins(18,16,18,16); ptitle=QLabel(loc("Vorgemerkte Orders","Pending orders")); ptitle.setObjectName("SectionTitle"); pendl.addWidget(ptitle)
        self.pending_table=QTableWidget(0,7); self.pending_table.setHorizontalHeaderLabels(["SYMBOL",loc("SEITE","SIDE"),loc("STÜCK","SHARES"),loc("REFERENZ","REFERENCE"),loc("STATUS","STATUS"),loc("ERSTELLT","CREATED"),loc("GRUND","REASON")]); self.pending_table.horizontalHeader().setSectionResizeMode(6,QHeaderView.ResizeMode.Stretch)
        for c_ in [0,1,2,3,4,5]: self.pending_table.horizontalHeader().setSectionResizeMode(c_,QHeaderView.ResizeMode.ResizeToContents)
        self.pending_table.verticalHeader().setVisible(False); self.pending_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.pending_table.setMinimumHeight(100); pendl.addWidget(self.pending_table); root.addWidget(pending,1)
        card=Card(); l=QVBoxLayout(card); l.setContentsMargins(18,16,18,16); t=QLabel(loc("Offene Positionen","Open positions")); t.setObjectName("SectionTitle"); l.addWidget(t)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(["SYMBOL",loc("NAME","NAME"),loc("STÜCK","SHARES"),loc("EINSTIEG","ENTRY"),loc("AKTUELL","LAST"),loc("WERT","VALUE"),"P/L",loc("PROFIL","PROFILE")]); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for c_ in [0,2,3,4,5,6,7]: self.table.horizontalHeader().setSectionResizeMode(c_,QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); l.addWidget(self.table); root.addWidget(card,2)
        trades=Card(); tl=QVBoxLayout(trades); tl.setContentsMargins(18,16,18,16); tt=QLabel(loc("Trade-Historie","Trade history")); tt.setObjectName("SectionTitle"); tl.addWidget(tt)
        self.trades=QTableWidget(0,8); self.trades.setHorizontalHeaderLabels([loc("ZEIT","TIME"),loc("SEITE","SIDE"),"SYMBOL",loc("STÜCK","SHARES"),loc("KURS","PRICE"),loc("WERT","VALUE"),"P/L",loc("SLIPPAGE","SLIPPAGE")]); self.trades.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for c_ in range(1,8): self.trades.horizontalHeader().setSectionResizeMode(c_,QHeaderView.ResizeMode.ResizeToContents)
        self.trades.verticalHeader().setVisible(False); self.trades.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); tl.addWidget(self.trades); root.addWidget(trades,2)
        self.refresh()

    def set_refresh_status(self, text: str, color: str | None = None):
        self.refresh_state.setText(text)
        self.refresh_state.setStyleSheet(f"color:{color or TEXT_3};")

    def refresh(self):
        cur=self.broker.state.get("currency","USD"); eq=self.broker.equity(); u=self.broker.unrealized_pnl(); r=self.broker.realized_pnl()
        for key,val in [("equity",eq),("cash",self.broker.cash),("unrealized",u),("realized",r)]: self.labels[key].setText(f"{val:+,.2f} {cur}" if key in {"unrealized","realized"} else f"{val:,.2f} {cur}")
        self.labels["unrealized"].setStyleSheet(f"font-size:23px;font-weight:760;color:{GREEN if u>=0 else RED};"); self.labels["realized"].setStyleSheet(f"font-size:23px;font-weight:760;color:{GREEN if r>=0 else RED};")
        pending=self.broker.pending_orders(); self.pending_table.setRowCount(len(pending))
        for row,o in enumerate(pending):
            created=str(o.get("created", ""))[:16].replace("T"," ")
            vals=[o.get("symbol",""),o.get("side",""),str(o.get("shares",0)),f"{float(o.get('reference_price',0) or 0):.2f}",loc("VORGEMERKT","PENDING"),created,order_reason_text(str(o.get("status_reason") or o.get("reason") or ""))]
            for col,v in enumerate(vals):
                cell=QTableWidgetItem(str(v))
                if col==4: cell.setForeground(QColor(YELLOW))
                self.pending_table.setItem(row,col,cell)
        ps=list(self.broker.positions.values()); self.table.setRowCount(len(ps))
        for row,p in enumerate(ps):
            sh=int(p.get("shares",0)); en=float(p.get("entry_price",0)); last=float(p.get("last_price",en)); val=sh*last; pnl=sh*(last-en); vals=[p.get("symbol",""),p.get("name",""),str(sh),f"{en:.2f}",f"{last:.2f}",f"{val:.2f}",f"{pnl:+.2f}",p.get("profile","")]
            for col,v in enumerate(vals):
                cell=QTableWidgetItem(v)
                if col==6: cell.setForeground(QColor(GREEN if pnl>=0 else RED))
                self.table.setItem(row,col,cell)
        ts=self.broker.trades[-100:][::-1]; self.trades.setRowCount(len(ts))
        for row,t in enumerate(ts):
            pnl=float(t.get("pnl",0)); slip=float(t.get("slippage_bps",0) or 0); vals=[str(t.get("time",""))[:16].replace("T"," "),t.get("side",""),t.get("symbol",""),str(t.get("shares",0)),f"{float(t.get('price',0)):.2f}",f"{float(t.get('value',0)):.2f}",f"{pnl:+.2f}" if t.get("side")=="SELL" else "—",f"{slip:.1f} bp"]
            for col,v in enumerate(vals):
                cell=QTableWidgetItem(v)
                if col==6 and t.get("side")=="SELL": cell.setForeground(QColor(GREEN if pnl>=0 else RED))
                self.trades.setItem(row,col,cell)


class EquityCurve(Card):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.setMinimumHeight(270)

    def set_points(self, points):
        self.points = list(points or [])
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(20, 16, -20, -16)
        p.setPen(QColor(TEXT))
        f = QFont("Segoe UI", 11); f.setBold(True); p.setFont(f)
        p.drawText(rect.left(), rect.top() + 8, loc("Portfolio-Entwicklung", "Portfolio performance"))
        plot = QRectF(rect.left(), rect.top() + 38, rect.width(), rect.height() - 58)
        p.setPen(QPen(QColor(BORDER_SOFT), 1))
        for i in range(5):
            y = plot.top() + i * plot.height() / 4
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        if len(self.points) < 2:
            p.setPen(QColor(TEXT_3)); p.setFont(QFont("Segoe UI", 9))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, loc("Performance-Daten entstehen mit den nächsten Kursupdates und Trades.", "Performance data will build up with the next quote updates and trades."))
            return
        vals = [_finite(x.get("equity")) for x in self.points]
        vals = [v for v in vals if v is not None and v > 0]
        if len(vals) < 2:
            return
        lo, hi = min(vals), max(vals)
        pad = max((hi - lo) * 0.15, hi * 0.002, 1.0)
        lo -= pad; hi += pad
        pts=[]
        for i,v in enumerate(vals):
            x=plot.left()+i/(len(vals)-1)*plot.width()
            y=plot.bottom()-(v-lo)/(hi-lo)*plot.height()
            pts.append(QPointF(x,y))
        path=QPainterPath(); path.moveTo(pts[0])
        for pt in pts[1:]: path.lineTo(pt)
        first,last=vals[0],vals[-1]
        color=GREEN if last >= first else RED
        p.setPen(QPen(QColor(color),2.2)); p.drawPath(path)
        area=QPainterPath(path); area.lineTo(pts[-1].x(),plot.bottom()); area.lineTo(pts[0].x(),plot.bottom()); area.closeSubpath()
        fill=QColor(color); fill.setAlpha(20); p.fillPath(area,fill)
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(pts[-1],4,4)
        p.setPen(QColor(TEXT_3)); p.setFont(QFont("Segoe UI",8))
        p.drawText(int(plot.right()-90),int(plot.top()+8),86,14,Qt.AlignmentFlag.AlignRight,f"{hi:,.0f}")
        p.drawText(int(plot.right()-90),int(plot.bottom()-5),86,14,Qt.AlignmentFlag.AlignRight,f"{lo:,.0f}")


class PerformanceRiskPage(QWidget):
    """0.9.10 performance monitoring plus transparent risk/position management."""
    def __init__(self, broker: PaperBroker, config: dict, parent=None):
        super().__init__(parent)
        self.broker=broker; self.config=config; self.data=None
        outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        page=QWidget(); page.setObjectName("PageSurface")
        root=QVBoxLayout(page); root.setContentsMargins(30,24,30,30); root.setSpacing(16)
        scroll.setWidget(page); outer.addWidget(scroll)

        head=QHBoxLayout(); left=QVBoxLayout()
        title=QLabel(loc("Performance & Risk", "Performance & Risk")); title.setObjectName("PageTitle")
        sub=QLabel(loc("Portfolio-Performance, Risikobudget und Positionsmanagement auf einen Blick.", "Portfolio performance, risk budget and position management at a glance.")); sub.setObjectName("Muted")
        left.addWidget(title); left.addWidget(sub); head.addLayout(left); head.addStretch(1)
        self.profile_badge=QLabel("—"); self.profile_badge.setStyleSheet(f"color:{BLUE_2};border:1px solid {BLUE_2};border-radius:8px;padding:6px 10px;font-weight:700;")
        head.addWidget(self.profile_badge); root.addLayout(head)

        metrics=QGridLayout(); metrics.setSpacing(12); self.metric_labels={}
        cards=[
            ("return",loc("Gesamtperformance","Total return")),("day_pnl",loc("Tages-P/L","Daily P/L")),
            ("total_pnl",loc("Gesamt P/L","Total P/L")),("win_rate",loc("Trefferquote","Win rate")),
            ("drawdown",loc("Max Drawdown","Max drawdown")),("closed",loc("Geschlossene Trades","Closed trades")),
            ("avg_trade",loc("Ø Gewinn / Verlust","Avg win / loss")),("profit_factor",loc("Profit Factor","Profit factor")),
        ]
        for i,(key,label) in enumerate(cards):
            card=Card(); l=QVBoxLayout(card); l.setContentsMargins(16,13,16,13)
            t=QLabel(label); t.setObjectName("Eyebrow"); v=QLabel("—"); v.setStyleSheet("font-size:22px;font-weight:760;")
            l.addWidget(t); l.addWidget(v); metrics.addWidget(card,i//4,i%4); self.metric_labels[key]=v
        root.addLayout(metrics)

        middle=QHBoxLayout(); middle.setSpacing(14)
        self.equity_chart=EquityCurve(); middle.addWidget(self.equity_chart,3)
        risk_card=Card(); rl=QVBoxLayout(risk_card); rl.setContentsMargins(18,16,18,16); rl.setSpacing(9)
        rt=info_title(loc("Risikobudget","Risk budget"),loc("Zeigt die Grenzen des gewählten Risikoprofils sowie die aktuelle Portfolio-Auslastung. Der Maximalbetrag pro Trade ist eine harte Nutzergrenze.","Shows the selected risk profile limits and current portfolio utilisation. The max trade amount is a hard user cap."),"SectionTitle"); rl.addWidget(rt)
        self.risk_lines={}
        for key in ("trade","invested","cash","positions","sector"):
            row=QHBoxLayout(); a=QLabel("—"); a.setObjectName("Muted"); b=QLabel("—"); b.setStyleSheet("font-weight:700;"); row.addWidget(a); row.addStretch(1); row.addWidget(b); rl.addLayout(row); self.risk_lines[key]=(a,b)
        self.risk_progress=QProgressBar(); self.risk_progress.setRange(0,100); self.risk_progress.setTextVisible(False); rl.addWidget(self.risk_progress)
        self.risk_note=QLabel(""); self.risk_note.setObjectName("Subtle"); self.risk_note.setWordWrap(True); rl.addWidget(self.risk_note); rl.addStretch(1)
        middle.addWidget(risk_card,2); root.addLayout(middle)

        pos=Card(); pl=QVBoxLayout(pos); pl.setContentsMargins(18,16,18,16)
        ph=info_title(loc("Position Management","Position management"),loc("Für jede offene Position werden Portfolio-Anteil sowie die aktiven Stop-Loss-, Take-Profit- und Trailing-Stop-Grenzen des Risikoprofils angezeigt.","Shows portfolio weight and active stop-loss, take-profit and trailing-stop levels for every open position."),"SectionTitle"); pl.addWidget(ph)
        self.position_table=QTableWidget(0,11)
        self.position_table.setHorizontalHeaderLabels(["SYMBOL",loc("SEKTOR","SECTOR"),loc("STÜCK","SHARES"),loc("WERT","VALUE"),"P/L %",loc("PORTFOLIO %","PORTFOLIO %"),"STOP",loc("ZIEL","TARGET"),"TRAIL",loc("PROFIL","PROFILE"),loc("STATUS","STATUS")])
        self.position_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        for col in [0,2,3,4,5,6,7,8,9,10]: self.position_table.horizontalHeader().setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
        self.position_table.verticalHeader().setVisible(False); self.position_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.position_table.setMinimumHeight(190); pl.addWidget(self.position_table)
        root.addWidget(pos)

        lower=QHBoxLayout(); lower.setSpacing(14)
        sector=Card(); sl=QVBoxLayout(sector); sl.setContentsMargins(18,16,18,16); st=QLabel(loc("Sektor-Exposure","Sector exposure")); st.setObjectName("SectionTitle"); sl.addWidget(st)
        self.sector_table=QTableWidget(0,3); self.sector_table.setHorizontalHeaderLabels([loc("SEKTOR","SECTOR"),loc("WERT","VALUE"),loc("ANTEIL","WEIGHT")]); self.sector_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch); self.sector_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.sector_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents); self.sector_table.verticalHeader().setVisible(False); self.sector_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.sector_table.setMinimumHeight(180); sl.addWidget(self.sector_table); lower.addWidget(sector,1)
        planner=Card(); ql=QVBoxLayout(planner); ql.setContentsMargins(18,16,18,16); qt=info_title(loc("Positionsplaner","Position planner"),loc("Berechnet für den aktuell analysierten Titel eine mögliche Paper-Positionsgröße. Signalstärke und Volatilität können die Größe reduzieren; der Nutzer-Maximalbetrag wird niemals überschritten.","Calculates a possible paper position for the currently analysed stock. Signal strength and volatility may reduce size; the user max trade amount is never exceeded."),"SectionTitle"); ql.addWidget(qt)
        self.plan_title=QLabel(loc("Noch keine Aktie analysiert","No stock analysed yet")); self.plan_title.setStyleSheet("font-size:17px;font-weight:700;"); ql.addWidget(self.plan_title)
        self.plan_text=QLabel("—"); self.plan_text.setObjectName("Muted"); self.plan_text.setWordWrap(True); ql.addWidget(self.plan_text); ql.addStretch(1); lower.addWidget(planner,1)
        root.addLayout(lower)
        note=QLabel(loc("Hinweis: Performance-Kennzahlen basieren ausschließlich auf dem lokalen Paper-Konto. Sie sind keine Prognose für reale Handelsergebnisse.","Note: Performance metrics are based only on the local paper account. They are not a forecast of real trading results.")); note.setObjectName("Subtle"); note.setWordWrap(True); root.addWidget(note)
        self.refresh()

    def set_analysis(self,data):
        self.data=data; self.refresh()

    def refresh(self):
        profile=str(self.config.get("bot_profile","balanced")); names={"defensive":loc("Defensiv","Defensive"),"balanced":loc("Ausgewogen","Balanced"),"offensive":loc("Offensiv","Offensive"),"speculative":loc("Spekulativ","Speculative")}
        self.profile_badge.setText(loc("RISIKOPROFIL: ","RISK PROFILE: ")+names.get(profile,profile))
        m=performance_metrics(self.broker)
        vals={"return":f"{m['return_pct']:+.2f}%","day_pnl":f"{m['day_pnl']:+,.2f} USD","total_pnl":f"{m['total_pnl']:+,.2f} USD","win_rate":f"{m['win_rate']:.1f}%","drawdown":f"{m['max_drawdown_pct']:.2f}%","closed":str(m['closed_trades']),"avg_trade":f"{m['avg_win']:+.2f} / {m['avg_loss']:+.2f}","profit_factor":("∞" if math.isinf(m['profit_factor']) else f"{m['profit_factor']:.2f}")}
        for key,text in vals.items():
            self.metric_labels[key].setText(text)
        self.metric_labels["return"].setStyleSheet(f"font-size:22px;font-weight:760;color:{GREEN if m['return_pct']>=0 else RED};")
        self.metric_labels["day_pnl"].setStyleSheet(f"font-size:22px;font-weight:760;color:{GREEN if m['day_pnl']>=0 else RED};")
        self.metric_labels["total_pnl"].setStyleSheet(f"font-size:22px;font-weight:760;color:{GREEN if m['total_pnl']>=0 else RED};")
        self.metric_labels["drawdown"].setStyleSheet(f"font-size:22px;font-weight:760;color:{GREEN if m['max_drawdown_pct']>-5 else YELLOW if m['max_drawdown_pct']>-10 else RED};")
        self.equity_chart.set_points(m.get("history",[]))

        ro=risk_overview(self.broker,profile,self.config.get("max_trade_value",1000.0))
        items={
            "trade":(loc("Max. Trade","Max trade"),f"{ro['effective_trade_limit']:,.2f} USD"),
            "invested":(loc("Investiert / Limit","Invested / limit"),f"{ro['committed_pct']:.1f}% / {ro['max_invested_pct']:.0f}%"),
            "cash":(loc("Cash / Mindestreserve","Cash / minimum reserve"),f"{ro['cash_pct']:.1f}% / {ro['cash_reserve_pct']:.0f}%"),
            "positions":(loc("Positionen / Maximum","Positions / maximum"),f"{ro['position_count']} + {ro['pending_count']} / {ro['max_positions']}"),
            "sector":(loc("Max. je Sektor","Max per sector"),f"{ro['max_sector_pct']:.0f}%"),
        }
        for key,(a,b) in items.items(): self.risk_lines[key][0].setText(a); self.risk_lines[key][1].setText(b)
        usage=min(100,int(round(ro['committed_pct']/max(1.0,ro['max_invested_pct'])*100))); self.risk_progress.setValue(usage); color=GREEN if usage<75 else YELLOW if usage<95 else RED; self.risk_progress.setStyleSheet(f"QProgressBar::chunk{{background:{color};border-radius:3px;}}")
        self.risk_note.setText(loc(f"Harter Nutzer-Maximalbetrag: {float(self.config.get('max_trade_value',1000.0)):,.2f} USD pro Trade.",f"Hard user max: {float(self.config.get('max_trade_value',1000.0)):,.2f} USD per trade."))

        rows=position_rows(self.broker); self.position_table.setRowCount(len(rows))
        status_map={"OK":loc("OK","OK"),"WATCH":loc("Beobachten","Watch"),"HIGH":loc("Nahe Stop","Near stop"),"EXIT":loc("Exit erreicht","Exit reached")}; status_col={"OK":GREEN,"WATCH":YELLOW,"HIGH":ORANGE,"EXIT":RED}
        for r,row in enumerate(rows):
            vals=[row['symbol'],row['sector'],str(row['shares']),f"{row['value']:.2f}",f"{row['pnl_pct']:+.2f}%",f"{row['portfolio_pct']:.1f}%",f"{row['stop']:.2f}",f"{row['take']:.2f}",(f"{row['trailing']:.2f}" if row['trailing'] else "—"),row['profile'],status_map.get(row['risk'],row['risk'])]
            for col,v in enumerate(vals):
                cell=QTableWidgetItem(str(v));
                if col==4: cell.setForeground(QColor(GREEN if row['pnl_pct']>=0 else RED))
                if col==10: cell.setForeground(QColor(status_col.get(row['risk'],TEXT_2)))
                self.position_table.setItem(r,col,cell)

        sectors=sector_exposure(self.broker); self.sector_table.setRowCount(len(sectors))
        for r,row in enumerate(sectors):
            for col,v in enumerate([row['sector'],f"{row['value']:.2f} USD",f"{row['pct']:.1f}%"]): self.sector_table.setItem(r,col,QTableWidgetItem(str(v)))

        plan=candidate_position_plan(self.data,self.broker,profile,self.config.get("max_trade_value",1000.0))
        if not plan.get("available"):
            self.plan_title.setText(loc("Noch keine Aktie analysiert","No stock analysed yet")); self.plan_text.setText(loc("Öffne eine Analyse, um eine mögliche Positionsgröße zu berechnen.","Open an analysis to calculate a possible position size.")); return
        risk=plan['risk']; guard=plan['guard']; self.plan_title.setText(f"{plan['name']} · {plan['symbol']}")
        blocks=plan.get('blocks',[]); state=loc("Freigegeben","Allowed") if not blocks else loc("Blockiert: ","Blocked: ")+", ".join(blocks)
        vol=risk.get('volatility_pct'); voltxt=f"{vol:.1f}%" if vol is not None else "—"
        self.plan_text.setText(loc(
            f"Vorschlag: {risk.get('shares',0)} Stück · {risk.get('planned_value',0):,.2f} USD\nSignalstärke: {risk.get('signal_strength',0):.0f}/100 · Volatilität: {voltxt}\nDynamischer Faktor: {risk.get('signal_multiplier',1)*risk.get('volatility_multiplier',1):.2f} · Projektierte Investition: {(guard.get('projected_invested_pct') or 0)*100:.1f}%\n{state}",
            f"Proposal: {risk.get('shares',0)} shares · {risk.get('planned_value',0):,.2f} USD\nSignal strength: {risk.get('signal_strength',0):.0f}/100 · Volatility: {voltxt}\nDynamic factor: {risk.get('signal_multiplier',1)*risk.get('volatility_multiplier',1):.2f} · Projected investment: {(guard.get('projected_invested_pct') or 0)*100:.1f}%\n{state}"))

# -----------------------------------------------------------------------------
# Seiten
# -----------------------------------------------------------------------------
class DashboardPage(QWidget):
    open_analysis = Signal(str)
    open_watchlist = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.watchlist = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(18)

        head = QHBoxLayout()
        hleft = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        subtitle = QLabel(tr("dashboard.subtitle"))
        subtitle.setObjectName("Muted")
        hleft.addWidget(title)
        hleft.addWidget(subtitle)
        head.addLayout(hleft)
        head.addStretch(1)
        sync = QLabel("●  Lokale Daten bereit")
        sync.setObjectName("MarketOpen")
        head.addWidget(sync)
        root.addLayout(head)

        metrics = QGridLayout()
        metrics.setSpacing(12)
        self.metric_watchlist = self._metric_card("☆", "WATCHLIST", "0", "gespeicherte Aktien", BLUE_2)
        self.metric_interesting = self._metric_card("↗", "INTERESSANT", "0", "attraktive Einstiege", GREEN)
        self.metric_observe = self._metric_card("◌", "BEOBACHTEN", "0", "weiter beobachten", YELLOW)
        self.metric_risky = self._metric_card("△", "RISIKO", "0", "riskante Rücksetzer", RED)
        for i, card in enumerate((self.metric_watchlist, self.metric_interesting, self.metric_observe, self.metric_risky)):
            metrics.addWidget(card, 0, i)
            metrics.setColumnStretch(i, 1)
        root.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(14)

        watch_card = Card()
        wl = QVBoxLayout(watch_card)
        wl.setContentsMargins(18, 16, 18, 16)
        wh = QHBoxLayout()
        wh.addWidget(self._section("Top Watchlist"))
        wh.addStretch(1)
        btn = QPushButton("Alle anzeigen  →")
        btn.setObjectName("Ghost")
        btn.clicked.connect(self.open_watchlist.emit)
        wh.addWidget(btn)
        wl.addLayout(wh)
        hint = QLabel("Nach Einstiegsscore sortiert · Doppelklick öffnet die Analyse")
        hint.setObjectName("Subtle")
        wl.addWidget(hint)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["SYMBOL", "UNTERNEHMEN", "U-SCORE", "EINSTIEG", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._double_click)
        wl.addWidget(self.table, 1)
        content.addWidget(watch_card, 3)

        side = QVBoxLayout()
        side.setSpacing(14)

        signal_card = Card()
        sl = QVBoxLayout(signal_card)
        sl.setContentsMargins(18, 16, 18, 16)
        sh = QHBoxLayout()
        sh.addWidget(self._section("Signalcenter"))
        sh.addStretch(1)
        badge = QLabel("LOCAL")
        badge.setStyleSheet(f"color:{GREEN}; background:#0c2d26; border:1px solid #1b5c47; border-radius:7px; padding:3px 7px; font-weight:700; font-size:10px;")
        sh.addWidget(badge)
        sl.addLayout(sh)
        self.signal_box = QVBoxLayout()
        self.signal_box.setSpacing(8)
        sl.addLayout(self.signal_box)
        sl.addStretch(1)
        side.addWidget(signal_card, 3)

        research = Card()
        rl = QVBoxLayout(research)
        rl.setContentsMargins(18, 16, 18, 16)
        rl.addWidget(self._section("TradePilot Research"))
        t = QLabel(
            "Qualität, Entwicklung, Bewertung, Timing und Value-Trap-Risiko werden getrennt bewertet. "
            "Die aktuelle Engine bleibt bewusst stabil, während wir die App weiter professionalisieren."
        )
        t.setObjectName("Muted")
        t.setWordWrap(True)
        rl.addWidget(t)
        foot = QLabel("Research Engine 0.6.1  ·  App 0.9.10")
        foot.setObjectName("Subtle")
        rl.addWidget(foot)
        side.addWidget(research, 2)

        content.addLayout(side, 2)
        root.addLayout(content, 1)

    def _metric_card(self, icon: str, title: str, value: str, caption: str, accent: str):
        card = QFrame()
        card.setObjectName("MetricCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(18, 15, 18, 15)
        l.setSpacing(4)
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size:17px;color:{accent};background:#10263c;border-radius:8px;")
        title_lbl = QLabel(title)
        title_lbl.setObjectName("Eyebrow")
        top.addWidget(icon_lbl)
        top.addWidget(title_lbl)
        top.addStretch(1)
        l.addLayout(top)
        b = QLabel(value)
        b.setStyleSheet(f"font-size:31px;font-weight:720;color:{accent};")
        c = QLabel(caption)
        c.setObjectName("Subtle")
        l.addWidget(b)
        l.addWidget(c)
        accent_line = QFrame()
        accent_line.setFixedHeight(3)
        accent_line.setStyleSheet(f"background:{accent};border-radius:1px;")
        l.addWidget(accent_line)
        card.value_label = b
        return card

    def _section(self, text: str):
        l = QLabel(text)
        l.setObjectName("SectionTitle")
        return l

    def _clear_signals(self):
        while self.signal_box.count():
            item = self.signal_box.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _signal_row(self, symbol: str, title: str, detail: str, color: str):
        row = QFrame()
        row.setStyleSheet("QFrame{background:#0e2033;border:1px solid #18324a;border-radius:9px;}")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 8, 10, 8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color};")
        lay.addWidget(dot)
        text = QVBoxLayout()
        a = QLabel(f"{symbol}  ·  {title}")
        a.setStyleSheet("font-weight:650;")
        b = QLabel(detail)
        b.setObjectName("Subtle")
        text.addWidget(a)
        text.addWidget(b)
        lay.addLayout(text, 1)
        return row

    def set_watchlist(self, watchlist: dict):
        self.watchlist = watchlist or {}
        records = list(self.watchlist.values())
        self.metric_watchlist.value_label.setText(str(len(records)))
        self.metric_interesting.value_label.setText(str(sum("INTERESSANT" in str(r.get("status", "")).upper() for r in records)))
        self.metric_observe.value_label.setText(str(sum("BEOBACHTEN" in str(r.get("status", "")).upper() for r in records)))
        self.metric_risky.value_label.setText(str(sum("RISIK" in str(r.get("status", "")).upper() for r in records)))

        records.sort(key=lambda r: (r.get("einstieg_score") is not None, r.get("einstieg_score") or -1), reverse=True)
        top_records = records[:8]
        self.table.setRowCount(len(top_records))
        for row, r in enumerate(top_records):
            values = [
                r.get("symbol", ""), r.get("name", ""),
                f"{r.get('unternehmensscore', '—')}/100",
                f"{r.get('einstieg_score', '—')}/100",
                r.get("status", ""),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col == 0:
                    item.setForeground(QColor(BLUE_2))
                if col == 4:
                    item.setForeground(QColor(status_color(str(val))))
                self.table.setItem(row, col, item)

        self._clear_signals()
        if not records:
            empty = QLabel("Noch keine Watchlist-Signale. Analysiere eine Aktie und füge sie deiner Watchlist hinzu.")
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            self.signal_box.addWidget(empty)
            return

        interesting = [r for r in records if "INTERESSANT" in str(r.get("status", "")).upper()]
        deltas = [r for r in records if isinstance(r.get("delta_einstieg_score"), (int, float)) and r.get("delta_einstieg_score") != 0]
        risky = [r for r in records if "RISIK" in str(r.get("status", "")).upper()]
        shown = 0
        for r in interesting[:2]:
            self.signal_box.addWidget(self._signal_row(r.get("symbol", ""), "Interessanter Einstieg", f"Einstieg {r.get('einstieg_score', '—')}/100", GREEN))
            shown += 1
        for r in sorted(deltas, key=lambda x: abs(x.get("delta_einstieg_score", 0)), reverse=True)[:2]:
            de = r.get("delta_einstieg_score")
            color = GREEN if de > 0 else RED
            self.signal_box.addWidget(self._signal_row(r.get("symbol", ""), "Score verändert", f"Einstieg {de:+d} seit letzter Analyse", color))
            shown += 1
        for r in risky[:1]:
            self.signal_box.addWidget(self._signal_row(r.get("symbol", ""), "Risiko", "Value-Trap-/Rücksetzer-Warnung aktiv", RED))
            shown += 1
        if shown == 0:
            best = records[0]
            self.signal_box.addWidget(self._signal_row(best.get("symbol", ""), "Top Watchlist", f"Einstieg {best.get('einstieg_score', '—')}/100", YELLOW))

    def _double_click(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                self.open_analysis.emit(item.text())


class AnalysisPage(QWidget):
    add_to_watchlist = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("PageSurface")
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(30, 22, 30, 28)
        self.layout.setSpacing(14)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._build_company_header()
        self._build_scores()
        self._build_main_area()
        self._build_detail_cards()

    def _build_company_header(self):
        hero = QFrame()
        hero.setObjectName("HeroCard")
        l = QHBoxLayout(hero)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(16)

        self.ticker_tile = QFrame()
        self.ticker_tile.setObjectName("TickerTile")
        self.ticker_tile.setFixedSize(68, 68)
        tile_l = QVBoxLayout(self.ticker_tile)
        tile_l.setContentsMargins(0, 0, 0, 0)
        self.ticker_letter = QLabel("TP")
        self.ticker_letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ticker_letter.setStyleSheet(f"font-size:20px;font-weight:800;color:{BLUE_2};")
        tile_l.addWidget(self.ticker_letter)
        l.addWidget(self.ticker_tile)

        left = QVBoxLayout()
        left.setSpacing(3)
        self.company = QLabel(tr("analysis.start"))
        self.company.setObjectName("HeroTitle")
        self.symbol_line = QLabel("TradePilot Analyse")
        self.symbol_line.setObjectName("Muted")
        self.meta = QLabel("Ticker oben eingeben und Analyse starten.")
        self.meta.setObjectName("Subtle")
        left.addWidget(self.company)
        left.addWidget(self.symbol_line)
        left.addWidget(self.meta)
        l.addLayout(left, 1)

        action = QVBoxLayout()
        action.setSpacing(7)
        self.status = QLabel("NOCH KEINE ANALYSE")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(f"padding:8px 14px;border:1px solid {BORDER};border-radius:9px;color:{TEXT_2};font-weight:700;")
        self.watch_button = QPushButton(tr("watch.add"))
        self.watch_button.setObjectName("Ghost")
        self.watch_button.setEnabled(False)
        self.watch_button.clicked.connect(self.add_to_watchlist.emit)
        action.addWidget(self.status)
        action.addWidget(self.watch_button)
        l.addLayout(action)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background:#1b334c;")
        l.addWidget(divider)

        price_box = QVBoxLayout()
        price_box.setSpacing(2)
        price_title = QLabel(tr("price.current"))
        price_title.setObjectName("Eyebrow")
        self.price = QLabel("—")
        self.price.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.price.setStyleSheet("font-size:31px;font-weight:730;")
        self.performance_today = QLabel("")
        self.performance_today.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.performance_today.setObjectName("Muted")
        price_box.addWidget(price_title)
        price_box.addWidget(self.price)
        price_box.addWidget(self.performance_today)
        l.addLayout(price_box)
        self.layout.addWidget(hero)

    def _build_scores(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        self.score_cards = {
            "unternehmensscore": ScoreCard("▦  " + tr("score.company"), info=tr("info.company_score")),
            "einstieg_score": ScoreCard("◎  " + tr("score.entry"), info=tr("info.entry_score")),
            "fundamental_score": ScoreCard("◇  " + tr("score.quality"), info=tr("info.quality_score")),
            "entwicklungs_score": ScoreCard("↗  " + tr("score.development"), info=tr("info.development_score")),
            "bewertungs_score": ScoreCard("⚖  " + tr("score.valuation"), info=tr("info.valuation_score")),
            "trap_score": ScoreCard("△  " + tr("score.trap"), inverse=True, info=tr("info.trap_score")),
        }
        for col, card in enumerate(self.score_cards.values()):
            grid.addWidget(card, 0, col)
            grid.setColumnStretch(col, 1)
        self.layout.addLayout(grid)

    def _build_main_area(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        chart_panel = Card()
        cp = QVBoxLayout(chart_panel)
        cp.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(18, 10, 18, 0)
        label = QLabel(tr("chart.title"))
        label.setObjectName("Eyebrow")
        toolbar.addWidget(label)
        toolbar.addStretch(1)
        self.time_group = QButtonGroup(self)
        self.time_group.setExclusive(True)
        for text, days in (("1M", 22), ("3M", 66), ("6M", 132), ("1J", 252), ("MAX", None)):
            b = QPushButton(text)
            b.setObjectName("TimeButton")
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, d=days, t=text: self._set_chart_period(d, t))
            self.time_group.addButton(b)
            toolbar.addWidget(b)
            if text == "1J":
                b.setChecked(True)
        cp.addLayout(toolbar)
        self.chart = PriceChart()
        self.chart.setStyleSheet("QFrame#Card{border:0;background:transparent;}")
        cp.addWidget(self.chart, 1)
        row.addWidget(chart_panel, 3)

        entry = Card()
        el = QVBoxLayout(entry)
        el.setContentsMargins(16, 14, 16, 14)
        title = info_title(tr("entry.title"), tr("info.entry_situation"))
        self.gauge = GaugeWidget()
        self.entry_text = QLabel("Noch keine Analyse")
        self.entry_text.setObjectName("Muted")
        self.entry_text.setWordWrap(True)
        self.entry_facts = QLabel("Trend  —\nMomentum  —\nDrawdown  —")
        self.entry_facts.setObjectName("Subtle")
        self.entry_facts.setWordWrap(True)
        el.addWidget(title)
        el.addWidget(self.gauge)
        el.addWidget(self.entry_text)
        el.addSpacing(5)
        el.addWidget(self.entry_facts)
        el.addStretch(1)
        row.addWidget(entry, 1)

        reasons = Card()
        rl = QVBoxLayout(reasons)
        rl.setContentsMargins(16, 14, 16, 14)
        title2 = QLabel(tr("reasons.title"))
        title2.setObjectName("SectionTitle")
        self.strengths = QLabel("Nach der Analyse erscheinen hier die wichtigsten Stärken.")
        self.strengths.setObjectName("Muted")
        self.strengths.setWordWrap(True)
        self.strengths.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.warnings = QLabel("")
        self.warnings.setWordWrap(True)
        self.warnings.setAlignment(Qt.AlignmentFlag.AlignTop)
        rl.addWidget(title2)
        rl.addWidget(self.strengths)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background:#1b334c;")
        rl.addWidget(line)
        rl.addWidget(self.warnings)
        rl.addStretch(1)
        row.addWidget(reasons, 2)
        self.layout.addLayout(row)

    def _set_chart_period(self, days, text):
        label = {"1M":"1 Monat", "3M":"3 Monate", "6M":"6 Monate", "1J":"1 Jahr", "MAX":"Max"}.get(text, text)
        self.chart.set_period(days, label)

    def _mini_card(self, icon: str, title: str, accent: str, metrics):
        card = Card()
        l = QVBoxLayout(card)
        l.setContentsMargins(16, 14, 16, 14)
        head = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet(f"font-size:17px;color:{accent};")
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        head.addWidget(ico)
        head.addWidget(t)
        head.addStretch(1)
        body = MetricList(metrics)
        l.addLayout(head)
        l.addWidget(body, 1)
        return card, body

    def _build_detail_cards(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        self.quality_card, self.quality_body = self._mini_card("◇", tr("detail.quality"), GREEN, [
            ("roe", "ROE", tr("info.roe")),
            ("net_margin", tr("metric.net_margin"), tr("info.net_margin")),
            ("fcf_margin", "FCF-" + tr("metric.margin"), tr("info.fcf_margin")),
        ])
        self.dev_card, self.dev_body = self._mini_card("↗", tr("detail.development"), GREEN, [
            ("revenue_growth", tr("metric.revenue_growth"), tr("info.revenue_growth")),
            ("multi_year", tr("metric.multiyear_score"), tr("info.multiyear_score")),
            ("trend_score", tr("metric.trend_score"), tr("info.trend_score")),
        ])
        self.val_card, self.val_body = self._mini_card("⚖", tr("detail.valuation"), YELLOW, [
            ("pe", tr("metric.pe"), tr("info.pe")),
            ("forward_pe", tr("metric.forward_pe"), tr("info.forward_pe")),
            ("peg", "PEG", tr("info.peg")),
        ])
        self.risk_card, self.risk_body = self._mini_card("△", tr("detail.risk"), RED, [
            ("drawdown", tr("metric.drawdown_52w"), tr("info.drawdown")),
            ("trap", "Value-Trap", tr("info.value_trap")),
            ("debt_cash", "Debt/Cash", tr("info.debt_cash")),
        ])
        grid.addWidget(self.quality_card, 0, 0)
        grid.addWidget(self.dev_card, 0, 1)
        grid.addWidget(self.val_card, 0, 2)
        grid.addWidget(self.risk_card, 0, 3)
        for i in range(4):
            grid.setColumnStretch(i, 1)
        self.layout.addLayout(grid)

    def _clear_analysis_details(self):
        """Entfernt alle Werte einer vorherigen Analyse aus der Oberfläche."""
        self.quality_body.set_values({
            "roe": "—",
            "net_margin": "—",
            "fcf_margin": "—",
        })
        self.dev_body.set_values({
            "revenue_growth": "—",
            "multi_year": "—",
            "trend_score": "—",
        })
        self.val_body.set_values({
            "pe": "—",
            "forward_pe": "—",
            "peg": "—",
        })
        self.risk_body.set_values({
            "drawdown": "—",
            "trap": "—",
            "debt_cash": "—",
        })

    def set_loading(self, symbol: str):
        # Nie Werte der zuletzt analysierten Aktie während einer neuen Analyse
        # stehen lassen. Das verhindert insbesondere irreführende Alt-Daten,
        # falls der neue Ticker anschließend fehlschlägt.
        self.data = None
        for card in self.score_cards.values():
            card.set_score(None, loc("Wird geladen", "Loading"))
        self._clear_analysis_details()
        self.chart.set_history(None)
        self.gauge.set_value(0, loc("Analyse läuft", "Analysis running"))
        self.entry_text.setText(loc("Daten werden geladen …", "Loading data …"))
        self.entry_facts.setText("Trend  —\nMomentum  —\nDrawdown  —")
        self.strengths.setText(loc("Analyse läuft …", "Analysis running …"))
        self.strengths.setStyleSheet(f"color:{TEXT_2};")
        self.warnings.setText("")
        self.price.setText("—")
        self.performance_today.setText("—")
        self.performance_today.setStyleSheet(f"color:{TEXT_2};font-weight:650;")
        self.watch_button.setEnabled(False)
        self.watch_button.setText(loc("Wird geladen …", "Loading …"))

        self.ticker_letter.setText(symbol[:2].upper())
        self.company.setText(loc(f"{symbol} wird analysiert …", f"Analyzing {symbol} …"))
        self.symbol_line.setText(loc("Daten werden geladen", "Loading data"))
        self.meta.setText(loc("Fundamentaldaten, Kursverlauf und Scores werden berechnet.", "Calculating fundamentals, price history and scores."))
        self.status.setText(loc("ANALYSE LÄUFT", "ANALYSIS RUNNING"))
        self.status.setStyleSheet(f"padding:8px 14px;border:1px solid {BLUE};border-radius:9px;color:{BLUE_2};font-weight:700;")

    def set_error(self, symbol: str, error: str):
        self.data = None
        self.ticker_letter.setText((symbol or "TP")[:2].upper())
        self.company.setText(loc("Ticker nicht verfügbar", "Ticker unavailable"))
        self.symbol_line.setText(str(symbol or ""))
        self.meta.setText(loc("Bitte Symbol prüfen oder später erneut versuchen.", "Check the symbol or try again later."))
        self.price.setText("—")
        self.performance_today.setText("—")
        self.performance_today.setStyleSheet(f"color:{TEXT_2};font-weight:650;")
        self.status.setText(loc("DATENFEHLER", "DATA ERROR"))
        self.status.setStyleSheet(f"padding:8px 14px;border:1px solid {RED};background:#0e2030;border-radius:9px;color:{RED};font-weight:700;")
        for card in self.score_cards.values():
            card.set_score(None, "")
        self.chart.set_history(None)
        self.gauge.set_value(0, loc("Keine Entscheidung", "No decision"))
        self.entry_text.setText(str(error))
        self.entry_facts.setText(loc("Keine belastbare Analyse verfügbar.", "No reliable analysis available."))
        self.strengths.setText("—")
        self.warnings.setText(loc("△  Daten konnten nicht zuverlässig geladen werden.", "△  Data could not be loaded reliably."))
        self.warnings.setStyleSheet(f"color:{RED};")
        self._clear_analysis_details()
        self.set_watchlist_state(False)
        self.watch_button.setText(loc("Nicht verfügbar", "Unavailable"))

    def set_watchlist_state(self, in_watchlist: bool):
        if not self.data:
            self.watch_button.setEnabled(False)
            self.watch_button.setText(tr("watch.add"))
            return
        self.watch_button.setEnabled(not in_watchlist)
        self.watch_button.setText(tr("watch.in") if in_watchlist else tr("watch.add"))

    def set_data(self, d: dict, in_watchlist: bool):
        self.data = d
        symbol = d.get("symbol", "")
        self.ticker_letter.setText(symbol[:2].upper() or "TP")
        self.company.setText(d.get("name", symbol))
        self.symbol_line.setText(f"{symbol}  ·  {d.get('modell_text', '')}")
        self.meta.setText(f"{d.get('sektor', '')}  ·  {d.get('branche', '')}")
        self.price.setText(price_text(d))
        perf = d.get("performance", {}) or {}
        today = perf.get("heute")
        today_col = GREEN if (today or 0) >= 0 else RED
        self.performance_today.setText(f"Heute {pct(today, signed=True)}")
        self.performance_today.setStyleSheet(f"color:{today_col};font-weight:650;")

        status = d.get("i_status", "")
        col = status_color(status)
        self.status.setText(translate_status(status))
        self.status.setStyleSheet(f"padding:8px 14px;border:1px solid {col};background:#0e2030;border-radius:9px;color:{col};font-weight:700;")

        score_captions = {
            "unternehmensscore": "Gesamtqualität",
            "einstieg_score": translate_status(d.get("i_status", "")),
            "fundamental_score": d.get("q_status", ""),
            "entwicklungs_score": d.get("e_status", ""),
            "bewertungs_score": "Bewertungsniveau",
            "trap_score": d.get("r_status", ""),
        }
        for key, card in self.score_cards.items():
            card.set_score(d.get(key), score_captions.get(key, ""))

        self.chart.set_history(d.get("historie"))
        self.gauge.set_value(int(d.get("einstieg_score", 0) or 0), translate_status(d.get("i_status", "")))
        self.entry_text.setText(d.get("i_text", ""))
        trend = d.get("trend", {}) or {}
        self.entry_facts.setText(
            f"Trend-Score   {trend.get('trend_score', '—')}/100\n"
            f"3M Momentum   {pct(trend.get('momentum_3m'), signed=True)}\n"
            f"52W Drawdown  {pct(trend.get('drawdown'))}"
        )

        strengths = list(d.get("staerken", []))[:5]
        warnings = list(d.get("warnungen", []))[:4]
        if strengths:
            self.strengths.setText("\n".join([f"✓  {x}" for x in strengths]))
            self.strengths.setStyleSheet(f"color:{GREEN};")
        else:
            self.strengths.setText("Keine besonderen Stärken verfügbar.")
            self.strengths.setStyleSheet(f"color:{TEXT_2};")
        if warnings:
            self.warnings.setText("\n".join([f"△  {x}" for x in warnings]))
            self.warnings.setStyleSheet(f"color:{ORANGE};")
        else:
            self.warnings.setText("✓  Keine größeren Warnsignale erkannt.")
            self.warnings.setStyleSheet(f"color:{GREEN};")

        info = d.get("info", {}) or {}
        self.quality_body.set_values({
            "roe": ratio_percent(wert(info, 'returnOnEquity')),
            "net_margin": ratio_percent(wert(info, 'profitMargins')),
            "fcf_margin": ratio_percent(d.get('fcf_marge')),
        })
        self.dev_body.set_values({
            "revenue_growth": ratio_percent(wert(info, 'revenueGrowth')),
            "multi_year": f"{d.get('entwicklungs_score', '—')}/100",
            "trend_score": f"{trend.get('trend_score', '—')}/100",
        })
        self.val_body.set_values({
            "pe": number(wert(info, 'trailingPE'), 1),
            "forward_pe": number(wert(info, 'forwardPE'), 1),
            "peg": number(wert(info, 'pegRatio'), 2),
        })
        self.risk_body.set_values({
            "drawdown": pct(trend.get('drawdown')),
            "trap": f"{d.get('trap_score', '—')}/100",
            "debt_cash": number(d.get('debt_cash'), 2),
        })
        self.set_watchlist_state(in_watchlist)


class WatchlistPage(QWidget):
    open_symbol = Signal(str)
    remove_symbol = Signal(str)
    refresh_all = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        tbox = QVBoxLayout()
        title = QLabel("Watchlist")
        title.setObjectName("PageTitle")
        self.subtitle = QLabel("0 Aktien gespeichert")
        self.subtitle.setObjectName("Muted")
        tbox.addWidget(title)
        tbox.addWidget(self.subtitle)
        top.addLayout(tbox)
        top.addStretch(1)
        self.open_btn = QPushButton("Analyse öffnen")
        self.remove_btn = QPushButton("Entfernen")
        self.remove_btn.setObjectName("Danger")
        self.refresh_btn = QPushButton("↻ Alle aktualisieren")
        self.refresh_btn.setObjectName("Primary")
        self.open_btn.clicked.connect(self._open)
        self.remove_btn.clicked.connect(self._remove)
        self.refresh_btn.clicked.connect(self.refresh_all.emit)
        top.addWidget(self.open_btn)
        top.addWidget(self.remove_btn)
        top.addWidget(self.refresh_btn)
        root.addLayout(top)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Unternehmen", "Kurs", "U-Score", "Einstieg", "Δ E", "Trap", "Status", "Aktualisiert"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._open)
        root.addWidget(self.table, 1)

    def set_watchlist(self, watchlist: dict):
        self.table.setSortingEnabled(False)
        records = list((watchlist or {}).values())
        self.subtitle.setText(f"{len(records)} Aktien gespeichert · Doppelklick öffnet die Analyse")
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            kurs = _finite(r.get("kurs"))
            kurs_txt = "—" if kurs is None else f"{kurs:.2f} {r.get('waehrung', '')}"
            de = r.get("delta_einstieg_score")
            de_txt = "—" if de is None else f"{de:+d}"
            values = [
                r.get("symbol", ""), r.get("name", ""), kurs_txt,
                r.get("unternehmensscore", "—"), r.get("einstieg_score", "—"),
                de_txt, r.get("trap_score", "—"), r.get("status", ""), r.get("updated", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (3, 4, 6):
                    raw = r.get({3: "unternehmensscore", 4: "einstieg_score", 6: "trap_score"}[col])
                    if isinstance(raw, (int, float)):
                        item.setData(Qt.ItemDataRole.UserRole, raw)
                if col == 5 and isinstance(de, (int, float)):
                    item.setForeground(QColor(GREEN if de > 0 else RED if de < 0 else TEXT_2))
                if col == 7:
                    item.setForeground(QColor(status_color(str(value))))
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(4, Qt.SortOrder.DescendingOrder)

    def selected_symbol(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.text().strip().upper() if item else None

    def _open(self):
        symbol = self.selected_symbol()
        if symbol:
            self.open_symbol.emit(symbol)

    def _remove(self):
        symbol = self.selected_symbol()
        if symbol:
            self.remove_symbol.emit(symbol)


class SignalsPage(QWidget):
    open_symbol = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.watchlist = {}
        self.candidates = {}
        root=QVBoxLayout(self); root.setContentsMargins(30,24,30,30); root.setSpacing(16)
        title=QLabel(loc("Signale","Signals")); title.setObjectName("PageTitle")
        sub=QLabel(loc("Watchlist-Signale und die Ergebnisse des letzten AutoTrader-Scans an einem Ort.","Watchlist signals and results of the latest AutoTrader scan in one place.")); sub.setObjectName("Muted")
        root.addWidget(title); root.addWidget(sub)

        metrics=QHBoxLayout(); metrics.setSpacing(12); self.metric_labels={}
        for key,label,color in [("interesting",loc("Interessant","Interesting"),GREEN),("watch",loc("Beobachten","Watching"),YELLOW),("ready",loc("AutoTrader frei","AutoTrader ready"),BLUE_2),("risk",loc("Blockiert / Risiko","Blocked / risk"),RED)]:
            card=Card(); lay=QVBoxLayout(card); lay.setContentsMargins(16,13,16,13); t=QLabel(label.upper()); t.setObjectName("Eyebrow"); v=QLabel("0"); v.setStyleSheet(f"font-size:25px;font-weight:760;color:{color};"); lay.addWidget(t); lay.addWidget(v); metrics.addWidget(card,1); self.metric_labels[key]=v
        root.addLayout(metrics)

        card=Card(); lay=QVBoxLayout(card); lay.setContentsMargins(18,16,18,16); lay.setSpacing(10)
        head=QHBoxLayout(); st=info_title(loc("Aktuelle Signale","Current signals"),loc("Zeigt Signale aus deiner Watchlist und die Entscheidungen des letzten AutoTrader-Scans. Ein AutoTrader-Signal ist keine Gewinnwahrscheinlichkeit.","Shows signals from your watchlist and decisions from the latest AutoTrader scan. An AutoTrader signal is not a probability of profit."),"SectionTitle"); head.addWidget(st); head.addStretch(1); self.summary=QLabel(loc("Noch keine Daten","No data yet")); self.summary.setObjectName("Muted"); head.addWidget(self.summary); lay.addLayout(head)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels([loc("QUELLE","SOURCE"),"SYMBOL",loc("UNTERNEHMEN","COMPANY"),"U","E","TRAP",loc("SIGNAL","SIGNAL"),loc("BESTÄTIGUNG","CONFIRMATION"),loc("GRUND","REASON")])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch); self.table.horizontalHeader().setSectionResizeMode(8,QHeaderView.ResizeMode.Stretch)
        for c_ in [3,4,5,6,7]: self.table.horizontalHeader().setSectionResizeMode(c_,QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.cellDoubleClicked.connect(self._open)
        lay.addWidget(self.table); root.addWidget(card,1)

    def set_watchlist(self, watchlist: dict):
        self.watchlist = watchlist or {}
        self._rebuild()

    def set_autotrader_candidates(self, candidates: dict):
        self.candidates = candidates or {}
        self._rebuild()

    def _rebuild(self):
        rows=[]
        interesting=watch=ready=risk=0
        for rec in self.watchlist.values():
            status=str(rec.get("status","") or "")
            up=status.upper()
            if "INTERESSANT" in up or "INTERESTING" in up: interesting+=1
            if "BEOBACHTEN" in up or up=="WATCH": watch+=1
            if "RISIK" in up or "RISK" in up: risk+=1
            delta=rec.get("delta_einstieg_score")
            reason=loc("Watchlist-Status", "Watchlist status")
            if isinstance(delta,(int,float)) and delta:
                reason=loc(f"Einstiegsscore seit letzter Analyse {int(delta):+d}",f"Entry score since last analysis {int(delta):+d}")
            rows.append({"source":"Watchlist","symbol":rec.get("symbol",""),"name":rec.get("name",""),"u":rec.get("unternehmensscore"),"e":rec.get("einstieg_score"),"trap":rec.get("trap_score"),"signal":translate_status(status),"confidence":"—","reason":reason,"color":status_color(status),"priority":1})
        dm={"READY":loc("Freigegeben","Ready"),"WAIT":loc("Beobachten","Watch"),"REJECT":loc("Abgelehnt","Rejected"),"BLOCKED":loc("Gesperrt","Blocked"),"ERROR":loc("Fehler","Error")}
        colors={"READY":GREEN,"WAIT":YELLOW,"REJECT":ORANGE,"BLOCKED":RED,"ERROR":RED}
        for rec in self.candidates.values():
            d=rec.get("decision")
            if d=="READY": ready+=1
            if d in {"BLOCKED","ERROR"}: risk+=1
            rows.append({"source":"AutoTrader","symbol":rec.get("symbol",""),"name":rec.get("name",""),"u":rec.get("company"),"e":rec.get("entry"),"trap":rec.get("trap"),"signal":dm.get(d,str(d or "—")),"confidence":f"{int(rec.get('confidence',0) or 0)}/100","reason":rec.get("filter_text","") or "—","color":colors.get(d,TEXT_2),"priority":0 if d=="READY" else 2})
        self.metric_labels["interesting"].setText(str(interesting)); self.metric_labels["watch"].setText(str(watch)); self.metric_labels["ready"].setText(str(ready)); self.metric_labels["risk"].setText(str(risk))
        rows.sort(key=lambda x:(x.get("priority",9),-(_finite(x.get("e"),0) or 0),str(x.get("symbol",""))))
        self.summary.setText(loc(f"{len(rows)} Einträge · Doppelklick öffnet Analyse",f"{len(rows)} entries · double-click opens analysis"))
        self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[row["source"],row["symbol"],row["name"],"—" if _finite(row["u"]) is None else str(int(round(_finite(row["u"])))),"—" if _finite(row["e"]) is None else str(int(round(_finite(row["e"])))),"—" if _finite(row["trap"]) is None else str(int(round(_finite(row["trap"])))),row["signal"],row["confidence"],row["reason"]]
            for c_,v in enumerate(vals):
                item=QTableWidgetItem(str(v)); item.setData(Qt.ItemDataRole.UserRole,row["symbol"])
                if c_==6: item.setForeground(QColor(row["color"]))
                self.table.setItem(r,c_,item)

    def _open(self,row,col):
        item=self.table.item(row,1)
        if item and item.text(): self.open_symbol.emit(item.text())


class HistoryPage(QWidget):
    open_symbol = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Verlauf")
        title.setObjectName("PageTitle")
        sub = QLabel("Gespeicherte Analysestände deiner Watchlist-Aktien.")
        sub.setObjectName("Muted")
        root.addWidget(title)
        root.addWidget(sub)
        root.addSpacing(10)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Datum", "Symbol", "Unternehmen", "U-Score", "Einstieg", "Trap", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._open)
        root.addWidget(self.table, 1)

    def set_watchlist(self, watchlist: dict):
        rows = []
        for symbol, record in (watchlist or {}).items():
            history = list(record.get("history", [])) + [record]
            for snap in history:
                rows.append((symbol, snap))
        rows.sort(key=lambda x: str(x[1].get("updated", "")), reverse=True)
        self.table.setRowCount(len(rows))
        for row, (symbol, r) in enumerate(rows):
            vals = [
                r.get("updated", ""), symbol, r.get("name", ""),
                r.get("unternehmensscore", "—"), r.get("einstieg_score", "—"),
                r.get("trap_score", "—"), r.get("status", ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if col == 6:
                    item.setForeground(QColor(status_color(str(val))))
                self.table.setItem(row, col, item)

    def _open(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 1)
            if item:
                self.open_symbol.emit(item.text())


class SettingsPage(QWidget):
    setting_changed = Signal(str, object)
    portfolio_changed = Signal()

    def __init__(self, config: dict, broker: PaperBroker, parent=None):
        super().__init__(parent)
        self.config = dict(config)
        self.broker = broker
        # eToro client belongs to SettingsPage because all eToro live controls
        # below call self.etoro. 0.9.11 accidentally initialized it only on
        # BotPage, which caused an AttributeError during application startup.
        self.etoro = EtoroLiveBroker(APP_DIR)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("PageSurface")
        root = QVBoxLayout(page)
        root.setContentsMargins(32, 26, 32, 28)
        root.setSpacing(18)
        scroll.setWidget(page)
        outer.addWidget(scroll)

        title = QLabel(tr("settings.title"))
        title.setObjectName("PageTitle")
        sub = QLabel(tr("settings.subtitle"))
        sub.setObjectName("Muted")
        root.addWidget(title)
        root.addWidget(sub)

        appearance = Card()
        al = QVBoxLayout(appearance)
        al.setContentsMargins(22, 20, 22, 20)
        al.setSpacing(12)
        ah = QLabel(tr("settings.appearance"))
        ah.setObjectName("SectionTitle")
        ahelp = QLabel(tr("settings.appearance_help"))
        ahelp.setObjectName("Muted")
        ahelp.setWordWrap(True)
        al.addWidget(ah)
        al.addWidget(ahelp)

        theme_row = QHBoxLayout()
        theme_label = QLabel(tr("settings.theme"))
        theme_label.setMinimumWidth(180)
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(220)
        self.theme_combo.addItem(tr("settings.dark"), "dark")
        self.theme_combo.addItem(tr("settings.light"), "light")
        idx = self.theme_combo.findData(self.config.get("theme", "dark"))
        self.theme_combo.setCurrentIndex(max(0, idx))
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        theme_row.addWidget(theme_label)
        theme_row.addStretch(1)
        theme_row.addWidget(self.theme_combo)
        al.addLayout(theme_row)
        root.addWidget(appearance)

        language = Card()
        ll = QVBoxLayout(language)
        ll.setContentsMargins(22, 20, 22, 20)
        ll.setSpacing(12)
        lh = QLabel(tr("settings.language"))
        lh.setObjectName("SectionTitle")
        lhelp = QLabel(tr("settings.language_help"))
        lhelp.setObjectName("Muted")
        lhelp.setWordWrap(True)
        ll.addWidget(lh)
        ll.addWidget(lhelp)
        lang_row = QHBoxLayout()
        lang_label = QLabel(tr("settings.language"))
        lang_label.setMinimumWidth(180)
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(220)
        self.language_combo.addItem(tr("settings.german"), "de")
        self.language_combo.addItem(tr("settings.english"), "en")
        idx = self.language_combo.findData(self.config.get("language", "de"))
        self.language_combo.setCurrentIndex(max(0, idx))
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        lang_row.addWidget(lang_label)
        lang_row.addStretch(1)
        lang_row.addWidget(self.language_combo)
        ll.addLayout(lang_row)
        root.addWidget(language)

        refresh_card = Card()
        rl = QVBoxLayout(refresh_card)
        rl.setContentsMargins(22, 20, 22, 20)
        rl.setSpacing(12)
        rh = QLabel(loc("Datenaktualisierung", "Data refresh"))
        rh.setObjectName("SectionTitle")
        rhelp = QLabel(loc(
            "TradePilot kann Kurse offener Paper-Positionen automatisch über Yahoo Finance aktualisieren. "
            "Das ist Polling und keine garantierte Börsen-Echtzeitversorgung. Ein kompletter AutoTrader-Scan "
            "läuft getrennt und kann optional zeitgesteuert werden.",
            "TradePilot can automatically refresh prices of open paper positions through Yahoo Finance. "
            "This is polling, not guaranteed exchange-grade real-time data. Full AutoTrader scans run "
            "separately and can optionally be scheduled."))
        rhelp.setObjectName("Muted")
        rhelp.setWordWrap(True)
        rl.addWidget(rh)
        rl.addWidget(rhelp)

        erow = QHBoxLayout()
        elabel = QLabel(loc("Automatische Kursaktualisierung", "Automatic price refresh"))
        elabel.setMinimumWidth(220)
        self.refresh_enabled_combo = QComboBox()
        self.refresh_enabled_combo.setMinimumWidth(220)
        self.refresh_enabled_combo.addItem(loc("Aktiv", "Enabled"), True)
        self.refresh_enabled_combo.addItem(loc("Aus", "Off"), False)
        self.refresh_enabled_combo.setCurrentIndex(max(0, self.refresh_enabled_combo.findData(bool(self.config.get("auto_refresh_enabled", True)))))
        self.refresh_enabled_combo.currentIndexChanged.connect(self._refresh_enabled_changed)
        erow.addWidget(elabel); erow.addStretch(1); erow.addWidget(self.refresh_enabled_combo)
        rl.addLayout(erow)

        irow = QHBoxLayout()
        ilabel = QLabel(loc("Kursintervall", "Price interval"))
        ilabel.setMinimumWidth(220)
        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.setMinimumWidth(220)
        for text, value in [(loc("30 Sekunden", "30 seconds"),30),(loc("60 Sekunden", "60 seconds"),60),(loc("2 Minuten", "2 minutes"),120),(loc("5 Minuten", "5 minutes"),300)]:
            self.refresh_interval_combo.addItem(text, value)
        self.refresh_interval_combo.setCurrentIndex(max(0, self.refresh_interval_combo.findData(int(self.config.get("quote_refresh_seconds",60)))))
        self.refresh_interval_combo.currentIndexChanged.connect(self._refresh_interval_changed)
        irow.addWidget(ilabel); irow.addStretch(1); irow.addWidget(self.refresh_interval_combo)
        rl.addLayout(irow)

        srow = QHBoxLayout()
        slabel = QLabel(loc("Automatische AutoTrader-Scans", "Automatic AutoTrader scans"))
        slabel.setMinimumWidth(220)
        self.auto_scan_enabled_combo = QComboBox()
        self.auto_scan_enabled_combo.setMinimumWidth(220)
        self.auto_scan_enabled_combo.addItem(loc("Aus", "Off"), False)
        self.auto_scan_enabled_combo.addItem(loc("Aktiv", "Enabled"), True)
        self.auto_scan_enabled_combo.setCurrentIndex(max(0, self.auto_scan_enabled_combo.findData(bool(self.config.get("auto_scan_enabled",False)))))
        self.auto_scan_enabled_combo.currentIndexChanged.connect(self._auto_scan_enabled_changed)
        srow.addWidget(slabel); srow.addStretch(1); srow.addWidget(self.auto_scan_enabled_combo)
        rl.addLayout(srow)

        sirow = QHBoxLayout()
        silabel = QLabel(loc("Scan-Intervall", "Scan interval"))
        silabel.setMinimumWidth(220)
        self.auto_scan_interval_combo = QComboBox()
        self.auto_scan_interval_combo.setMinimumWidth(220)
        for text, value in [(loc("5 Minuten", "5 minutes"),5),(loc("15 Minuten", "15 minutes"),15),(loc("30 Minuten", "30 minutes"),30),(loc("60 Minuten", "60 minutes"),60)]:
            self.auto_scan_interval_combo.addItem(text, value)
        self.auto_scan_interval_combo.setCurrentIndex(max(0, self.auto_scan_interval_combo.findData(int(self.config.get("auto_scan_minutes",15)))))
        self.auto_scan_interval_combo.currentIndexChanged.connect(self._auto_scan_interval_changed)
        sirow.addWidget(silabel); sirow.addStretch(1); sirow.addWidget(self.auto_scan_interval_combo)
        rl.addLayout(sirow)

        warn = QLabel(loc(
            "Hinweis: Ist AutoTrader aktiv, können zeitgesteuerte Scans Paper-Trades eröffnen oder schließen. "
            "Automatische eToro-LIVE-Orders bleiben in 0.9.12 deaktiviert; nur ein doppelt bestätigter manueller Echtgeld-Test bis 10 EUR ist möglich.",
            "Note: If AutoTrader is active, scheduled scans may open or close paper trades. "
            "Automatic broker orders remain disabled in 0.9.11; only confirmed manual eToro live tests are available."))
        warn.setWordWrap(True)
        warn.setStyleSheet(f"color:{YELLOW};")
        rl.addWidget(warn)
        root.addWidget(refresh_card)
        self._sync_refresh_controls()

        paper = Card()
        pl = QVBoxLayout(paper); pl.setContentsMargins(22,20,22,20); pl.setSpacing(12)
        ph = QLabel(loc("Paper Trading","Paper trading")); ph.setObjectName("SectionTitle")
        phelp = QLabel(loc("Startkapital für neue Paper-Konten und sichere Testfunktionen. Das Zurücksetzen löscht ausschließlich simulierte Positionen und Trades.","Start capital for new paper accounts and safe testing. Resetting deletes simulated positions and trades only.")); phelp.setObjectName("Muted"); phelp.setWordWrap(True)
        pl.addWidget(ph); pl.addWidget(phelp)
        prow = QHBoxLayout(); pcap = QLabel(loc("Startkapital","Start capital")); pcap.setMinimumWidth(180); self.paper_capital = QLineEdit(f"{float(self.config.get('demo_capital',10000.0)):.2f}"); self.paper_capital.setMaximumWidth(220); self.paper_capital.editingFinished.connect(self._paper_capital_changed); prow.addWidget(pcap); prow.addStretch(1); prow.addWidget(self.paper_capital); pl.addLayout(prow)
        mrow = QHBoxLayout(); mlab = info_title(loc("Maximalbetrag pro Trade","Maximum per trade"),loc("Harte Obergrenze für jede neue Position. Der Risk Manager darf abhängig von Signalstärke, Volatilität und Risikoprofil weniger investieren, aber niemals mehr als diesen Betrag.","Hard cap for every new position. The Risk Manager may invest less depending on signal strength, volatility and risk profile, but never more than this amount."),"Muted"); self.max_trade_input = QLineEdit(f"{float(self.config.get('max_trade_value',1000.0)):.2f}"); self.max_trade_input.setMaximumWidth(220); self.max_trade_input.editingFinished.connect(self._max_trade_changed); mrow.addWidget(mlab); mrow.addStretch(1); mrow.addWidget(self.max_trade_input); pl.addLayout(mrow)
        sliprow=QHBoxLayout(); sl=info_title(loc("Paper-Slippage","Paper slippage"),loc("Simuliert eine kleine ungünstige Abweichung zwischen beobachtetem Marktkurs und tatsächlichem Paper-Ausführungskurs. BUY wird etwas teurer, SELL etwas günstiger ausgeführt.","Simulates a small adverse difference between the observed market quote and the paper fill price. BUY fills slightly higher, SELL slightly lower."),"Muted"); self.slippage_combo=QComboBox(); self.slippage_combo.setMinimumWidth(220)
        for text,value in [("0 bp",0.0),("2 bp",2.0),("5 bp",5.0),("10 bp",10.0)]: self.slippage_combo.addItem(text,value)
        self.slippage_combo.setCurrentIndex(max(0,self.slippage_combo.findData(float(self.config.get("paper_slippage_bps",5.0))))); self.slippage_combo.currentIndexChanged.connect(self._slippage_changed); sliprow.addWidget(sl); sliprow.addStretch(1); sliprow.addWidget(self.slippage_combo); pl.addLayout(sliprow)
        rrow = QHBoxLayout(); self.paper_state = QLabel(""); self.paper_state.setObjectName("Muted"); rrow.addWidget(self.paper_state); rrow.addStretch(1); reset = QPushButton(loc("Paper-Konto zurücksetzen","Reset paper account")); reset.setObjectName("Danger"); reset.clicked.connect(self._reset_paper); rrow.addWidget(reset); pl.addLayout(rrow)
        root.addWidget(paper)
        self._refresh_paper_state()

        etoro = Card()
        etl = QVBoxLayout(etoro); etl.setContentsMargins(22,20,22,20); etl.setSpacing(12)
        eth = QLabel(loc("eToro REAL API", "eToro REAL API")); eth.setObjectName("SectionTitle")
        ethelp = QLabel(loc(
            "0.9.12 verbindet TradePilot mit der eToro-REAL-API. Zugangsdaten bleiben lokal in .env. LIVE-Orders sind nur manuell nach Doppelbestätigung möglich; AutoTrader→eToro LIVE bleibt in dieser Version gesperrt.",
            "0.9.12 connects TradePilot to the eToro REAL API. Credentials stay local in .env. LIVE orders are manual-only with double confirmation; AutoTrader→eToro LIVE remains disabled in this version."))
        ethelp.setObjectName("Muted"); ethelp.setWordWrap(True); etl.addWidget(eth); etl.addWidget(ethelp)

        apirow=QHBoxLayout(); apil=QLabel("API Key"); apil.setMinimumWidth(180); self.etoro_api_key=QLineEdit(); self.etoro_api_key.setPlaceholderText(loc("Public API Key", "Public API Key")); apirow.addWidget(apil); apirow.addStretch(1); apirow.addWidget(self.etoro_api_key); etl.addLayout(apirow)
        userrow=QHBoxLayout(); userl=QLabel("User Key (REAL)"); userl.setMinimumWidth(180); self.etoro_user_key=QLineEdit(); self.etoro_user_key.setEchoMode(QLineEdit.EchoMode.Password); self.etoro_user_key.setPlaceholderText(loc("REAL User Key", "REAL User Key")); userrow.addWidget(userl); userrow.addStretch(1); userrow.addWidget(self.etoro_user_key); etl.addLayout(userrow)

        saved_api, saved_user = self.etoro.credentials()
        if saved_api: self.etoro_api_key.setText(saved_api)
        if saved_user: self.etoro_user_key.setText(saved_user)

        btnrow=QHBoxLayout(); self.etoro_status=QLabel(loc("Nicht getestet", "Not tested")); self.etoro_status.setObjectName("Muted"); btnrow.addWidget(self.etoro_status); btnrow.addStretch(1)
        savebtn=QPushButton(loc("Keys lokal speichern", "Save keys locally")); savebtn.clicked.connect(self._etoro_save_keys); btnrow.addWidget(savebtn)
        testbtn=QPushButton(loc("Verbindung testen", "Test connection")); testbtn.setObjectName("Primary"); testbtn.clicked.connect(self._etoro_test_connection); btnrow.addWidget(testbtn); etl.addLayout(btnrow)

        orderrow=QHBoxLayout(); syml=QLabel(loc("Manueller LIVE-Test", "Manual LIVE test")); syml.setMinimumWidth(180); self.etoro_symbol=QLineEdit("AAPL"); self.etoro_symbol.setMaximumWidth(120); self.etoro_amount=QLineEdit("10"); self.etoro_amount.setMaximumWidth(120); orderbtn=QPushButton(loc("LIVE BUY senden", "Send LIVE BUY")); orderbtn.setObjectName("Danger"); orderbtn.clicked.connect(self._etoro_manual_buy); orderrow.addWidget(syml); orderrow.addStretch(1); orderrow.addWidget(self.etoro_symbol); orderrow.addWidget(self.etoro_amount); orderrow.addWidget(orderbtn); etl.addLayout(orderrow)
        orderhint=QLabel(loc("ECHTGELD: Harte Obergrenze 10,00 EUR pro Order. TradePilot rechnet den Betrag mit einem frischen EUR/USD-Kurs in den von eToro dokumentierten USD-Orderbetrag um. Falls FX nicht geladen werden kann oder bereits eine offene REAL-Position existiert, wird die Order blockiert. Hebel bleibt 1. AutoTrader→LIVE ist gesperrt.", "REAL MONEY: hard limit EUR 10.00 per order. TradePilot converts the budget with a fresh EUR/USD quote to the documented USD order amount. If FX cannot be loaded or a REAL position already exists, the order is blocked. Leverage stays at 1. AutoTrader→LIVE is disabled.")); orderhint.setObjectName("Muted"); orderhint.setWordWrap(True); etl.addWidget(orderhint)
        root.addWidget(etoro)

        info = Card()
        il = QVBoxLayout(info)
        il.setContentsMargins(22, 20, 22, 20)
        st = QLabel(tr("settings.info"))
        st.setObjectName("SectionTitle")
        details = QLabel(
            f"TradePilot {VERSION}\n\n"
            "PySide6 / Qt 6\n"
            "Yahoo Finance via yfinance\n"
            "Research Engine 0.6.1\n"
            "Watchlist + Einstellungen lokal gespeichert\n"
            "AutoTrader 0.9.12: eToro REAL API + manueller LIVE-Sicherheitstest bis 10 EUR; AutoTrader→eToro LIVE weiterhin gesperrt"
        )
        details.setObjectName("Muted")
        il.addWidget(st)
        il.addWidget(details)
        root.addWidget(info)
        root.addStretch(1)

    def _sync_refresh_controls(self):
        enabled = bool(self.refresh_enabled_combo.currentData()) if hasattr(self, "refresh_enabled_combo") else True
        auto_scan = bool(self.auto_scan_enabled_combo.currentData()) if hasattr(self, "auto_scan_enabled_combo") else False
        if hasattr(self, "refresh_interval_combo"):
            self.refresh_interval_combo.setEnabled(enabled)
        if hasattr(self, "auto_scan_interval_combo"):
            self.auto_scan_interval_combo.setEnabled(auto_scan)

    def _refresh_enabled_changed(self):
        value = bool(self.refresh_enabled_combo.currentData())
        self.config["auto_refresh_enabled"] = value
        self._sync_refresh_controls()
        self.setting_changed.emit("auto_refresh_enabled", value)

    def _refresh_interval_changed(self):
        value = int(self.refresh_interval_combo.currentData() or 60)
        self.config["quote_refresh_seconds"] = value
        self.setting_changed.emit("quote_refresh_seconds", value)

    def _auto_scan_enabled_changed(self):
        value = bool(self.auto_scan_enabled_combo.currentData())
        self.config["auto_scan_enabled"] = value
        self._sync_refresh_controls()
        self.setting_changed.emit("auto_scan_enabled", value)

    def _auto_scan_interval_changed(self):
        value = int(self.auto_scan_interval_combo.currentData() or 15)
        self.config["auto_scan_minutes"] = value
        self.setting_changed.emit("auto_scan_minutes", value)

    def _slippage_changed(self):
        value=float(self.slippage_combo.currentData() or 0.0)
        self.config["paper_slippage_bps"]=value
        self.setting_changed.emit("paper_slippage_bps",value)

    def _max_trade_changed(self):
        try:
            value=max(1.0,float(self.max_trade_input.text().replace(" ","").replace(",",".")))
        except Exception:
            value=float(self.config.get("max_trade_value",1000.0))
        self.max_trade_input.setText(f"{value:.2f}")
        self.config["max_trade_value"]=value
        self.setting_changed.emit("max_trade_value",value)

    def _paper_capital_value(self):
        try:
            return max(100.0, float(self.paper_capital.text().replace(" ","").replace(",",".")))
        except Exception:
            return float(self.config.get("demo_capital",10000.0))

    def _paper_capital_changed(self):
        value=self._paper_capital_value(); self.paper_capital.setText(f"{value:.2f}"); self.config["demo_capital"]=value; self.setting_changed.emit("demo_capital",value)

    def _refresh_paper_state(self):
        cur=self.broker.state.get("currency","USD")
        self.paper_state.setText(loc(f"Aktuell: {self.broker.equity():,.2f} {cur} · Cash {self.broker.cash:,.2f} {cur} · {self.broker.open_count()} offene Positionen · {self.broker.pending_count()} vorgemerkte Orders",f"Current: {self.broker.equity():,.2f} {cur} · Cash {self.broker.cash:,.2f} {cur} · {self.broker.open_count()} open positions · {self.broker.pending_count()} pending orders"))

    def _reset_paper(self):
        value=self._paper_capital_value()
        ans=QMessageBox.question(self,"TradePilot",loc(f"Paper-Konto wirklich auf {value:,.2f} USD zurücksetzen?\nAlle simulierten Positionen und Trades werden gelöscht.",f"Really reset the paper account to {value:,.2f} USD?\nAll simulated positions and trades will be deleted."),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans!=QMessageBox.StandardButton.Yes: return
        self.config["demo_capital"]=value; self.setting_changed.emit("demo_capital",value); self.broker.reset(value); self._refresh_paper_state(); self.portfolio_changed.emit()

    def _etoro_save_keys(self):
        try:
            self.etoro.save_credentials(self.etoro_api_key.text(), self.etoro_user_key.text())
            self.etoro_status.setText(loc("REAL-Keys lokal gespeichert (.env)", "REAL keys saved locally (.env)"))
            self.etoro_status.setStyleSheet(f"color:{GREEN};")
        except Exception as exc:
            QMessageBox.warning(self, "TradePilot", str(exc))

    def _etoro_test_connection(self):
        try:
            self.etoro.save_credentials(self.etoro_api_key.text(), self.etoro_user_key.text())
            result = self.etoro.test_connection()
            parts=[loc("REAL verbunden", "REAL connected")]
            if result.get("equity") is not None: parts.append(f"Equity {result.get('equity')}")
            if result.get("buying_power") is not None: parts.append(f"Buying Power {result.get('buying_power')}")
            if result.get("positions") is not None: parts.append(loc(f"{result.get('positions')} Positionen", f"{result.get('positions')} positions"))
            self.etoro_status.setText(" · ".join(parts)); self.etoro_status.setStyleSheet(f"color:{GREEN};")
        except Exception as exc:
            self.etoro_status.setText(loc("REAL-Verbindung fehlgeschlagen", "REAL connection failed")); self.etoro_status.setStyleSheet(f"color:{RED};")
            QMessageBox.warning(self, "eToro REAL", str(exc))

    def _etoro_manual_buy(self):
        symbol=self.etoro_symbol.text().strip().upper()
        try:
            amount=float(self.etoro_amount.text().replace(",","."))
        except Exception:
            amount=0.0
        if not symbol or amount <= 0 or amount > 10.0:
            QMessageBox.warning(self,"eToro REAL",loc("Ticker angeben und EUR-Budget zwischen 0,01 und 10,00 wählen.","Enter a ticker and choose an EUR budget between 0.01 and 10.00.")); return
        try:
            self.etoro.save_credentials(self.etoro_api_key.text(), self.etoro_user_key.text())
            usd, fx = self.etoro.live_amount_usd_for_eur_budget(amount)
        except Exception as exc:
            QMessageBox.warning(self,"eToro REAL",str(exc)); return
        ans=QMessageBox.question(self,"eToro REAL — ECHTGELD",loc(
            f"ACHTUNG: Diese Order verwendet echtes Geld.\n\n{symbol} · Budget {amount:.2f} EUR ≈ {usd:.2f} USD\nEUR/USD {fx:.4f} · Hebel 1\n\nWirklich fortfahren?",
            f"WARNING: This order uses real money.\n\n{symbol} · budget EUR {amount:.2f} ≈ USD {usd:.2f}\nEUR/USD {fx:.4f} · leverage 1\n\nReally continue?"),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if ans!=QMessageBox.StandardButton.Yes: return
        text, ok = QInputDialog.getText(self, "LIVE-Bestätigung", loc("Zur endgültigen Bestätigung LIVE eintippen:", "Type LIVE to confirm:"))
        if not ok or text.strip().upper() != "LIVE":
            QMessageBox.information(self,"eToro REAL",loc("LIVE-Order abgebrochen.","LIVE order cancelled.")); return
        try:
            result=self.etoro.place_live_market_buy(symbol, amount)
            response=result.get("response")
            QMessageBox.information(self,"eToro REAL",loc(
                f"LIVE-Order wurde an eToro gesendet.\n\nBudget: {result.get('budget_eur'):.2f} EUR\nGesendet: {result.get('amount_usd'):.2f} USD\nInstrument-ID: {result.get('instrument_id')}\nAntwort: {response}",
                f"LIVE order sent to eToro.\n\nBudget: EUR {result.get('budget_eur'):.2f}\nSent: USD {result.get('amount_usd'):.2f}\nInstrument ID: {result.get('instrument_id')}\nResponse: {response}"))
            self._etoro_test_connection()
        except Exception as exc:
            QMessageBox.warning(self,"eToro REAL",str(exc))

    def _theme_changed(self):
        value = self.theme_combo.currentData()
        if value and value != self.config.get("theme"):
            self.config["theme"] = value
            self.setting_changed.emit("theme", value)

    def _language_changed(self):
        value = self.language_combo.currentData()
        if value and value != self.config.get("language"):
            self.config["language"] = value
            self.setting_changed.emit("language", value)


# -----------------------------------------------------------------------------
# Hauptfenster
# -----------------------------------------------------------------------------
class TradePilotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TradePilot {VERSION}")
        self.resize(1500, 920)
        self.setMinimumSize(1180, 760)
        self.current_data = None
        self.analysis_threads: list[QThread] = []
        self.refresh_thread = None
        self.quote_refresh_thread = None
        self._quote_results: dict[str, dict] = {}
        self._quote_failures: dict[str, str] = {}
        self._last_exit_alerts: dict[str, str] = {}
        app_dir = Path(__file__).resolve().parent
        self.app_dir = app_dir
        self.config = load_config(app_dir)
        set_theme(self.config.get("theme", "dark"))
        set_language(self.config.get("language", "de"))
        refresh_theme_tokens()
        QApplication.instance().setStyleSheet(QSS)
        self.watch_path = watchlist_path(app_dir)
        # Migration aus der bisherigen Ein-Datei-Version: Liegt die alte
        # TradePilot_watchlist.json direkt im übergeordneten C:\TradePilot-Ordner,
        # wird sie automatisch weiterverwendet.
        legacy_path = app_dir.parent / "TradePilot_watchlist.json"
        if not self.watch_path.exists() and legacy_path.exists():
            self.watch_path = legacy_path
        self.watchlist = load_watchlist(self.watch_path)
        self.paper_broker = PaperBroker(app_dir / "tradepilot_paper_portfolio.json", self.config.get("demo_capital", 10000.0), "USD")
        if not self.paper_broker.state.get("equity_history"):
            self.paper_broker.record_equity_snapshot("STARTUP", 0)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_topbar())
        right.addWidget(self._build_market_bar())

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.analysis = AnalysisPage()
        self.watchpage = WatchlistPage()
        self.portfolio = PaperPortfolioPage(self.paper_broker)
        self.performance_risk = PerformanceRiskPage(self.paper_broker, self.config)
        self.signals = SignalsPage()
        self.bot = BotPage(self.config, self.paper_broker)
        self.history = HistoryPage()
        self.settings = SettingsPage(self.config, self.paper_broker)

        for page in (self.dashboard, self.analysis, self.watchpage, self.portfolio, self.performance_risk, self.signals, self.bot, self.history, self.settings):
            self.stack.addWidget(page)
        right.addWidget(self.stack, 1)
        right.addWidget(self._build_footer())
        layout.addLayout(right, 1)

        self.dashboard.open_analysis.connect(self.run_analysis)
        self.dashboard.open_watchlist.connect(lambda: self.navigate(2))
        self.watchpage.open_symbol.connect(self.run_analysis)
        self.watchpage.remove_symbol.connect(self.remove_from_watchlist)
        self.watchpage.refresh_all.connect(self.refresh_watchlist)
        self.history.open_symbol.connect(self.run_analysis)
        self.signals.open_symbol.connect(self.run_analysis)
        self.analysis.add_to_watchlist.connect(self.add_current_to_watchlist)
        self.settings.setting_changed.connect(self._setting_changed)
        self.settings.portfolio_changed.connect(self._portfolio_changed)
        self.portfolio.refresh_requested.connect(lambda: self._auto_refresh_prices(True))
        self.bot.setting_changed.connect(self._bot_setting_changed)
        self.bot.portfolio_changed.connect(self._portfolio_changed)
        self.bot.candidates_changed.connect(self.signals.set_autotrader_candidates)
        self.bot.status_changed.connect(self._autotrader_status)
        self.bot.open_symbol.connect(self.run_analysis)

        self._sync_watchlist_views()
        self.navigate(0)

        # 0.9.10: price polling and optional scheduled AutoTrader scans.
        self.quote_timer = QTimer(self)
        self.quote_timer.timeout.connect(self._auto_refresh_prices)
        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.timeout.connect(self._scheduled_autotrader_scan)
        self.exchange_timer = QTimer(self)
        self.exchange_timer.setInterval(1000)
        self.exchange_timer.timeout.connect(self._refresh_exchange_bar)
        self.exchange_timer.start()
        self._configure_refresh_timers()
        if self.config.get("auto_refresh_enabled", True) and (self.paper_broker.open_count() > 0 or self.paper_broker.pending_count() > 0):
            QTimer.singleShot(2500, self._auto_refresh_prices)

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(228)
        l = QVBoxLayout(side)
        l.setContentsMargins(16, 18, 16, 16)
        l.setSpacing(7)

        brand_row = QHBoxLayout()
        mark = QFrame()
        mark.setFixedSize(36, 36)
        mark.setStyleSheet(f"background:{BLUE};border-radius:10px;")
        ml = QVBoxLayout(mark)
        ml.setContentsMargins(0, 0, 0, 0)
        logo = QLabel("▥")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size:19px;color:white;font-weight:800;")
        ml.addWidget(logo)
        brand = QLabel("TradePilot")
        brand.setObjectName("Brand")
        brand_row.addWidget(mark)
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        l.addLayout(brand_row)
        version = QLabel(f"Research UI  ·  {VERSION}")
        version.setObjectName("Subtle")
        l.addWidget(version)
        l.addSpacing(17)

        section = QLabel(tr("section.workspace"))
        section.setObjectName("Eyebrow")
        l.addWidget(section)
        l.addSpacing(2)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        nav = [
            ("⌂    " + tr("nav.dashboard"), 0),
            ("⌁    " + tr("nav.analysis"), 1),
            ("☆    " + tr("nav.watchlist"), 2),
            ("◔    " + tr("nav.portfolio"), 3),
            ("▰    " + loc("Performance & Risk", "Performance & Risk"), 4),
            ("◎    " + tr("nav.signals"), 5),
            ("◆    " + tr("nav.bot"), 6),
            ("↺    " + tr("nav.history"), 7),
        ]
        self.nav_buttons = []
        for text, idx in nav:
            b = QPushButton(text)
            b.setObjectName("NavButton")
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, i=idx: self.navigate(i))
            self.nav_group.addButton(b)
            self.nav_buttons.append(b)
            l.addWidget(b)

        l.addSpacing(10)
        section2 = QLabel(tr("section.system"))
        section2.setObjectName("Eyebrow")
        l.addWidget(section2)
        settings_btn = QPushButton("⚙    " + tr("nav.settings"))
        settings_btn.setObjectName("NavButton")
        settings_btn.setCheckable(True)
        settings_btn.clicked.connect(lambda checked=False: self.navigate(8))
        self.nav_group.addButton(settings_btn)
        self.nav_buttons.append(settings_btn)
        l.addWidget(settings_btn)

        l.addStretch(1)
        pro = Card()
        pl = QVBoxLayout(pro)
        pl.setContentsMargins(13, 12, 13, 12)
        crown = QLabel("◆  TradePilot Research")
        crown.setStyleSheet(f"color:{YELLOW};font-weight:700;")
        note = QLabel("Lokale Analyse auf diesem PC\nAutoTrader im Paper-Modus")
        note.setObjectName("Subtle")
        note.setWordWrap(True)
        pl.addWidget(crown)
        pl.addWidget(note)
        l.addWidget(pro)
        return side

    def _build_topbar(self):
        top = QFrame()
        top.setObjectName("Topbar")
        top.setFixedHeight(74)
        l = QHBoxLayout(top)
        l.setContentsMargins(24, 12, 24, 12)
        l.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("top.search"))
        self.search.setFixedWidth(440)
        self.search.returnPressed.connect(self._search_clicked)
        l.addWidget(self.search)

        self.analyse_button = QPushButton(tr("top.analyze"))
        self.analyse_button.setObjectName("Primary")
        self.analyse_button.clicked.connect(self._search_clicked)
        l.addWidget(self.analyse_button)
        l.addStretch(1)

        data = QVBoxLayout()
        data.setSpacing(0)
        source = QLabel(tr("top.data"))
        source.setObjectName("Eyebrow")
        row = QHBoxLayout()
        self.top_status_dot = QLabel("●")
        self.top_status_dot.setStyleSheet(f"color:{GREEN};font-size:11px;")
        self.top_status = QLabel(tr("top.ready"))
        self.top_status.setObjectName("Muted")
        row.addWidget(self.top_status_dot)
        row.addWidget(self.top_status)
        data.addWidget(source)
        data.addLayout(row)
        l.addLayout(data)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setFixedHeight(34)
        divider.setStyleSheet("background:#1b334c;")
        l.addWidget(divider)

        avatar = QLabel("TP")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background:#172a40;border:1px solid #2d4a65;border-radius:18px;font-weight:750;color:#cbd9e6;")
        l.addWidget(avatar)
        return top

    def _build_market_bar(self):
        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setStyleSheet(f"background:{SIDEBAR};border-bottom:1px solid {BORDER_SOFT};")
        l = QHBoxLayout(bar)
        l.setContentsMargins(24, 4, 24, 4)
        l.setSpacing(12)
        title = QLabel(loc("BÖRSEN", "MARKETS"))
        title.setObjectName("Eyebrow")
        l.addWidget(title)
        self.exchange_labels = {}
        for code in ("NYSE", "NASDAQ", "XETRA", "VIE"):
            lab = QLabel(code)
            lab.setMinimumWidth(205 if code in {"NYSE","NASDAQ"} else 190)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.exchange_labels[code] = lab
            l.addWidget(lab)
        l.addStretch(1)
        note = QLabel(loc("reguläre Handelszeiten", "regular sessions"))
        note.setObjectName("Subtle")
        note.setToolTip(loc("Lokaler Börsenkalender mit regulären Handelszeiten und wichtigen Feiertagen. Sonderhandelstage können abweichen; für Paper-Orders ist zusätzlich ein frischer Marktkurs Pflicht.", "Local exchange calendar using regular sessions and major holidays. Special sessions may differ; paper orders additionally require a fresh market quote."))
        l.addWidget(note)
        self._refresh_exchange_bar()
        return bar

    def _refresh_exchange_bar(self):
        if not hasattr(self, "exchange_labels"):
            return
        try:
            statuses = all_exchange_statuses()
        except Exception:
            return
        lang = language()
        for st in statuses:
            code = st.get("code")
            lab = self.exchange_labels.get(code)
            if lab is None:
                continue
            opened = bool(st.get("is_open"))
            color = GREEN if opened else RED
            countdown = format_countdown(st.get("seconds", 0), lang)
            if opened:
                text = loc(f"● {code} · OFFEN · schließt in {countdown}", f"● {code} · OPEN · closes in {countdown}")
            else:
                text = loc(f"● {code} · ZU · öffnet in {countdown}", f"● {code} · CLOSED · opens in {countdown}")
            lab.setText(text)
            lab.setStyleSheet(f"color:{color};border:1px solid {color};border-radius:7px;padding:4px 8px;font-size:11px;font-weight:650;")
            local_time = str(st.get("local_time", "")).replace("T", " ")[:16]
            lab.setToolTip(loc(
                f"{code} · lokale Zeit {local_time}\nRegulär {st.get('regular_hours','—')} · {st.get('timezone','')}\nStatus lokal berechnet; Sonderhandelstage können abweichen.",
                f"{code} · local time {local_time}\nRegular {st.get('regular_hours','—')} · {st.get('timezone','')}\nStatus calculated locally; special sessions may differ."))

    def _build_footer(self):
        foot = QFrame()
        foot.setFixedHeight(34)
        foot.setStyleSheet(f"border-top:1px solid {BORDER_SOFT};background:#07111d;")
        l = QHBoxLayout(foot)
        l.setContentsMargins(22, 4, 22, 4)
        note = QLabel("ⓘ  Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse.")
        note.setObjectName("Subtle")
        l.addWidget(note)
        l.addStretch(1)
        self.footer_status = QLabel("Lokal · Yahoo Finance")
        self.footer_status.setObjectName("Subtle")
        l.addWidget(self.footer_status)
        return foot

    def navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
        if index == 0:
            self.dashboard.set_watchlist(self.watchlist)
        elif index == 2:
            self.watchpage.set_watchlist(self.watchlist)
        elif index == 3:
            self.portfolio.refresh()
        elif index == 4:
            self.performance_risk.set_analysis(self.current_data)
            self.performance_risk.refresh()
        elif index == 5:
            self.signals.set_watchlist(self.watchlist)
            self.signals.set_autotrader_candidates(self.bot.candidates)
        elif index == 6:
            self.bot.set_analysis(self.current_data)
            self.bot.set_watchlist(self.watchlist)
            self.bot.refresh_portfolio()
        elif index == 7:
            self.history.set_watchlist(self.watchlist)
        elif index == 8:
            self.settings._refresh_paper_state()

    def _search_clicked(self):
        self.run_analysis(self.search.text())

    def run_analysis(self, symbol: str):
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            QMessageBox.information(self, "TradePilot", "Bitte zuerst ein Aktien-Symbol eingeben.")
            return
        self.search.setText(symbol)
        self.navigate(1)
        self.analysis.set_loading(symbol)
        self.analyse_button.setEnabled(False)
        self.top_status.setText(f"Analysiere {symbol} …")
        self.top_status_dot.setStyleSheet(f"color:{BLUE_2};font-size:12px;")

        worker = AnalysisThread(symbol)
        self.analysis_threads.append(worker)
        worker.result.connect(lambda data, w=worker: self._analysis_ready(data, w))
        worker.error.connect(lambda err, w=worker: self._analysis_error(err, w))
        worker.finished.connect(lambda w=worker: self._cleanup_thread(w))
        worker.start()

    def _analysis_ready(self, data: dict, worker):
        self.current_data = data
        symbol = data.get("symbol", "")
        # Ist die Aktie bereits auf der Watchlist, wird der gespeicherte Stand aktualisiert.
        if symbol in self.watchlist:
            merge_analysis(self.watchlist, data)
            self._save_watchlist_silent()
        self.analysis.set_data(data, symbol in self.watchlist)
        self.bot.set_analysis(data)
        self.performance_risk.set_analysis(data)
        self._sync_watchlist_views()
        self.analyse_button.setEnabled(True)
        self.top_status.setText("Analyse aktuell")
        self.top_status_dot.setStyleSheet(f"color:{GREEN};font-size:12px;")
        self.footer_status.setText(f"Zuletzt analysiert: {symbol}")

    def _analysis_error(self, error: str, worker):
        self.analyse_button.setEnabled(True)
        self.current_data = None
        symbol = getattr(worker, "symbol", "")
        self.analysis.set_error(symbol, error)
        self.bot.set_analysis(None)
        self.performance_risk.set_analysis(None)
        self.top_status.setText(loc("Analyse nicht verfügbar", "Analysis unavailable"))
        self.top_status_dot.setStyleSheet(f"color:{RED};font-size:12px;")
        self.footer_status.setText(loc(f"{symbol}: Datenfehler", f"{symbol}: data error"))
        QMessageBox.critical(self, "TradePilot", loc(f"Die Analyse für {symbol} konnte nicht zuverlässig geladen werden:\n\n{error}", f"The analysis for {symbol} could not be loaded reliably:\n\n{error}"))

    def _cleanup_thread(self, worker):
        try:
            self.analysis_threads.remove(worker)
        except ValueError:
            pass
        worker.deleteLater()

    def add_current_to_watchlist(self):
        if not self.current_data:
            return
        symbol = self.current_data.get("symbol", "")
        merge_analysis(self.watchlist, self.current_data)
        if self._save_watchlist_silent():
            self.analysis.set_watchlist_state(True)
            self._sync_watchlist_views()
            self.top_status.setText(f"{symbol} zur Watchlist hinzugefügt")

    def remove_from_watchlist(self, symbol: str):
        symbol = str(symbol).upper()
        if symbol not in self.watchlist:
            return
        answer = QMessageBox.question(
            self,
            "TradePilot",
            f"{symbol} wirklich aus der Watchlist entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.watchlist.pop(symbol, None)
        self._save_watchlist_silent()
        if self.current_data and self.current_data.get("symbol") == symbol:
            self.analysis.set_watchlist_state(False)
        self._sync_watchlist_views()

    def refresh_watchlist(self):
        if self.refresh_thread and self.refresh_thread.isRunning():
            return
        symbols = sorted(self.watchlist.keys())
        if not symbols:
            QMessageBox.information(self, "TradePilot", "Die Watchlist ist noch leer.")
            return
        self.watchpage.refresh_btn.setEnabled(False)
        self.refresh_thread = WatchlistRefreshThread(symbols)
        self.refresh_thread.item_ready.connect(self._watch_item_ready)
        self.refresh_thread.progress.connect(self._watch_progress)
        self.refresh_thread.failed.connect(self._watch_failed)
        self.refresh_thread.done.connect(self._watch_done)
        self.refresh_thread.start()

    def _watch_item_ready(self, data: dict):
        merge_analysis(self.watchlist, data)
        self._save_watchlist_silent()
        self._sync_watchlist_views()

    def _watch_progress(self, text: str):
        self.top_status.setText(text)
        self.top_status_dot.setStyleSheet(f"color:{BLUE_2};font-size:12px;")

    def _watch_failed(self, symbol: str, error: str):
        self.footer_status.setText(f"{symbol}: Aktualisierung fehlgeschlagen")

    def _watch_done(self):
        self.watchpage.refresh_btn.setEnabled(True)
        self.top_status.setText("Watchlist aktuell")
        self.top_status_dot.setStyleSheet(f"color:{GREEN};font-size:12px;")
        self._sync_watchlist_views()
        if self.refresh_thread:
            self.refresh_thread.deleteLater()
            self.refresh_thread = None

    def _configure_refresh_timers(self):
        if not hasattr(self, "quote_timer") or not hasattr(self, "auto_scan_timer"):
            return
        self.quote_timer.stop()
        self.auto_scan_timer.stop()

        refresh_enabled = bool(self.config.get("auto_refresh_enabled", True))
        quote_seconds = int(self.config.get("quote_refresh_seconds", 60) or 60)
        scan_enabled = bool(self.config.get("auto_scan_enabled", False))
        scan_minutes = int(self.config.get("auto_scan_minutes", 15) or 15)

        if refresh_enabled:
            self.quote_timer.setInterval(max(30, quote_seconds) * 1000)
            self.quote_timer.start()
            self.portfolio.set_refresh_status(
                loc(f"Auto-Refresh aktiv · alle {quote_seconds} Sek. · Yahoo Finance Polling",
                    f"Auto refresh enabled · every {quote_seconds} sec · Yahoo Finance polling"),
                BLUE_2,
            )
        else:
            self.portfolio.set_refresh_status(loc("Auto-Refresh ausgeschaltet", "Auto refresh disabled"), TEXT_3)

        if scan_enabled:
            self.auto_scan_timer.setInterval(max(5, scan_minutes) * 60 * 1000)
            self.auto_scan_timer.start()

    def _auto_refresh_prices(self, force: bool = False):
        if not force and not bool(self.config.get("auto_refresh_enabled", True)):
            return
        if self.quote_refresh_thread and self.quote_refresh_thread.isRunning():
            return
        if self.bot.scan_thread and self.bot.scan_thread.isRunning():
            return

        pending_symbols={str(o.get("symbol","")).upper() for o in self.paper_broker.pending_orders() if str(o.get("symbol","")).strip()}
        symbols = sorted(set(self.paper_broker.positions.keys()) | pending_symbols)
        if not symbols:
            self.portfolio.set_refresh_status(
                loc("Auto-Refresh aktiv · keine offenen Positionen oder Orders", "Auto refresh enabled · no open positions or orders"),
                TEXT_3,
            )
            return

        self._quote_results = {}
        self._quote_failures = {}
        self.portfolio.refresh_prices_btn.setEnabled(False)
        self.portfolio.set_refresh_status(
            loc(f"Kurse werden aktualisiert · {len(symbols)} Titel …", f"Refreshing prices · {len(symbols)} symbols …"),
            BLUE_2,
        )
        self.footer_status.setText(loc("Automatische Kursaktualisierung läuft …", "Automatic price refresh running …"))

        worker = QuoteRefreshThread(symbols)
        self.quote_refresh_thread = worker
        worker.quote_ready.connect(self._quote_ready)
        worker.failed.connect(self._quote_failed)
        worker.done.connect(self._quote_refresh_done)
        worker.start()

    def _quote_ready(self, symbol: str, quote: dict):
        price = _finite((quote or {}).get("price"))
        if price is None or price <= 0:
            self._quote_failures[symbol] = "INVALID_PRICE"
            return
        self._quote_results[symbol] = dict(quote or {})

        if self.paper_broker.has_position(symbol):
            self.paper_broker.update_price(
                symbol, price, quote_time=(quote or {}).get("quote_time"),
                quote_source=(quote or {}).get("provider"),
                quote_fresh=bool((quote or {}).get("fresh", False)),
            )

        # 0.9.10 Order Engine: pending orders are only filled from fresh regular
        # session quotes. Every BUY is rechecked immediately before execution.
        filled_buy = False
        for order in list(self.paper_broker.pending_orders()):
            if str(order.get("symbol","")).upper() != str(symbol).upper():
                continue
            if bool(order.get("requires_autotrader", True)) and not self.bot.enabled:
                continue
            check = validate_pending_execution(
                self.paper_broker, order, quote,
                slippage_bps=float(self.config.get("paper_slippage_bps",5.0) or 5.0),
                max_order_age_hours=float(self.config.get("pending_order_max_age_hours",96) or 96),
                max_gap_pct=float(self.config.get("pending_order_max_gap_pct",3.0) or 3.0),
                max_trade_value=float(self.config.get("max_trade_value",1000.0) or 1000.0),
            )
            blocks=list(check.get("blocks",[]))
            hard=[b for b in blocks if b not in {"MARKET_CLOSED","STALE_QUOTE"}]
            if check.get("allowed"):
                ok, reason, pnl = self.paper_broker.execute_pending(
                    order.get("order_id"), check.get("fill_price"), market_price=check.get("market_price"),
                    quote_time=(quote or {}).get("quote_time"), quote_source=(quote or {}).get("provider"),
                    slippage_bps=float(self.config.get("paper_slippage_bps",5.0) or 5.0),
                )
                if ok:
                    if str(order.get("side")).upper()=="BUY":
                        filled_buy=True
                        self.bot._log(symbol,loc(
                            f"Pending BUY ausgeführt · {int(order.get('shares',0))} Stk. zu {check.get('fill_price'):.2f}",
                            f"Pending BUY filled · {int(order.get('shares',0))} shares at {check.get('fill_price'):.2f}"),persist=True)
                    else:
                        self.bot._log(symbol,loc(f"Pending SELL ausgeführt · P/L {pnl:+.2f}",f"Pending SELL filled · P/L {pnl:+.2f}"),persist=True)
                elif reason not in {"ORDER_NOT_PENDING"}:
                    self.bot._log(symbol,loc(f"Orderausführung fehlgeschlagen · {reason}",f"Order fill failed · {reason}"),persist=True)
            elif hard:
                self.paper_broker.mark_order(order.get("order_id"),"REJECTED",hard[0])
                self.bot._log(symbol,loc(f"Pending Order verworfen · {hard[0]}",f"Pending order rejected · {hard[0]}"),persist=True)
            elif blocks:
                order["status_reason"]=blocks[0]; order["updated"]=datetime.now().astimezone().isoformat(timespec="seconds"); self.paper_broker.save()

        # A newly filled BUY should not immediately trigger an exit from the very
        # same quote. Existing positions are checked for price exits below.
        position = self.paper_broker.positions.get(symbol)
        if filled_buy or not position or not bool((quote or {}).get("fresh", False)) or not bool((quote or {}).get("session_open", False)):
            return
        if self.paper_broker.has_pending_order(symbol,"SELL"):
            return
        exit_result = evaluate_exit(position, None, position.get("profile", "balanced"))
        reason = exit_result.get("reason")
        if not exit_result.get("exit") or reason not in {"STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP"}:
            self._last_exit_alerts.pop(symbol, None)
            return

        if self.bot.enabled:
            ok, _, order_id = self.paper_broker.queue_sell(symbol, reason or "PRICE_EXIT", requires_autotrader=True)
            if ok and order_id:
                order=self.paper_broker._order(order_id)
                check=validate_pending_execution(self.paper_broker,order,quote,slippage_bps=float(self.config.get("paper_slippage_bps",5.0) or 5.0),max_order_age_hours=float(self.config.get("pending_order_max_age_hours",96) or 96),max_gap_pct=float(self.config.get("pending_order_max_gap_pct",3.0) or 3.0),max_trade_value=float(self.config.get("max_trade_value",1000.0) or 1000.0))
                if check.get("allowed"):
                    ok2,_,pnl=self.paper_broker.execute_pending(order_id,check.get("fill_price"),market_price=check.get("market_price"),quote_time=quote.get("quote_time"),quote_source=quote.get("provider"),slippage_bps=float(self.config.get("paper_slippage_bps",5.0) or 5.0))
                    if ok2:
                        self.bot._log(symbol,loc(f"Auto-Exit ausgeführt · {reason} · P/L {pnl:+.2f}",f"Auto exit filled · {reason} · P/L {pnl:+.2f}"),persist=True)
                        self._last_exit_alerts.pop(symbol, None)
        else:
            marker = f"{reason}:{price:.4f}"
            if self._last_exit_alerts.get(symbol) != marker:
                self._last_exit_alerts[symbol] = marker
                self.bot._log(symbol,loc(f"Ausstiegssignal {reason} · AutoTrader pausiert",f"Exit signal {reason} · AutoTrader paused"),persist=True)

    def _quote_failed(self, symbol: str, error: str):
        self._quote_failures[symbol] = error

    def _quote_refresh_done(self, ok: int, failed: int):
        if ok:
            self.paper_broker.record_equity_snapshot("QUOTE_REFRESH", 30)
        self.portfolio.refresh()
        self.performance_risk.refresh()
        self.bot.refresh_portfolio()
        self.settings._refresh_paper_state()
        now = datetime.now().strftime("%H:%M:%S")
        total = ok + failed
        fresh = sum(1 for q in self._quote_results.values() if q.get("fresh"))

        if ok:
            if fresh:
                text = loc(
                    f"Auto-Refresh · {ok}/{total} Kurse · {fresh} aktuell · {now} · Yahoo Polling",
                    f"Auto refresh · {ok}/{total} prices · {fresh} current · {now} · Yahoo polling",
                )
                color = GREEN
            else:
                text = loc(
                    f"Auto-Refresh · {ok}/{total} letzte Börsenkurse · {now} · Markt ggf. geschlossen/verzögert",
                    f"Auto refresh · {ok}/{total} last market prices · {now} · market may be closed/delayed",
                )
                color = YELLOW
        else:
            text = loc(
                f"Auto-Refresh fehlgeschlagen · {failed}/{total or failed} Kurse · {now}",
                f"Auto refresh failed · {failed}/{total or failed} prices · {now}",
            )
            color = RED

        self.portfolio.set_refresh_status(text, color)
        self.portfolio.refresh_prices_btn.setEnabled(True)
        self.footer_status.setText(text)
        if self.quote_refresh_thread:
            self.quote_refresh_thread.deleteLater()
            self.quote_refresh_thread = None

    def _scheduled_autotrader_scan(self):
        if not bool(self.config.get("auto_scan_enabled", False)):
            return
        if self.bot.scan_thread and self.bot.scan_thread.isRunning():
            return
        if self.quote_refresh_thread and self.quote_refresh_thread.isRunning():
            return
        self.footer_status.setText(loc("Zeitgesteuerter AutoTrader-Scan startet …", "Scheduled AutoTrader scan starting …"))
        self.bot.start_scan()

    def _portfolio_changed(self):
        self.portfolio.refresh()
        self.performance_risk.refresh()
        self.footer_status.setText(loc("Paper-Portfolio aktualisiert", "Paper portfolio updated"))

    def _autotrader_status(self, text: str):
        self.top_status.setText(text)
        self.top_status_dot.setStyleSheet(f"color:{BLUE_2};font-size:12px;")

    def _bot_setting_changed(self, key: str, value):
        self.config[key] = value
        try:
            save_config(self.app_dir, self.config)
        except Exception as exc:
            QMessageBox.critical(self, "TradePilot", f"Bot-Einstellung konnte nicht gespeichert werden:\n{exc}")
        if key == "bot_profile":
            self.performance_risk.refresh()

    def _setting_changed(self, key: str, value):
        self.config[key] = value
        try:
            save_config(self.app_dir, self.config)
        except Exception as exc:
            QMessageBox.critical(self, "TradePilot", f"Einstellung konnte nicht gespeichert werden:\n{exc}")
            return

        if key == "demo_capital":
            try:
                self.bot.demo_capital=float(value); self.bot.capital_input.setText(f"{float(value):.2f}")
            except Exception:
                pass
            return
        if key == "paper_slippage_bps":
            try:
                self.bot.slippage_bps=float(value)
            except Exception:
                pass
            return
        if key == "max_trade_value":
            try:
                self.bot.max_trade_value=float(value)
                self.performance_risk.refresh()
            except Exception:
                pass
            return
        if key in {"auto_refresh_enabled", "quote_refresh_seconds", "auto_scan_enabled", "auto_scan_minutes"}:
            self._configure_refresh_timers()
            if key == "auto_refresh_enabled" and bool(value) and (self.paper_broker.open_count() > 0 or self.paper_broker.pending_count() > 0):
                QTimer.singleShot(250, self._auto_refresh_prices)
            return
        if key not in {"theme","language"}:
            return

        # Für einen konsistenten Theme-/Sprachwechsel wird das Hauptfenster
        # innerhalb derselben App neu aufgebaut. Analyse-Engine und Watchlist
        # bleiben unverändert und die Einstellung ist bereits gespeichert.
        app = QApplication.instance()
        replacement = TradePilotWindow()
        app._tradepilot_window = replacement
        replacement.show()
        self.close()

    def closeEvent(self, event):
        try:
            if hasattr(self, "quote_timer"):
                self.quote_timer.stop()
            if hasattr(self, "auto_scan_timer"):
                self.auto_scan_timer.stop()
            if hasattr(self, "exchange_timer"):
                self.exchange_timer.stop()
            if self.quote_refresh_thread and self.quote_refresh_thread.isRunning():
                self.quote_refresh_thread.stop()
            if self.bot.scan_thread and self.bot.scan_thread.isRunning():
                self.bot.stop_scan()
        except Exception:
            pass
        super().closeEvent(event)

    def _save_watchlist_silent(self) -> bool:
        try:
            save_watchlist(self.watch_path, self.watchlist)
            return True
        except Exception as exc:
            QMessageBox.critical(self, "TradePilot", f"Watchlist konnte nicht gespeichert werden:\n{exc}")
            return False

    def _sync_watchlist_views(self):
        self.dashboard.set_watchlist(self.watchlist)
        self.watchpage.set_watchlist(self.watchlist)
        self.history.set_watchlist(self.watchlist)
        self.signals.set_watchlist(self.watchlist)
        self.signals.set_autotrader_candidates(self.bot.candidates)
        self.bot.set_watchlist(self.watchlist)
        if self.current_data:
            self.analysis.set_watchlist_state(self.current_data.get("symbol") in self.watchlist)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TradePilot")
    app.setApplicationVersion(VERSION)
    app.setStyle("Fusion")
    config = load_config(APP_DIR)
    set_theme(config.get("theme", "dark"))
    set_language(config.get("language", "de"))
    refresh_theme_tokens()
    app.setStyleSheet(QSS)

    window = TradePilotWindow()
    app._tradepilot_window = window
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
