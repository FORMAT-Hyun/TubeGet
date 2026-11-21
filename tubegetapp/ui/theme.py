"""어두운 테마(빨강 포인트), 앱 아이콘."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from ..paths import resource_path

# --- 색 ----------------------------------------------------------------
ACCENT = "#ff4d4f"            # 기본(포인트) 색: 빨강
ACCENT_HOVER = "#ff6466"
ACCENT_PRESS = "#e03e40"
ACCENT_SOFT = "#3a2225"       # 선택/강조 배경 (어두운 빨강)
ACCENT_TEXT = "#ff7b7d"       # 어두운 바탕 위 빨강 글자
BG = "#141518"
TOOLBAR_BG = "#1a1c20"
SURFACE = "#1d1f24"
SURFACE2 = "#272a31"
INPUT_BG = "#15161a"
BORDER = "#2b2e36"
BORDER_STRONG = "#3b404b"
TEXT = "#e8e9ec"
MUTED = "#9aa0aa"
PLACEHOLDER = "#6b717c"
DISABLED = "#5f6570"
ICON = "#aab0ba"              # 아이콘 기본 색
SUCCESS = "#3ecf8e"
DANGER = "#ff6b6b"
WARNING = "#f5b544"
FRESH_BG = "#2a1d1f"          # 방금 끝난 항목
FRESH_BORDER = "#6a3034"
ROW_HOVER = "#23262d"

FONT_STACK = '"Pretendard", "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", "Noto Sans CJK KR", sans-serif'


def _qss() -> str:
    check = resource_path("assets", "check.svg").as_posix()
    chevron = resource_path("assets", "chevron_down.svg").as_posix()
    return f"""
* {{ font-family: {FONT_STACK}; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#Central {{ background: {BG}; }}
QLabel {{ background: transparent; }}

/* ---------- 상단 툴바 ---------- */
QFrame#Toolbar {{ background: {TOOLBAR_BG}; border: none; border-bottom: 1px solid {BORDER}; }}
QLabel#ChipLabel {{ color: {MUTED}; }}

/* ---------- 정보 패널 ---------- */
QFrame#InfoPanel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#InfoPanel QLineEdit {{ background: {INPUT_BG}; }}
QFrame#Divider {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QLabel#Pill {{
    background: {SURFACE2}; color: {MUTED}; border-radius: 11px; padding: 3px 11px; font-size: 9pt;
}}
QLabel#PillAccent {{
    background: {ACCENT_SOFT}; color: {ACCENT_TEXT}; border-radius: 11px; padding: 3px 11px; font-size: 9pt;
}}
QLabel#SectionLabel {{ color: {MUTED}; font-size: 9pt; }}

/* ---------- 목록 ---------- */
QFrame#QueueItem {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#QueueItem:hover {{ background: {ROW_HOVER}; border-color: {BORDER_STRONG}; }}
QFrame#ReadyItem {{ background: {SURFACE}; border: 1px solid {BORDER_STRONG}; border-radius: 12px; }}
QFrame#ReadyItem[selected="true"] {{ border-color: {ACCENT}; }}
QFrame#QueueItem[fresh="true"] {{ background: {FRESH_BG}; border-color: {FRESH_BORDER}; }}
QFrame#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#AppTitle {{ font-size: 15pt; font-weight: 700; }}
QLabel#AppVersion {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Small {{ color: {MUTED}; font-size: 9pt; }}
QLabel#VideoTitle {{ font-size: 12.5pt; font-weight: 600; }}
QLabel#JobTitle {{ font-weight: 600; }}
QLabel#Notice {{ color: {WARNING}; }}
QLabel#Error {{ color: {DANGER}; }}
QLabel#Success {{ color: {SUCCESS}; }}
QLabel#FieldLabel {{ color: {MUTED}; }}
QLabel#Thumb {{ background: {SURFACE2}; border-radius: 8px; color: {MUTED}; }}
QLabel#Empty {{ color: {MUTED}; font-size: 10.5pt; }}
QLabel#EmptyTitle {{ color: {TEXT}; font-size: 13pt; font-weight: 600; }}
QLabel#ToastTitle {{ font-weight: 600; }}
QLabel#ToastBody {{ color: {MUTED}; }}
QFrame#Toast {{ background: {SURFACE2}; border: 1px solid {BORDER_STRONG}; border-radius: 12px; }}

/* ---------- 입력 ---------- */
QLineEdit, QComboBox, QSpinBox {{
    background: {INPUT_BG}; border: 1px solid {BORDER_STRONG}; border-radius: 8px;
    padding: 6px 10px;
}}
QLineEdit, QSpinBox {{ selection-background-color: {ACCENT}; selection-color: white; }}
QComboBox {{ selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QLineEdit#UrlInput {{ font-size: 10.5pt; padding: 8px 12px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {DISABLED}; background: {SURFACE}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE2}; border: 1px solid {BORDER_STRONG}; outline: none; padding: 4px;
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT};
}}
QComboBox QAbstractItemView::item {{ padding: 6px 10px; min-height: 22px; border-radius: 4px; }}
QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {{
    background: {ACCENT_SOFT}; color: {TEXT};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}

/* ---------- 버튼 ---------- */
QPushButton {{
    background: {SURFACE2}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; padding: 6px 14px;
}}
QPushButton:hover {{ background: #30343d; }}
QPushButton:pressed {{ background: #22252b; }}
QPushButton:disabled {{ color: {DISABLED}; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: white; font-weight: 600; padding: 8px 18px;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:pressed {{ background: {ACCENT_PRESS}; border-color: {ACCENT_PRESS}; }}
QPushButton[primary="true"]:disabled {{ background: #5a2a2c; border-color: #5a2a2c; color: #c9a3a4; }}
QPushButton[segment="true"] {{ border-radius: 0px; padding: 6px 18px; }}
QPushButton[segment="true"][first="true"] {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QPushButton[segment="true"][last="true"] {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
QPushButton[segment="true"]:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton[ghost="true"] {{
    background: transparent; border: none; color: {MUTED}; padding: 5px 9px; border-radius: 8px;
}}
QPushButton[ghost="true"]:hover {{ background: {SURFACE2}; color: {TEXT}; }}
QPushButton[ghost="true"]:disabled {{ color: {DISABLED}; background: transparent; }}
QPushButton[iconbtn="true"] {{
    background: transparent; border: none; border-radius: 8px; padding: 5px; min-width: 20px; min-height: 20px;
}}
QPushButton[iconbtn="true"]:hover {{ background: {SURFACE2}; }}
QPushButton[iconbtn="true"]:pressed {{ background: #30343d; }}
QPushButton[link="true"] {{
    background: transparent; border: none; color: {ACCENT_TEXT}; padding: 2px 0px; text-align: left;
}}
QPushButton[link="true"]:hover {{ text-decoration: underline; }}
QPushButton[pill="true"] {{
    background: transparent; border: 1px solid {BORDER_STRONG}; border-radius: 16px; padding: 6px 15px;
}}
QPushButton[pill="true"]:hover {{ background: {SURFACE2}; border-color: #4a4f5c; }}
QPushButton[pill="true"][active="true"] {{ background: {ACCENT_SOFT}; border-color: {ACCENT}; color: {ACCENT_TEXT}; }}
QPushButton[tab="true"] {{
    background: transparent; border: none; border-bottom: 2px solid transparent; border-radius: 0px;
    color: {MUTED}; padding: 9px 4px; margin-right: 14px;
}}
QPushButton[tab="true"]:hover {{ color: {TEXT}; background: transparent; }}
QPushButton[tab="true"]:checked {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QDialogButtonBox QPushButton {{ min-width: 76px; }}

/* ---------- 체크/라디오 ---------- */
QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid #596070; background: {INPUT_BG};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url("{check}"); }}
QCheckBox:disabled {{ color: {DISABLED}; }}
QCheckBox::indicator:disabled {{ background: {SURFACE}; border-color: {BORDER}; }}
QCheckBox[pill="true"] {{
    border: 1px solid {BORDER_STRONG}; border-radius: 16px; padding: 6px 15px; spacing: 0px;
}}
QCheckBox[pill="true"]::indicator {{ width: 0px; height: 0px; border: none; margin: 0px; image: none; background: transparent; }}
QCheckBox[pill="true"]:hover {{ background: {SURFACE2}; border-color: #4a4f5c; }}
QCheckBox[pill="true"]:checked {{ background: {ACCENT_SOFT}; border-color: {ACCENT}; color: {ACCENT_TEXT}; }}
QRadioButton {{ spacing: 7px; background: transparent; padding: 2px 0; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 8px; border: 2px solid #596070; background: {INPUT_BG};
}}
QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
QRadioButton::indicator:checked {{ border: 4px solid {ACCENT}; background: white; width: 10px; height: 10px; }}
QRadioButton:disabled {{ color: {DISABLED}; }}

/* ---------- 진행 막대 ---------- */
QProgressBar {{
    background: #2c3038; border: none; border-radius: 2px; max-height: 4px; min-height: 4px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}
QProgressBar[state="done"]::chunk {{ background: {SUCCESS}; }}
QProgressBar[state="failed"]::chunk {{ background: {DANGER}; }}
QProgressBar[state="canceled"]::chunk {{ background: #5b606b; }}

/* ---------- 탭(대화상자용) ---------- */
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 8px 14px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

/* ---------- 스크롤 ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3a3e48; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #4a4f5a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #3a3e48; border-radius: 4px; min-width: 30px; }}
QSplitter::handle {{ background: transparent; }}

/* ---------- 표/목록 ---------- */
QTreeWidget, QListWidget {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; outline: none;
    alternate-background-color: #20232a;
}}
QTreeWidget::item, QListWidget::item {{ padding: 5px 4px; }}
QListWidget::indicator {{
    width: 15px; height: 15px; border-radius: 4px; border: 1px solid #596070; background: {INPUT_BG};
}}
QListWidget::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url("{check}"); }}
QListWidget::indicator:disabled {{ border-color: transparent; background: transparent; }}
QListWidget::item:disabled {{ color: {DISABLED}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {ROW_HOVER}; }}
QHeaderView::section {{
    background: {SURFACE}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 6px 8px;
}}

QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 10px; margin-top: 16px; padding: 14px 12px 10px 12px;
    background: {SURFACE};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {MUTED}; }}

/* ---------- 기타 ---------- */
QStatusBar {{ background: {TOOLBAR_BG}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ color: {MUTED}; font-size: 9pt; }}
QStatusBar QPushButton {{ font-size: 9pt; }}
QStatusBar::item {{ border: none; }}
QToolTip {{
    background: #2a2d35; color: {TEXT}; border: 1px solid {BORDER_STRONG}; padding: 6px 8px; border-radius: 6px;
}}
QMenu {{ background: {SURFACE2}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 24px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}
QMenu::item:disabled {{ color: {DISABLED}; }}
QMenu::separator {{ height: 1px; background: {BORDER_STRONG}; margin: 5px 6px; }}
QPlainTextEdit {{
    background: {INPUT_BG}; border: 1px solid {BORDER}; border-radius: 8px;
    font-family: "Cascadia Mono", Consolas, "D2Coding", monospace; font-size: 9pt;
}}
QMessageBox QLabel {{ min-width: 320px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(INPUT_BG))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(SURFACE2))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#5a2a2d"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2a2d35"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(PLACEHOLDER))
    pal.setColor(QPalette.ColorRole.Link, QColor(ACCENT_TEXT))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(DISABLED))
    app.setPalette(pal)
    app.setStyleSheet(_qss())


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def make_icon_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    rect = QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0, QColor("#ff6a5c"))
    grad.setColorAt(1, QColor("#e5283a"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(rect, s * 0.22, s * 0.22)
    # 아래 화살표
    path = QPainterPath()
    cx = s / 2
    path.moveTo(QPointF(cx - s * 0.085, s * 0.22))
    path.lineTo(QPointF(cx + s * 0.085, s * 0.22))
    path.lineTo(QPointF(cx + s * 0.085, s * 0.47))
    path.lineTo(QPointF(cx + s * 0.20, s * 0.47))
    path.lineTo(QPointF(cx, s * 0.68))
    path.lineTo(QPointF(cx - s * 0.20, s * 0.47))
    path.lineTo(QPointF(cx - s * 0.085, s * 0.47))
    path.closeSubpath()
    p.setBrush(QColor("white"))
    p.drawPath(path)
    pen = QPen(QColor("white"), s * 0.065, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(s * 0.28, s * 0.79), QPointF(s * 0.72, s * 0.79))
    p.end()
    return pm


def app_icon() -> QIcon:
    ico = resource_path("assets", "icon.png")
    if ico.exists():
        return QIcon(str(ico))
    return QIcon(make_icon_pixmap())
