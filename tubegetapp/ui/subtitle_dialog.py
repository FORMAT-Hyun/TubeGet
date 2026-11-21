"""영상별 자막 / 더빙(음성 언어) 선택 창.

- 영상: 그 영상에 실제로 있는 자막(올린 자막 / 자동 생성 자막) 중에서 고른다.
- 재생목록: 영상마다 자막이 달라서 언어 코드로 고른다 (있는 영상만 받아짐).
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QRadioButton, QVBoxLayout, QWidget)

from ..core.metadata import MediaInfo
from .widgets import make_button

LANG_NAMES = {
    "ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어", "zh-Hans": "중국어(간체)",
    "zh-Hant": "중국어(번체)", "zh-CN": "중국어(간체)", "zh-TW": "중국어(번체)", "es": "스페인어",
    "fr": "프랑스어", "de": "독일어", "ru": "러시아어", "pt": "포르투갈어", "it": "이탈리아어",
    "vi": "베트남어", "th": "태국어", "id": "인도네시아어", "ar": "아랍어", "hi": "힌디어",
    "tr": "튀르키예어", "nl": "네덜란드어", "pl": "폴란드어", "uk": "우크라이나어", "sv": "스웨덴어",
    "ms": "말레이어", "fil": "필리핀어", "tl": "타갈로그어",
}
COMMON_LANGS = ["ko", "en", "ja", "zh-Hans", "zh-Hant", "es", "fr", "de", "ru", "pt", "vi", "th", "id"]
_PRIORITY = ["ko", "en", "ja"]

MODES = [
    ("embed", "영상에 넣기", "영상 파일 안에 자막 트랙으로 들어가요. 플레이어에서 켜고 끌 수 있어요."),
    ("file", ".srt 파일로 따로 저장", "영상 옆에 '제목.ko.srt' 처럼 따로 저장돼요. 편집 프로그램에서 쓰기 좋아요."),
    ("both", "둘 다", "영상에도 넣고 .srt 파일도 남겨요."),
]


def lang_label(code: str, name: str = "") -> str:
    base = code.split("-")[0]
    is_orig = code.endswith("-orig")
    ko = LANG_NAMES.get(code) or LANG_NAMES.get(code.replace("-orig", "")) or LANG_NAMES.get(base)
    label = ko or name or code
    if is_orig:
        label += " (원본 음성)"
    return f"{label}  [{code}]"


def _auto_sort_key(code: str, name: str) -> tuple:
    orig = code.endswith("-orig") or "original" in name.lower()
    base = code.split("-")[0]
    pri = _PRIORITY.index(base) if base in _PRIORITY else len(_PRIORITY)
    return (0 if orig else 1, pri, (name or code).lower())


def dub_name(code: str) -> str:
    return LANG_NAMES.get(code) or LANG_NAMES.get(code.split("-")[0]) or code


def summarize(langs: list[str], auto: bool, mode: str, audio: bool, dub: str = "") -> str:
    if not langs:
        return f"자막 없음 · 더빙 {dub_name(dub)}" if dub else "자막: 없음"
    names = [LANG_NAMES.get(c.split("-")[0], c) for c in langs]
    shown = ", ".join(names[:3]) + (f" 외 {len(names) - 3}개" if len(names) > 3 else "")
    m = "파일" if audio else {"embed": "넣기", "file": "파일", "both": "넣기+파일"}.get(mode, "")
    text = f"자막: {shown} ({m})"
    return f"{text} · 더빙 {dub_name(dub)}" if dub else text


class SubtitleDialog(QDialog):
    def __init__(self, info: Optional[MediaInfo], selected: list[str], auto: bool, mode: str,
                 audio_mode: bool, playlist_default: str = "ko,en", dub: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("자막 / 더빙 선택")
        self.resize(520, 660)
        self.info = info
        self.generic = info is None or info.kind != "video"
        self.audio_mode = audio_mode

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        self.manual_list: Optional[QListWidget] = None
        self.auto_list: Optional[QListWidget] = None
        self.generic_list: Optional[QListWidget] = None
        sel = set(selected)

        if self.generic:
            head = QLabel("<b>재생목록 자막</b>")
            lay.addWidget(head)
            note = QLabel("영상마다 자막이 달라서 언어를 미리 골라두면, 그 언어 자막이 있는 영상만 함께 받아요.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
            lay.addWidget(note)
            self.generic_list = QListWidget()
            codes = list(dict.fromkeys(COMMON_LANGS + [c for c in selected if c not in COMMON_LANGS]))
            for c in codes:
                self._add_item(self.generic_list, c, "", c in sel)
            lay.addWidget(self.generic_list, 1)
            row = QHBoxLayout()
            self.extra = QLineEdit()
            self.extra.setPlaceholderText("다른 언어 코드 직접 입력 (예: ar, hi)")
            row.addWidget(self.extra, 1)
            lay.addLayout(row)
            self.cb_auto = QCheckBox("올린 자막이 없으면 자동 생성 자막 받기")
            self.cb_auto.setChecked(auto)
            lay.addWidget(self.cb_auto)
        else:
            subs, autos = info.subtitles, info.auto_captions
            if not subs and not autos:
                empty = QLabel("이 영상에는 자막이 없어요.")
                empty.setObjectName("Notice")
                lay.addWidget(empty)
            if subs:
                lay.addWidget(QLabel(f"<b>올린 자막</b> ({len(subs)})"))
                self.manual_list = QListWidget()
                for code in sorted(subs, key=lambda c: _auto_sort_key(c, subs[c])[1:]):
                    self._add_item(self.manual_list, code, subs[code], code in sel)
                self.manual_list.setMaximumHeight(min(40 + 30 * len(subs), 190))
                lay.addWidget(self.manual_list)
            autos_only = {c: n for c, n in autos.items() if c not in subs}
            if autos_only:
                lay.addWidget(QLabel(f"<b>자동 생성 자막</b> ({len(autos_only)})"))
                hint = QLabel("자동 인식/자동 번역 자막이에요. 정확도가 낮을 수 있고, 번역 자막은 가끔 받기에 실패해요.")
                hint.setObjectName("Small")
                hint.setWordWrap(True)
                lay.addWidget(hint)
                self.filter = QLineEdit()
                self.filter.setPlaceholderText("언어 검색")
                self.filter.textChanged.connect(self._apply_filter)
                lay.addWidget(self.filter)
                self.auto_list = QListWidget()
                for code in sorted(autos_only, key=lambda c: _auto_sort_key(c, autos_only[c])):
                    self._add_item(self.auto_list, code, autos_only[code], code in sel)
                lay.addWidget(self.auto_list, 1)
            else:
                lay.addStretch(1)

        # 더빙 (음성 언어) -------------------------------------------------
        lay.addSpacing(4)
        lay.addWidget(QLabel("<b>더빙 (음성 언어)</b>"))
        self.dub_combo = QComboBox()
        self.dub_combo.addItem("원본 음성 (기본)", "")
        if self.generic:
            codes = list(dict.fromkeys(COMMON_LANGS[:3] + [c for c in COMMON_LANGS if c not in ("zh-Hans", "zh-Hant")]
                                       + ([dub] if dub else [])))
            for c in codes:
                self.dub_combo.addItem(lang_label(c), c)
            dub_note = "영상마다 다르고, 고른 언어 음성이 없는 영상은 원본 음성으로 받아요."
        else:
            dubs = info.dubs
            for c in sorted(dubs, key=lambda c: _auto_sort_key(c, dubs[c])):
                tag = " (원본)" if dubs[c] == "original" else ""
                self.dub_combo.addItem(lang_label(c) + tag, c)
            if dub and self.dub_combo.findData(dub) < 0:
                self.dub_combo.addItem(lang_label(dub), dub)
            dub_note = ("유튜브의 자동 더빙 등 다른 언어 음성으로 받아요." if len(dubs) > 1
                        else "이 영상에는 다른 언어 음성이 없어요. (원본 음성으로 받아요)")
        self.dub_combo.setCurrentIndex(max(0, self.dub_combo.findData(dub)))
        self.dub_combo.setEnabled(self.dub_combo.count() > 1)
        lay.addWidget(self.dub_combo)
        dn = QLabel(dub_note)
        dn.setObjectName("Small")
        dn.setWordWrap(True)
        lay.addWidget(dn)

        # 저장 방식 ------------------------------------------------------
        lay.addSpacing(4)
        lay.addWidget(QLabel("<b>저장 방식</b>"))
        self.mode_group = QButtonGroup(self)
        self.mode_buttons: dict[str, QRadioButton] = {}
        for key, label, desc in MODES:
            rb = QRadioButton(label)
            rb.setToolTip(desc)
            self.mode_group.addButton(rb)
            self.mode_buttons[key] = rb
            lay.addWidget(rb)
        self.mode_buttons.get(mode, self.mode_buttons["embed"]).setChecked(True)
        if audio_mode:
            for k, rb in self.mode_buttons.items():
                rb.setEnabled(k == "file")
            self.mode_buttons["file"].setChecked(True)
            n = QLabel("음원 파일에는 자막을 넣을 수 없어서 .srt 파일로 저장돼요.")
            n.setObjectName("Small")
            lay.addWidget(n)

        box = QDialogButtonBox()
        clear = make_button("자막 모두 해제", ghost=True)
        clear.clicked.connect(self._clear)
        box.addButton(clear, QDialogButtonBox.ButtonRole.ResetRole)
        ok = make_button("확인", primary=True)
        box.addButton(ok, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    # ------------------------------------------------------------------
    @staticmethod
    def _add_item(lst: QListWidget, code: str, name: str, checked: bool) -> None:
        item = QListWidgetItem(lang_label(code, name))
        item.setData(Qt.ItemDataRole.UserRole, code)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        lst.addItem(item)

    def _apply_filter(self, text: str) -> None:
        t = text.strip().lower()
        for i in range(self.auto_list.count()):
            it = self.auto_list.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def _lists(self):
        return [x for x in (self.manual_list, self.auto_list, self.generic_list) if x is not None]

    def _clear(self) -> None:
        for lst in self._lists():
            for i in range(lst.count()):
                lst.item(i).setCheckState(Qt.CheckState.Unchecked)

    @staticmethod
    def _checked(lst: Optional[QListWidget]) -> list[str]:
        if lst is None:
            return []
        return [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                if lst.item(i).checkState() == Qt.CheckState.Checked]

    def result_dub(self) -> str:
        return str(self.dub_combo.currentData() or "")

    def result_selection(self) -> tuple[list[str], bool, str]:
        """(언어 코드 목록, 자동 생성 자막 허용, 저장 방식)"""
        mode = next((k for k, rb in self.mode_buttons.items() if rb.isChecked()), "embed")
        if self.generic:
            langs = self._checked(self.generic_list)
            extra = [x.strip() for x in self.extra.text().replace(" ", ",").split(",") if x.strip()]
            langs += [x for x in extra if x not in langs]
            return langs, self.cb_auto.isChecked(), mode
        manual = self._checked(self.manual_list)
        autos = self._checked(self.auto_list)
        return manual + autos, bool(autos), mode


def default_selection(info: MediaInfo, default_langs: str, allow_auto: bool) -> tuple[list[str], bool]:
    """설정의 기본 언어 중 이 영상에 있는 자막을 미리 골라둔다."""
    wanted = [c.strip() for c in (default_langs or "").split(",") if c.strip()]
    if not wanted or info.kind != "video":
        return [], False
    picked, used_auto = [], False
    for w in wanted:
        match = next((c for c in info.subtitles if c == w or c.split("-")[0] == w), None)
        if match:
            picked.append(match)
            continue
        if allow_auto:
            amatch = next((c for c in info.auto_captions if c == w or c == f"{w}-orig"), None) \
                or next((c for c in info.auto_captions if c.split("-")[0] == w), None)
            if amatch and amatch not in picked:
                picked.append(amatch)
                used_auto = True
    return picked, used_auto
