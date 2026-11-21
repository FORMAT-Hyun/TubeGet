"""다운로드 큐: 동시 실행 수 제한과 상태 관리."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from .deps import Deps
from .runner import CANCELED, DONE, FAILED, QUEUED, RUNNING, DownloadJob


class QueueManager(QObject):
    jobAdded = Signal(object)
    jobRemoved = Signal(object)
    jobFinished = Signal(object)
    countsChanged = Signal()
    allDone = Signal(int, int)   # 성공 수, 실패 수 (이번 묶음)

    def __init__(self, deps_provider: Callable[[], Optional[Deps]], max_concurrent: int = 2,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self.jobs: list[DownloadJob] = []
        self._deps_provider = deps_provider
        self.max_concurrent = max_concurrent
        self._paused = False
        self._batch_ok = 0
        self._batch_fail = 0
        self._dying: list[DownloadJob] = []   # 목록에서 지웠지만 프로세스가 아직 끝나지 않은 작업

    # ------------------------------------------------------------------
    def add(self, job: DownloadJob) -> None:
        job.setParent(self)
        job.finished.connect(self._on_job_finished)
        job.changed.connect(self.countsChanged)
        self.jobs.append(job)
        self.jobAdded.emit(job)
        self.countsChanged.emit()
        self._pump()

    def remove(self, job: DownloadJob, delete_partials: bool = False) -> None:
        if job not in self.jobs:
            return
        try:
            job.finished.disconnect(self._on_job_finished)
        except (RuntimeError, TypeError):
            pass
        was_running = job.state == RUNNING
        if job.state in (QUEUED, RUNNING):
            job.cancel()
        self.jobs.remove(job)
        self.jobRemoved.emit(job)
        self.countsChanged.emit()
        if was_running:
            # 프로세스가 완전히 끝난 뒤에 파일을 지워야 함 (윈도우는 쓰는 중인 파일을 못 지움)
            self._dying.append(job)

            def gone(j: DownloadJob, dp: bool = delete_partials) -> None:
                if dp:
                    j.delete_partials()
                if j in self._dying:
                    self._dying.remove(j)
                j.deleteLater()
                self._pump()

            job.finished.connect(gone)
        else:
            if delete_partials:
                job.delete_partials()
            job.deleteLater()
        self._pump()

    def retry(self, job: DownloadJob, overwrite: bool = False) -> None:
        job.requeue(overwrite=overwrite)
        self.countsChanged.emit()
        self._pump()

    def cancel_all(self) -> None:
        was_paused = self._paused
        self._paused = True  # 취소 도중 다음 작업이 시작되지 않게
        try:
            for job in list(self.jobs):
                if job.state == QUEUED:
                    job.cancel()
            for job in list(self.jobs):
                if job.state == RUNNING:
                    job.cancel()
        finally:
            self._paused = was_paused

    def clear_finished(self, delete_partials: bool = False) -> None:
        for job in [j for j in self.jobs if j.state in (DONE, CANCELED, FAILED)]:
            self.remove(job, delete_partials=delete_partials and job.state != DONE)

    def set_max_concurrent(self, n: int) -> None:
        self.max_concurrent = max(1, n)
        self._pump()

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if not paused:
            self._pump()

    # ------------------------------------------------------------------
    def counts(self) -> dict[str, int]:
        c = {QUEUED: 0, RUNNING: 0, DONE: 0, FAILED: 0, CANCELED: 0}
        for j in self.jobs:
            c[j.state] = c.get(j.state, 0) + 1
        return c

    def running_count(self) -> int:
        return sum(1 for j in self.jobs if j.state == RUNNING)

    def has_active(self) -> bool:
        return any(j.is_active for j in self.jobs)

    def _pump(self) -> None:
        if self._paused:
            return
        if not any(j.state == QUEUED for j in self.jobs):
            self.countsChanged.emit()
            return
        deps = self._deps_provider()
        if deps is None or not deps.ytdlp.ok:
            # 도구 확인 전이거나 yt-dlp 가 없으면 대기 상태로 둔다 (설치되면 다시 시작)
            self.countsChanged.emit()
            return
        while self.running_count() < self.max_concurrent:
            busy = {j.conflict_key() for j in self.jobs if j.state == RUNNING}
            busy |= {j.conflict_key() for j in self._dying if j.state == RUNNING}
            nxt = next((j for j in self.jobs if j.state == QUEUED and j.conflict_key() not in busy), None)
            if nxt is None:
                break
            nxt.start(deps)
        self.countsChanged.emit()

    def _on_job_finished(self, job: DownloadJob) -> None:
        if job.state == DONE:
            self._batch_ok += 1
        elif job.state == FAILED:
            self._batch_fail += 1
        self.jobFinished.emit(job)
        self._pump()
        if not self.has_active():
            ok, fail = self._batch_ok, self._batch_fail
            self._batch_ok = self._batch_fail = 0
            if ok or fail:
                self.allDone.emit(ok, fail)
        self.countsChanged.emit()
