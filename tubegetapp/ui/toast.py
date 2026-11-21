"""화면 오른쪽 아래에 잠깐 뜨는 알림 (다운로드 완료/실패 등)."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from . import icons
from .theme import DANGER, SUCCESS, WARNING
from .widgets import icon_button

_COLORS = {"ok": SUCCESS, "error": DANGER, "warn": WARNING}
_ICONS = {"ok": "check_circle", "error": "error_circle", "warn": "error_circle"}
TOAST_WIDTH = 320
MARGIN = 16
GAP = 10


BODY_WIDTH = TOAST_WIDTH - 14 - 8 - 22 - 24 - 10 * 2   # 본문 글자가 들어갈 너비


def clamp_lines(fm: QFontMetrics, text: str, width: int, lines: int) -> str:
    """글이 정해진 줄 수를 넘으면 끝을 '…'로 줄인다."""
    def height(s: str) -> int:
        return fm.boundingRect(QRect(0, 0, width, 10000), int(Qt.TextFlag.TextWordWrap), s).height()
    limit = fm.lineSpacing() * lines + 2
    if height(text) <= limit:
        return text
    while text and height(text + "…") > limit:
        text = text[:-1]
    return text.rstrip() + "…"


class Toast(QFrame):
    def __init__(self, parent: QWidget, kind: str, title: str, body: str):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFixedWidth(TOAST_WIDTH)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.setGraphicsEffect(shadow)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 8, 12)
        root.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap(_ICONS.get(kind, "check_circle"), _COLORS.get(kind, SUCCESS), 22))
        ic.setFixedSize(QSize(22, 22))
        root.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel(title)
        t.setObjectName("ToastTitle")
        t.ensurePolished()
        t.setFixedHeight(QFontMetrics(t.font()).lineSpacing() + 2)
        col.addWidget(t)
        if body:
            b = QLabel()
            b.setObjectName("ToastBody")
            b.setWordWrap(True)
            b.ensurePolished()          # 스타일시트 글꼴이 적용된 뒤에 글 높이를 잰다
            fm = QFontMetrics(b.font())
            text = clamp_lines(fm, body, BODY_WIDTH, 3)
            b.setText(text)
            h = fm.boundingRect(QRect(0, 0, BODY_WIDTH, 10000), int(Qt.TextFlag.TextWordWrap), text).height() + 2
            b.setFixedSize(BODY_WIDTH, h)
            b.setToolTip(body)
            col.addWidget(b)
        root.addLayout(col, 1)

        self.btn = icon_button("close", "닫기", color="#9aa0aa", size=14, box=24)
        root.addWidget(self.btn, 0, Qt.AlignmentFlag.AlignTop)
        self.setFixedHeight(self.sizeHint().height())


class ToastManager(QObject):
    """창 오른쪽 아래에 알림을 쌓아서 보여주고, 시간이 지나면 지워요."""

    def __init__(self, host: QWidget, anchor_bottom_offset=lambda: 0):
        super().__init__(host)
        self.host = host
        self._toasts: list[Toast] = []
        self._bottom_offset = anchor_bottom_offset
        host.installEventFilter(self)

    def show(self, kind: str, title: str, body: str = "", timeout_ms: int = 5000) -> Toast:
        # 같은 내용이 이미 떠 있으면 새로 만들지 않고 시간만 늘린다
        for t in self._toasts:
            if getattr(t, "_key", None) == (kind, title, body):
                t._timer.start(timeout_ms)
                return t
        toast = Toast(self.host, kind, title, body)
        toast._key = (kind, title, body)
        toast._timer = QTimer(toast)
        toast._timer.setSingleShot(True)
        toast._timer.timeout.connect(lambda t=toast: self._dismiss(t))
        toast.btn.clicked.connect(lambda _=False, t=toast: self._dismiss(t))
        self._toasts.append(toast)
        if len(self._toasts) > 4:
            self._dismiss(self._toasts[0])
        toast.show()
        toast.raise_()
        self._layout()
        toast._timer.start(timeout_ms)
        return toast

    def _dismiss(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            toast.hide()
            toast.deleteLater()
            self._layout()

    def clear(self) -> None:
        for t in list(self._toasts):
            self._dismiss(t)

    def _layout(self) -> None:
        y = self.host.height() - MARGIN - self._bottom_offset()
        for t in reversed(self._toasts):
            t.adjustSize()
            y -= t.height()
            t.move(QPoint(self.host.width() - MARGIN - t.width(), y))
            y -= GAP
            t.raise_()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.host and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._layout()
        return False
