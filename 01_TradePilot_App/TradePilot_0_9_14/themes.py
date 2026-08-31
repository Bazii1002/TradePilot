from __future__ import annotations

THEMES = {
    "dark": {
        "bg":"#071526", "sidebar":"#071321", "top":"#081728",
        "surface":"#0a1b2e", "surface2":"#0b1e33", "surface3":"#102843",
        "border":"#1a3958", "border2":"#2a5278",
        "text":"#f5f8fc", "muted":"#a8b8cb", "subtle":"#7c91a8",
        "input":"#08192b", "table":"#091a2c", "header":"#0d2239",
        "selection":"#0d3159", "grid":"#163653", "scroll":"#31506e"
    },
    "light": {
        "bg":"#f2f6fa", "sidebar":"#ffffff", "top":"#ffffff",
        "surface":"#ffffff", "surface2":"#f8fafc", "surface3":"#edf4fb",
        "border":"#d9e3ec", "border2":"#bfd0df",
        "text":"#142235", "muted":"#607489", "subtle":"#8393a3",
        "input":"#ffffff", "table":"#ffffff", "header":"#f4f7fa",
        "selection":"#e5f0ff", "grid":"#dce6ee", "scroll":"#b6c5d2"
    },
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
QFrame#Card, QFrame#HeroCard, QFrame#Panel {{ background:{p['surface']}; border:1px solid {p['border']}; border-radius:15px; }}
QFrame#HeroCard {{ border-color:{p['border2']}; }}
QFrame#MetricCard {{ background:{p['surface2']}; border:1px solid {p['border']}; border-radius:15px; }}
QFrame#TickerTile {{ background:{p['surface3']}; border:1px solid {p['border2']}; border-radius:12px; }}
QFrame#InsetRow {{ background:{p['surface2']}; border:1px solid {p['border']}; border-radius:9px; }}
QLabel#InfoIcon {{color:{blue2};font-size:13px;font-weight:800;background:transparent;border:0;}}
QFrame#MetricSeparator {{background:{p['border']};border:0;}}
QLabel#Brand {{ font-size:24px; font-weight:760; letter-spacing:-0.5px; }}
QLabel#PageTitle {{font-size:27px;font-weight:760;letter-spacing:-0.4px;}}
QLabel#HeroTitle {{font-size:28px;font-weight:760;}}
QLabel#SectionTitle {{font-size:15px;font-weight:700;}}
QLabel#Eyebrow {{color:{p['subtle']};font-size:10px;font-weight:700;letter-spacing:0.5px;}}
QLabel#Muted {{color:{p['muted']};}} QLabel#Subtle {{color:{p['subtle']};}} QLabel#MarketOpen {{color:{green};font-weight:650;}}
QLabel#StatusPillGood {{ color:{green}; background:rgba(56,217,138,0.08); border:1px solid rgba(56,217,138,0.35); border-radius:9px; padding:6px 10px; font-size:10px; font-weight:750; }}
QLabel#StatusPillNeutral {{ color:{p['muted']}; background:{p['surface3']}; border:1px solid {p['border']}; border-radius:9px; padding:5px 9px; font-size:10px; font-weight:700; }}
QLineEdit, QComboBox {{background:{p['input']};border:1px solid {p['border2']};border-radius:9px;padding:9px 12px;font-size:13px;}}
QLineEdit:focus, QComboBox:focus {{border:1px solid {blue2};}}
QComboBox QAbstractItemView {{background:{p['surface']};color:{p['text']};selection-background-color:{p['selection']};border:1px solid {p['border']};}}
QPushButton {{background:{p['surface3']};border:1px solid {p['border2']};border-radius:9px;padding:9px 13px;font-weight:650;}}
QPushButton:hover {{border-color:{blue2};background:{p['surface2']};}} QPushButton:disabled {{color:{p['subtle']};background:{p['surface2']};border-color:{p['border']};}}
QPushButton#Primary {{background:#1475ff;border-color:#1475ff;color:white;padding-left:17px;padding-right:17px;}} QPushButton#Primary:hover {{background:#2e86ff;border-color:#2e86ff;}}
QPushButton#Ghost {{background:transparent;border-color:transparent;color:{p['muted']};}} QPushButton#Ghost:hover {{background:{p['surface3']};color:{p['text']};}}
QPushButton#Danger {{background:transparent;border-color:rgba(255,95,102,0.55);color:{red};}} QPushButton#Danger:hover {{background:rgba(255,95,102,0.07);border-color:{red};}}
QPushButton#NavButton {{background:transparent;border:0;border-radius:10px;text-align:left;padding:13px 14px;color:{p['muted']};font-size:13px;font-weight:600;}}
QPushButton#NavButton:hover {{background:{p['surface3']};color:{p['text']};}} QPushButton#NavButton:checked {{background:{p['selection']};color:{blue2};border-left:3px solid {blue2};padding-left:10px;}}
QPushButton#TimeButton {{background:transparent;border:0;color:{p['subtle']};padding:6px 10px;border-radius:7px;}} QPushButton#TimeButton:hover {{color:{p['text']};background:{p['surface3']};}} QPushButton#TimeButton:checked {{color:{blue2};background:{p['selection']};}}
QProgressBar {{background:{p['border']};border:0;border-radius:3px;height:6px;}} QProgressBar::chunk {{background:{blue};border-radius:3px;}}
QTableWidget {{background:{p['table']};alternate-background-color:{p['surface2']};border:1px solid {p['border']};border-radius:10px;gridline-color:transparent;selection-background-color:{p['selection']};outline:none;}}
QTableWidget::item {{padding:8px;border-bottom:1px solid {p['border']};}} QHeaderView::section {{background:{p['header']};color:{p['subtle']};border:0;border-bottom:1px solid {p['border']};padding:9px 8px;font-size:10px;font-weight:750;}}
QScrollArea {{border:0;background:transparent;}} QScrollArea > QWidget > QWidget {{background:transparent;}} QScrollBar:vertical {{background:transparent;width:8px;margin:3px;}} QScrollBar::handle:vertical {{background:{p['scroll']};border-radius:4px;min-height:32px;}} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
QFrame#BrandMark { background:#1475ff; border:0; border-radius:11px; }
QLabel#BrandGlyph { color:white; font-size:20px; font-weight:800; }
QFrame#SidebarAccount { background:{p['surface']}; border:1px solid {p['border']}; border-radius:12px; }
QLabel#SidebarAccountTitle { color:{green}; font-weight:700; }
QLabel#SidebarAccountLock { color:{p['muted']}; font-size:11px; }
QPushButton#IconButton { background:transparent; border:0; color:{p['muted']}; font-size:18px; padding:0; }
QPushButton#IconButton:hover { background:{p['surface3']}; color:{p['text']}; }
QLabel#Avatar { background:{p['surface3']}; border:1px solid {p['border2']}; border-radius:20px; font-weight:750; color:{p['text']}; }
QLineEdit#GlobalSearch { min-height:28px; padding:10px 14px; }
QToolTip {{background:{p['surface3']};color:{p['text']};border:1px solid {p['border2']};padding:8px;border-radius:7px;font-size:12px;}}
QMessageBox {{background:{p['surface']};}} QMessageBox QLabel {{background:transparent;color:{p['text']};}} QMessageBox QLabel#qt_msgbox_label {{min-width:390px;}}
QMessageBox QPushButton {{background:{p['surface3']};color:{p['text']};border:1px solid {p['border2']};border-radius:8px;padding:8px 18px;min-width:72px;}} QMessageBox QPushButton:hover {{border-color:{blue2};}}
"""
