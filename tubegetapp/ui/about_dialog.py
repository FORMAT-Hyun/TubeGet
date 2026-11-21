"""앱 정보 창: 버전, 사용 중인 도구 버전, 데이터 폴더, 안내문. (문제 신고용 정보 복사 포함)"""
from __future__ import annotations

import platform
from typing import Optional

import PySide6
from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from .. import APP_NAME, APP_STAGE, APP_VERSION
from ..core.deps import Deps
from ..paths import data_dir
from ..utils import reveal_in_explorer
from .theme import make_icon_pixmap
from .widgets import make_button

NOTICE = ("TubeGet은 yt-dlp와 FFmpeg를 이용하는 화면(GUI) 프로그램이에요. "
          "본인이 올렸거나 받을 권리가 있는 영상만 내려받아 주세요. "
          "유튜브 이용약관과 저작권법을 지키는 책임은 사용하는 사람에게 있어요.")
LICENSES = "사용한 도구: yt-dlp(Unlicense), FFmpeg(LGPL/GPL), Qt for Python·PySide6(LGPL). 각 도구는 자기 라이선스를 따라요."


def version_text() -> str:
    return f"{APP_VERSION} ({APP_STAGE})" if APP_STAGE else APP_VERSION


def tool_line(tool) -> str:
    if tool is None or not tool.ok:
        return "없음"
    return (tool.version or "설치됨") + (" · TubeGet 폴더" if tool.managed else " · 시스템")


def report_text(deps: Optional[Deps]) -> str:
    """문제를 알릴 때 붙여넣기 좋은 한 덩어리 정보."""
    d = deps or Deps()
    js = d.js
    lines = [
        f"{APP_NAME} {version_text()}",
        f"yt-dlp: {tool_line(d.ytdlp)}",
        f"ffmpeg: {tool_line(d.ffmpeg)}",
        f"JS 런타임: {(js.name + ' ' + tool_line(js)) if js else '없음'}",
        f"Python {platform.python_version()} · PySide6 {PySide6.__version__} · Qt {qVersion()}",
        f"OS: {platform.platform()}",
    ]
    return "\n".join(lines)


class AboutDialog(QDialog):
    def __init__(self, deps: Optional[Deps], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 정보")
        self.setMinimumWidth(500)
        self.deps = deps

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(16)
        icon = QLabel()
        icon.setPixmap(make_icon_pixmap(256).scaled(
            72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("VideoTitle")
        title.setStyleSheet("font-size: 18pt; font-weight: 700;")
        self.version = QLabel(f"버전 {version_text()}")
        sub = QLabel("yt-dlp 기반 유튜브 다운로더")
        sub.setObjectName("Muted")
        col.addWidget(title)
        col.addWidget(self.version)
        col.addWidget(sub)
        head.addLayout(col, 1)
        lay.addLayout(head)

        line = QFrame()
        line.setObjectName("Divider")
        lay.addWidget(line)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(7)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        d = deps or Deps()

        def row(name: str, value: str) -> QLabel:
            v = QLabel(value)
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            v.setWordWrap(True)
            k = QLabel(name)
            k.setObjectName("Muted")
            form.addRow(k, v)
            return v

        row("yt-dlp", tool_line(d.ytdlp))
        row("ffmpeg", tool_line(d.ffmpeg))
        row("JS 런타임", f"{d.js.name} {tool_line(d.js)}" if d.js else "없음")
        row("실행 환경", f"Python {platform.python_version()} · PySide6 {PySide6.__version__} · Qt {qVersion()}")
        self.data_path = str(data_dir())
        row("데이터 폴더", self.data_path)
        lay.addLayout(form)

        for text, small in ((NOTICE, False), (LICENSES, True)):
            lbl = QLabel(text)
            lbl.setObjectName("Small" if small else "Muted")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        btns = QHBoxLayout()
        self.b_copy = make_button("정보 복사", ghost=True, tooltip="문제를 알릴 때 붙여넣을 수 있게 버전 정보를 복사해요")
        self.b_copy.clicked.connect(self._copy)
        b_open = make_button("데이터 폴더 열기", ghost=True)
        b_open.clicked.connect(lambda: reveal_in_explorer(self.data_path))
        ok = make_button("닫기", primary=True)
        ok.clicked.connect(self.accept)
        btns.addWidget(self.b_copy)
        btns.addWidget(b_open)
        btns.addStretch(1)
        btns.addWidget(ok)
        lay.addLayout(btns)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(report_text(self.deps))
        self.b_copy.setText("복사했어요 ✓")
