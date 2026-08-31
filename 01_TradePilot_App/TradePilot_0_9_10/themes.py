from __future__ import annotations

THEMES = {
"dark": {
"bg":"#07111f","sidebar":"#081525","top":"#081421","surface":"#0c1a2a","surface2":"#0d1c2d","surface3":"#10233a","border":"#1b334c","border2":"#24405c","text":"#f4f7fb","muted":"#9fb1c5","subtle":"#6f849b","input":"#0b1a2a","table":"#0b1928","header":"#0f2032","selection":"#123b65","grid":"#173049","scroll":"#2b425a"},
"light": {
"bg":"#eef3f8","sidebar":"#ffffff","top":"#ffffff","surface":"#ffffff","surface2":"#f7f9fc","surface3":"#edf4fb","border":"#d6e0ea","border2":"#c4d4e3","text":"#152235","muted":"#5f7287","subtle":"#8190a0","input":"#ffffff","table":"#ffffff","header":"#f3f6f9","selection":"#dcecff","grid":"#dce5ee","scroll":"#b8c6d4"},
}
_current="dark"

def set_theme(name: str):
    global _current
    _current = name if name in THEMES else "dark"

def theme(): return _current
def c(key: str): return THEMES[_current][key]

def build_qss(blue="#2678ff", blue2="#4e98ff", green="#38d98a", red="#ff5f66"):
    p=THEMES[_current]
    return f"""
* {{ font-family:'Segoe UI'; color:{p['text']}; }}
QMainWindow, QWidget#Root, QStackedWidget, QWidget#PageSurface {{ background:{p['bg']}; }}
QFrame#Sidebar {{ background:{p['sidebar']}; border-right:1px solid {p['border']}; }}
QFrame#Topbar {{ background:{p['top']}; border-bottom:1px solid {p['border']}; }}
QFrame#Card, QFrame#HeroCard, QFrame#Panel {{ background:{p['surface']}; border:1px solid {p['border']}; border-radius:14px; }}
QFrame#HeroCard {{ border-color:{p['border2']}; }}
QFrame#MetricCard {{ background:{p['surface2']}; border:1px solid {p['border']}; border-radius:14px; }}
QFrame#TickerTile {{ background:{p['surface3']}; border:1px solid {p['border2']}; border-radius:14px; }}
QLabel#InfoIcon {{color:#4e98ff;font-size:13px;font-weight:800;background:transparent;border:0;}}
QLabel#InfoIcon:hover {{color:#76adff;}}
QFrame#MetricSeparator {{background:{p['border']};border:0;}}
QLabel#Brand {{ font-size:26px; font-weight:750; }} QLabel#PageTitle {{font-size:29px;font-weight:720;}} QLabel#HeroTitle {{font-size:29px;font-weight:720;}} QLabel#SectionTitle {{font-size:16px;font-weight:650;}} QLabel#Eyebrow {{color:{p['subtle']};font-size:11px;font-weight:650;}} QLabel#Muted {{color:{p['muted']};}} QLabel#Subtle {{color:{p['subtle']};}} QLabel#MarketOpen {{color:{green};font-weight:650;}}
QLineEdit, QComboBox {{background:{p['input']};border:1px solid {p['border2']};border-radius:10px;padding:10px 14px;font-size:13px;}}
QLineEdit:focus, QComboBox:focus {{border:1px solid {blue2};}}
QComboBox QAbstractItemView {{background:{p['surface']};color:{p['text']};selection-background-color:{p['selection']};border:1px solid {p['border']};}}
QPushButton {{background:{p['surface3']};border:1px solid {p['border2']};border-radius:9px;padding:10px 14px;font-weight:600;}}
QPushButton:hover {{border-color:{blue2};}} QPushButton:disabled {{color:{p['subtle']};background:{p['surface2']};border-color:{p['border']};}}
QPushButton#Primary {{background:#1475ff;border-color:#1475ff;color:white;padding-left:18px;padding-right:18px;}} QPushButton#Primary:hover {{background:#3188ff;border-color:#3188ff;}}
QPushButton#Ghost {{background:transparent;}} QPushButton#Danger:hover {{border-color:{red};}}
QPushButton#NavButton {{background:transparent;border:0;border-radius:10px;text-align:left;padding:12px 14px;color:{p['muted']};font-weight:550;}}
QPushButton#NavButton:hover {{background:{p['surface3']};color:{p['text']};}} QPushButton#NavButton:checked {{background:{p['selection']};color:{blue2};border-left:3px solid {blue2};padding-left:11px;}}
QPushButton#TimeButton {{background:transparent;border:0;color:{p['subtle']};padding:6px 10px;border-radius:7px;}} QPushButton#TimeButton:hover {{color:{p['text']};background:{p['surface3']};}} QPushButton#TimeButton:checked {{color:{blue2};background:{p['selection']};}}
QProgressBar {{background:{p['border']};border:0;border-radius:3px;height:6px;}} QProgressBar::chunk {{background:{blue};border-radius:3px;}}
QTableWidget {{background:{p['table']};alternate-background-color:{p['surface2']};border:1px solid {p['border']};border-radius:11px;gridline-color:transparent;selection-background-color:{p['selection']};outline:none;}}
QTableWidget::item {{padding:9px;border-bottom:1px solid {p['border']};}} QHeaderView::section {{background:{p['header']};color:{p['muted']};border:0;border-bottom:1px solid {p['border']};padding:10px 8px;font-weight:650;}}
QScrollArea {{border:0;background:transparent;}} QScrollArea > QWidget > QWidget {{background:transparent;}} QScrollBar:vertical {{background:transparent;width:9px;margin:3px;}} QScrollBar::handle:vertical {{background:{p['scroll']};border-radius:4px;min-height:32px;}} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
QToolTip {{background:{p['surface3']};color:{p['text']};border:1px solid {p['border2']};padding:9px;border-radius:7px;font-size:12px;}}
QMessageBox {{background:{p['surface']};}}
QMessageBox QLabel {{background:transparent;color:{p['text']};}}
QMessageBox QLabel#qt_msgbox_label {{min-width:360px;}}
QMessageBox QPushButton {{background:{p['surface3']};color:{p['text']};border:1px solid {p['border2']};border-radius:8px;padding:8px 18px;min-width:72px;}}
QMessageBox QPushButton:hover {{border-color:{blue2};}}
"""
