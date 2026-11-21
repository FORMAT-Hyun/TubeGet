"""영상/재생목록 정보 조회 (yt-dlp -J)."""
from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..paths import data_dir
from .deps import Deps
from .errors import explain
from .metadata import parse_info
from .options import info_args
from .proc import kill_tree, make_process

FETCH_TIMEOUT_MS = 120_000


class InfoFetcher(QObject):
    succeeded = Signal(object, str)   # MediaInfo, 요청한 url
    failed = Signal(str, str, str)    # 안내 메시지, url, 원본 로그

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._url = ""
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timed_out = False

    @property
    def busy(self) -> bool:
        return self._proc is not None

    def fetch(self, url: str, deps: Deps, playlist: bool, cookies_browser: str = "") -> None:
        self.abort()
        if not deps.ytdlp.ok:
            self.failed.emit("yt-dlp가 설치되어 있지 않아요. [도구 상태]에서 설치해 주세요.", url, "")
            return
        self._url = url
        self._stdout = bytearray()
        self._stderr = bytearray()
        self._timed_out = False
        proc = make_process(deps.ytdlp.path, info_args(url, playlist, cookies_browser, deps), self)
        proc.readyReadStandardOutput.connect(lambda: self._stdout.extend(bytes(proc.readAllStandardOutput())))
        proc.readyReadStandardError.connect(lambda: self._stderr.extend(bytes(proc.readAllStandardError())))
        proc.finished.connect(lambda code, status, p=proc: self._on_finished(p, code))
        proc.errorOccurred.connect(lambda err, p=proc: self._on_error(p, err))
        self._proc = proc
        self._timer.start(FETCH_TIMEOUT_MS)
        proc.start()

    def abort(self) -> None:
        proc, self._proc = self._proc, None
        self._timer.stop()
        if proc is not None:
            try:
                proc.finished.disconnect()
                proc.errorOccurred.disconnect()
            except (RuntimeError, TypeError):
                pass
            kill_tree(proc)
            proc.deleteLater()

    def _on_timeout(self) -> None:
        if self._proc is not None:
            self._timed_out = True
            kill_tree(self._proc)

    def _on_error(self, proc: QProcess, err) -> None:
        if proc is not self._proc:
            return
        if err == QProcess.ProcessError.FailedToStart:
            self._proc = None
            self._timer.stop()
            proc.deleteLater()
            self.failed.emit("yt-dlp를 실행하지 못했어요. [도구 상태]에서 다시 설치해 주세요.", self._url, "")

    def _on_finished(self, proc: QProcess, code: int) -> None:
        if proc is not self._proc:
            return
        self._proc = None
        self._timer.stop()
        self._stdout.extend(bytes(proc.readAllStandardOutput()))
        self._stderr.extend(bytes(proc.readAllStandardError()))
        proc.deleteLater()
        err_text = self._stderr.decode("utf-8", "replace")
        if self._timed_out:
            self._fail("정보를 불러오는 데 너무 오래 걸려요. 인터넷 연결을 확인하고 다시 시도해 주세요.", err_text)
            return
        out = self._stdout.decode("utf-8", "replace").strip()
        if code != 0 and not out:
            self._fail(explain(err_text), err_text)
            return
        # -J 는 한 줄짜리 JSON. 앞에 다른 출력이 섞였을 때를 대비해 마지막 JSON 줄을 사용
        data = None
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    break
                except ValueError:
                    continue
        if data is None:
            self._fail(explain(err_text) if err_text.strip() else "정보를 읽지 못했어요.", err_text)
            return
        _save_diag("last_info.json", line)
        try:
            info = parse_info(data)
        except Exception as exc:  # noqa: BLE001
            self._fail(f"정보를 해석하지 못했어요: {exc}", err_text)
            return
        self.succeeded.emit(info, self._url)

    def _fail(self, message: str, log: str) -> None:
        _save_diag("last_error.txt", f"URL: {self._url}\n\n{log}")
        self.failed.emit(message, self._url, log)


def _save_diag(name: str, text: str) -> None:
    """문제가 생겼을 때 확인할 수 있게 마지막 조회 결과를 남겨둔다."""
    try:
        (data_dir() / name).write_text(text, encoding="utf-8")
    except OSError:
        pass
