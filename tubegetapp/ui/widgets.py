"""공용 위젯: 말줄임 라벨, 썸네일 로더, 세그먼트 토글, 로그 창."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QUrl, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION
from . import icons
from .theme import ACCENT, DISABLED, ICON, MUTED, SURFACE2, TEXT
from ..i18n import tr


class ElidedLabel(QLabel):
    """너비가 모자라면 '…'로 줄이는 한 줄 라벨."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None,
                 mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight):
        super().__init__(parent)
        self._full = text
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(10)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text or ""
        self.setToolTip(self._full if len(self._full) > 20 else "")
        self._update()

    def fullText(self) -> str:  # noqa: N802
        return self._full

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update()

    def _update(self) -> None:
        width = max(self.width(), 10)
        super().setText(self.fontMetrics().elidedText(self._full, self._mode, width))


def rounded(pm: QPixmap, size: QSize, radius: int = 8, badge: Optional[str] = None) -> QPixmap:
    """썸네일을 꽉 채워 자르고 모서리를 둥글게. badge 를 주면 오른쪽 아래에 (영상 길이 같은) 작은 표시를 얹는다."""
    dpr = 2.0
    target = QPixmap(int(size.width() * dpr), int(size.height() * dpr))
    target.setDevicePixelRatio(dpr)
    target.fill(Qt.GlobalColor.transparent)
    scaled = pm.scaled(size * dpr, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                       Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    p = QPainter(target)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
    p.setClipPath(path)
    x = (size.width() - scaled.width() / dpr) / 2
    y = (size.height() - scaled.height() / dpr) / 2
    p.drawPixmap(int(x), int(y), scaled)
    if badge:
        f = p.font()
        f.setPointSizeF(9.0)
        f.setBold(True)
        p.setFont(f)
        fm = QFontMetrics(f)
        w, h = fm.horizontalAdvance(badge) + 12, fm.height() + 4
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 190))
        p.drawRoundedRect(QRectF(size.width() - w - 8, size.height() - h - 8, w, h), 6, 6)
        p.setPen(QColor("white"))
        p.drawText(QRectF(size.width() - w - 8, size.height() - h - 8, w, h), Qt.AlignmentFlag.AlignCenter, badge)
    p.end()
    return target


class ThumbLoader(QObject):
    """썸네일 비동기 로딩 + 메모리 캐시."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        self._cache: dict[str, QPixmap] = {}
        self._waiting: dict[str, list[Callable[[QPixmap], None]]] = {}

    def load(self, url: Optional[str], callback: Callable[[QPixmap], None]) -> None:
        if not url:
            return
        if url in self._cache:
            _safe_call(callback, self._cache[url])
            return
        if url in self._waiting:
            self._waiting[url].append(callback)
            return
        self._waiting[url] = [callback]
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, f"{APP_NAME}/{APP_VERSION}")
        reply = self._nam.get(req)
        reply.finished.connect(lambda r=reply, u=url: self._done(r, u))

    def _done(self, reply: QNetworkReply, url: str) -> None:
        callbacks = self._waiting.pop(url, [])
        pm = QPixmap()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pm.loadFromData(bytes(reply.readAll()))
        reply.deleteLater()
        if pm.isNull():
            return
        if len(self._cache) > 300:
            self._cache.clear()
        self._cache[url] = pm
        for cb in callbacks:
            _safe_call(cb, pm)


def _safe_call(cb: Callable, *args) -> None:
    try:
        cb(*args)
    except RuntimeError:
        # 위젯이 이미 사라진 경우
        pass


class SegmentedToggle(QWidget):
    """[영상 | 음원만] 같은 붙은 버튼 그룹."""
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for i, (key, label) in enumerate(options):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setProperty("segment", True)
            b.setProperty("first", i == 0)
            b.setProperty("last", i == len(options) - 1)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(b)
            self._buttons[key] = b
            lay.addWidget(b)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))

    def value(self) -> str:
        for k, b in self._buttons.items():
            if b.isChecked():
                return k
        return next(iter(self._buttons))

    def setValue(self, key: str) -> None:  # noqa: N802
        b = self._buttons.get(key)
        if b:
            b.setChecked(True)


SHORT_ROLE = Qt.ItemDataRole.UserRole + 11


def _paint_chip(w: QWidget, text: str, hover: bool, bold_font) -> None:
    """칩(납작한 드롭다운) 모양 그리기: 글자 + 바로 옆 ▾, 마우스를 올리면 연한 회색 배경."""
    p = QPainter(w)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = w.rect()
    if w.isEnabled() and hover:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(SURFACE2))
        p.drawRoundedRect(QRectF(r).adjusted(0.5, 2.5, -0.5, -2.5), 6, 6)
    p.setFont(bold_font)
    p.setPen(QColor(TEXT if w.isEnabled() else DISABLED))
    fm = QFontMetrics(bold_font)
    text = fm.elidedText(text, Qt.TextElideMode.ElideRight, r.width() - 8 - 2 - 16 - 6)
    p.drawText(r.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
    pm = icons.pixmap("chevron_down", MUTED if w.isEnabled() else DISABLED, 16)
    p.drawPixmap(8 + fm.horizontalAdvance(text) + 2, (r.height() - 16) // 2, pm)


class ChipCombo(QComboBox):
    """툴바용 납작한 드롭다운. 칩에는 짧은 값만 굵게 보이고, 펼친 목록에는 긴 설명이 보여요."""

    HEIGHT = 32

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Chip")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._hover = False
        self._open = False
        m = self.model()
        for sig in (m.rowsInserted, m.rowsRemoved, m.modelReset, m.dataChanged):
            sig.connect(lambda *_: self.updateGeometry())
        self.currentIndexChanged.connect(lambda *_: (self.updateGeometry(), self.update()))

    def event(self, e) -> bool:  # noqa: N802
        r = super().event(e)
        if e.type() in (QEvent.Type.Polish, QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.updateGeometry()
        return r

    def addChip(self, long_text: str, data=None, short: Optional[str] = None) -> None:  # noqa: N802
        self.addItem(long_text, data)
        if short:
            self.setItemData(self.count() - 1, short, SHORT_ROLE)

    def _short(self, i: int) -> str:
        if i < 0:
            return ""
        return self.itemData(i, SHORT_ROLE) or self.itemText(i)

    def _bold_font(self):
        f = self.font()
        f.setBold(True)
        return f

    def sizeHint(self) -> QSize:  # noqa: N802
        self.ensurePolished()      # 스타일시트의 글꼴(10pt)이 적용된 뒤에 폭을 잰다
        fm = QFontMetrics(self._bold_font())
        return QSize(fm.horizontalAdvance(self._short(self.currentIndex())) + 8 + 2 + 16 + 8, self.HEIGHT)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def showPopup(self) -> None:  # noqa: N802
        view = self.view()
        view.setMinimumWidth(max(self.width(), view.sizeHintForColumn(0) + 36))
        self._open = True
        self.update()
        super().showPopup()

    def hidePopup(self) -> None:  # noqa: N802
        super().hidePopup()
        self._open = False
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        _paint_chip(self, self._short(self.currentIndex()), self._hover or self._open or self.hasFocus(),
                    self._bold_font())


class ChipButton(QAbstractButton):
    """칩 모양의 버튼 (클릭하면 메뉴를 띄우는 용도). 글자 + ▾."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._hover = False

    def _bold_font(self):
        f = self.font()
        f.setBold(True)
        return f

    def event(self, e) -> bool:  # noqa: N802
        r = super().event(e)
        if e.type() in (QEvent.Type.Polish, QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.updateGeometry()
        return r

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(text)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        self.ensurePolished()
        fm = QFontMetrics(self._bold_font())
        return QSize(fm.horizontalAdvance(self.text()) + 8 + 2 + 16 + 8, ChipCombo.HEIGHT)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        _paint_chip(self, self.text(), self._hover or self.hasFocus(), self._bold_font())


class ModeCombo(ChipCombo):
    """[영상 | 오디오] 고르기. SegmentedToggle 과 같은 사용법(value/setValue/changed)."""
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        for key, label in options:
            self.addChip(label, key)
        self.activated.connect(lambda i: self.changed.emit(self.itemData(i)))

    def value(self) -> str:
        return self.currentData() or self.itemData(0)

    def setValue(self, key: str) -> None:  # noqa: N802
        i = self.findData(key)
        if i >= 0:
            self.setCurrentIndex(i)


class ToggleSwitch(QAbstractButton):
    """둥근 켜기/끄기 스위치."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._animate)

    def _on_anim(self, v) -> None:
        self._pos = float(v)
        self.update()

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setCheckedSilently(self, on: bool) -> None:  # noqa: N802
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        off, on = QColor("#4a4f5a"), QColor(ACCENT)
        t = self._pos
        track = QColor(int(off.red() + (on.red() - off.red()) * t),
                       int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t))
        if not self.isEnabled():
            p.setOpacity(0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(1, 2, self.width() - 2, self.height() - 4), 10, 10)
        d = 16
        x = 4 + t * (self.width() - 8 - d)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(QRectF(x, 4.6, d, d))
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 4, d, d))


def icon_button(name: str, tooltip: str = "", *, color: str = ICON, size: int = 20,
                box: int = 32) -> QPushButton:
    """아이콘만 있는 납작한 버튼."""
    b = QPushButton()
    b.setProperty("iconbtn", True)
    b.setIcon(icons.icon(name, color, size))
    b.setIconSize(QSize(size, size))
    b.setFixedSize(box, box)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    return b


def pill_check(text: str) -> "QCheckBox":
    """알약 모양 켜기/끄기 버튼 (켜면 빨간 테두리 + ✓)."""
    cb = QCheckBox(text)
    cb.setProperty("pill", True)
    cb.setCursor(Qt.CursorShape.PointingHandCursor)
    cb.toggled.connect(lambda on, t=text: cb.setText(("✓  " if on else "") + t))
    return cb


def make_button(text: str, *, primary: bool = False, ghost: bool = False, link: bool = False,
                tooltip: str = "") -> QPushButton:
    b = QPushButton(text)
    if primary:
        b.setProperty("primary", True)
    if ghost:
        b.setProperty("ghost", True)
    if link:
        b.setProperty("link", True)
    if tooltip:
        b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def show_log_dialog(parent: QWidget, title: str, lines: list[str]) -> None:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(760, 460)
    lay = QVBoxLayout(dlg)
    text = QPlainTextEdit()
    text.setReadOnly(True)
    text.setPlainText("\n".join(lines) or tr("(로그 없음)"))
    text.moveCursor(text.textCursor().MoveOperation.End)
    lay.addWidget(text)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    copy = box.addButton(tr("복사"), QDialogButtonBox.ButtonRole.ActionRole)
    copy.clicked.connect(lambda: (text.selectAll(), text.copy()))
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.exec()


def field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl
