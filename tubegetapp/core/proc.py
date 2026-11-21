"""QProcess 공통 처리: 환경 변수, 프로세스 트리 종료, 줄 단위 읽기."""
from __future__ import annotations

import os
import signal
import subprocess
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment

from ..utils import no_window_flags


def make_process(program: str, args: list[str], parent=None) -> QProcess:
    proc = QProcess(parent)
    proc.setProgram(program)
    proc.setArguments(args)
    env = QProcessEnvironment.systemEnvironment()
    env.insert("PYTHONIOENCODING", "utf-8")
    env.insert("PYTHONUTF8", "1")
    proc.setProcessEnvironment(env)
    if sys.platform != "win32" and hasattr(QProcess, "setUnixProcessParameters"):
        # 새 세션으로 띄워서 취소할 때 ffmpeg 같은 자식 프로세스까지 한 번에 종료
        try:
            proc.setUnixProcessParameters(QProcess.UnixProcessFlag.CreateNewSession)
        except Exception:  # pragma: no cover - 구버전 Qt
            pass
    return proc


def kill_tree(proc: QProcess) -> None:
    """yt-dlp 와 그 자식(ffmpeg 등)을 모두 종료."""
    if proc is None or proc.state() == QProcess.ProcessState.NotRunning:
        return
    pid = int(proc.processId() or 0)
    if pid:
        if sys.platform == "win32":
            try:
                subprocess.Popen(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=no_window_flags(),
                )
                return
            except OSError:
                pass
        else:
            try:
                os.killpg(pid, signal.SIGTERM)
                return
            except (OSError, AttributeError):
                pass
    proc.kill()


class LineBuffer:
    """바이트 조각을 받아 완성된 줄만 돌려준다."""

    def __init__(self) -> None:
        self._buf = b""

    def feed(self, data: bytes) -> list[str]:
        self._buf += data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        *lines, self._buf = self._buf.split(b"\n")
        return [ln.decode("utf-8", "replace") for ln in lines if ln]

    def flush(self) -> list[str]:
        rest, self._buf = self._buf, b""
        return [rest.decode("utf-8", "replace")] if rest.strip() else []
