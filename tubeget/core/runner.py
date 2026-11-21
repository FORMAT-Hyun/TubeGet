"""다운로드 작업 하나 = yt-dlp 프로세스 하나."""
from __future__ import annotations

import glob
import os
import time
import uuid
from collections import deque
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..utils import human_eta, human_size, human_speed
from .deps import Deps
from .errors import explain
from .options import DownloadOptions, build_args
from .proc import LineBuffer, kill_tree, make_process
from .progress import overall_fraction, parse_line

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELED = "canceled"

STATE_LABELS = {
    QUEUED: "대기 중",
    RUNNING: "진행 중",
    DONE: "완료",
    FAILED: "실패",
    CANCELED: "취소됨",
}

POSTPROCESS_FRACTION = 0.97   # 다운로드가 끝나고 합치기/변환하는 동안 보여줄 진행률


class DownloadJob(QObject):
    changed = Signal()            # 진행률/상태 텍스트 변경
    finished = Signal(object)     # self

    def __init__(self, url: str, title: str, options: DownloadOptions,
                 thumbnail: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.id = uuid.uuid4().hex
        self.url = url
        self.title = title or url
        self.options = options
        self.thumbnail = thumbnail

        self.state = QUEUED
        self.fraction: Optional[float] = None   # 0~1 전체 진행률, None = 알 수 없음(막대 애니메이션)
        self.detail = "대기 중"
        self.filepath: Optional[str] = None
        self.error: Optional[str] = None
        self.skipped = False                    # 이미 있는 파일이라 건너뜀
        self.log: deque[str] = deque(maxlen=300)
        self.partial_files: set[str] = set()    # 받는 중에 생긴 임시 파일들 (정리용)

        self._proc: Optional[QProcess] = None
        self._out = LineBuffer()
        self._err = LineBuffer()
        self._cancel_requested = False
        self._reset_runtime()

    # ------------------------------------------------------------------
    # 저장/복원 (프로그램을 껐다 켜도 목록 유지)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        state = QUEUED if self.state in (QUEUED, RUNNING) else self.state
        return {
            "url": self.url,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "options": self.options.to_dict(),
            "state": state,
            "error": self.error,
            "partial_files": sorted(self.partial_files),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadJob":
        job = cls(data.get("url", ""), data.get("title", ""),
                  DownloadOptions.from_dict(data.get("options") or {}), data.get("thumbnail"))
        state = data.get("state")
        job.partial_files = set(data.get("partial_files") or [])
        if state in (FAILED, CANCELED):
            job.state = state
            job.error = data.get("error")
            job.detail = job.error or ("취소됨 (다시 시도하면 이어받아요)" if state == CANCELED else "실패")
        return job

    # ------------------------------------------------------------------
    def conflict_key(self) -> tuple:
        """같은 파일을 만들게 되는 작업끼리는 동시에 실행하지 않기 위한 키."""
        o = self.options
        fmt = o.audio_format if o.mode == "audio" else o.container
        return (self.url, os.path.normcase(os.path.abspath(o.output_dir)), o.output_template(), o.mode, fmt)

    @property
    def is_active(self) -> bool:
        return self.state in (QUEUED, RUNNING)

    def start(self, deps: Deps) -> None:
        if self.state == RUNNING:
            return
        self._reset_runtime()
        if not deps.ytdlp.ok:
            self._finish(FAILED, error="yt-dlp가 설치되어 있지 않아요. [도구 상태]에서 설치해 주세요.")
            return
        self.state = RUNNING
        self.detail = "시작하는 중…"
        self.fraction = None
        self.changed.emit()

        args = build_args(self.options, self.url, deps)
        self.log.append("$ yt-dlp " + " ".join(args))
        proc = make_process(deps.ytdlp.path, args, self)
        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.readyReadStandardError.connect(self._on_stderr)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        self._proc = proc
        proc.start()

    def cancel(self) -> None:
        if self.state == QUEUED:
            self._finish(CANCELED)
            return
        if self.state != RUNNING:
            return
        self._cancel_requested = True
        self.detail = "취소하는 중…"
        self.changed.emit()
        if self._proc is not None:
            kill_tree(self._proc)
            proc = self._proc

            def force_kill() -> None:
                try:
                    if proc.state() != QProcess.ProcessState.NotRunning:
                        proc.kill()
                except RuntimeError:  # 이미 정리된 프로세스
                    pass

            QTimer.singleShot(5000, force_kill)

    def requeue(self, overwrite: bool = False) -> None:
        if self.state in (FAILED, CANCELED, DONE):
            if overwrite:
                self.options = self.options.copy(overwrite=True)
            self._reset_runtime()
            self.state = QUEUED
            self.detail = "대기 중"
            self.fraction = None
            self.error = None
            self.changed.emit()

    def delete_partials(self) -> int:
        """완료되지 않은 작업의 임시 파일(.part, 조각, 중간 스트림, 자막) 삭제. 지운 개수 반환."""
        if self.state in (DONE, RUNNING):
            return 0
        targets: set[str] = set()
        for f in self.partial_files:
            base = f[:-5] if f.endswith(".part") else f
            for cand in (base, base + ".part", base + ".ytdl", f):
                targets.add(cand)
            targets.update(glob.glob(glob.escape(base) + ".part-Frag*"))
        removed = 0
        for t in targets:
            if self.filepath and os.path.abspath(t) == os.path.abspath(self.filepath):
                continue
            try:
                if os.path.isfile(t):
                    os.remove(t)
                    removed += 1
            except OSError:
                pass
        self.partial_files.clear()
        return removed

    # ------------------------------------------------------------------
    def _reset_runtime(self) -> None:
        self._out = LineBuffer()
        self._err = LineBuffer()
        self._cancel_requested = False
        self._streams: list = []
        self._stream_idx = 0
        self._dl_started = False
        self._saw_download = False
        self._started_at = time.time()
        self.filepath = None
        self.error = None
        self.skipped = False

    def _on_stdout(self) -> None:
        if self._proc is None:
            return
        for line in self._out.feed(bytes(self._proc.readAllStandardOutput())):
            self._handle_line(line)

    def _on_stderr(self) -> None:
        if self._proc is None:
            return
        for line in self._err.feed(bytes(self._proc.readAllStandardError())):
            self.log.append(line)

    def _handle_line(self, line: str) -> None:
        parsed = parse_line(line)
        if parsed is None:
            self.log.append(line)
            return
        kind, value = parsed
        if kind == "progress":
            self._on_progress(value)
        elif kind == "streams":
            self._dl_started = True
            self._streams = value.sizes
            self._stream_idx = 0
            self.detail = "다운로드 준비 중…"
            self.fraction = None
            self.changed.emit()
        elif kind == "stage":
            if value == "postprocess":
                self.detail = self._postprocess_label()
                self.fraction = POSTPROCESS_FRACTION if self._saw_download else None
                self.changed.emit()
        elif kind == "file":
            self.filepath = value

    def _postprocess_label(self) -> str:
        o = self.options
        if o.mode == "audio":
            return "음원으로 변환하는 중…"
        if o.has_subs or o.embed_thumbnail:
            return "영상·음성 합치고 정리하는 중…"
        return "영상·음성 합치는 중…"

    def _on_progress(self, p) -> None:
        if p.tmpfilename:
            self.partial_files.add(p.tmpfilename)
        if not self._dl_started:
            # 자막/썸네일 같은 부가 파일 다운로드 - 진행률에는 반영하지 않음
            return
        self._saw_download = True
        if p.status == "finished":
            self._stream_idx += 1
            if self._streams:
                self.fraction = overall_fraction(self._streams, self._stream_idx, 0.0) * POSTPROCESS_FRACTION \
                    if self._stream_idx < len(self._streams) else POSTPROCESS_FRACTION
            self.changed.emit()
            return
        if p.status != "downloading":
            return
        kind = p.stream_kind
        n = len(self._streams)
        if self.options.mode == "audio":
            label = "음원 받는 중"
        elif kind == "audio":
            label = "음성 받는 중"
        elif kind == "video":
            label = "영상 받는 중"
        else:
            label = "받는 중"
        if n > 1:
            label += f" ({min(self._stream_idx + 1, n)}/{n})"
        cur = p.fraction
        if cur is None and not self._streams:
            self.fraction = None
        else:
            total_frac = overall_fraction(self._streams or [None], self._stream_idx, cur)
            self.fraction = None if total_frac is None else total_frac * POSTPROCESS_FRACTION
        bits = [label]
        if self.fraction is not None:
            bits.append(f"{self.fraction * 100:.1f}%")
        if p.total:
            bits.append(f"{human_size(p.downloaded)} / {human_size(p.total)}")
        elif p.downloaded:
            bits.append(human_size(p.downloaded))
        speed = human_speed(p.speed)
        if speed:
            bits.append(speed)
        eta = human_eta(p.eta)
        if eta:
            bits.append(eta)
        self.detail = " · ".join(bits)
        self.changed.emit()

    def _on_error(self, err) -> None:
        if err == QProcess.ProcessError.FailedToStart:
            self._finish(FAILED, error="yt-dlp를 실행하지 못했어요. [도구 상태]에서 다시 설치해 주세요.")

    def _on_finished(self, exit_code: int, exit_status) -> None:
        for line in self._out.flush():
            self._handle_line(line)
        for line in self._err.flush():
            self.log.append(line)
        if self.state != RUNNING:
            return
        if self._cancel_requested:
            self._finish(CANCELED)
        elif exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            self.skipped = self._looks_skipped()
            self._finish(DONE)
        else:
            self._finish(FAILED, error=explain("\n".join(self.log)))

    def _looks_skipped(self) -> bool:
        """받은 데이터가 없고 결과 파일이 이번 작업 전에 이미 있었으면 '건너뜀'."""
        if self._saw_download or self.options.overwrite or not self.filepath:
            return False
        try:
            return os.path.getmtime(self.filepath) < self._started_at - 1
        except OSError:
            return False

    def _finish(self, state: str, error: Optional[str] = None) -> None:
        self.state = state
        self.error = error
        if state == DONE:
            self.fraction = 1.0
            self.detail = "이미 받은 파일이 있어서 건너뛰었어요" if self.skipped else "완료"
            self.partial_files.clear()
        elif state == CANCELED:
            self.detail = "취소됨 (다시 시도하면 이어받아요)"
        else:
            self.detail = error or "실패"
        if self._proc is not None:
            self._proc.deleteLater()
            self._proc = None
        self.changed.emit()
        self.finished.emit(self)
