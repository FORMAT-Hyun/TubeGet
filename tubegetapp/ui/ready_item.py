"""목록에 올라가는 '받을 영상' 카드: 링크를 불러오면 여기에 정보가 나타나고, 카드의 버튼으로 바로 받는다."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..core.metadata import MediaInfo
from ..core.options import height_label
from ..utils import has_playlist_param, human_duration, human_size
from . import icons
from .theme import repolish
from .tag_dialog import TagState
from .widgets import ThumbLoader, icon_button, make_button, rounded
from ..i18n import tr

THUMB_SIZE = QSize(160, 90)


class ReadyItem(QFrame):
    downloadRequested = Signal(object)
    removeRequested = Signal(object)
    selectRequested = Signal(object)
    loadPlaylistRequested = Signal(object)

    def __init__(self, info: MediaInfo, url: str, thumbs: ThumbLoader, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ReadyItem")
        self.info = info
        self.url = url
        self.alive = True
        # 이 영상에만 적용되는 설정 (위쪽 바의 자막/더빙·태그 칩이 편집하는 대상)
        self.sub_langs: list[str] = []
        self.sub_auto = False
        self.dub_lang = ""
        self.tag_state = TagState()
        self.vtag_state = TagState()

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 14, 14, 14)
        row.setSpacing(16)

        self.thumb = QLabel(tr("미리보기"))
        self.thumb.setObjectName("Thumb")
        self.thumb.setFixedSize(THUMB_SIZE)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(8)
        self.v_title = QLabel(info.title)
        self.v_title.setObjectName("VideoTitle")
        self.v_title.setWordWrap(True)
        self.v_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.v_title.setMaximumHeight(52)
        col.addWidget(self.v_title)
        self.meta_row = QHBoxLayout()
        self.meta_row.setSpacing(6)
        col.addLayout(self.meta_row)
        self.v_notice = QLabel()
        self.v_notice.setObjectName("Notice")
        self.v_notice.setWordWrap(True)
        self.v_notice.setVisible(False)
        col.addWidget(self.v_notice)
        self.b_load_playlist = make_button(tr("이 주소의 재생목록 전체 불러오기 →"), link=True)
        self.b_load_playlist.setVisible(False)
        self.b_load_playlist.clicked.connect(lambda: self.loadPlaylistRequested.emit(self))
        col.addWidget(self.b_load_playlist, 0, Qt.AlignmentFlag.AlignLeft)
        col.addStretch(1)
        row.addLayout(col, 1)

        right = QVBoxLayout()
        right.setSpacing(8)
        self.b_close = icon_button("close", tr("목록에서 지우기"), color="#9aa0aa", size=14, box=28)
        self.b_close.clicked.connect(lambda: self.removeRequested.emit(self))
        right.addWidget(self.b_close, 0, Qt.AlignmentFlag.AlignRight)
        right.addStretch(1)
        self.est_label = QLabel()
        self.est_label.setObjectName("Muted")
        self.est_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.est_label)
        self.b_download = make_button(tr("다운로드"), primary=True)
        self.b_download.setIcon(icons.icon("download", "#ffffff", 18))
        self.b_download.setIconSize(QSize(18, 18))
        self.b_download.setMinimumSize(150, 40)
        self.b_download.clicked.connect(lambda: self.downloadRequested.emit(self))
        right.addWidget(self.b_download)
        row.addLayout(right)

        self._fill(info)
        thumbs.load(info.thumbnail, self._set_thumb)

    # ------------------------------------------------------------------
    def _fill(self, info: MediaInfo) -> None:
        bits: list[tuple[str, bool]] = []
        if info.kind == "playlist":
            n_ok = sum(1 for e in info.entries if e.available)
            bits = [(tr("재생목록"), False)]
            if info.uploader:
                bits.append((info.uploader, False))
            bits.append((tr("영상 {len}개").format(len=len(info.entries)), False))
            self.b_download.setText(tr("재생목록에서 선택… ({n_ok})").format(n_ok=n_ok))
            if n_ok < len(info.entries):
                self.v_notice.setText(tr("비공개·삭제된 영상 {v}개는 건너뛰어요.").format(v=len(info.entries) - n_ok))
                self.v_notice.setVisible(True)
        else:
            if info.uploader:
                bits.append((info.uploader, False))
            if info.heights:
                bits.append((tr("최대 {height_label}").format(height_label=height_label(info.heights[0])), True))
            if info.subtitles:
                bits.append((tr("자막 {len}개").format(len=len(info.subtitles)), False))
            if len(info.dubs) > 1:
                bits.append((tr("더빙 {len}개").format(len=len(info.dubs)), False))
            if info.is_live:
                self.v_notice.setText(tr("라이브 방송이나 예정된 최초 공개는 받을 수 없어요. 방송이 끝난 뒤 다시 시도해 주세요."))
                self.v_notice.setVisible(True)
            if has_playlist_param(self.url):
                self.b_load_playlist.setVisible(True)
        for text, accent in bits:
            lbl = QLabel(text)
            lbl.setObjectName("PillAccent" if accent else "Pill")
            self.meta_row.addWidget(lbl)
        self.meta_row.addStretch(1)
        self.b_download.setEnabled(self.can_download())

    def can_download(self) -> bool:
        if self.info.kind == "playlist":
            return any(e.available for e in self.info.entries)
        return not self.info.is_live

    def _set_thumb(self, pm) -> None:
        if not self.alive:
            return
        badge = human_duration(self.info.duration) if self.info.kind == "video" and self.info.duration else None
        self.thumb.setText("")
        self.thumb.setPixmap(rounded(pm, THUMB_SIZE, 10, badge=badge))

    def update_estimate(self, mode: str, height: int) -> None:
        info = self.info
        if info.kind == "playlist":
            n = sum(1 for e in info.entries if e.available)
            self.est_label.setText(tr("받을 수 있는 영상 {n}개").format(n=n))
            return
        size = info.estimated_size(0, "audio") if mode == "audio" else info.estimated_size(height)
        self.est_label.setText(tr("예상 크기 ≈ {human_size}").format(human_size=human_size(size)) if size else "")

    def set_selected(self, on: bool) -> None:
        if bool(self.property("selected")) != on:
            self.setProperty("selected", on)
            repolish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.selectRequested.emit(self)
        super().mousePressEvent(event)
