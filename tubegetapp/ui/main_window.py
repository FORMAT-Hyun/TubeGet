"""메인 창."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QFontMetrics, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QSystemTrayIcon,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION
from ..config import Settings
from ..core.deps import Deps
from ..core.fetcher import InfoFetcher
from ..core.history import History
from ..core.installer import DepsChecker, YtdlpUpdater, cleanup_old_files
from ..core.metadata import MediaInfo
from ..core.options import (AUDIO_FORMATS, AUDIO_QUALITIES, LOSSY_AUDIO, HEIGHT_CHOICES, VIDEO_CONTAINERS, DownloadOptions,
                            height_label)
from ..core.queue import QueueManager
from ..core.queue_store import load_jobs, save_jobs
from ..core.runner import DONE, FAILED, DownloadJob
from ..utils import (has_playlist_param, has_video_param, human_duration, human_size, is_url,
                     is_youtube_url, reveal_in_explorer)
from .about_dialog import AboutDialog, version_text
from .deps_dialog import DepsDialog
from .history_view import HistoryView
from .playlist_dialog import PlaylistDialog
from .queue_item import QueueItemWidget
from .ready_item import ReadyItem
from .settings_dialog import SettingsDialog
from .subtitle_dialog import LANG_NAMES, SubtitleDialog, default_selection, dub_name, summarize
from .tag_dialog import TagDialog, TagState
from . import icons
from .theme import BORDER, DANGER, ICON, MUTED, WARNING, app_icon, repolish
from .toast import ToastManager
from .widgets import (ChipButton, ChipCombo, ElidedLabel, ModeCombo, ThumbLoader, ToggleSwitch, field_label,
                      icon_button, make_button, rounded, show_log_dialog)
from ..i18n import current_language, resolve, tr

THUMB_SIZE = QSize(176, 99)
MIN_WINDOW_WIDTH = 1160
_CHANNEL_RE = re.compile(r"youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+)/?(?:[?#].*)?$",
                         re.IGNORECASE)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.history = History()
        self.deps = Deps()
        self.deps_ready = False
        self.info: Optional[MediaInfo] = None
        self.info_url = ""
        self._ready: list[ReadyItem] = []     # 목록에 올라온 '받을 영상' 카드
        self._sel: Optional[ReadyItem] = None
        self._last_clip = ""
        self._channel_retry = False
        self._updater: Optional[YtdlpUpdater] = None
        self._deps_dialog_shown = False
        self._closing = False
        self._last_fetch_log = ""
        self.sub_langs: list[str] = []     # 지금 영상에서 고른 자막
        self.sub_auto = False
        self.dub_lang = ""                 # 지금 영상에서 고른 더빙(음성 언어)
        self.tag_state = TagState()           # 음원 태그 (영상마다)
        self.vtag_state = TagState()          # 영상(MP4 등) 태그 (영상마다)
        self._auto_pending = False            # '바로 받기'로 불러온 링크인지
        self._panel_open = False              # 정보 패널이 열려 있는지
        self._loading_ui = False

        self.thumbs = ThumbLoader(self)
        self.fetcher = InfoFetcher(self)
        self.fetcher.succeeded.connect(self._on_info)
        self.fetcher.failed.connect(self._on_info_failed)
        self.queue = QueueManager(lambda: self.deps if self.deps_ready else None, self.settings.max_concurrent, self)
        self.queue.set_paused(True)  # 도구 확인이 끝나면 시작
        self.queue.jobAdded.connect(self._on_job_added)
        self.queue.jobRemoved.connect(self._on_job_removed)
        self.queue.jobFinished.connect(self._on_job_finished)
        self.queue.countsChanged.connect(self._update_counts)
        self.queue.allDone.connect(self._on_all_done)
        self._item_widgets: dict[str, QueueItemWidget] = {}
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._save_queue)
        self.queue.jobAdded.connect(lambda _j: self._schedule_save())
        self.queue.jobRemoved.connect(lambda _j: self._schedule_save())
        self.queue.jobFinished.connect(lambda _j: self._schedule_save())

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1200, 820)
        self.setMinimumSize(MIN_WINDOW_WIDTH, 600)
        self.setAcceptDrops(True)

        self._build_ui()
        self._build_tray()
        self._apply_settings_to_ui()
        self._set_info(None)
        self._update_counts()
        self._restore_queue()

        cleanup_old_files()
        self._check_deps(initial=True)

    # ==================================================================
    # UI 구성
    # ==================================================================
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 상단 툴바 ---------------------------------------------------
        bar = QFrame()
        bar.setObjectName("Toolbar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 12, 14, 12)
        bl.setSpacing(4)

        self.b_paste = QPushButton(tr("  링크 붙여넣기"))
        self.b_paste.setProperty("primary", True)
        self.b_paste.setIcon(icons.icon("link_play", "#ffffff", 22))
        self.b_paste.setIconSize(QSize(22, 22))
        self.b_paste.setMinimumHeight(40)
        self.b_paste.setMinimumWidth(158)
        self.b_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_paste.setToolTip(tr("복사해 둔 주소를 붙여넣고 영상 정보를 불러와요 (Ctrl+L: 직접 입력)"))
        self.b_paste.clicked.connect(self._paste)
        bl.addWidget(self.b_paste)
        bl.addSpacing(10)

        self.auto_toggle = ToggleSwitch()
        self.auto_toggle.setToolTip(tr("바로 받기\n켜면 링크를 붙여넣자마자 지금 고른 설정으로 바로 다운로드해요.\n"
                                    "(재생목록은 고르는 창이 떠요)"))
        self.auto_toggle.toggled.connect(self._on_auto_toggled)
        bl.addWidget(self.auto_toggle)
        self.l_auto = QLabel(tr("바로 받기"))
        self.l_auto.setObjectName("ChipLabel")
        bl.addWidget(self.l_auto)
        bl.addSpacing(12)

        def chip_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setObjectName("ChipLabel")
            return lbl

        self.mode = ModeCombo([("video", tr("영상")), ("audio", tr("오디오"))])
        self.mode.changed.connect(self._on_mode_changed)
        self.quality = ChipCombo()
        self.quality.currentIndexChanged.connect(self._on_option_changed)
        self.fmt = ChipCombo()
        self.fmt.currentIndexChanged.connect(self._on_option_changed)
        self.l_quality = chip_label(tr("화질"))
        self.l_fmt = chip_label(tr("포맷"))
        bl.addWidget(chip_label(tr("다운로드")))
        bl.addWidget(self.mode)
        bl.addSpacing(8)
        bl.addWidget(self.l_quality)
        bl.addWidget(self.quality)
        bl.addSpacing(8)
        bl.addWidget(self.l_fmt)
        bl.addWidget(self.fmt)
        bl.addSpacing(8)
        bl.addWidget(chip_label(tr("저장 위치")))
        self.dest_btn = ChipButton()
        self.dest_btn.clicked.connect(self._dest_menu)
        bl.addWidget(self.dest_btn)
        bl.addSpacing(8)
        self.l_subs = chip_label(tr("자막/더빙"))
        self.b_subs = ChipButton()
        self.b_subs.setToolTip(tr("받을 자막 언어, 더빙(음성 언어), 저장 방식을 골라요 (영상마다 따로 정할 수 있어요)"))
        self.b_subs.clicked.connect(self._choose_subs)
        bl.addWidget(self.l_subs)
        bl.addWidget(self.b_subs)
        bl.addSpacing(8)
        self.l_tags = chip_label(tr("태그"))
        self.b_tags = ChipButton()
        self.b_tags.setToolTip(tr("음원 파일의 제목·아티스트·앨범·커버 태그를 넣을지, 어떤 값으로 넣을지 골라요"))
        self.b_tags.clicked.connect(self._choose_tags)
        bl.addWidget(self.l_tags)
        bl.addWidget(self.b_tags)
        bl.addStretch(1)

        self.b_settings = icon_button("gear", tr("설정"), size=22, box=36)
        self.b_settings.clicked.connect(self._open_settings)
        self.b_tools = icon_button("info", tr("도구 상태"), size=22, box=36)
        self.b_tools.clicked.connect(lambda: self._open_deps_dialog())
        bl.addWidget(self.b_settings)
        bl.addWidget(self.b_tools)
        root.addWidget(bar)
        # 칩 글자가 길어지면(언어·자막 선택에 따라) 창이 툴바보다 좁아져 버튼이 겹치지 않게
        self.toolbar = bar
        bar.installEventFilter(self)

        self.fetch_bar = QProgressBar()
        self.fetch_bar.setRange(0, 0)
        self.fetch_bar.setTextVisible(False)
        self.fetch_bar.setStyleSheet("QProgressBar { border-radius: 0px; max-height: 3px; min-height: 3px; }"
                                     "QProgressBar::chunk { border-radius: 0px; }")
        self.fetch_bar.setVisible(False)
        root.addWidget(self.fetch_bar)

        body = QWidget()
        bd = QVBoxLayout(body)
        bd.setContentsMargins(20, 14, 20, 8)
        bd.setSpacing(10)
        root.addWidget(body, 1)

        # ---- 정보 패널 (링크를 불러오면 나타남) ---------------------------------
        self.panel = QFrame()
        self.panel.setObjectName("InfoPanel")
        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.setSpacing(10)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_edit = QLineEdit()
        self.url_edit.setObjectName("UrlInput")
        self.url_edit.setPlaceholderText(tr("유튜브 영상이나 재생목록 주소를 붙여넣고 Enter"))
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self._fetch_clicked)
        self.b_fetch = make_button(tr("불러오기"), primary=True)
        self.b_fetch.clicked.connect(self._fetch_clicked)
        self.b_close_panel = icon_button("close", tr("닫기 (Esc)"), color="#9aa0aa", size=16, box=30)
        self.b_close_panel.clicked.connect(self._close_panel)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.b_fetch)
        url_row.addWidget(self.b_close_panel)
        pl.addLayout(url_row)

        notice_row = QHBoxLayout()
        notice_row.setSpacing(8)
        notice_row.setContentsMargins(0, 0, 0, 0)
        self.v_notice = QLabel()
        self.v_notice.setObjectName("Notice")
        self.v_notice.setWordWrap(True)
        self.b_fetch_log = make_button(tr("자세한 로그 보기"), link=True)
        self.b_fetch_log.clicked.connect(
            lambda: show_log_dialog(self, tr("불러오기 로그"), self._last_fetch_log.splitlines()))
        notice_row.addWidget(self.v_notice, 1)
        notice_row.addWidget(self.b_fetch_log, 0, Qt.AlignmentFlag.AlignTop)
        self.notice_box = QWidget()
        self.notice_box.setLayout(notice_row)
        pl.addWidget(self.notice_box)

        bd.addWidget(self.panel)
        self.panel.setVisible(False)

        # ---- 필터 탭 줄 ----------------------------------------------------
        tab_row = QFrame()
        tab_row.setObjectName("TabRow")
        tab_row.setStyleSheet(f"QFrame#TabRow {{ border: none; border-bottom: 1px solid {BORDER}; }}")
        tl = QHBoxLayout(tab_row)
        tl.setContentsMargins(2, 0, 0, 0)
        tl.setSpacing(0)
        self._filter = "all"
        self._filter_btns: dict[str, QPushButton] = {}
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        for key, label in (("all", tr("전체")), ("video", tr("동영상")), ("audio", tr("오디오")), ("history", tr("기록"))):
            b = QPushButton(label)
            b.setProperty("tab", True)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            self._filter_group.addButton(b)
            self._filter_btns[key] = b
            tl.addWidget(b)
        self._filter_btns["all"].setChecked(True)
        tl.addStretch(1)
        self.q_status = QLabel()
        self.q_status.setObjectName("Muted")
        tl.addWidget(self.q_status)
        tl.addSpacing(6)
        self.b_list_menu = icon_button("kebab", tr("목록 관리"), size=18, box=30)
        self.b_list_menu.clicked.connect(self._list_menu)
        tl.addWidget(self.b_list_menu)
        bd.addWidget(tab_row)

        # ---- 목록 / 기록 -------------------------------------------------------
        self.stack = QStackedWidget()
        self.q_scroll = QScrollArea()
        self.q_scroll.setWidgetResizable(True)
        self.q_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        self.q_layout = QVBoxLayout(holder)
        self.q_layout.setContentsMargins(0, 2, 4, 0)
        self.q_layout.setSpacing(8)

        self.q_empty = QWidget()
        el = QVBoxLayout(self.q_empty)
        el.setContentsMargins(0, 56, 0, 0)
        el.setSpacing(6)
        empty_icon = QLabel()
        empty_icon.setPixmap(icons.pixmap("download", "#454a55", 56))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.q_empty_title = QLabel(tr("링크를 붙여넣어 시작하세요"))
        self.q_empty_title.setObjectName("EmptyTitle")
        self.q_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.q_empty_sub = QLabel(tr("위의 [링크 붙여넣기]를 누르거나, 창에 주소를 끌어다 놓아도 돼요.\n"
                                  "유튜브 영상·재생목록·쇼츠 주소를 지원해요."))
        self.q_empty_sub.setObjectName("Empty")
        self.q_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(empty_icon)
        el.addWidget(self.q_empty_title)
        el.addWidget(self.q_empty_sub)
        self.q_layout.addWidget(self.q_empty)
        self.q_layout.addStretch(1)
        self.q_scroll.setWidget(holder)
        self.stack.addWidget(self.q_scroll)

        self.history_view = HistoryView(self.history)
        self.history_view.redownloadRequested.connect(self._redownload)
        self.stack.addWidget(self.history_view)
        bd.addWidget(self.stack, 1)

        # ---- 상태 표시줄 -------------------------------------------------------
        self.status_msg = QLabel(tr("도구 확인 중…"))
        self.status_msg.setContentsMargins(10, 0, 0, 0)
        self.statusBar().addWidget(self.status_msg, 1)
        self.statusBar().setSizeGripEnabled(False)
        self.deps_btn = QPushButton("")
        self.deps_btn.setProperty("ghost", True)
        self.deps_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deps_btn.clicked.connect(lambda: self._open_deps_dialog())
        self.statusBar().addPermanentWidget(self.deps_btn)
        self.about_btn = QPushButton(f"{APP_NAME} {APP_VERSION}")
        self.about_btn.setProperty("ghost", True)
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.setToolTip(tr("앱 정보 · {version_text} (F1)").format(version_text=version_text()))
        self.about_btn.clicked.connect(self._open_about)
        self.statusBar().addPermanentWidget(self.about_btn)
        QShortcut(QKeySequence("F1"), self, activated=self._open_about)

        self.toasts = ToastManager(central)

        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self._open_panel(focus=True))
        QShortcut(QKeySequence("Escape"), self, activated=self._escape)

    def _build_tray(self) -> None:
        self.tray: Optional[QSystemTrayIcon] = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu(self)
        a_show = QAction(tr("창 열기"), self)
        a_show.triggered.connect(self._raise)
        a_quit = QAction(tr("종료"), self)
        a_quit.triggered.connect(self.close)
        menu.addAction(a_show)
        menu.addAction(a_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: reason == QSystemTrayIcon.ActivationReason.Trigger and self._raise())
        self.tray.show()

    def _raise(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    # ==================================================================
    # 설정 ↔ UI
    # ==================================================================
    def _apply_settings_to_ui(self) -> None:
        s = self.settings
        self._loading_ui = True
        self.mode.setValue(s.mode)
        self.auto_toggle.setCheckedSilently(s.auto_download)
        self._update_dest_chip()
        self._fill_format_combo()
        self._fill_quality_combo()
        self._update_mode_enabled()
        self._loading_ui = False
        self.queue.set_max_concurrent(s.max_concurrent)

    def _fill_format_combo(self) -> None:
        self.fmt.blockSignals(True)
        self.fmt.clear()
        if self.mode.value() == "audio":
            for key, label in AUDIO_FORMATS:
                self.fmt.addChip(label, key, short=label.split(" ")[0])
            self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.settings.audio_format)))
        else:
            for c in VIDEO_CONTAINERS:
                self.fmt.addChip(c.upper(), c)
            self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.settings.container)))
        self.fmt.blockSignals(False)

    def _fill_quality_combo(self) -> None:
        self.quality.blockSignals(True)
        self.quality.clear()
        if self.mode.value() == "audio":
            self._fill_audio_quality()
            self.quality.blockSignals(False)
            return
        self.l_quality.setText(tr("화질"))
        self.quality.setEnabled(True)
        self.quality.setToolTip("")
        info = self.info
        heights = info.heights if (info and info.kind == "video" and info.heights) else HEIGHT_CHOICES
        best_size = info.estimated_size(0) if (info and info.kind == "video") else None
        self.quality.addChip(tr("최고 화질") + (f"  ≈ {human_size(best_size)}" if best_size else ""), 0, short=tr("최고"))
        for h in heights:
            size = info.estimated_size(h) if (info and info.kind == "video") else None
            label = height_label(h)
            if info and info.kind == "video" and size:
                label += f"  ≈ {human_size(size)}"
            elif not (info and info.kind == "video"):
                label = tr("최대 {label}").format(label=label)
            self.quality.addChip(label, h, short=height_label(h).split(" ")[0])
        want = self.settings.max_height
        idx = self.quality.findData(want)
        if idx < 0 and want:
            # 원하는 화질이 없으면 그보다 낮은 것 중 가장 높은 화질
            lower = [h for h in heights if h <= want]
            idx = self.quality.findData(max(lower)) if lower else 0
        self.quality.setCurrentIndex(max(0, idx))
        self.quality.blockSignals(False)

    def _fill_audio_quality(self) -> None:
        """음원일 때는 같은 칸이 '음질'이 된다 (설정 창에 있던 것을 툴바로 옮김)."""
        self.l_quality.setText(tr("음질"))
        for key, label in AUDIO_QUALITIES:
            self.quality.addChip(label, key, short=tr("최고") if key == "0" else label.replace(" kbps", "k"))
        self.quality.setCurrentIndex(max(0, self.quality.findData(self.settings.audio_quality or "0")))
        lossy = self.settings.audio_format in LOSSY_AUDIO
        # FLAC·WAV·원본은 음질을 고를 게 없다
        self.quality.setEnabled(lossy)
        self.quality.setToolTip("" if lossy else tr("무손실·원본 형식은 음질을 고르지 않아요"))

    def _update_mode_enabled(self) -> None:
        for w in (self.quality, self.l_quality):
            w.setVisible(True)
        for w in (self.b_tags, self.l_tags):
            w.setVisible(True)
        self._update_tags_button()
        self._update_subs_button()
        self._update_estimate()

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.mode = mode
        self.settings.save()
        self._fill_format_combo()
        self._fill_quality_combo()
        self._update_mode_enabled()

    def _on_option_changed(self, *_args) -> None:
        if getattr(self, "_loading_ui", False):
            return
        s = self.settings
        if self.mode.value() == "audio":
            fmt = self.fmt.currentData() or "mp3"
            if self.sender() is self.quality:
                s.audio_quality = str(self.quality.currentData() or "0")
            s.audio_format = fmt
            s.save()
            if self.sender() is self.fmt:
                self._fill_quality_combo()   # 무손실 형식이면 음질 칸을 끈다
        else:
            s.container = self.fmt.currentData() or "mp4"
            s.max_height = int(self.quality.currentData() or 0)
            s.save()
        self._update_estimate()

    def _video_height(self) -> int:
        """영상 화질 (음원 모드에서는 화질 칸이 음질이라 저장된 값을 쓴다)."""
        if self.mode.value() == "audio":
            return int(self.settings.max_height or 0)
        return int(self.quality.currentData() or 0)

    def _update_estimate(self) -> None:
        mode = self.mode.value()
        height = self._video_height()
        for r in self._ready:
            r.update_estimate(mode, height)

    # ==================================================================
    # 도구 확인 / 업데이트
    # ==================================================================
    def _check_deps(self, initial: bool = False) -> None:
        self._checker = DepsChecker(self)
        self._checker.done.connect(lambda d: self._on_deps_checked(d, initial))
        self._checker.start()
        app = QApplication.instance()
        if app is not None and not getattr(self, "_quit_hooked", False):
            self._quit_hooked = True
            app.aboutToQuit.connect(self._wait_threads)

    def _wait_threads(self) -> None:
        """종료할 때 백그라운드 스레드가 끝나길 기다린다 (강제 종료 오류 방지)."""
        checker = getattr(self, "_checker", None)
        if checker is not None:
            try:
                checker.wait(5000)
            except RuntimeError:
                pass

    def _on_deps_checked(self, deps: Deps, initial: bool) -> None:
        self._checker.wait(1000)
        self._checker.deleteLater()
        self._checker = None
        self._set_deps(deps)
        if initial and deps.ytdlp.ok and deps.ytdlp.managed and self.settings.auto_update_ytdlp \
                and self._update_due():
            self._auto_update()
            return
        self.queue.set_paused(False)
        if initial:
            missing = deps.missing_required()
            if missing:
                self._open_deps_dialog(
                    intro=tr("처음 사용하려면 도구가 필요해요: ") + ", ".join(missing)
                    + tr("\n[없는 도구 설치]를 누르면 자동으로 받아요 (약 200MB, 한 번만 받으면 돼요)."))
            else:
                self._maybe_paste_clipboard()

    def _set_deps(self, deps: Deps) -> None:
        self.deps = deps
        self.deps_ready = True
        self.queue.set_paused(self.queue._paused)   # 도구가 새로 설치됐으면 대기 중인 작업 시작
        missing = deps.missing_required()
        if missing:
            self.deps_btn.setText(tr("⚠ 필요한 도구 없음: ") + ", ".join(missing))
            self.deps_btn.setStyleSheet(f"color: {WARNING};")
            self.b_tools.setIcon(icons.icon("info", WARNING, 22))
            self.b_tools.setToolTip(tr("도구 상태 · 필요한 도구가 없어요: ") + ", ".join(missing))
        else:
            js = deps.js.name if deps.js else ""
            self.deps_btn.setText(f"yt-dlp {deps.ytdlp.version} · ffmpeg ✔ · {js} ✔")
            self.deps_btn.setStyleSheet("")
            self.b_tools.setIcon(icons.icon("info", ICON, 22))
            self.b_tools.setToolTip(tr("도구 상태 · yt-dlp {version} · ffmpeg ✔ · {js} ✔").format(version=deps.ytdlp.version, js=js))
        if self.status_msg.text() == tr("도구 확인 중…"):
            self.status_msg.setText(tr("준비됐어요"))

    def _update_due(self) -> bool:
        """yt-dlp 업데이트 확인은 하루에 한 번만."""
        try:
            last = datetime.fromisoformat(self.settings.last_update_check)
        except ValueError:
            return True
        return datetime.now() - last >= timedelta(hours=24) or last > datetime.now()

    def _auto_update(self) -> None:
        self.status_msg.setText(tr("yt-dlp 업데이트 확인 중…"))
        self._updater = YtdlpUpdater(self.deps.ytdlp.path, self)

        def done(ok: bool, last: str) -> None:
            self._updater.deleteLater()
            self._updater = None
            if ok:
                self.settings.last_update_check = datetime.now().isoformat(timespec="seconds")
                self.settings.save()
            if ok and "Updated yt-dlp" in last:
                self.status_msg.setText(tr("yt-dlp를 최신 버전으로 업데이트했어요"))
                self._check_deps(initial=False)
            elif ok:
                self.status_msg.setText(tr("yt-dlp가 최신 버전이에요"))
            else:
                self.status_msg.setText(tr("yt-dlp 업데이트 확인 실패 (인터넷 연결 확인)"))
            self.queue.set_paused(False)
            missing = self.deps.missing_required()
            if missing:
                self._open_deps_dialog(intro=tr("필요한 도구가 없어요: ") + ", ".join(missing))
            else:
                self._maybe_paste_clipboard()

        self._updater.done.connect(done)
        self._updater.start()

    def _open_deps_dialog(self, intro: str = "") -> None:
        dlg = DepsDialog(self.deps if self.deps_ready else None, self, intro=intro)
        dlg.depsChanged.connect(self._set_deps)
        if not self.deps_ready:
            dlg.recheck()
        self.queue.set_paused(True)   # 설치/업데이트 중 실행 파일이 바뀌지 않게
        dlg.exec()
        dlg.deleteLater()
        self.queue.set_paused(False)

    def _open_about(self) -> None:
        dlg = AboutDialog(self.deps if self.deps_ready else None, self)
        dlg.exec()
        dlg.deleteLater()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        saved = dlg.exec()
        dlg.deleteLater()
        if saved:
            self._apply_settings_to_ui()
            self.status_msg.setText(tr("설정을 저장했어요"))
            if resolve(self.settings.language) != current_language():
                QMessageBox.information(self, tr("언어 / Language"), tr("언어는 프로그램을 다시 시작하면 바뀌어요."))

    # ==================================================================
    # 정보 불러오기
    # ==================================================================
    def _paste(self) -> None:
        """[링크 붙여넣기] - 클립보드의 주소로 바로 불러오기."""
        text = (QGuiApplication.clipboard().text() or "").strip()
        first = text.splitlines()[0].strip() if text else ""
        if first and is_url(first):
            self.url_edit.setText(first)
            self._auto_pending = self.auto_toggle.isChecked()
            self.fetch()
        else:
            self.toasts.show("warn", tr("클립보드에 링크가 없어요"),
                             tr("주소를 복사한 뒤 다시 눌러 주세요. (직접 입력하려면 Ctrl+L)"))

    def _fetch_clicked(self) -> None:
        self._auto_pending = False       # 직접 입력해서 누른 건 먼저 보고 고르기
        self.fetch()

    def _on_auto_toggled(self, on: bool) -> None:
        self.settings.auto_download = on
        self.settings.save()
        self.status_msg.setText(tr("바로 받기 켬 - 링크를 붙여넣으면 지금 설정으로 바로 받아요") if on
                                else tr("바로 받기 끔 - 링크를 붙여넣으면 정보를 먼저 보여줘요"))

    # ---- 정보 패널 --------------------------------------------------------
    def _open_panel(self, focus: bool = False) -> None:
        self._panel_open = True
        self._update_panel_state()
        if focus:
            self.url_edit.setFocus()
            self.url_edit.selectAll()

    def _close_panel(self) -> None:
        if self.fetcher.busy:
            self.fetcher.abort()
            self._fetch_ui_idle()
        self._auto_pending = False
        self._panel_open = False
        self.url_edit.clear()
        self._show_notice("")
        self._update_panel_state()

    def _update_panel_state(self) -> None:
        has_notice = bool(self.v_notice.text()) and not self.v_notice.isHidden()
        self.panel.setVisible(self._panel_open)
        self.notice_box.setVisible(has_notice or self.b_fetch_log.isVisibleTo(self.notice_box))

    def fetch(self, force_playlist: bool = False) -> None:
        url = self.url_edit.text().strip()
        if not url:
            self._open_panel(focus=True)
            return
        if not is_url(url):
            if re.fullmatch(r"[\w-]{11}", url):   # 영상 ID 만 넣은 경우
                url = f"https://www.youtube.com/watch?v={url}"
                self.url_edit.setText(url)
            else:
                self._report_error(tr("올바른 주소가 아니에요. https:// 로 시작하는 주소를 넣어 주세요."))
                return
        if not self.deps_ready:
            self.status_msg.setText(tr("도구 확인이 끝나면 다시 눌러 주세요"))
            return
        if not self.deps.ytdlp.ok:
            self._open_deps_dialog(intro=tr("영상 정보를 불러오려면 yt-dlp가 필요해요."))
            if not self.deps.ytdlp.ok:
                return
        playlist = bool(force_playlist) or (self.settings.prefer_playlist and has_playlist_param(url)) \
            or (has_playlist_param(url) and not has_video_param(url))
        if not force_playlist:
            self._channel_retry = False
        self.b_fetch.setEnabled(False)
        self.b_fetch.setText(tr("불러오는 중…"))
        self.fetch_bar.setVisible(True)
        self.status_msg.setText(tr("영상 정보를 불러오는 중… (Esc로 취소)"))
        self.fetcher.fetch(url, self.deps, playlist=playlist, cookies_browser=self.settings.cookies_browser)

    def _escape(self) -> None:
        if self.fetcher.busy:
            self.fetcher.abort()
            self._fetch_ui_idle()
            self.status_msg.setText(tr("불러오기를 취소했어요"))
        elif self._panel_open:
            self._close_panel()

    def _fetch_ui_idle(self) -> None:
        self.b_fetch.setEnabled(True)
        self.b_fetch.setText(tr("불러오기"))
        self.fetch_bar.setVisible(False)

    def _on_info(self, info: MediaInfo, url: str) -> None:
        # 채널 주소면 '동영상' 탭으로 한 번 더
        if info.kind == "playlist" and info.nested_tabs and not self._channel_retry and _CHANNEL_RE.search(url):
            self._channel_retry = True
            videos_url = re.sub(r"[?#].*$", "", url).rstrip("/") + "/videos"
            self.url_edit.setText(videos_url)
            self.fetch(force_playlist=True)
            return
        self._fetch_ui_idle()
        if info.kind == "playlist" and info.nested_tabs:
            self._show_notice(tr("채널 주소예요. 채널의 '동영상' 탭 주소(…/videos)나 재생목록 주소를 넣어 주세요."))
            self.status_msg.setText(tr("불러왔어요"))
            return
        item = self._add_ready(info, url)
        self.status_msg.setText(tr("불러왔어요 - 목록의 [다운로드]를 눌러 받으세요"))
        if self._auto_pending:          # '바로 받기': 카드를 거치지 않고 바로 받기
            self._auto_pending = False
            if item.can_download() and info.kind == "video":
                before = len(self.queue.jobs)
                self._download_ready(item)
                if len(self.queue.jobs) > before:
                    self._close_panel()
                    self.toasts.show("ok", tr("다운로드 목록에 추가했어요"), info.title, timeout_ms=3500)
                    return
        # 주소 입력 칸은 닫고, 카드는 목록 맨 위에 보여준다
        self._panel_open = False
        self.url_edit.clear()
        self._update_panel_state()
        self.q_scroll.verticalScrollBar().setValue(0)

    def _on_info_failed(self, message: str, url: str, log: str = "") -> None:
        self._fetch_ui_idle()
        self._auto_pending = False
        self._last_fetch_log = log
        self._report_error(message, log)
        self.status_msg.setText(tr("불러오지 못했어요"))

    def _can_download(self, info: MediaInfo) -> bool:
        if info.kind == "playlist":
            return any(e.available for e in info.entries)
        return not info.is_live

    def _report_error(self, message: str, log: str = "") -> None:
        """입력 칸이 열려 있으면 그 안에, 아니면 알림으로 알려준다 (갑자기 입력 칸이 튀어나오지 않게)."""
        if self._panel_open:
            self._show_notice(message, error=True)
            self.b_fetch_log.setVisible(bool(log.strip()))
            self._update_panel_state()
        else:
            self.toasts.show("error", tr("불러오지 못했어요"), message[:160], timeout_ms=7000)

    def _show_notice(self, text: str, error: bool = False) -> None:
        self.v_notice.setObjectName("Error" if error else "Notice")
        repolish(self.v_notice)
        self.v_notice.setText(text)
        self.v_notice.setVisible(bool(text))
        if not text:
            self.b_fetch_log.setVisible(False)
        self._update_panel_state()

    def _set_info(self, info: Optional[MediaInfo], error: str = "") -> None:
        """(호환용) 정보를 카드로 올리거나, 오류 문구를 보여준다."""
        if info is None:
            if error:
                self._report_error(error)
            else:
                self._show_notice("")
            return
        self._add_ready(info, self.info_url)

    # ---- '받을 영상' 카드 --------------------------------------------------
    def _fresh_state(self, item: ReadyItem) -> None:
        info, s = item.info, self.settings
        item.sub_langs, item.sub_auto = default_selection(info, s.sub_default_langs, s.sub_default_auto)
        if info.kind == "playlist" and s.sub_default_langs:
            item.sub_langs = [c.strip() for c in s.sub_default_langs.split(",") if c.strip()]
            item.sub_auto = s.sub_default_auto
        item.dub_lang = s.dub_default if info.kind == "playlist" else ""
        item.tag_state = TagState.for_info(info, s.audio_tags_default, s.embed_thumbnail, s.audio_tag_clean)
        item.vtag_state = TagState(s.embed_metadata, s.embed_thumbnail, None, False)

    def _add_ready(self, info: MediaInfo, url: str) -> ReadyItem:
        item = next((r for r in self._ready if r.info is info), None)
        if item is not None:                      # 같은 정보를 다시 올리면 설정만 처음으로
            self._fresh_state(item)
            self._select_ready(item, store=False)
            return item
        item = ReadyItem(info, url, self.thumbs)
        item.downloadRequested.connect(self._download_ready)
        item.removeRequested.connect(self._remove_ready)
        item.selectRequested.connect(self._select_ready)
        item.loadPlaylistRequested.connect(self._load_playlist_for)
        self._fresh_state(item)
        self._ready.insert(0, item)
        if self._filter == "history":
            self._set_filter("all")
        self.q_layout.insertWidget(0, item)
        self._select_ready(item)
        self._apply_filter()
        return item

    def _store_ready_state(self) -> None:
        r = self._sel
        if r is not None:
            r.sub_langs, r.sub_auto, r.dub_lang = list(self.sub_langs), self.sub_auto, self.dub_lang
            r.tag_state, r.vtag_state = self.tag_state, self.vtag_state

    def _select_ready(self, item: Optional[ReadyItem], store: bool = True) -> None:
        if store:
            self._store_ready_state()
        self._sel = item
        for r in self._ready:
            r.set_selected(r is item and len(self._ready) > 1)
        if item is not None:
            self.info, self.info_url = item.info, item.url
            self.sub_langs, self.sub_auto, self.dub_lang = list(item.sub_langs), item.sub_auto, item.dub_lang
            self.tag_state, self.vtag_state = item.tag_state, item.vtag_state
        else:
            self.info, self.info_url = None, ""
            self.sub_langs, self.sub_auto, self.dub_lang = [], False, ""
            self.tag_state = TagState.for_info(None, self.settings.audio_tags_default,
                                               self.settings.embed_thumbnail, self.settings.audio_tag_clean)
            self.vtag_state = TagState(self.settings.embed_metadata, self.settings.embed_thumbnail, None, False)
        self._update_tags_button()
        self._update_subs_button()
        self._fill_quality_combo()
        self._update_estimate()

    def _download_ready(self, item: ReadyItem) -> None:
        self._select_ready(item)
        before = len(self.queue.jobs)
        self.add_download()
        if len(self.queue.jobs) > before:
            self._remove_ready(item)

    def _remove_ready(self, item: ReadyItem) -> None:
        if item not in self._ready:
            return
        was_sel = item is self._sel
        self._ready.remove(item)
        item.alive = False
        item.setParent(None)
        item.deleteLater()
        if was_sel:
            self._sel = None
            self._select_ready(self._ready[0] if self._ready else None, store=False)
        else:
            for r in self._ready:
                r.set_selected(r is self._sel and len(self._ready) > 1)
        self._apply_filter()

    def _load_playlist_for(self, item: ReadyItem) -> None:
        self.url_edit.setText(item.url)
        self._auto_pending = False
        self.fetch(force_playlist=True)

    # ==================================================================
    # 다운로드 추가
    # ==================================================================
    def _ensure_dir(self) -> str:
        d = Path(self.settings.download_dir).expanduser()
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return str(d)

    def _choose_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("저장 위치 선택"), self.settings.download_dir)
        if d:
            self.settings.download_dir = d
            self.settings.save()
            self._update_dest_chip()

    def _update_dest_chip(self) -> None:
        path = self.settings.download_dir
        name = Path(path).name or path
        f = self.dest_btn.font()
        f.setBold(True)
        self.dest_btn.setText(QFontMetrics(f).elidedText(name, Qt.TextElideMode.ElideMiddle, 150))
        self.dest_btn.setToolTip(path)

    def _dest_menu(self) -> None:
        m = QMenu(self)
        m.addAction(tr("폴더 변경…"), self._choose_dir)
        m.addAction(tr("폴더 열기"), lambda: reveal_in_explorer(self._ensure_dir()))
        m.exec(self.dest_btn.mapToGlobal(QPoint(0, self.dest_btn.height() + 2)))
        m.deleteLater()

    def _current_options(self) -> Optional[DownloadOptions]:
        s = self.settings
        ts = self._cur_tags()
        out_dir = self._ensure_dir()
        if not Path(out_dir).is_dir():
            QMessageBox.warning(self, tr("저장 위치"), tr("저장 폴더를 만들 수 없어요:\n{out_dir}").format(out_dir=out_dir))
            return None
        return DownloadOptions(
            mode=self.mode.value(),
            max_height=self._video_height(),
            container=s.container,
            compat_h264=s.compat_h264,
            audio_format=s.audio_format,
            audio_quality=s.audio_quality,
            sub_langs=",".join(self.sub_langs),
            auto_subs=self.sub_auto,
            dub_lang=self.dub_lang,
            sub_mode=s.sub_mode,
            overwrite=s.overwrite_existing,
            embed_thumbnail=ts.cover,
            audio_tags=ts.on,
            tag_values=dict(ts.values) if ts.values else None,
            tag_smart=ts.smart,
            embed_metadata=ts.on if self.mode.value() == "video" else s.embed_metadata,
            output_dir=out_dir,
            filename_template=s.filename_template,
            cookies_browser=s.cookies_browser,
            rate_limit=s.rate_limit,
            section_start=None,
            section_end=None,
        )

    def add_download(self) -> None:
        info = self.info
        if info is None:
            return
        if not self.deps.ytdlp.ok:
            self._open_deps_dialog(intro=tr("다운로드하려면 yt-dlp가 필요해요."))
            if not self.deps.ytdlp.ok:
                return
        missing = [m for m in self.deps.missing_required() if m != "yt-dlp"]
        if missing:
            r = QMessageBox.question(
                self, tr("도구 없음"),
                tr("{join}이(가) 없어서 일부 형식이 실패하거나 화질이 낮을 수 있어요.\n지금 설치할까요?").format(join=', '.join(missing)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self._open_deps_dialog()
                return
        opts = self._current_options()
        if opts is None:
            return

        if info.kind == "playlist":
            dlg = PlaylistDialog(info, self.settings.playlist_folder, self.settings.playlist_numbering, self)
            accepted = dlg.exec()
            chosen = dlg.selected() if accepted else []
            make_folder, numbering = dlg.cb_folder.isChecked(), dlg.cb_number.isChecked()
            dlg.deleteLater()
            if not chosen:
                return
            folder = info.title if make_folder else ""
            width = max(2, len(str(len(info.entries))))
            for idx, entry in chosen:
                o = opts.copy(subfolder=folder, index=idx if numbering else None,
                              index_width=width)
                job = DownloadJob(entry.url, entry.title, o, entry.thumbnail or info.thumbnail)
                job.duration = entry.duration
                self.queue.add(job)
            self.status_msg.setText(tr("{len}개를 다운로드 목록에 추가했어요").format(len=len(chosen)))
        else:
            url = info.url or self.info_url
            dup = next((j for j in self.queue.jobs if j.url == url and j.is_active
                        and j.options.summary() == opts.summary()), None)
            if dup is not None:
                r = QMessageBox.question(self, tr("이미 목록에 있어요"), tr("같은 설정으로 받는 중이에요. 한 번 더 추가할까요?"))
                if r != QMessageBox.StandardButton.Yes:
                    return
            job = DownloadJob(url, info.title, opts, info.thumbnail)
            job.duration = info.duration
            self.queue.add(job)
            self.status_msg.setText(tr("다운로드 목록에 추가했어요"))
        if self._filter == "history" or self._filter not in ("all", opts.mode):
            self._set_filter("all")

    def _redownload(self, url: str) -> None:
        if not url:
            return
        self.url_edit.setText(url)
        self._auto_pending = False
        self.fetch()

    # ==================================================================
    # 큐 이벤트
    # ==================================================================
    def _on_job_added(self, job: DownloadJob) -> None:
        w = QueueItemWidget(job, self.thumbs)
        w.removeRequested.connect(
            lambda j: self.queue.remove(j, delete_partials=self.settings.delete_partials_on_remove))
        w.retryRequested.connect(lambda j: (self.queue.retry(j), self._schedule_save()))
        w.overwriteRequested.connect(lambda j: (self.queue.retry(j, overwrite=True), self._schedule_save()))
        self._item_widgets[job.id] = w
        # 빈 안내 문구 다음 / stretch 앞에 추가 (최근 것이 아래)
        self.q_layout.insertWidget(self.q_layout.count() - 1, w)
        self._apply_filter()
        QTimer.singleShot(50, lambda: self.q_scroll.verticalScrollBar().setValue(
            self.q_scroll.verticalScrollBar().maximum()))

    def _on_job_removed(self, job: DownloadJob) -> None:
        w = self._item_widgets.pop(job.id, None)
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        self._apply_filter()

    def _on_job_finished(self, job: DownloadJob) -> None:
        if job.state in (DONE, FAILED):
            summary = job.options.summary() + (tr(" · 이미 있음") if job.skipped else "")
            self.history.add(title=job.title, url=job.url, filepath=job.filepath, summary=summary,
                             ok=job.state == DONE, error=job.error, thumbnail=job.thumbnail)
            self.history_view.reload()
        if self._closing:
            return
        if job.state == DONE:
            if job.skipped:
                self.toasts.show("warn", tr("이미 받은 파일이에요"), job.title)
            else:
                self.toasts.show("ok", tr("다운로드 완료"), job.title)
        elif job.state == FAILED:
            self.toasts.show("error", tr("다운로드 실패"), (job.error or job.title)[:140], timeout_ms=8000)

    # ---- 필터 / 목록 관리 --------------------------------------------------
    def _set_filter(self, key: str) -> None:
        self._filter = key
        btn = self._filter_btns.get(key)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)
        self.stack.setCurrentIndex(1 if key == "history" else 0)
        self.b_list_menu.setVisible(key != "history")
        self.q_status.setVisible(key != "history")
        self._apply_filter()

    def _apply_filter(self) -> None:
        shown = 0
        for w in self._item_widgets.values():
            ok = self._filter in ("all", "history") or w.job.options.mode == self._filter
            w.setVisible(ok)
            shown += ok
        for r in self._ready:
            r.setVisible(True)
        shown += len(self._ready)
        self.q_empty.setVisible(shown == 0)
        if self._item_widgets and shown == 0:
            self.q_empty_title.setText(tr("받은 동영상이 없어요") if self._filter == "video" else tr("받은 오디오가 없어요"))
            self.q_empty_sub.setText(tr("다른 탭에서 전체 목록을 볼 수 있어요."))
        else:
            self.q_empty_title.setText(tr("링크를 붙여넣어 시작하세요"))
            self.q_empty_sub.setText(tr("위의 [링크 붙여넣기]를 누르거나, 창에 주소를 끌어다 놓아도 돼요.\n"
                                     "유튜브 영상·재생목록·쇼츠 주소를 지원해요."))

    def _list_menu(self) -> None:
        m = QMenu(self)
        m.addAction(tr("완료 항목 정리"),
                    lambda: self.queue.clear_finished(delete_partials=self.settings.delete_partials_on_remove))
        m.addAction(tr("모두 취소"), self.queue.cancel_all)
        m.exec(self.b_list_menu.mapToGlobal(QPoint(self.b_list_menu.width() - 150, self.b_list_menu.height() + 2)))
        m.deleteLater()

    def _update_counts(self) -> None:
        c = self.queue.counts()
        active = c["running"] + c["queued"]
        parts = [tr("{len} 아이템").format(len=len(self.queue.jobs))]
        if c["running"]:
            parts.append(tr("진행 {v}").format(v=c['running']))
        if c["queued"]:
            parts.append(tr("대기 {v}").format(v=c['queued']))
        if c["done"]:
            parts.append(tr("완료 {v}").format(v=c['done']))
        if c["failed"]:
            parts.append(tr("실패 {v}").format(v=c['failed']))
        if c["canceled"]:
            parts.append(tr("취소 {v}").format(v=c['canceled']))
        self.q_status.setText(" · ".join(parts))
        title = APP_NAME
        if c["running"]:
            fr = [j.fraction for j in self.queue.jobs if j.state == "running" and j.fraction is not None]
            if fr:
                title = tr("{int}% · {active}개 진행 - {APP_NAME}").format(int=int(sum(fr) / len(fr) * 100), active=active, APP_NAME=APP_NAME)
            else:
                title = tr("{active}개 진행 - {APP_NAME}").format(active=active, APP_NAME=APP_NAME)
        if self.windowTitle() != title:
            self.setWindowTitle(title)

    def _on_all_done(self, ok: int, fail: int) -> None:
        msg = tr("다운로드가 끝났어요 · 성공 {ok}개").format(ok=ok) + (tr(", 실패 {fail}개").format(fail=fail) if fail else "")
        self.status_msg.setText(msg)
        if not self.settings.notify_on_finish:
            return
        QApplication.alert(self)
        if self.tray is not None and not self.isActiveWindow():
            self.tray.showMessage(APP_NAME, msg, app_icon(), 5000)

    # ==================================================================
    # 자막 / 접기 / 크기 조절 / 목록 저장
    # ==================================================================
    def _choose_subs(self) -> None:
        audio = self.mode.value() == "audio"
        info = self.info
        selected = self.sub_langs
        if (info is None or info.kind != "video") and not selected:
            selected = []
        dlg = SubtitleDialog(info, selected, self.sub_auto, self.settings.sub_mode, audio, dub=self.dub_lang, parent=self)
        accepted = dlg.exec()
        result = dlg.result_selection()
        dub = dlg.result_dub()
        dlg.deleteLater()
        if accepted:
            langs, auto, mode = result
            self.sub_langs, self.sub_auto = langs, auto
            self.dub_lang = dub
            if not audio:
                self.settings.sub_mode = mode
                self.settings.save()
            self._update_subs_button()
            self._store_ready_state()

    def _cur_tags(self) -> TagState:
        return self.tag_state if self.mode.value() == "audio" else self.vtag_state

    def _choose_tags(self) -> None:
        audio = self.mode.value() == "audio"
        dlg = TagDialog(self.info, self._cur_tags(), self, audio=audio)
        accepted = dlg.exec()
        result = dlg.result_state()
        dlg.deleteLater()
        if accepted:
            if audio:
                self.tag_state = result
            else:
                self.vtag_state = result
            self._store_ready_state()
            self._update_tags_button()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is getattr(self, "toolbar", None) and event.type() == QEvent.Type.LayoutRequest:
            need = max(MIN_WINDOW_WIDTH, self.toolbar.minimumSizeHint().width())
            if need != self.minimumWidth():
                self.setMinimumWidth(need)
        return super().eventFilter(obj, event)

    @staticmethod
    def _clip(widget: QWidget, text: str, n: int = 9) -> str:
        """칩 글자를 '한글 n글자' 너비까지만 보이게 줄인다 (언어마다 글자 폭이 달라서 픽셀로 잰다)."""
        fm = widget.fontMetrics()
        return fm.elidedText(text, Qt.TextElideMode.ElideRight, fm.horizontalAdvance("가" * n))

    def _update_tags_button(self) -> None:
        ts = self._cur_tags()
        text = ts.button_text()
        prefix = tr("태그: ")
        if text.startswith(prefix):
            text = text[len(prefix):]
        self.b_tags.setText(self._clip(self.b_tags, text, 9))
        if ts.on and ts.values:
            v = ts.values
            self.b_tags.setToolTip("\n".join(f"{k}: {v.get(f, '')}" for f, k in
                                             (("title", tr("제목")), ("artist", tr("아티스트")), ("album", tr("앨범")), ("year", tr("연도")))))
        else:
            self.b_tags.setToolTip(tr("음원 파일의 제목·아티스트·앨범·커버 태그를 넣을지, 어떤 값으로 넣을지 골라요"))

    def _update_subs_button(self) -> None:
        audio = self.mode.value() == "audio"
        full = summarize(self.sub_langs, self.sub_auto, self.settings.sub_mode, audio, self.dub_lang)
        names = [LANG_NAMES.get(c.split("-")[0], c) for c in self.sub_langs]
        text = (", ".join(names[:2]) + (tr(" 외 {v}").format(v=len(names) - 2) if len(names) > 2 else "")) if names else tr("없음")
        info = self.info
        if not names and info is not None and info.kind == "video" and not info.subtitles and not info.auto_captions:
            text = tr("자막 없음")
        if self.dub_lang:
            text += tr(" · {dub_name} 더빙").format(dub_name=dub_name(self.dub_lang))
        self.b_subs.setToolTip(tr("받을 자막 언어, 더빙(음성 언어), 저장 방식을 골라요 (영상마다 따로 정할 수 있어요)\n지금: ") + full)
        self.b_subs.setText(self._clip(self.b_subs, text, 8))

    @staticmethod
    def _set_pill_active(btn: QPushButton, on: bool) -> None:
        """알약 버튼이 '켜진' 상태(빨간 테두리)인지 표시."""
        if bool(btn.property("active")) != on:
            btn.setProperty("active", on)
            repolish(btn)

    def _schedule_save(self) -> None:
        if not self._closing and not self._save_timer.isActive():
            self._save_timer.start()

    def _save_queue(self) -> None:
        if not self._closing:
            save_jobs(self.queue.jobs)

    def _restore_queue(self) -> None:
        jobs = load_jobs()
        if not jobs:
            return
        for job in jobs:
            self.queue.add(job)
        waiting = sum(1 for j in jobs if j.state == "queued")
        if waiting:
            self.status_msg.setText(tr("지난번에 받던 {waiting}개를 이어서 받아요").format(waiting=waiting))

    # ==================================================================
    # 클립보드 / 드래그 앤 드롭 / 종료
    # ==================================================================
    def _maybe_paste_clipboard(self) -> None:
        if not self.settings.clipboard_autofetch or self.fetcher.busy or not self.deps.ytdlp.ok:
            return
        if self.url_edit.text().strip():
            return
        text = (QGuiApplication.clipboard().text() or "").strip()
        if text and text != self._last_clip and is_youtube_url(text):
            self._last_clip = text
            self.url_edit.setText(text)
            self.fetch()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow() and self.deps_ready:
            QTimer.singleShot(150, self._maybe_paste_clipboard)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        md = event.mimeData()
        if md.hasUrls() or (md.hasText() and is_url(md.text().strip())):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        md = event.mimeData()
        url = ""
        if md.hasUrls():
            u = md.urls()[0]
            url = u.toString() if not u.isLocalFile() else ""
        if not url and md.hasText():
            url = md.text().strip().splitlines()[0] if md.text().strip() else ""
        if is_url(url):
            self.url_edit.setText(url)
            self._auto_pending = self.auto_toggle.isChecked()
            self.fetch()
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.queue.has_active():
            box = QMessageBox(self)
            box.setWindowTitle(tr("종료"))
            box.setIcon(QMessageBox.Icon.Question)
            box.setText(tr("받는 중이거나 대기 중인 다운로드가 있어요.\n지금 종료하면 다음에 켤 때 이어서 받아요."))
            b_quit = box.addButton(tr("종료"), QMessageBox.ButtonRole.AcceptRole)
            box.addButton(tr("계속 받기"), QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not b_quit:
                event.ignore()
                return
        # 지금 상태(진행 중 → 대기)로 목록을 저장한 다음 취소
        self._save_queue()
        self._closing = True
        self._save_timer.stop()
        self.queue.cancel_all()
        self.fetcher.abort()
        self.settings.save()
        if self.tray is not None:
            self.tray.hide()
        event.accept()
        QApplication.quit()
