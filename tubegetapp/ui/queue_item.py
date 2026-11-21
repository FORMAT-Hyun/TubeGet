"""다운로드 목록의 한 줄 (4K Video Downloader+ 같은 납작한 행)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QProgressBar, QSizePolicy,
                               QVBoxLayout, QWidget)

from ..core.options import AUDIO_FORMATS, height_label
from ..core.runner import CANCELED, DONE, FAILED, QUEUED, RUNNING, DownloadJob
from ..utils import human_duration, human_size, reveal_in_explorer
from . import icons
from .theme import repolish
from .widgets import ElidedLabel, ThumbLoader, icon_button, make_button, rounded, show_log_dialog

THUMB = QSize(72, 40)
FRESH_MS = 9000        # 방금 끝난 항목을 연한 노란 테두리로 보여주는 시간


def placeholder_thumb(mode: str) -> QPixmap:
    """썸네일이 오기 전/없을 때 보여줄 회색 칸 + 아이콘."""
    dpr = 2.0
    pm = QPixmap(int(THUMB.width() * dpr), int(THUMB.height() * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(Qt.GlobalColor.transparent)
    from PySide6.QtGui import QColor
    p.setBrush(QColor("#eceff2"))
    p.drawRoundedRect(0, 0, THUMB.width(), THUMB.height(), 6, 6)
    ic = icons.pixmap("music" if mode == "audio" else "video", "#aab1b9", 22)
    p.drawPixmap((THUMB.width() - 22) // 2, (THUMB.height() - 22) // 2, ic)
    p.end()
    return pm


def format_bits(job: DownloadJob) -> list[str]:
    """'MP3 · 192k' / '1080p · MP4' 같은 형식 설명."""
    o = job.options
    bits: list[str] = []
    if o.mode == "audio":
        label = dict(AUDIO_FORMATS).get(o.audio_format, o.audio_format)
        bits.append(label.split(" ")[0])
        q = (o.audio_quality or "").upper()
        if q.endswith("K") and o.audio_format in ("mp3", "m4a", "opus"):
            bits.append(q[:-1].lstrip("0") + "k")
    else:
        bits.append(height_label(o.max_height).split(" ")[0] if o.max_height else "최고 화질")
        bits.append(o.container.upper())
    return bits


def done_meta(job: DownloadJob) -> str:
    """완료된 항목 아래 줄: 길이 · 크기 · 형식 · 저장 폴더."""
    bits: list[str] = []
    if job.duration:
        bits.append(human_duration(job.duration))
    path = job.filepath
    if path and os.path.exists(path):
        try:
            bits.append(human_size(os.path.getsize(path)))
        except OSError:
            pass
    bits += format_bits(job)
    folder = Path(path).parent.name if path else Path(job.options.output_dir).name
    if folder:
        bits.append(folder)
    if job.skipped:
        bits.insert(0, "이미 받은 파일이라 건너뛰었어요")
    return " · ".join(bits)


class QueueItemWidget(QFrame):
    removeRequested = Signal(object)
    retryRequested = Signal(object)
    overwriteRequested = Signal(object)

    def __init__(self, job: DownloadJob, thumbs: ThumbLoader, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.job = job
        self.setObjectName("QueueItem")
        self.setMinimumHeight(62)
        # 목록이 좁아도 행이 찌그러지지 않게 (자기 높이 이하로는 줄어들지 않음)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 6, 10)
        root.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(THUMB)
        self.thumb.setPixmap(placeholder_thumb(job.options.mode))
        root.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignVCenter)

        mid = QVBoxLayout()
        mid.setSpacing(3)
        self.title = ElidedLabel(job.title)
        self.title.setObjectName("JobTitle")
        self.meta = ElidedLabel("")
        self.meta.setObjectName("Small")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        mid.addStretch(1)
        mid.addWidget(self.title)
        mid.addWidget(self.meta)
        mid.addSpacing(1)
        mid.addWidget(self.bar)
        mid.addStretch(1)
        root.addLayout(mid, 1)

        btns = QHBoxLayout()
        btns.setSpacing(0)
        self.btn_overwrite = make_button("덮어쓰기", ghost=True, tooltip="기존 파일을 덮어쓰고 새로 받기")
        self.btn_retry = icon_button("retry", "다시 시도 (받던 부분부터 이어받기)")
        self.btn_cancel = icon_button("close", "다운로드 취소")
        self.btn_open = icon_button("folder", "파일 위치 열기")
        self.btn_more = icon_button("kebab", "더 보기")
        for b in (self.btn_overwrite, self.btn_retry, self.btn_cancel, self.btn_open, self.btn_more):
            btns.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(btns)

        self.btn_cancel.clicked.connect(job.cancel)
        self.btn_retry.clicked.connect(lambda: self.retryRequested.emit(self.job))
        self.btn_open.clicked.connect(self._open)
        self.btn_overwrite.clicked.connect(lambda: self.overwriteRequested.emit(self.job))
        self.btn_more.clicked.connect(self._more_menu)
        job.changed.connect(self.refresh)

        self._fresh_timer = QTimer(self)
        self._fresh_timer.setSingleShot(True)
        self._fresh_timer.timeout.connect(lambda: self.set_fresh(False))
        self._last_state = job.state

        if job.thumbnail:
            thumbs.load(job.thumbnail, self._set_thumb)
        self.refresh()

    # ------------------------------------------------------------------
    def _set_thumb(self, pm) -> None:
        self.thumb.setPixmap(rounded(pm, THUMB, 6))

    def _open(self) -> None:
        reveal_in_explorer(self.job.filepath or self.job.options.output_dir)

    def set_fresh(self, on: bool) -> None:
        if bool(self.property("fresh")) != on:
            self.setProperty("fresh", on)
            repolish(self)

    def _more_menu(self) -> None:
        j = self.job
        m = QMenu(self)
        if j.state == DONE:
            m.addAction("파일 위치 열기", self._open)
            if j.skipped:
                m.addAction("덮어쓰고 다시 받기", lambda: self.overwriteRequested.emit(j))
        if j.state in (FAILED, CANCELED):
            m.addAction("다시 시도", lambda: self.retryRequested.emit(j))
        if j.state in (QUEUED, RUNNING):
            m.addAction("취소", j.cancel)
        if j.log:
            m.addAction("로그 보기", lambda: show_log_dialog(self, f"로그 - {j.title}", list(j.log)))
        if j.state != RUNNING:
            m.addSeparator()
            m.addAction("목록에서 지우기", lambda: self.removeRequested.emit(j))
        pos = self.btn_more.mapToGlobal(QPoint(self.btn_more.width() - 4, self.btn_more.height() - 2))
        # 오른쪽 끝에 맞춰 왼쪽으로 펼치기
        m.exec(pos - QPoint(m.sizeHint().width(), 0))
        m.deleteLater()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        j = self.job
        state = j.state

        if state == DONE and self._last_state != DONE and not j.skipped:
            self.set_fresh(True)
            self._fresh_timer.start(FRESH_MS)
        self._last_state = state

        if state == DONE:
            text = done_meta(j)
            style = "Notice" if j.skipped else "Small"
        elif state == FAILED:
            text, style = (j.error or j.detail or "실패"), "Error"
        elif state == CANCELED:
            text, style = j.detail or "취소됨", "Small"
        elif state == QUEUED:
            text, style = f"대기 중 · {' · '.join(format_bits(j))}", "Small"
        else:
            text, style = j.detail, "Small"
        self.meta.setText(text)
        if self.meta.objectName() != style:
            self.meta.setObjectName(style)
            repolish(self.meta)

        show_bar = state in (QUEUED, RUNNING)
        self.bar.setVisible(show_bar)
        if state == RUNNING and j.fraction is None:
            self.bar.setRange(0, 0)          # 움직이는 막대
        else:
            self.bar.setRange(0, 1000)
            frac = j.fraction if j.fraction is not None else 0.0
            self.bar.setValue(int(frac * 1000))
        bar_state = {DONE: "done", FAILED: "failed", CANCELED: "canceled"}.get(state, "")
        if self.bar.property("state") != bar_state:
            self.bar.setProperty("state", bar_state)
            repolish(self.bar)

        self.btn_cancel.setVisible(state in (QUEUED, RUNNING))
        self.btn_retry.setVisible(state in (FAILED, CANCELED))
        self.btn_open.setVisible(state == DONE)
        self.btn_overwrite.setVisible(state == DONE and j.skipped)
        self.btn_more.setVisible(True)
