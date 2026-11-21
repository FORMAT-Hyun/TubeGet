"""도구 상태 / 설치 / 업데이트 창."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar,
                               QVBoxLayout, QWidget)

from ..core.deps import LABELS, MANUAL_HINTS, Deps, Tool, download_spec
from ..core.installer import DepInstaller, DepsChecker, YtdlpUpdater
from ..paths import bin_dir, data_dir
from ..utils import human_size, reveal_in_explorer
from .widgets import make_button
from ..i18n import tr


class DepsDialog(QDialog):
    depsChanged = Signal(object)  # Deps

    def __init__(self, deps: Optional[Deps], parent: Optional[QWidget] = None, intro: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("도구 상태"))
        self.resize(640, 470)
        self.deps = deps or Deps()
        self._installer: Optional[DepInstaller] = None
        self._updater: Optional[YtdlpUpdater] = None
        self._checker: Optional[DepsChecker] = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        if intro:
            t = QLabel(intro)
            t.setObjectName("Notice")
            t.setWordWrap(True)
            lay.addWidget(t)
        desc = QLabel(tr("TubeGet은 아래 도구들을 사용해요. 없는 도구는 버튼 한 번으로 TubeGet 전용 폴더에 설치할 수 있어요."))
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(8)
        self.rows: dict[str, tuple[QLabel, QLabel]] = {}
        for r, key in enumerate(("yt-dlp", "ffmpeg", "deno")):
            name = QLabel(LABELS[key])
            status = QLabel(tr("확인 중…"))
            where = QLabel("")
            where.setObjectName("Small")
            where.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.grid.addWidget(name, r * 2, 0)
            self.grid.addWidget(status, r * 2, 1)
            self.grid.addWidget(where, r * 2 + 1, 0, 1, 2)
            self.rows[key] = (status, where)
        self.grid.setColumnStretch(1, 1)
        lay.addLayout(self.grid)

        btns = QHBoxLayout()
        self.b_install = make_button(tr("없는 도구 설치"), primary=True)
        self.b_update = make_button(tr("yt-dlp 업데이트"))
        self.b_recheck = make_button(tr("다시 확인"), ghost=True)
        self.b_folder = make_button(tr("설치 폴더 열기"), ghost=True)
        self.b_diag = make_button(tr("진단 정보 폴더"), ghost=True,
                                  tooltip=tr("마지막으로 불러온 영상 정보(last_info.json)와 오류(last_error.txt)가 있어요"))
        btns.addWidget(self.b_install)
        btns.addWidget(self.b_update)
        btns.addStretch(1)
        btns.addWidget(self.b_recheck)
        btns.addWidget(self.b_folder)
        btns.addWidget(self.b_diag)
        lay.addLayout(btns)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setVisible(False)
        lay.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        lay.addWidget(self.log, 1)

        close = make_button(tr("닫기"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)

        self.b_install.clicked.connect(self.install_missing)
        self.b_update.clicked.connect(self.update_ytdlp)
        self.b_recheck.clicked.connect(self.recheck)
        self.b_folder.clicked.connect(lambda: reveal_in_explorer(str(bin_dir())))
        self.b_diag.clicked.connect(lambda: reveal_in_explorer(str(data_dir())))
        self._render()

    # ------------------------------------------------------------------
    def _render(self) -> None:
        d = self.deps
        js: Optional[Tool] = d.js
        items = {"yt-dlp": d.ytdlp, "ffmpeg": d.ffmpeg, "deno": js}
        for key, tool in items.items():
            status, where = self.rows[key]
            if tool and tool.ok:
                ver = tool.version or "?"
                label = f"✔  {ver}"
                if key == "deno" and tool.name != "deno":
                    label = tr("✔  {name} {ver} (대신 사용)").format(name=tool.name, ver=ver)
                status.setText(label)
                status.setObjectName("Success")
                where.setText((tr("TubeGet 전용: ") if tool.managed else tr("시스템: ")) + tool.path)
            else:
                status.setText(tr("✖  없음"))
                status.setObjectName("Error")
                hint = MANUAL_HINTS.get(key, "") if download_spec(key) is None else ""
                where.setText(hint)
            status.style().unpolish(status)
            status.style().polish(status)
        missing = d.missing_required()
        busy = self._busy()
        self.b_install.setEnabled(bool(missing) and not busy)
        self.b_install.setText(tr("없는 도구 설치") + (f" ({', '.join(missing)})" if missing else ""))
        self.b_update.setEnabled(d.ytdlp.ok and not busy)
        self.b_recheck.setEnabled(not busy)

    def _busy(self) -> bool:
        return any(x is not None for x in (self._installer, self._updater, self._checker))

    def _append(self, text: str) -> None:
        self.log.appendPlainText(text)

    # ------------------------------------------------------------------
    def install_missing(self, names: Optional[list[str]] = None) -> None:
        names = names or self.deps.missing_required()
        names = [n for n in names if download_spec(n) is not None]
        if not names:
            self._append(tr("자동으로 설치할 수 있는 도구가 없어요."))
            return
        self._installer = DepInstaller(names, self)
        self._installer.progress.connect(self._on_progress)
        self._installer.message.connect(self._append)
        self._installer.result.connect(self._on_install_done)
        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self._render()
        self._installer.start()

    def _on_progress(self, name: str, done: float, total: float) -> None:
        if total > 0:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(done / total * 1000))
            self.bar.setToolTip(f"{name}: {human_size(done)} / {human_size(total)}")
        else:
            self.bar.setRange(0, 0)

    def _on_install_done(self, ok: bool, summary: str) -> None:
        self._append(summary)
        self._installer.wait(2000)
        self._installer.deleteLater()
        self._installer = None
        self.bar.setVisible(False)
        self.recheck()

    def update_ytdlp(self) -> None:
        tool = self.deps.ytdlp
        if not tool.ok:
            return
        if not tool.managed:
            self._append(tr("시스템에 설치된 yt-dlp를 쓰고 있어요. 항상 최신으로 유지되도록 TubeGet 전용 yt-dlp를 설치할게요."))
            self.install_missing(["yt-dlp"])
            return
        self._append(tr("yt-dlp 업데이트 확인 중…"))
        self._updater = YtdlpUpdater(tool.path, self)
        self._updater.output.connect(self._append)
        self._updater.done.connect(self._on_update_done)
        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self._render()
        self._updater.start()

    def _on_update_done(self, ok: bool, last: str) -> None:
        self._append(tr("업데이트 완료") if ok else tr("업데이트 실패 - 로그를 확인해 주세요"))
        self._updater.deleteLater()
        self._updater = None
        self.bar.setVisible(False)
        self.recheck()

    def recheck(self) -> None:
        if self._checker is not None:
            return
        self._checker = DepsChecker(self)
        self._checker.done.connect(self._on_checked)
        self._render()
        self._checker.start()

    def _on_checked(self, deps: Deps) -> None:
        self._checker.wait(1000)
        self._checker.deleteLater()
        self._checker = None
        self.deps = deps
        self._render()
        self.depsChanged.emit(deps)

    def reject(self) -> None:
        self.accept()

    def accept(self) -> None:
        if self._installer is not None:
            self._installer.cancel()
            self._installer.wait(5000)
        if self._checker is not None:
            self._checker.wait(30000)
        super().accept()
