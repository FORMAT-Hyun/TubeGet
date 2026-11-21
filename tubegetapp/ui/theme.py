"""다크 테마, 앱 아이콘."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QPixmap)
from PySide6.QtWidgets import QApplication, QWidget

from ..paths import resource_path

ACCENT = "#ff4d4f"
ACCENT_HOVER = "#ff6466"
BG = "#121316"
SURFACE = "#1b1d22"
SURFACE2 = "#23262d"
BORDER = "#2c3038"
TEXT = "#e8e9ec"
MUTED = "#9aa0aa"
SUCCESS = "#3ecf8e"
DANGER = "#ff6b6b"
WARNING = "#f5b544"

FONT_STACK = '"Pretendard", "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif'


def _qss() -> str:
    check = resource_path("assets", "check.svg").as_posix()
    return f"""
* {{ font-family: {FONT_STACK}; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#Central {{ background: {BG}; }}
QFrame#Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#QueueItem {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel {{ background: transparent; }}
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

QLineEdit, QComboBox, QSpinBox {{
    background: {SURFACE2}; border: 1px solid #343842; border-radius: 8px;
    padding: 7px 10px; selection-background-color: {ACCENT};
}}
QLineEdit#UrlInput {{ font-size: 11pt; padding: 9px 12px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: #666b75; background: #1f2227; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE2}; border: 1px solid #343842; outline: none;
    selection-background-color: #3d2b2d; padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}

QPushButton {{
    background: #2a2e36; border: 1px solid #363b45; border-radius: 8px; padding: 7px 14px;
}}
QPushButton:hover {{ background: #333842; }}
QPushButton:pressed {{ background: #262a31; }}
QPushButton:disabled {{ color: #666b75; background: #1f2227; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: white; font-weight: 600; padding: 8px 18px;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:disabled {{ background: #5a2a2b; border-color: #5a2a2b; color: #c9a3a4; }}
QPushButton[segment="true"] {{ border-radius: 0px; padding: 7px 18px; }}
QPushButton[segment="true"][first="true"] {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QPushButton[segment="true"][last="true"] {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
QPushButton[segment="true"]:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton[ghost="true"] {{
    background: transparent; border: none; color: {MUTED}; padding: 5px 9px; border-radius: 6px;
}}
QPushButton[ghost="true"]:hover {{ background: #2a2e36; color: {TEXT}; }}
QPushButton[ghost="true"]:disabled {{ color: #4a4f58; background: transparent; }}
QPushButton[link="true"] {{
    background: transparent; border: none; color: {ACCENT}; padding: 2px 0px; text-align: left;
}}
QPushButton[link="true"]:hover {{ color: {ACCENT_HOVER}; text-decoration: underline; }}

QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid #4a505c; background: {SURFACE2};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url("{check}"); }}
QCheckBox:disabled {{ color: #666b75; }}
QRadioButton {{ spacing: 7px; background: transparent; padding: 2px 0; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 8px; border: 2px solid #555b67; background: {SURFACE2};
}}
QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
QRadioButton::indicator:checked {{ border: 4px solid {ACCENT}; background: white; width: 10px; height: 10px; }}
QRadioButton:disabled {{ color: #666b75; }}
QCheckBox::indicator:disabled {{ background: #1f2227; border-color: {BORDER}; }}

QProgressBar {{
    background: #2a2d34; border: none; border-radius: 3px; max-height: 6px; min-height: 6px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QProgressBar[state="done"]::chunk {{ background: {SUCCESS}; }}
QProgressBar[state="failed"]::chunk {{ background: {DANGER}; }}
QProgressBar[state="canceled"]::chunk {{ background: #5b606b; }}

QTabWidget::pane {{ border: none; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 8px 14px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QScrollArea {{ background: transparent; border: none; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:vertical {{ height: 10px; image: none; }}
QSplitter::handle:hover {{ background: #2a2e36; border-radius: 4px; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3a3e48; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #4a4f5a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #3a3e48; border-radius: 4px; min-width: 30px; }}

QTreeWidget, QListWidget {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; outline: none;
    alternate-background-color: #1e2025;
}}
QTreeWidget::item, QListWidget::item {{ padding: 5px 4px; }}
QListWidget::indicator {{
    width: 15px; height: 15px; border-radius: 4px; border: 1px solid #555b67; background: {SURFACE2};
}}
QListWidget::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url("{check}"); }}
QListWidget::indicator:disabled {{ border-color: transparent; background: transparent; }}
QListWidget::item:disabled {{ color: #5b606b; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: #3d2b2d; color: {TEXT}; }}
QHeaderView::section {{
    background: {SURFACE}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 6px 8px;
}}

QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 10px; margin-top: 16px; padding: 14px 12px 10px 12px;
    background: {SURFACE};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {MUTED}; }}

QStatusBar {{ background: #0e0f12; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ color: {MUTED}; }}
QStatusBar::item {{ border: none; }}
QToolTip {{
    background: #2a2e36; color: {TEXT}; border: 1px solid #3a3e48; padding: 6px; border-radius: 6px;
}}
QMenu {{ background: {SURFACE2}; border: 1px solid #343842; padding: 4px; }}
QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: #3d2b2d; }}
QPlainTextEdit {{
    background: #0e0f12; border: 1px solid {BORDER}; border-radius: 8px;
    font-family: "Cascadia Mono", Consolas, "D2Coding", monospace; font-size: 9pt;
}}
QMessageBox QLabel {{ min-width: 320px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(SURFACE2))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2e36"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2a2e36"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6b717c"))
    pal.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor("#666b75"))
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
