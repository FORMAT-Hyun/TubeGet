"""태그 설정 창 (영상마다). 음원과 영상(MP4 등) 모두."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QVBoxLayout, QWidget)

from ..core import tags
from ..core.metadata import MediaInfo
from .widgets import make_button


class TagState:
    """영상 하나의 태그 설정."""

    def __init__(self, on: bool = True, cover: bool = True, values: Optional[dict] = None, smart: bool = False):
        self.on = on
        self.cover = cover
        self.values = values      # 영상: 직접 정한 값 / 재생목록: None
        self.smart = smart        # 재생목록: 영상마다 자동 정리

    @classmethod
    def for_info(cls, info: Optional[MediaInfo], on: bool, cover: bool, clean: bool) -> "TagState":
        if info is not None and info.kind == "video":
            values = tags.guess_tags(info) if clean else tags.raw_tags(info)
            return cls(on, cover, values, False)
        return cls(on, cover, None, clean)

    def button_text(self) -> str:
        if not self.on:
            return "태그: 끔"
        if self.values:
            return "태그: " + (tags.summary(self.values) or "켬")
        return "태그: 켬 (자동 정리)" if self.smart else "태그: 켬"


class TagDialog(QDialog):
    def __init__(self, info: Optional[MediaInfo], state: TagState, parent: Optional[QWidget] = None,
                 audio: bool = True):
        super().__init__(parent)
        self.audio = audio
        self._initial: dict = {}
        self._had_values = bool(state.values)
        self.setWindowTitle("음원 태그" if audio else "영상 태그")
        self.resize(480, 0)
        self.info = info
        self.per_video = info is not None and info.kind == "video"

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        self.cb_on = QCheckBox("태그 넣기")
        self.cb_on.setStyleSheet("font-weight: 600; font-size: 11pt;")
        self.cb_on.setChecked(state.on)
        lay.addWidget(self.cb_on)
        desc = QLabel("음악 앱이나 MP3 플레이어에 보이는 제목·아티스트·앨범·커버예요. "
                      "끄면 태그 없이 깨끗한 파일로 저장돼요." if audio else
                      "MP4·MKV 파일 정보(속성)에 보이는 제목·아티스트·연도·표지예요. "
                      "끄면 태그 없이 저장돼요. 건드리지 않으면 유튜브 정보 그대로 들어가요.")
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self.body = QFrame()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(8)
        self.cb_cover = QCheckBox("앨범 커버 넣기 (영상 썸네일)" if audio else "표지 이미지 넣기 (영상 썸네일)")
        self.cb_cover.setChecked(state.cover)
        bl.addWidget(self.cb_cover)

        self.edits: dict[str, QLineEdit] = {}
        if self.per_video:
            form = QFormLayout()
            form.setSpacing(8)
            values = state.values or (tags.guess_tags(info) if audio else tags.raw_tags(info))
            self._initial = dict(values)
            for f in tags.FIELDS:
                e = QLineEdit(values.get(f, ""))
                e.setPlaceholderText("비워두면 넣지 않음")
                self.edits[f] = e
                form.addRow(tags.LABELS[f], e)
            self.edits["year"].setMaxLength(10)
            bl.addLayout(form)
            row = QHBoxLayout()
            b_guess = make_button("자동 정리 값으로", ghost=True,
                                  tooltip="'아티스트 - 곡명' 을 나누고 (Official Video) 같은 꼬리표를 지운 값")
            b_raw = make_button("유튜브 원래 값으로", ghost=True, tooltip="영상 제목·채널 이름 그대로")
            b_guess.clicked.connect(lambda: self._fill(tags.guess_tags(info)))
            b_raw.clicked.connect(lambda: self._fill(tags.raw_tags(info)))
            row.addWidget(b_guess)
            row.addWidget(b_raw)
            row.addStretch(1)
            bl.addLayout(row)
        else:
            self.cb_smart = QCheckBox("영상마다 '아티스트 - 곡명'을 나누고 (Official Video) 같은 꼬리표 지우기")
            self.cb_smart.setChecked(state.smart)
            bl.addWidget(self.cb_smart)
            note = QLabel("재생목록은 영상마다 값을 미리 볼 수 없어서 자동으로 정리해요.")
            note.setObjectName("Small")
            note.setWordWrap(True)
            bl.addWidget(note)
        lay.addWidget(self.body)

        box = QDialogButtonBox()
        ok = make_button("확인", primary=True)
        box.addButton(ok, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

        self.cb_on.toggled.connect(self.body.setEnabled)
        self.body.setEnabled(state.on)

    def _fill(self, values: dict) -> None:
        for f, e in self.edits.items():
            e.setText(values.get(f, ""))

    def result_state(self) -> TagState:
        values = {f: e.text().strip() for f, e in self.edits.items()} if self.per_video else None
        if values is not None and not self.audio and values == self._initial and not self._had_values:
            values = None   # 건드리지 않았으면 유튜브 기본값 그대로
        smart = self.cb_smart.isChecked() if not self.per_video else False
        return TagState(self.cb_on.isChecked(), self.cb_cover.isChecked(), values, smart)
