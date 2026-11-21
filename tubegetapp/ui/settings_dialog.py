"""설정 창."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from ..config import COOKIE_BROWSERS, FILENAME_PRESETS, Settings
from ..core.options import AUDIO_QUALITIES
from .widgets import make_button

CUSTOM = "직접 입력"


def hint_label(text: str) -> QLabel:
    """체크박스 아래에 들여써서 붙이는 작은 설명."""
    lbl = QLabel(text)
    lbl.setObjectName("Small")
    lbl.setWordWrap(True)
    lbl.setContentsMargins(25, 0, 0, 6)
    return lbl


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle("설정")
        self.resize(660, 720)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setSpacing(6)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # 저장 ------------------------------------------------------------
        g = QGroupBox("저장")
        f = QFormLayout(g)
        f.setVerticalSpacing(6)
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(settings.download_dir)
        b = make_button("찾아보기")
        b.clicked.connect(self._browse)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(b)
        f.addRow("기본 저장 위치", row)

        self.name_combo = QComboBox()
        for label in FILENAME_PRESETS:
            self.name_combo.addItem(label, FILENAME_PRESETS[label])
        self.name_combo.addItem(CUSTOM, "")
        self.name_edit = QLineEdit(settings.filename_template)
        self.name_edit.setPlaceholderText("%(title)s [%(id)s].%(ext)s")
        idx = self.name_combo.findData(settings.filename_template)
        self.name_combo.setCurrentIndex(idx if idx >= 0 else self.name_combo.count() - 1)
        self.name_edit.setVisible(idx < 0)
        self.name_combo.currentIndexChanged.connect(self._on_name_preset)
        f.addRow("파일 이름 규칙", self.name_combo)
        f.addRow("", self.name_edit)
        hint = QLabel("yt-dlp 출력 템플릿 문법을 그대로 써요. 예: %(uploader)s/%(title)s.%(ext)s")
        hint.setObjectName("Small")
        hint.setWordWrap(True)
        f.addRow("", hint)
        lay.addWidget(g)

        # 다운로드 --------------------------------------------------------
        g = QGroupBox("다운로드")
        f = QFormLayout(g)
        f.setVerticalSpacing(6)
        self.concurrent = QSpinBox()
        self.concurrent.setRange(1, 5)
        self.concurrent.setValue(settings.max_concurrent)
        f.addRow("동시 다운로드 수", self.concurrent)
        self.rate = QLineEdit(settings.rate_limit)
        self.rate.setPlaceholderText("비워두면 제한 없음 (예: 5M, 800K)")
        f.addRow("속도 제한", self.rate)
        self.audio_q = QComboBox()
        for key, label in AUDIO_QUALITIES:
            self.audio_q.addItem(label, key)
        self.audio_q.setCurrentIndex(max(0, self.audio_q.findData(settings.audio_quality)))
        f.addRow("음원 음질 (MP3/M4A/Opus)", self.audio_q)
        self.meta = QCheckBox("영상 파일에 제목·채널 등 메타데이터 넣기")
        self.meta.setChecked(settings.embed_metadata)
        f.addRow("", self.meta)
        self.audio_tags = QCheckBox("음원에 태그 넣기")
        self.audio_tags.setChecked(settings.audio_tags_default)
        f.addRow("", self.audio_tags)
        f.addRow("", hint_label("기본값이에요. 영상마다 [태그] 버튼으로 바꿀 수 있어요."))
        self.audio_clean = QCheckBox("음원 태그 자동 정리")
        self.audio_clean.setChecked(settings.audio_tag_clean)
        f.addRow("", self.audio_clean)
        f.addRow("", hint_label("'아티스트 - 곡명'을 나누고, (Official Video) 같은 꼬리표를 지워요."))
        self.compat = QCheckBox("편집 호환 (H.264) 우선")
        self.compat.setChecked(settings.compat_h264)
        f.addRow("", self.compat)
        f.addRow("", hint_label("CapCut·프리미어 같은 편집 프로그램에서 잘 열려요. 화질이 최대 1080p로 제한될 수 있어요."))
        self.overwrite = QCheckBox("같은 이름의 파일이 있으면 덮어쓰기")
        self.overwrite.setChecked(settings.overwrite_existing)
        f.addRow("", self.overwrite)
        f.addRow("", hint_label("끄면 건너뛰고 목록에 '이미 받은 파일'로 표시해요."))
        self.del_partials = QCheckBox("목록에서 지울 때 받다 만 파일(.part 등)도 함께 삭제")
        self.del_partials.setChecked(settings.delete_partials_on_remove)
        f.addRow("", self.del_partials)
        lay.addWidget(g)

        # 자막 -----------------------------------------------------------
        g = QGroupBox("자막 기본값 (자막은 영상마다 [자막] 버튼으로 골라요)")
        f = QFormLayout(g)
        f.setVerticalSpacing(6)
        self.sub_default = QLineEdit(settings.sub_default_langs)
        self.sub_default.setPlaceholderText("비워두면 미리 고르지 않음 (예: ko,en)")
        f.addRow("미리 골라둘 언어", self.sub_default)
        self.sub_default_auto = QCheckBox("올린 자막이 없으면 자동 생성 자막으로 골라두기")
        self.sub_default_auto.setChecked(settings.sub_default_auto)
        f.addRow("", self.sub_default_auto)
        lay.addWidget(g)

        # 재생목록 ---------------------------------------------------------
        g = QGroupBox("재생목록")
        v = QVBoxLayout(g)
        self.pl_folder = QCheckBox("재생목록 이름으로 폴더 만들기")
        self.pl_folder.setChecked(settings.playlist_folder)
        self.pl_number = QCheckBox("파일 이름 앞에 재생목록 번호 붙이기")
        self.pl_number.setChecked(settings.playlist_numbering)
        self.pl_prefer = QCheckBox("재생목록이 붙은 영상 주소는 목록 전체 불러오기")
        self.pl_prefer.setChecked(settings.prefer_playlist)
        for w in (self.pl_folder, self.pl_number, self.pl_prefer):
            v.addWidget(w)
        v.addWidget(hint_label("영상 주소에 재생목록(list=)이 붙어 있을 때 영상 하나 대신 재생목록 전체를 보여줘요."))
        lay.addWidget(g)

        # 로그인 쿠키 ------------------------------------------------------
        g = QGroupBox("브라우저 쿠키 (연령 제한·멤버십·봇 확인 영상용)")
        f = QFormLayout(g)
        f.setVerticalSpacing(6)
        self.cookies = QComboBox()
        for key, label in COOKIE_BROWSERS:
            self.cookies.addItem(label, key)
        self.cookies.setCurrentIndex(max(0, self.cookies.findData(settings.cookies_browser)))
        f.addRow("쿠키 가져올 브라우저", self.cookies)
        note = QLabel("유튜브에 로그인된 브라우저를 고르세요. 크롬 계열은 브라우저를 완전히 닫아야 읽히는 경우가 많고, "
                      "최신 크롬은 보안 정책 때문에 실패할 수 있어서 Firefox가 가장 안정적이에요. "
                      "평소에는 '사용 안 함'을 권장해요.")
        note.setObjectName("Small")
        note.setWordWrap(True)
        f.addRow("", note)
        lay.addWidget(g)

        # 기타 ------------------------------------------------------------
        g = QGroupBox("기타")
        v = QVBoxLayout(g)
        self.auto_update = QCheckBox("시작할 때 yt-dlp 자동 업데이트")
        self.auto_update.setChecked(settings.auto_update_ytdlp)
        self.clipboard = QCheckBox("창을 열 때 복사된 유튜브 주소 자동으로 불러오기")
        self.clipboard.setChecked(settings.clipboard_autofetch)
        self.notify = QCheckBox("다운로드가 모두 끝나면 알림")
        self.notify.setChecked(settings.notify_on_finish)
        v.addWidget(self.auto_update)
        v.addWidget(hint_label("유튜브가 바뀌어도 계속 받을 수 있게, 하루에 한 번만 확인해요."))
        v.addWidget(self.clipboard)
        v.addWidget(hint_label("끄는 것을 권장해요. 직접 [링크 붙여넣기]를 눌러 불러오는 쪽이 안전해요."))
        v.addWidget(self.notify)
        lay.addWidget(g)
        lay.addStretch(1)

        box = QDialogButtonBox()
        save = make_button("저장", primary=True)
        box.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        box.accepted.connect(self._save)
        box.rejected.connect(self.reject)
        outer.addWidget(box)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "저장 위치 선택", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _on_name_preset(self) -> None:
        data = self.name_combo.currentData()
        custom = not data
        self.name_edit.setVisible(custom)
        if data:
            self.name_edit.setText(data)

    def _save(self) -> None:
        s = self.s
        s.download_dir = self.dir_edit.text().strip() or s.download_dir
        tpl = self.name_edit.text().strip()
        if "%(ext)s" not in tpl:
            tpl = (tpl or "%(title)s [%(id)s]") + ".%(ext)s"
        s.filename_template = tpl
        s.max_concurrent = self.concurrent.value()
        s.rate_limit = self.rate.text().strip()
        s.audio_quality = self.audio_q.currentData()
        s.embed_metadata = self.meta.isChecked()
        s.audio_tags_default = self.audio_tags.isChecked()
        s.audio_tag_clean = self.audio_clean.isChecked()
        s.sub_default_langs = self.sub_default.text().strip().replace(" ", "")
        s.sub_default_auto = self.sub_default_auto.isChecked()
        s.overwrite_existing = self.overwrite.isChecked()
        s.compat_h264 = self.compat.isChecked()
        s.delete_partials_on_remove = self.del_partials.isChecked()
        s.playlist_folder = self.pl_folder.isChecked()
        s.playlist_numbering = self.pl_number.isChecked()
        s.prefer_playlist = self.pl_prefer.isChecked()
        s.cookies_browser = self.cookies.currentData()
        s.auto_update_ytdlp = self.auto_update.isChecked()
        s.clipboard_autofetch = self.clipboard.isChecked()
        s.notify_on_finish = self.notify.isChecked()
        s.save()
        self.accept()
