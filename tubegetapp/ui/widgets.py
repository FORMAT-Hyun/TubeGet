"""공용 위젯: 말줄임 라벨, 썸네일 로더, 세그먼트 토글, 로그 창."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION


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


def rounded(pm: QPixmap, size: QSize, radius: int = 8) -> QPixmap:
    """썸네일을 꽉 채워 자르고 모서리를 둥글게."""
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
    text.setPlainText("\n".join(lines) or "(로그 없음)")
    text.moveCursor(text.textCursor().MoveOperation.End)
    lay.addWidget(text)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    copy = box.addButton("복사", QDialogButtonBox.ButtonRole.ActionRole)
    copy.clicked.connect(lambda: (text.selectAll(), text.copy()))
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.exec()


def field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl
