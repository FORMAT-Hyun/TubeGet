"""마우스 휠로 드롭다운·숫자 칸 값이 바뀌지 않게 막는다.

화면을 스크롤하다가 커서가 드롭다운 위를 지나가면 원하지 않는 값으로 바뀌는 문제가 있어서,
휠은 값 대신 그 칸이 들어 있는 스크롤 영역으로 넘겨 화면만 움직이게 한다.
펼친 목록 안에서 휠을 굴리는 것은 목록(뷰)이 받으므로 그대로 동작한다.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QSlider,
                               QWidget)

_GUARDED = (QComboBox, QAbstractSpinBox, QSlider)


def _scroll_area_of(w: QWidget):
    p = w.parentWidget()
    while p is not None:
        if isinstance(p, QAbstractScrollArea):
            return p
        p = p.parentWidget()
    return None


class WheelGuard(QObject):
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel and isinstance(obj, _GUARDED):
            area = _scroll_area_of(obj)
            if area is not None:
                horizontal = abs(event.angleDelta().x()) > abs(event.angleDelta().y())
                bar = area.horizontalScrollBar() if horizontal else area.verticalScrollBar()
                if bar is not None and bar.isVisible():
                    QApplication.sendEvent(bar, event)
            return True  # 값은 바꾸지 않는다
        return False


_guard: WheelGuard | None = None


def install(app: QApplication) -> None:
    """앱 전체에 한 번만 설치한다."""
    global _guard
    if _guard is None:
        _guard = WheelGuard(app)
        app.installEventFilter(_guard)
