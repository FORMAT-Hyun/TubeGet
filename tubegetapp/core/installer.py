"""도구 확인/설치/업데이트를 백그라운드에서 실행."""
from __future__ import annotations

import shutil
import ssl
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .. import APP_NAME, APP_VERSION
from ..paths import IS_WINDOWS, bin_dir
from .deps import Deps, check_all, download_spec
from .proc import LineBuffer, make_process
from ..i18n import tr


class DepsChecker(QThread):
    """도구 버전 확인 (몇 초 걸릴 수 있어 스레드에서)."""
    done = Signal(object)  # Deps

    def run(self) -> None:  # noqa: D401
        try:
            deps = check_all()
        except Exception:  # noqa: BLE001
            deps = Deps()
        self.done.emit(deps)


class InstallCanceled(Exception):
    pass


class DepInstaller(QThread):
    """GitHub 최신 릴리스에서 도구를 받아 TubeGet 전용 bin 폴더에 설치."""
    progress = Signal(str, float, float)   # 도구 이름, 받은 바이트, 전체 바이트(0=모름)
    message = Signal(str)
    result = Signal(bool, str)             # 성공 여부, 요약

    def __init__(self, names: list[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.names = names
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        installed, failed = [], []
        for name in self.names:
            if self._cancel:
                break
            spec = download_spec(name)
            if spec is None:
                failed.append(tr("{name}: 이 운영체제에서는 자동 설치를 지원하지 않아요").format(name=name))
                continue
            try:
                self.message.emit(tr("{name} 내려받는 중…").format(name=name))
                self._install(name, spec)
                installed.append(name)
                self.message.emit(tr("{name} 설치 완료").format(name=name))
            except InstallCanceled:
                failed.append(tr("{name}: 취소됨").format(name=name))
                break
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{name}: {exc}")
                self.message.emit(tr("{name} 설치 실패: {exc}").format(name=name, exc=exc))
        ok = not failed
        summary = []
        if installed:
            summary.append(tr("설치됨: ") + ", ".join(installed))
        if failed:
            summary.append(tr("실패: ") + " / ".join(failed))
        self.result.emit(ok, "\n".join(summary) or tr("변경 없음"))

    # ------------------------------------------------------------------
    def _download(self, name: str, url: str, dest: Path) -> None:
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp, open(dest, "wb") as fh:
            total = float(resp.headers.get("Content-Length") or 0)
            done = 0.0
            while True:
                if self._cancel:
                    raise InstallCanceled()
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                self.progress.emit(name, done, total)
        if total and done < total:
            raise IOError(tr("다운로드가 중간에 끊겼어요"))

    def _install(self, name: str, spec: dict) -> None:
        target_dir = bin_dir()
        with tempfile.TemporaryDirectory(dir=target_dir) as tmp:
            tmp_path = Path(tmp)
            archive = spec.get("archive")
            fname = PurePosixPath(spec["url"]).name
            downloaded = tmp_path / fname
            self._download(name, spec["url"], downloaded)
            self.message.emit(tr("{name} 설치하는 중…").format(name=name))

            if archive is None:
                _place(downloaded, target_dir / spec["save_as"])
                return

            members = spec.get("members") or []
            extracted: dict[str, Path] = {}
            out_dir = tmp_path / "x"
            out_dir.mkdir()
            if archive == "zip":
                with zipfile.ZipFile(downloaded) as zf:
                    for info in zf.infolist():
                        base = PurePosixPath(info.filename).name
                        if base in members and not info.is_dir() and base not in extracted:
                            p = out_dir / base
                            with zf.open(info) as src, open(p, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            extracted[base] = p
            elif archive == "tar.xz":
                with tarfile.open(downloaded, "r:xz") as tf:
                    for m in tf.getmembers():
                        base = PurePosixPath(m.name).name
                        if base in members and m.isfile() and base not in extracted:
                            src = tf.extractfile(m)
                            if src is None:
                                continue
                            p = out_dir / base
                            with src, open(p, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            extracted[base] = p
            missing = [m for m in members if m not in extracted]
            if missing:
                raise IOError(tr("압축 파일에서 {names} 을(를) 찾지 못했어요").format(names=", ".join(missing)))
            for base, p in extracted.items():
                _place(p, target_dir / base)


def _place(src: Path, dest: Path) -> None:
    """실행 권한을 주고 기존 파일을 안전하게 교체."""
    if not IS_WINDOWS:
        src.chmod(src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if dest.exists():
        old = dest.with_name(dest.name + ".old")
        try:
            if old.exists():
                old.unlink()
            dest.replace(old)
        except OSError:
            pass
    shutil.move(str(src), str(dest))
    old = dest.with_name(dest.name + ".old")
    try:
        if old.exists():
            old.unlink()
    except OSError:
        pass  # 윈도우에서 실행 중이면 다음 기회에 정리


class YtdlpUpdater(QObject):
    """TubeGet 전용 yt-dlp 를 `yt-dlp -U` 로 업데이트."""
    output = Signal(str)
    done = Signal(bool, str)   # 성공 여부, 마지막 메시지

    def __init__(self, ytdlp_path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._path = ytdlp_path
        self._buf = LineBuffer()
        self._last = ""
        self._proc = None

    def start(self) -> None:
        proc = make_process(self._path, ["--ignore-config", "-U"], self)
        proc.setProcessChannelMode(proc.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_out)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(lambda e: e == proc.ProcessError.FailedToStart and self.done.emit(False, tr("실행 실패")))
        self._proc = proc
        proc.start()

    def _on_out(self) -> None:
        for line in self._buf.feed(bytes(self._proc.readAllStandardOutput())):
            self._last = line
            self.output.emit(line)

    def _on_finished(self, code: int, _status) -> None:
        for line in self._buf.flush():
            self._last = line
            self.output.emit(line)
        self.done.emit(code == 0, self._last)
        self._proc.deleteLater()
        self._proc = None


def cleanup_old_files() -> None:
    """이전 업데이트에서 남은 *.old 파일 정리."""
    for p in bin_dir().glob("*.old"):
        try:
            p.unlink()
        except OSError:
            pass


__all__ = ["DepsChecker", "DepInstaller", "YtdlpUpdater", "cleanup_old_files"]
