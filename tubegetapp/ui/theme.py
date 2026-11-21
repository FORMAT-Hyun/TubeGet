"""밝은 테마(4K Video Downloader+ 느낌), 앱 아이콘."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from ..paths import resource_path

# --- 색 ----------------------------------------------------------------
GREEN = "#5fb320"
GREEN_HOVER = "#55a41a"
GREEN_PRESS = "#4b9415"
GREEN_SOFT = "#eaf6df"        # 선택/강조 배경
GREEN_TEXT = "#3f8a0f"        # 흰 바탕 위 초록 글자 (대비 확보)
BG = "#ffffff"
SURFACE = "#f6f7f9"
SURFACE2 = "#eceff2"
BORDER = "#e3e6ea"
BORDER_STRONG = "#cdd2d8"
TEXT = "#23272b"
MUTED = "#6b737c"
PLACEHOLDER = "#9aa1a9"
SUCCESS = "#2e8b1a"
DANGER = "#d33a3a"
WARNING = "#b56a00"
FRESH_BG = "#fffdf4"          # 방금 끝난 항목 (연한 노랑)
FRESH_BORDER = "#f0dd9c"

# 예전 이름 호환 (다른 파일에서 쓰던 것)
ACCENT = GREEN
ACCENT_HOVER = GREEN_HOVER

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
QFrame#Toolbar {{ background: {BG}; border: none; border-bottom: 1px solid {BORDER}; }}
QLabel#ChipLabel {{ color: {MUTED}; }}
QFrame#ToolbarSep {{ background: {BORDER}; max-width: 1px; min-width: 1px; border: none; }}

/* ---------- 정보 패널 ---------- */
QFrame#InfoPanel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#InfoPanel QLineEdit {{ background: {BG}; }}
QFrame#Divider {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}

/* ---------- 목록 ---------- */
QFrame#QueueItem {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
QFrame#QueueItem:hover {{ background: #fbfcfd; border-color: {BORDER_STRONG}; }}
QFrame#QueueItem[fresh="true"] {{ background: {FRESH_BG}; border-color: {FRESH_BORDER}; }}
QFrame#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#AppTitle {{ font-size: 15pt; font-weight: 700; }}
QLabel#AppVersion {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Small {{ color: {MUTED}; font-size: 9pt; }}
QLabel#VideoTitle {{ font-size: 12pt; font-weight: 600; }}
QLabel#JobTitle {{ font-weight: 600; }}
QLabel#Notice {{ color: {WARNING}; }}
QLabel#Error {{ color: {DANGER}; }}
QLabel#Success {{ color: {SUCCESS}; }}
QLabel#FieldLabel {{ color: {MUTED}; }}
QLabel#Thumb {{ background: {SURFACE2}; border-radius: 6px; color: {MUTED}; }}
QLabel#Empty {{ color: {MUTED}; font-size: 10.5pt; }}
QLabel#EmptyTitle {{ color: {TEXT}; font-size: 13pt; font-weight: 600; }}
QLabel#ToastTitle {{ font-weight: 600; }}
QLabel#ToastBody {{ color: {MUTED}; }}
QFrame#Toast {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 10px; }}

/* ---------- 입력 ---------- */
QLineEdit, QComboBox, QSpinBox {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; border-radius: 6px;
    padding: 6px 10px;
}}
QLineEdit, QSpinBox {{ selection-background-color: {GREEN}; selection-color: white; }}
QComboBox {{ selection-background-color: {GREEN_SOFT}; selection-color: {TEXT}; }}
QLineEdit#UrlInput {{ font-size: 10.5pt; padding: 8px 12px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {GREEN}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: #a4abb3; background: {SURFACE}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; outline: none; padding: 4px;
    selection-background-color: {GREEN_SOFT}; selection-color: {TEXT};
}}
QComboBox QAbstractItemView::item {{ padding: 6px 10px; min-height: 22px; border-radius: 4px; }}
QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {{
    background: {GREEN_SOFT}; color: {TEXT};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}

/* ---------- 버튼 ---------- */
QPushButton {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; border-radius: 6px; padding: 6px 14px;
}}
QPushButton:hover {{ background: {SURFACE}; }}
QPushButton:pressed {{ background: {SURFACE2}; }}
QPushButton:disabled {{ color: #a4abb3; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {GREEN}; border: 1px solid {GREEN}; color: white; font-weight: 600; padding: 8px 18px;
}}
QPushButton[primary="true"]:hover {{ background: {GREEN_HOVER}; border-color: {GREEN_HOVER}; }}
QPushButton[primary="true"]:pressed {{ background: {GREEN_PRESS}; border-color: {GREEN_PRESS}; }}
QPushButton[primary="true"]:disabled {{ background: #bfe0a4; border-color: #bfe0a4; color: white; }}
QPushButton[segment="true"] {{ border-radius: 0px; padding: 6px 18px; }}
QPushButton[segment="true"][first="true"] {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QPushButton[segment="true"][last="true"] {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton[segment="true"]:checked {{ background: {GREEN}; border-color: {GREEN}; color: white; font-weight: 600; }}
QPushButton[ghost="true"] {{
    background: transparent; border: none; color: {MUTED}; padding: 5px 9px; border-radius: 6px;
}}
QPushButton[ghost="true"]:hover {{ background: {SURFACE2}; color: {TEXT}; }}
QPushButton[ghost="true"]:disabled {{ color: #b6bcc3; background: transparent; }}
QPushButton[iconbtn="true"] {{
    background: transparent; border: none; border-radius: 6px; padding: 5px; min-width: 20px; min-height: 20px;
}}
QPushButton[iconbtn="true"]:hover {{ background: {SURFACE2}; }}
QPushButton[iconbtn="true"]:pressed {{ background: #e0e4e8; }}
QPushButton[link="true"] {{
    background: transparent; border: none; color: {GREEN_TEXT}; padding: 2px 0px; text-align: left;
}}
QPushButton[link="true"]:hover {{ text-decoration: underline; }}
QPushButton[tab="true"] {{
    background: transparent; border: none; border-bottom: 2px solid transparent; border-radius: 0px;
    color: {MUTED}; padding: 9px 4px; margin-right: 14px;
}}
QPushButton[tab="true"]:hover {{ color: {TEXT}; background: transparent; }}
QPushButton[tab="true"]:checked {{ color: {TEXT}; border-bottom: 2px solid {GREEN}; }}
QPushButton[chip="true"] {{
    background: transparent; border: none; border-radius: 6px; padding: 5px 6px; font-weight: 600; text-align: left;
}}
QPushButton[chip="true"]:hover {{ background: {SURFACE2}; }}
QPushButton[chip="true"]::menu-indicator {{ image: none; width: 0px; }}
QDialogButtonBox QPushButton {{ min-width: 76px; }}

/* ---------- 체크/라디오 ---------- */
QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid #aeb5bd; background: {BG};
}}
QCheckBox::indicator:hover {{ border-color: {GREEN}; }}
QCheckBox::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; image: url("{check}"); }}
QCheckBox:disabled {{ color: #a4abb3; }}
QCheckBox::indicator:disabled {{ background: {SURFACE}; border-color: {BORDER}; }}
QRadioButton {{ spacing: 7px; background: transparent; padding: 2px 0; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 8px; border: 2px solid #aeb5bd; background: {BG};
}}
QRadioButton::indicator:hover {{ border-color: {GREEN}; }}
QRadioButton::indicator:checked {{ border: 4px solid {GREEN}; background: white; width: 10px; height: 10px; }}
QRadioButton:disabled {{ color: #a4abb3; }}

/* ---------- 진행 막대 ---------- */
QProgressBar {{
    background: #e6e9ed; border: none; border-radius: 2px; max-height: 4px; min-height: 4px;
}}
QProgressBar::chunk {{ background: {GREEN}; border-radius: 2px; }}
QProgressBar[state="done"]::chunk {{ background: {GREEN}; }}
QProgressBar[state="failed"]::chunk {{ background: {DANGER}; }}
QProgressBar[state="canceled"]::chunk {{ background: #aab1b9; }}

/* ---------- 탭(대화상자용) ---------- */
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 8px 14px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {GREEN}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

/* ---------- 스크롤 ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #cfd4da; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #b4bbc3; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #cfd4da; border-radius: 4px; min-width: 30px; }}
QSplitter::handle {{ background: transparent; }}

/* ---------- 표/목록 ---------- */
QTreeWidget, QListWidget {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; outline: none;
    alternate-background-color: #fafbfc;
}}
QTreeWidget::item, QListWidget::item {{ padding: 5px 4px; }}
QListWidget::indicator {{
    width: 15px; height: 15px; border-radius: 4px; border: 1px solid #aeb5bd; background: {BG};
}}
QListWidget::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; image: url("{check}"); }}
QListWidget::indicator:disabled {{ border-color: transparent; background: transparent; }}
QListWidget::item:disabled {{ color: #a4abb3; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {GREEN_SOFT}; color: {TEXT}; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {SURFACE}; }}
QHeaderView::section {{
    background: {SURFACE}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 6px 8px;
}}

QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 8px; margin-top: 16px; padding: 14px 12px 10px 12px;
    background: {BG};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {MUTED}; }}

/* ---------- 기타 ---------- */
QStatusBar {{ background: {BG}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ color: {MUTED}; font-size: 9pt; }}
QStatusBar QPushButton {{ font-size: 9pt; }}
QStatusBar::item {{ border: none; }}
QToolTip {{
    background: #2b2f33; color: white; border: none; padding: 6px 8px; border-radius: 6px;
}}
QMenu {{ background: {BG}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 7px 24px 7px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background: {SURFACE2}; }}
QMenu::item:disabled {{ color: #a4abb3; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 6px; }}
QPlainTextEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    font-family: "Cascadia Mono", Consolas, "D2Coding", monospace; font-size: 9pt;
}}
QMessageBox QLabel {{ min-width: 320px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(BG))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(BG))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    # 선택 표시는 연한 초록 + 진한 글자 (드롭다운 목록·글자 선택에 쓰임)
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#cfe9b8"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2b2f33"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("white"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(PLACEHOLDER))
    pal.setColor(QPalette.ColorRole.Link, QColor(GREEN_TEXT))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor("#a4abb3"))
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
    grad.setColorAt(0, QColor("#7bcf3c"))
    grad.setColorAt(1, QColor("#4a9a14"))
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
