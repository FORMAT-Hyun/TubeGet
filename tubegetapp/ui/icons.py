"""직접 그린 아이콘.

이미지 파일 없이 코드로 그려서 어떤 화면 배율(DPI)에서도 선명하고, 색을 바꾸기 쉬워요.
모든 아이콘은 24x24 칸 기준으로 그린 뒤 원하는 크기로 늘려요.
"""
from __future__ import annotations

import math
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_Draw = Callable[[QPainter, QColor], None]


def _pen(color: QColor, width: float = 1.8) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _stroke(p: QPainter, color: QColor, width: float = 1.8) -> None:
    p.setPen(_pen(color, width))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _fill(p: QPainter, color: QColor) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)


# ---------------------------------------------------------------------------
# 그리기 함수들 (24x24)
# ---------------------------------------------------------------------------
def _folder(p: QPainter, c: QColor) -> None:
    _stroke(p, c)
    path = QPainterPath()
    path.moveTo(3.2, 6.8)
    path.lineTo(9.0, 6.8)
    path.lineTo(11.0, 9.0)
    path.lineTo(20.8, 9.0)
    path.lineTo(20.8, 18.6)
    path.lineTo(3.2, 18.6)
    path.closeSubpath()
    p.drawPath(path)


def _kebab(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    for y in (5.2, 12.0, 18.8):
        p.drawEllipse(QPointF(12, y), 1.9, 1.9)


def _gear(p: QPainter, c: QColor) -> None:
    outer = QPainterPath()
    outer.addEllipse(QPointF(12, 12), 6.6, 6.6)
    for i in range(8):
        tooth = QPainterPath()
        tooth.addRoundedRect(QRectF(-1.9, -10.2, 3.8, 4.6), 0.9, 0.9)
        from PySide6.QtGui import QTransform
        t = QTransform()
        t.translate(12, 12)
        t.rotate(i * 45)
        outer = outer.united(t.map(tooth))
    hole = QPainterPath()
    hole.addEllipse(QPointF(12, 12), 3.1, 3.1)
    _fill(p, c)
    p.drawPath(outer.subtracted(hole))


def _info(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.7)
    p.drawEllipse(QPointF(12, 12), 9.0, 9.0)
    _fill(p, c)
    p.drawEllipse(QPointF(12, 7.9), 1.15, 1.15)
    _stroke(p, c, 1.9)
    p.drawLine(QPointF(12, 11), QPointF(12, 16.6))


def _close(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.9)
    p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
    p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))


def _chevron_down(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    p.drawPolyline([QPointF(6.2, 9.2), QPointF(12, 15), QPointF(17.8, 9.2)])


def _check_circle(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.8)
    p.drawEllipse(QPointF(12, 12), 9.2, 9.2)
    p.drawPolyline([QPointF(7.6, 12.4), QPointF(10.7, 15.4), QPointF(16.6, 9.0)])


def _error_circle(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.8)
    p.drawEllipse(QPointF(12, 12), 9.2, 9.2)
    p.drawLine(QPointF(12, 7.0), QPointF(12, 13.0))
    _fill(p, c)
    p.drawEllipse(QPointF(12, 16.4), 1.15, 1.15)


def _retry(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.9)
    rect = QRectF(5.0, 5.0, 14.0, 14.0)
    path = QPainterPath()
    path.arcMoveTo(rect, 60)
    path.arcTo(rect, 60, 270)
    p.drawPath(path)
    # 화살촉
    tip = QPointF(12 + 7 * math.cos(math.radians(60)), 12 - 7 * math.sin(math.radians(60)))
    _fill(p, c)
    tri = QPainterPath()
    tri.moveTo(tip.x() + 3.4, tip.y() - 0.4)
    tri.lineTo(tip.x() - 0.2, tip.y() - 3.4)
    tri.lineTo(tip.x() - 0.8, tip.y() + 2.4)
    tri.closeSubpath()
    p.drawPath(tri)


def _music(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawEllipse(QPointF(8.2, 17.6), 3.0, 2.5)
    p.drawEllipse(QPointF(17.0, 15.8), 3.0, 2.5)
    _stroke(p, c, 1.9)
    p.drawLine(QPointF(10.9, 17.2), QPointF(10.9, 6.2))
    p.drawLine(QPointF(19.7, 15.4), QPointF(19.7, 4.6))
    p.drawLine(QPointF(10.9, 6.2), QPointF(19.7, 4.6))


def _video(p: QPainter, c: QColor) -> None:
    _fill(p, c)
    p.drawRoundedRect(QRectF(3, 5.5, 18, 13), 3.2, 3.2)
    p.setBrush(QColor(255, 255, 255, 235))
    tri = QPainterPath()
    tri.moveTo(10, 9.2)
    tri.lineTo(15.4, 12)
    tri.lineTo(10, 14.8)
    tri.closeSubpath()
    p.drawPath(tri)


def _download(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(12, 4.2), QPointF(12, 14.6))
    p.drawPolyline([QPointF(7.6, 10.4), QPointF(12, 14.8), QPointF(16.4, 10.4)])
    p.drawPolyline([QPointF(4.6, 15.6), QPointF(4.6, 19.4), QPointF(19.4, 19.4), QPointF(19.4, 15.6)])


def _link_play(p: QPainter, c: QColor) -> None:
    """초록 버튼 위에 얹는 흰색 '재생 상자' (c = 상자 색)."""
    box = QPainterPath()
    box.addRoundedRect(QRectF(2.2, 5.2, 19.6, 13.6), 3.6, 3.6)
    tri = QPainterPath()
    tri.moveTo(10.0, 8.9)
    tri.lineTo(15.6, 12.0)
    tri.lineTo(10.0, 15.1)
    tri.closeSubpath()
    _fill(p, c)
    p.drawPath(box.subtracted(tri))


def _search(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.9)
    p.drawEllipse(QPointF(10.6, 10.6), 6.0, 6.0)
    p.drawLine(QPointF(15.2, 15.2), QPointF(20.2, 20.2))


_ICONS: dict[str, _Draw] = {
    "folder": _folder, "kebab": _kebab, "gear": _gear, "info": _info, "close": _close,
    "chevron_down": _chevron_down, "check_circle": _check_circle, "error_circle": _error_circle,
    "retry": _retry, "music": _music, "video": _video, "download": _download,
    "link_play": _link_play, "search": _search,
}

_cache: dict[tuple, QIcon] = {}


def pixmap(name: str, color: str = "#5f6670", size: int = 20) -> QPixmap:
    """아이콘을 선명한 QPixmap 으로 (2배 해상도로 그려서 축소 표시)."""
    dpr = 3.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(size / 24.0, size / 24.0)
    _ICONS[name](p, QColor(color))
    p.end()
    return pm


def icon(name: str, color: str = "#5f6670", size: int = 20) -> QIcon:
    key = (name, color, size)
    ic = _cache.get(key)
    if ic is None:
        ic = QIcon(pixmap(name, color, size))
        _cache[key] = ic
    return ic


def icon_size(size: int = 20) -> QSize:
    return QSize(size, size)
