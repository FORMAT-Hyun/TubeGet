"""큐 목록의 다운로드 한 줄."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from ..core.runner import CANCELED, DONE, FAILED, QUEUED, RUNNING, DownloadJob
from ..utils import reveal_in_explorer
from .theme import repolish
from .widgets import ElidedLabel, ThumbLoader, make_button, rounded, show_log_dialog

THUMB = QSize(112, 63)


class QueueItemWidget(QFrame):
    removeRequested = Signal(object)
    retryRequested = Signal(object)
    overwriteRequested = Signal(object)

    def __init__(self, job: DownloadJob, thumbs: ThumbLoader, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.job = job
        self.setObjectName("QueueItem")

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        self.thumb = QLabel("▶")
        self.thumb.setObjectName("Thumb")
        self.thumb.setFixedSize(THUMB)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.thumb)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        self.title = ElidedLabel(job.title)
        self.title.setObjectName("JobTitle")
        self.summary = ElidedLabel(job.options.summary())
        self.summary.setObjectName("Small")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        self.detail = ElidedLabel("")
        self.detail.setObjectName("Muted")
        mid.addWidget(self.title)
        mid.addWidget(self.summary)
        mid.addSpacing(2)
        mid.addWidget(self.bar)
        mid.addWidget(self.detail)
        root.addLayout(mid, 1)

        btns = QHBoxLayout()
        btns.setSpacing(2)
        self.btn_cancel = make_button("취소", ghost=True, tooltip="다운로드 취소")
        self.btn_retry = make_button("다시", ghost=True, tooltip="다시 시도 (받던 부분부터 이어받기)")
        self.btn_open = make_button("열기", ghost=True, tooltip="파일 위치 열기")
        self.btn_overwrite = make_button("덮어쓰기", ghost=True, tooltip="기존 파일을 덮어쓰고 새로 받기")
        self.btn_log = make_button("로그", ghost=True, tooltip="yt-dlp 로그 보기")
        self.btn_remove = make_button("✕", ghost=True, tooltip="목록에서 지우기")
        for b in (self.btn_cancel, self.btn_retry, self.btn_overwrite, self.btn_open, self.btn_log, self.btn_remove):
            btns.addWidget(b)
        root.addLayout(btns)

        self.btn_cancel.clicked.connect(job.cancel)
        self.btn_retry.clicked.connect(lambda: self.retryRequested.emit(self.job))
        self.btn_open.clicked.connect(self._open)
        self.btn_overwrite.clicked.connect(lambda: self.overwriteRequested.emit(self.job))
        self.btn_log.clicked.connect(lambda: show_log_dialog(self, f"로그 - {job.title}", list(job.log)))
        self.btn_remove.clicked.connect(lambda: self.removeRequested.emit(self.job))
        job.changed.connect(self.refresh)

        if job.thumbnail:
            thumbs.load(job.thumbnail, self._set_thumb)
        self.refresh()

    def _set_thumb(self, pm) -> None:
        self.thumb.setText("")
        self.thumb.setPixmap(rounded(pm, THUMB, 8))

    def _open(self) -> None:
        path = self.job.filepath or self.job.options.output_dir
        reveal_in_explorer(path)

    def refresh(self) -> None:
        j = self.job
        state = j.state
        self.detail.setText(j.detail)
        style = {FAILED: "Error", DONE: "Success"}.get(state, "Muted")
        if state == DONE and j.skipped:
            style = "Notice"
        self.detail.setObjectName(style)
        repolish(self.detail)

        if state == RUNNING and j.fraction is None:
            self.bar.setRange(0, 0)          # 움직이는 막대
        else:
            self.bar.setRange(0, 1000)
            frac = j.fraction if j.fraction is not None else 0.0
            if state == DONE:
                frac = 1.0
            self.bar.setValue(int(frac * 1000))
        bar_state = {DONE: "done", FAILED: "failed", CANCELED: "canceled"}.get(state, "")
        if state == DONE and j.skipped:
            bar_state = "canceled"
        if self.bar.property("state") != bar_state:
            self.bar.setProperty("state", bar_state)
            repolish(self.bar)

        self.btn_cancel.setVisible(state in (QUEUED, RUNNING))
        self.btn_retry.setVisible(state in (FAILED, CANCELED))
        self.btn_open.setVisible(state == DONE)
        self.btn_overwrite.setVisible(state == DONE and j.skipped)
        self.btn_log.setVisible(state in (FAILED, DONE, CANCELED) and bool(j.log))
        self.btn_remove.setVisible(state not in (RUNNING,))
