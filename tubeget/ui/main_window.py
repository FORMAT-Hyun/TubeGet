"""메인 창."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter, QSystemTrayIcon,
                               QTabWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION
from ..config import Settings
from ..core.deps import Deps
from ..core.fetcher import InfoFetcher
from ..core.history import History
from ..core.installer import DepsChecker, YtdlpUpdater, cleanup_old_files
from ..core.metadata import MediaInfo
from ..core.options import (AUDIO_FORMATS, HEIGHT_CHOICES, VIDEO_CONTAINERS, DownloadOptions,
                            height_label)
from ..core.queue import QueueManager
from ..core.queue_store import load_jobs, save_jobs
from ..core.runner import DONE, FAILED, DownloadJob
from ..utils import (has_playlist_param, has_video_param, human_duration, human_size, is_url,
                     is_youtube_url, parse_timecode, reveal_in_explorer)
from .deps_dialog import DepsDialog
from .history_view import HistoryView
from .playlist_dialog import PlaylistDialog
from .queue_item import QueueItemWidget
from .settings_dialog import SettingsDialog
from .subtitle_dialog import SubtitleDialog, default_selection, summarize
from .tag_dialog import TagDialog, TagState
from .theme import app_icon, make_icon_pixmap, repolish
from .widgets import (ElidedLabel, SegmentedToggle, ThumbLoader, field_label, make_button,
                      rounded, show_log_dialog)

THUMB_SIZE = QSize(208, 117)
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
        self._last_clip = ""
        self._channel_retry = False
        self._updater: Optional[YtdlpUpdater] = None
        self._deps_dialog_shown = False
        self._closing = False
        self._last_fetch_log = ""
        self.sub_langs: list[str] = []     # 지금 영상에서 고른 자막
        self.sub_auto = False
        self.tag_state = TagState()           # 음원 태그 (영상마다)

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
        self.resize(960, 920)
        self.setMinimumSize(780, 680)
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
        root.setContentsMargins(18, 14, 18, 10)
        root.setSpacing(12)

        # 머리글 ------------------------------------------------------
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(make_icon_pixmap(64).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        ver = QLabel(f"v{APP_VERSION} · yt-dlp GUI")
        ver.setObjectName("AppVersion")
        head.addWidget(logo)
        head.addSpacing(4)
        head.addWidget(title)
        head.addSpacing(6)
        head.addWidget(ver, 0, Qt.AlignmentFlag.AlignBottom)
        head.addStretch(1)
        self.b_tools = make_button("도구 상태", ghost=True)
        self.b_settings = make_button("설정", ghost=True)
        self.b_tools.clicked.connect(lambda: self._open_deps_dialog())
        self.b_settings.clicked.connect(self._open_settings)
        head.addWidget(self.b_tools)
        head.addWidget(self.b_settings)
        root.addLayout(head)

        # 주소 입력 ----------------------------------------------------
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_edit = QLineEdit()
        self.url_edit.setObjectName("UrlInput")
        self.url_edit.setPlaceholderText("유튜브 영상이나 재생목록 주소를 붙여넣으세요")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self.fetch)
        self.b_paste = make_button("붙여넣기")
        self.b_paste.clicked.connect(self._paste)
        self.b_fetch = make_button("불러오기", primary=True)
        self.b_fetch.clicked.connect(self.fetch)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.b_paste)
        url_row.addWidget(self.b_fetch)
        root.addLayout(url_row)
        self.fetch_bar = QProgressBar()
        self.fetch_bar.setRange(0, 0)
        self.fetch_bar.setTextVisible(False)
        self.fetch_bar.setVisible(False)
        root.addWidget(self.fetch_bar)

        # 정보 + 옵션 카드 ----------------------------------------------
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)

        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        self.thumb = QLabel()
        self.thumb.setObjectName("Thumb")
        self.thumb.setFixedSize(THUMB_SIZE)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignTop)
        meta_col = QVBoxLayout()
        meta_col.setSpacing(6)
        self.v_title = QLabel()
        self.v_title.setObjectName("VideoTitle")
        self.v_title.setWordWrap(True)
        self.v_title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.v_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.v_meta = QLabel()
        self.v_meta.setObjectName("Muted")
        self.v_meta.setWordWrap(True)
        self.v_notice = QLabel()
        self.v_notice.setObjectName("Notice")
        self.v_notice.setWordWrap(True)
        self.b_load_playlist = make_button("이 주소의 재생목록 전체 불러오기 →", link=True)
        self.b_load_playlist.clicked.connect(lambda: self.fetch(force_playlist=True))
        meta_col.addWidget(self.v_title)
        meta_col.addWidget(self.v_meta)
        meta_col.addWidget(self.v_notice)
        meta_col.addWidget(self.b_load_playlist, 0, Qt.AlignmentFlag.AlignLeft)
        self.b_fetch_log = make_button("자세한 로그 보기", link=True)
        self.b_fetch_log.clicked.connect(
            lambda: show_log_dialog(self, "불러오기 로그", self._last_fetch_log.splitlines()))
        meta_col.addWidget(self.b_fetch_log, 0, Qt.AlignmentFlag.AlignLeft)
        meta_col.addStretch(1)
        info_row.addLayout(meta_col, 1)
        self.b_collapse = make_button("옵션 접기 ▲", ghost=True, tooltip="옵션 영역을 접어서 다운로드 목록을 넓게 보기")
        self.b_collapse.clicked.connect(lambda: self._set_collapsed(not self.settings.options_collapsed))
        info_row.addWidget(self.b_collapse, 0, Qt.AlignmentFlag.AlignTop)
        cl.addLayout(info_row)

        self.options_box = QWidget()
        ob = QVBoxLayout(self.options_box)
        ob.setContentsMargins(0, 0, 0, 0)
        ob.setSpacing(10)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2c3038; background: #2c3038; max-height: 1px; border: none;")
        ob.addWidget(line)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.mode = SegmentedToggle([("video", "영상"), ("audio", "음원만")])
        self.mode.changed.connect(self._on_mode_changed)
        grid.addWidget(field_label("받을 형식"), 0, 0)
        grid.addWidget(self.mode, 0, 1, 1, 3, Qt.AlignmentFlag.AlignLeft)

        self.quality = QComboBox()
        self.quality.setMinimumWidth(180)
        self.quality.currentIndexChanged.connect(self._on_option_changed)
        self.fmt = QComboBox()
        self.fmt.setMinimumWidth(150)
        self.fmt.currentIndexChanged.connect(self._on_option_changed)
        self.l_quality = field_label("화질")
        grid.addWidget(self.l_quality, 1, 0)
        grid.addWidget(self.quality, 1, 1)
        self.l_fmt = field_label("파일 형식")
        grid.addWidget(self.l_fmt, 1, 2)
        grid.addWidget(self.fmt, 1, 3)

        opts = QHBoxLayout()
        opts.setSpacing(18)
        self.b_subs = make_button("자막: 없음", tooltip="이 영상에 있는 자막 중에서 받을 언어와 저장 방식을 골라요")
        self.b_subs.clicked.connect(self._choose_subs)
        opts.addWidget(self.b_subs)
        self.b_tags = make_button("태그: 켬", tooltip="음원 파일의 제목·아티스트·앨범·커버 태그를 넣을지, 어떤 값으로 넣을지 골라요")
        self.b_tags.clicked.connect(self._choose_tags)
        opts.addWidget(self.b_tags)
        opts.addSpacing(6)
        self.cb_thumb = QCheckBox("썸네일 넣기")
        self.cb_thumb.setToolTip("썸네일을 파일 표지로 넣어요 (MP4/MKV/MP3/M4A 등).")
        self.cb_compat = QCheckBox("편집 호환 (H.264)")
        self.cb_compat.setToolTip("CapCut·프리미어 같은 편집 프로그램이나 오래된 기기에서 잘 열리도록\n"
                                  "H.264 코덱을 우선해요. 대신 화질이 최대 1080p로 제한될 수 있어요.")
        for cb in (self.cb_thumb, self.cb_compat):
            cb.toggled.connect(self._on_option_changed)
            opts.addWidget(cb)
        opts.addStretch(1)
        grid.addWidget(field_label("옵션"), 2, 0)
        grid.addLayout(opts, 2, 1, 1, 3)

        sec = QHBoxLayout()
        sec.setSpacing(8)
        self.sec_start = QLineEdit()
        self.sec_start.setPlaceholderText("시작 (예: 1:30)")
        self.sec_end = QLineEdit()
        self.sec_end.setPlaceholderText("끝 (예: 2:45)")
        for e in (self.sec_start, self.sec_end):
            e.setMaximumWidth(140)
            e.textChanged.connect(self._validate_sections)
        tilde = QLabel("~")
        tilde.setObjectName("Muted")
        sec_hint = QLabel("비워두면 전체")
        sec_hint.setObjectName("Small")
        sec.addWidget(self.sec_start)
        sec.addWidget(tilde)
        sec.addWidget(self.sec_end)
        sec.addSpacing(6)
        sec.addWidget(sec_hint)
        sec.addStretch(1)
        grid.addWidget(field_label("구간 자르기"), 3, 0)
        grid.addLayout(sec, 3, 1, 1, 3)

        dest = QHBoxLayout()
        dest.setSpacing(6)
        self.dest_label = ElidedLabel("", mode=Qt.TextElideMode.ElideMiddle)
        self.b_dest = make_button("변경")
        self.b_dest.clicked.connect(self._choose_dir)
        self.b_dest_open = make_button("열기", ghost=True)
        self.b_dest_open.clicked.connect(lambda: reveal_in_explorer(self._ensure_dir()))
        dest.addWidget(self.dest_label, 1)
        dest.addWidget(self.b_dest)
        dest.addWidget(self.b_dest_open)
        grid.addWidget(field_label("저장 위치"), 4, 0)
        grid.addLayout(dest, 4, 1, 1, 3)
        ob.addLayout(grid)
        cl.addWidget(self.options_box)

        action = QHBoxLayout()
        self.est_label = QLabel()
        self.est_label.setObjectName("Muted")
        self.est_label.setMinimumWidth(240)
        self.b_download = make_button("다운로드", primary=True)
        self.b_download.setMinimumWidth(170)
        self.b_download.setMinimumHeight(38)
        self.b_download.clicked.connect(self.add_download)
        action.addWidget(self.est_label)
        action.addStretch(1)
        action.addWidget(self.b_download)
        cl.addLayout(action)
        self.top_scroll = QScrollArea()
        self.top_scroll.setWidgetResizable(True)
        self.top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.top_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.top_scroll.setWidget(card)
        self.top_scroll.setMinimumHeight(150)

        # 탭: 다운로드 큐 / 기록 ------------------------------------------
        self.tabs = QTabWidget()
        q_page = QWidget()
        ql = QVBoxLayout(q_page)
        ql.setContentsMargins(0, 8, 0, 0)
        ql.setSpacing(8)
        q_tools = QHBoxLayout()
        self.q_status = QLabel()
        self.q_status.setObjectName("Muted")
        b_clear = make_button("완료 항목 정리", ghost=True)
        b_clear.clicked.connect(
            lambda: self.queue.clear_finished(delete_partials=self.settings.delete_partials_on_remove))
        b_cancel = make_button("모두 취소", ghost=True)
        b_cancel.clicked.connect(self.queue.cancel_all)
        q_tools.addWidget(self.q_status)
        q_tools.addStretch(1)
        q_tools.addWidget(b_clear)
        q_tools.addWidget(b_cancel)
        ql.addLayout(q_tools)

        self.q_scroll = QScrollArea()
        self.q_scroll.setWidgetResizable(True)
        self.q_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        self.q_layout = QVBoxLayout(holder)
        self.q_layout.setContentsMargins(0, 0, 4, 0)
        self.q_layout.setSpacing(8)
        self.q_empty = QLabel("아직 다운로드가 없어요.\n위에 주소를 붙여넣고 [불러오기]를 눌러 보세요.")
        self.q_empty.setObjectName("Empty")
        self.q_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.q_layout.addWidget(self.q_empty)
        self.q_layout.addStretch(1)
        self.q_scroll.setWidget(holder)
        ql.addWidget(self.q_scroll, 1)
        self.tabs.addTab(q_page, "다운로드")

        self.history_view = HistoryView(self.history)
        self.history_view.redownloadRequested.connect(self._redownload)
        self.tabs.addTab(self.history_view, "기록")
        self.tabs.setMinimumHeight(160)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.top_scroll)
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.splitterMoved.connect(lambda *_: self._remember_splitter())
        root.addWidget(self.splitter, 1)

        # 상태 표시줄 ----------------------------------------------------
        self.status_msg = QLabel("도구 확인 중…")
        self.status_msg.setContentsMargins(8, 0, 0, 0)
        self.statusBar().addWidget(self.status_msg, 1)
        self.deps_btn = QPushButton("")
        self.deps_btn.setProperty("ghost", True)
        self.deps_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deps_btn.clicked.connect(lambda: self._open_deps_dialog())
        self.statusBar().addPermanentWidget(self.deps_btn)

        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: (self.url_edit.setFocus(), self.url_edit.selectAll()))
        QShortcut(QKeySequence("Escape"), self, activated=self._escape)

    def _build_tray(self) -> None:
        self.tray: Optional[QSystemTrayIcon] = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu(self)
        a_show = QAction("창 열기", self)
        a_show.triggered.connect(self._raise)
        a_quit = QAction("종료", self)
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
        self.cb_thumb.setChecked(s.embed_thumbnail)
        self.cb_compat.setChecked(s.compat_h264)
        self.dest_label.setText(s.download_dir)
        self.dest_label.setToolTip(s.download_dir)
        self._fill_format_combo()
        self._fill_quality_combo()
        self._update_mode_enabled()
        self._loading_ui = False
        self.queue.set_max_concurrent(s.max_concurrent)
        self._set_collapsed(s.options_collapsed, save=False)

    def _fill_format_combo(self) -> None:
        self.fmt.blockSignals(True)
        self.fmt.clear()
        if self.mode.value() == "audio":
            for key, label in AUDIO_FORMATS:
                self.fmt.addItem(label, key)
            self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.settings.audio_format)))
        else:
            for c in VIDEO_CONTAINERS:
                self.fmt.addItem(c.upper(), c)
            self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.settings.container)))
        self.fmt.blockSignals(False)

    def _fill_quality_combo(self) -> None:
        self.quality.blockSignals(True)
        self.quality.clear()
        info = self.info
        heights = info.heights if (info and info.kind == "video" and info.heights) else HEIGHT_CHOICES
        best_size = info.estimated_size(0) if (info and info.kind == "video") else None
        self.quality.addItem("최고 화질" + (f"  ≈ {human_size(best_size)}" if best_size else ""), 0)
        for h in heights:
            size = info.estimated_size(h) if (info and info.kind == "video") else None
            label = height_label(h)
            if info and info.kind == "video" and size:
                label += f"  ≈ {human_size(size)}"
            elif not (info and info.kind == "video"):
                label = f"최대 {label}"
            self.quality.addItem(label, h)
        want = self.settings.max_height
        idx = self.quality.findData(want)
        if idx < 0 and want:
            # 원하는 화질이 없으면 그보다 낮은 것 중 가장 높은 화질
            lower = [h for h in heights if h <= want]
            idx = self.quality.findData(max(lower)) if lower else 0
        self.quality.setCurrentIndex(max(0, idx))
        self.quality.blockSignals(False)

    def _update_mode_enabled(self) -> None:
        video = self.mode.value() == "video"
        for w in (self.quality, self.l_quality, self.cb_compat):
            w.setEnabled(video)
        # 음원은 커버를 태그 창에서 정하므로 '썸네일 넣기' 대신 [태그] 버튼
        self.cb_thumb.setVisible(video)
        self.cb_compat.setVisible(video)
        self.b_tags.setVisible(not video)
        self.l_fmt.setText("파일 형식" if video else "음원 형식")
        self._update_subs_button()
        self._update_estimate()

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.mode = mode
        self.settings.save()
        self._fill_format_combo()
        self._update_mode_enabled()

    def _on_option_changed(self, *_args) -> None:
        if getattr(self, "_loading_ui", False):
            return
        s = self.settings
        if self.mode.value() == "audio":
            s.audio_format = self.fmt.currentData() or "mp3"
        else:
            s.container = self.fmt.currentData() or "mp4"
            s.max_height = int(self.quality.currentData() or 0)
        s.embed_thumbnail = self.cb_thumb.isChecked()
        s.compat_h264 = self.cb_compat.isChecked()
        s.save()
        self._update_collapsed_summary()

    def _update_estimate(self) -> None:
        prefix = getattr(self, "_collapsed_text", "")
        prefix = f"{prefix}   " if prefix else ""
        info = self.info
        if not info:
            self.est_label.setText(prefix.strip())
            return
        if info.kind == "playlist":
            n = sum(1 for e in info.entries if e.available)
            self.est_label.setText(f"{prefix}받을 수 있는 영상 {n}개")
            return
        if self.mode.value() == "audio":
            size = info.estimated_size(0, "audio")
        else:
            size = info.estimated_size(int(self.quality.currentData() or 0))
        self.est_label.setText(prefix + (f"예상 크기 ≈ {human_size(size)}" if size else ""))

    def _validate_sections(self) -> bool:
        ok = True
        for e in (self.sec_start, self.sec_end):
            bad = bool(e.text().strip()) and parse_timecode(e.text()) is None
            e.setStyleSheet("border-color: #ff6b6b;" if bad else "")
            ok = ok and not bad
        return ok

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
                    intro="처음 사용하려면 도구가 필요해요: " + ", ".join(missing)
                    + "\n[없는 도구 설치]를 누르면 자동으로 받아요 (약 200MB, 한 번만 받으면 돼요).")
            else:
                self._maybe_paste_clipboard()

    def _set_deps(self, deps: Deps) -> None:
        self.deps = deps
        self.deps_ready = True
        self.queue.set_paused(self.queue._paused)   # 도구가 새로 설치됐으면 대기 중인 작업 시작
        missing = deps.missing_required()
        if missing:
            self.deps_btn.setText("⚠ 필요한 도구 없음: " + ", ".join(missing))
            self.deps_btn.setStyleSheet("color: #f5b544;")
        else:
            js = deps.js.name if deps.js else ""
            self.deps_btn.setText(f"yt-dlp {deps.ytdlp.version} · ffmpeg ✔ · {js} ✔")
            self.deps_btn.setStyleSheet("")
        if self.status_msg.text() == "도구 확인 중…":
            self.status_msg.setText("준비됐어요")

    def _update_due(self) -> bool:
        """yt-dlp 업데이트 확인은 하루에 한 번만."""
        try:
            last = datetime.fromisoformat(self.settings.last_update_check)
        except ValueError:
            return True
        return datetime.now() - last >= timedelta(hours=24) or last > datetime.now()

    def _auto_update(self) -> None:
        self.status_msg.setText("yt-dlp 업데이트 확인 중…")
        self._updater = YtdlpUpdater(self.deps.ytdlp.path, self)

        def done(ok: bool, last: str) -> None:
            self._updater.deleteLater()
            self._updater = None
            if ok:
                self.settings.last_update_check = datetime.now().isoformat(timespec="seconds")
                self.settings.save()
            if ok and "Updated yt-dlp" in last:
                self.status_msg.setText("yt-dlp를 최신 버전으로 업데이트했어요")
                self._check_deps(initial=False)
            elif ok:
                self.status_msg.setText("yt-dlp가 최신 버전이에요")
            else:
                self.status_msg.setText("yt-dlp 업데이트 확인 실패 (인터넷 연결 확인)")
            self.queue.set_paused(False)
            missing = self.deps.missing_required()
            if missing:
                self._open_deps_dialog(intro="필요한 도구가 없어요: " + ", ".join(missing))
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

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        saved = dlg.exec()
        dlg.deleteLater()
        if saved:
            self._apply_settings_to_ui()
            self.status_msg.setText("설정을 저장했어요")

    # ==================================================================
    # 정보 불러오기
    # ==================================================================
    def _paste(self) -> None:
        text = QGuiApplication.clipboard().text().strip()
        if text:
            self.url_edit.setText(text)
            self.fetch()

    def fetch(self, force_playlist: bool = False) -> None:
        url = self.url_edit.text().strip()
        if not url:
            self.url_edit.setFocus()
            return
        if not is_url(url):
            if re.fullmatch(r"[\w-]{11}", url):   # 영상 ID 만 넣은 경우
                url = f"https://www.youtube.com/watch?v={url}"
                self.url_edit.setText(url)
            else:
                self._set_info(None, error="올바른 주소가 아니에요. https:// 로 시작하는 주소를 넣어 주세요.")
                return
        if not self.deps_ready:
            self.status_msg.setText("도구 확인이 끝나면 다시 눌러 주세요")
            return
        if not self.deps.ytdlp.ok:
            self._open_deps_dialog(intro="영상 정보를 불러오려면 yt-dlp가 필요해요.")
            if not self.deps.ytdlp.ok:
                return
        playlist = bool(force_playlist) or (self.settings.prefer_playlist and has_playlist_param(url)) \
            or (has_playlist_param(url) and not has_video_param(url))
        if not force_playlist:
            self._channel_retry = False
        self.b_fetch.setEnabled(False)
        self.b_fetch.setText("불러오는 중…")
        self.fetch_bar.setVisible(True)
        self.b_download.setEnabled(False)
        self.status_msg.setText("영상 정보를 불러오는 중… (Esc로 취소)")
        self.fetcher.fetch(url, self.deps, playlist=playlist, cookies_browser=self.settings.cookies_browser)

    def _escape(self) -> None:
        if self.fetcher.busy:
            self.fetcher.abort()
            self._fetch_ui_idle()
            self.status_msg.setText("불러오기를 취소했어요")

    def _fetch_ui_idle(self) -> None:
        self.b_fetch.setEnabled(True)
        self.b_fetch.setText("불러오기")
        self.fetch_bar.setVisible(False)
        self.b_download.setEnabled(self.info is not None and self._can_download(self.info))

    def _on_info(self, info: MediaInfo, url: str) -> None:
        # 채널 주소면 '동영상' 탭으로 한 번 더
        if info.kind == "playlist" and info.nested_tabs and not self._channel_retry and _CHANNEL_RE.search(url):
            self._channel_retry = True
            videos_url = re.sub(r"[?#].*$", "", url).rstrip("/") + "/videos"
            self.url_edit.setText(videos_url)
            self.fetch(force_playlist=True)
            return
        self._fetch_ui_idle()
        self.info_url = url
        self._set_info(info)
        self.status_msg.setText("불러왔어요")

    def _on_info_failed(self, message: str, url: str, log: str = "") -> None:
        self._fetch_ui_idle()
        self._last_fetch_log = log
        self._set_info(None, error=message)
        self.b_fetch_log.setVisible(bool(log.strip()))
        self.status_msg.setText("불러오지 못했어요")

    def _can_download(self, info: MediaInfo) -> bool:
        if info.kind == "playlist":
            return any(e.available for e in info.entries)
        return not info.is_live

    def _set_info(self, info: Optional[MediaInfo], error: str = "") -> None:
        self.info = info
        self.thumb.clear()
        self.thumb.setText("미리보기")
        self.v_notice.setVisible(False)
        self.b_load_playlist.setVisible(False)
        self.b_fetch_log.setVisible(False)
        if info is not None:
            self.sub_langs, self.sub_auto = default_selection(
                info, self.settings.sub_default_langs, self.settings.sub_default_auto)
            if info.kind == "playlist" and self.settings.sub_default_langs:
                self.sub_langs = [c.strip() for c in self.settings.sub_default_langs.split(",") if c.strip()]
                self.sub_auto = self.settings.sub_default_auto
        else:
            self.sub_langs, self.sub_auto = [], False
        self.tag_state = TagState.for_info(info, self.settings.audio_tags_default,
                                           self.settings.embed_thumbnail, self.settings.audio_tag_clean)
        self._update_tags_button()
        self._update_subs_button()
        if info is None:
            self.v_title.setText("주소를 넣고 [불러오기]를 누르면\n영상 정보가 여기에 보여요" if not error else "불러오지 못했어요")
            self.v_meta.setText("유튜브 영상·재생목록·쇼츠 주소를 지원해요. 창에 주소를 끌어다 놓아도 돼요.")
            if error:
                self.v_notice.setText(error)
                self.v_notice.setObjectName("Error")
                repolish(self.v_notice)
                self.v_notice.setVisible(True)
            self.b_download.setEnabled(False)
            self.b_download.setText("다운로드")
            self._fill_quality_combo()
            self._update_estimate()
            return

        self.v_title.setText(info.title)
        self.v_notice.setObjectName("Notice")
        repolish(self.v_notice)
        if info.kind == "playlist":
            n_ok = sum(1 for e in info.entries if e.available)
            bits = ["재생목록", f"영상 {len(info.entries)}개"]
            if info.uploader:
                bits.insert(1, info.uploader)
            self.v_meta.setText(" · ".join(bits))
            if info.nested_tabs:
                self.v_notice.setText("채널 주소예요. 채널의 '동영상' 탭 주소(…/videos)나 재생목록 주소를 넣어 주세요.")
                self.v_notice.setVisible(True)
            elif n_ok < len(info.entries):
                self.v_notice.setText(f"비공개·삭제된 영상 {len(info.entries) - n_ok}개는 건너뛰어요.")
                self.v_notice.setVisible(True)
            self.b_download.setText(f"재생목록에서 선택… ({n_ok})")
        else:
            bits = [b for b in (info.uploader, human_duration(info.duration)) if b]
            if info.heights:
                bits.append(f"최대 {height_label(info.heights[0])}")
            self.v_meta.setText(" · ".join(bits))
            if info.is_live:
                self.v_notice.setText("라이브 방송이나 예정된 최초 공개는 받을 수 없어요. 방송이 끝난 뒤 다시 시도해 주세요.")
                self.v_notice.setVisible(True)
            if has_playlist_param(self.info_url):
                self.b_load_playlist.setVisible(True)
            self.b_download.setText("다운로드")
        self.b_download.setEnabled(self._can_download(info))
        self._fill_quality_combo()
        self._update_estimate()
        if info.thumbnail:
            want = info.thumbnail

            def set_thumb(pm, want=want):
                if self.info is not None and self.info.thumbnail == want:
                    self.thumb.setText("")
                    self.thumb.setPixmap(rounded(pm, THUMB_SIZE, 10))

            self.thumbs.load(info.thumbnail, set_thumb)

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
        d = QFileDialog.getExistingDirectory(self, "저장 위치 선택", self.settings.download_dir)
        if d:
            self.settings.download_dir = d
            self.settings.save()
            self.dest_label.setText(d)
            self.dest_label.setToolTip(d)

    def _current_options(self) -> Optional[DownloadOptions]:
        if not self._validate_sections():
            QMessageBox.warning(self, "구간 형식", "구간은 1:30 또는 01:02:03 처럼 입력해 주세요.")
            return None
        start = parse_timecode(self.sec_start.text())
        end = parse_timecode(self.sec_end.text())
        if start is not None and end is not None and start >= end:
            QMessageBox.warning(self, "구간", "끝 시간이 시작 시간보다 뒤여야 해요.")
            return None
        info = self.info
        if info and info.kind == "video" and info.duration and start is not None and start >= info.duration:
            QMessageBox.warning(self, "구간", f"영상 길이({human_duration(info.duration)})보다 시작 시간이 뒤예요.")
            return None
        s = self.settings
        out_dir = self._ensure_dir()
        if not Path(out_dir).is_dir():
            QMessageBox.warning(self, "저장 위치", f"저장 폴더를 만들 수 없어요:\n{out_dir}")
            return None
        return DownloadOptions(
            mode=self.mode.value(),
            max_height=int(self.quality.currentData() or 0),
            container=s.container,
            compat_h264=self.cb_compat.isChecked(),
            audio_format=s.audio_format,
            audio_quality=s.audio_quality,
            sub_langs=",".join(self.sub_langs),
            auto_subs=self.sub_auto,
            sub_mode=s.sub_mode,
            overwrite=s.overwrite_existing,
            embed_thumbnail=self.tag_state.cover if self.mode.value() == "audio" else self.cb_thumb.isChecked(),
            audio_tags=self.tag_state.on,
            tag_values=dict(self.tag_state.values) if self.tag_state.values else None,
            tag_smart=self.tag_state.smart,
            embed_metadata=s.embed_metadata,
            output_dir=out_dir,
            filename_template=s.filename_template,
            cookies_browser=s.cookies_browser,
            rate_limit=s.rate_limit,
            section_start=start,
            section_end=end,
        )

    def add_download(self) -> None:
        info = self.info
        if info is None:
            return
        if not self.deps.ytdlp.ok:
            self._open_deps_dialog(intro="다운로드하려면 yt-dlp가 필요해요.")
            if not self.deps.ytdlp.ok:
                return
        missing = [m for m in self.deps.missing_required() if m != "yt-dlp"]
        if missing:
            r = QMessageBox.question(
                self, "도구 없음",
                f"{', '.join(missing)}이(가) 없어서 일부 형식이 실패하거나 화질이 낮을 수 있어요.\n지금 설치할까요?",
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
                self.queue.add(DownloadJob(entry.url, entry.title, o, entry.thumbnail or info.thumbnail))
            self.status_msg.setText(f"{len(chosen)}개를 다운로드 목록에 추가했어요")
        else:
            url = info.url or self.info_url
            dup = next((j for j in self.queue.jobs if j.url == url and j.is_active
                        and j.options.summary() == opts.summary()), None)
            if dup is not None:
                r = QMessageBox.question(self, "이미 목록에 있어요", "같은 설정으로 받는 중이에요. 한 번 더 추가할까요?")
                if r != QMessageBox.StandardButton.Yes:
                    return
            self.queue.add(DownloadJob(url, info.title, opts, info.thumbnail))
            self.status_msg.setText("다운로드 목록에 추가했어요")
        self.tabs.setCurrentIndex(0)
        if self.sec_start.text() or self.sec_end.text():
            self.sec_start.clear()
            self.sec_end.clear()

    def _redownload(self, url: str) -> None:
        if not url:
            return
        self.url_edit.setText(url)
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
        self.q_empty.setVisible(False)
        QTimer.singleShot(50, lambda: self.q_scroll.verticalScrollBar().setValue(
            self.q_scroll.verticalScrollBar().maximum()))

    def _on_job_removed(self, job: DownloadJob) -> None:
        w = self._item_widgets.pop(job.id, None)
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        self.q_empty.setVisible(not self._item_widgets)

    def _on_job_finished(self, job: DownloadJob) -> None:
        if job.state in (DONE, FAILED):
            summary = job.options.summary() + (" · 이미 있음" if job.skipped else "")
            self.history.add(title=job.title, url=job.url, filepath=job.filepath, summary=summary,
                             ok=job.state == DONE, error=job.error, thumbnail=job.thumbnail)
            self.history_view.reload()

    def _update_counts(self) -> None:
        c = self.queue.counts()
        active = c["running"] + c["queued"]
        parts = []
        if c["running"]:
            parts.append(f"진행 {c['running']}")
        if c["queued"]:
            parts.append(f"대기 {c['queued']}")
        if c["done"]:
            parts.append(f"완료 {c['done']}")
        if c["failed"]:
            parts.append(f"실패 {c['failed']}")
        if c["canceled"]:
            parts.append(f"취소 {c['canceled']}")
        self.q_status.setText(" · ".join(parts) if parts else "")
        self.tabs.setTabText(0, f"다운로드 ({active})" if active else "다운로드")
        title = APP_NAME
        if c["running"]:
            fr = [j.fraction for j in self.queue.jobs if j.state == "running" and j.fraction is not None]
            if fr:
                title = f"{int(sum(fr) / len(fr) * 100)}% · {active}개 진행 - {APP_NAME}"
            else:
                title = f"{active}개 진행 - {APP_NAME}"
        if self.windowTitle() != title:
            self.setWindowTitle(title)

    def _on_all_done(self, ok: int, fail: int) -> None:
        msg = f"다운로드가 끝났어요 · 성공 {ok}개" + (f", 실패 {fail}개" if fail else "")
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
        dlg = SubtitleDialog(info, selected, self.sub_auto, self.settings.sub_mode, audio, parent=self)
        accepted = dlg.exec()
        result = dlg.result_selection()
        dlg.deleteLater()
        if accepted:
            langs, auto, mode = result
            self.sub_langs, self.sub_auto = langs, auto
            if not audio:
                self.settings.sub_mode = mode
                self.settings.save()
            self._update_subs_button()

    def _choose_tags(self) -> None:
        dlg = TagDialog(self.info, self.tag_state, self)
        accepted = dlg.exec()
        result = dlg.result_state()
        dlg.deleteLater()
        if accepted:
            self.tag_state = result
            self._update_tags_button()
            self._update_collapsed_summary()

    def _update_tags_button(self) -> None:
        text = self.tag_state.button_text()
        self.b_tags.setText(text if len(text) <= 34 else text[:33] + "…")
        if self.tag_state.on and self.tag_state.values:
            v = self.tag_state.values
            self.b_tags.setToolTip("\n".join(f"{k}: {v.get(f, '')}" for f, k in
                                             (("title", "제목"), ("artist", "아티스트"), ("album", "앨범"), ("year", "연도"))))
        else:
            self.b_tags.setToolTip("음원 파일의 제목·아티스트·앨범·커버 태그를 넣을지, 어떤 값으로 넣을지 골라요")

    def _update_subs_button(self) -> None:
        audio = self.mode.value() == "audio"
        text = summarize(self.sub_langs, self.sub_auto, self.settings.sub_mode, audio)
        self.b_subs.setText(text)
        info = self.info
        if info is not None and info.kind == "video" and not info.subtitles and not info.auto_captions:
            self.b_subs.setText("자막: 이 영상엔 없음")
        self._update_collapsed_summary()

    def _set_collapsed(self, collapsed: bool, save: bool = True) -> None:
        self.settings.options_collapsed = collapsed
        self.options_box.setVisible(not collapsed)
        self.b_collapse.setText("옵션 펼치기 ▼" if collapsed else "옵션 접기 ▲")
        self._update_collapsed_summary()
        if save:
            self.settings.save()
            # 접으면 위쪽 칸을 내용 크기에 맞게 줄여서 목록을 넓힌다
            QTimer.singleShot(0, self._fit_top)

    def _fit_top(self) -> None:
        card = self.top_scroll.widget()
        want = card.sizeHint().height() + 4
        total = sum(self.splitter.sizes())
        if total < 400:
            return
        top = min(want, max(150, total - 200))
        self.splitter.setSizes([top, total - top])
        self._remember_splitter()

    def _update_collapsed_summary(self) -> None:
        if not hasattr(self, "options_box"):
            return
        if self.settings.options_collapsed and hasattr(self, "fmt"):
            try:
                o = self._options_preview()
                self.est_label.setToolTip(o)
                self._collapsed_text = o
            except Exception:  # noqa: BLE001
                self._collapsed_text = ""
        else:
            self._collapsed_text = ""
        self._update_estimate()

    def _options_preview(self) -> str:
        s = self.settings
        preview = DownloadOptions(
            mode=self.mode.value(), max_height=int(self.quality.currentData() or 0), container=s.container,
            compat_h264=self.cb_compat.isChecked(), audio_format=s.audio_format,
            audio_tags=self.tag_state.on, tag_values=self.tag_state.values, tag_smart=self.tag_state.smart,
            sub_langs=",".join(self.sub_langs), sub_mode=s.sub_mode)
        return preview.summary()

    def _remember_splitter(self) -> None:
        sizes = self.splitter.sizes()
        if len(sizes) == 2 and all(sizes):
            self.settings.splitter_sizes = f"{sizes[0]},{sizes[1]}"

    def _restore_splitter(self) -> None:
        try:
            a, b = (int(x) for x in self.settings.splitter_sizes.split(","))
            if a > 0 and b > 0:
                self.splitter.setSizes([a, b])
                return
        except ValueError:
            pass
        self._fit_top()

    def _schedule_save(self) -> None:
        if not self._closing and not self._save_timer.isActive():
            self._save_timer.start()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not getattr(self, "_shown_once", False):
            self._shown_once = True
            QTimer.singleShot(0, self._restore_splitter)

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
            self.status_msg.setText(f"지난번에 받던 {waiting}개를 이어서 받아요")

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
            self.fetch()
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.queue.has_active():
            box = QMessageBox(self)
            box.setWindowTitle("종료")
            box.setIcon(QMessageBox.Icon.Question)
            box.setText("받는 중이거나 대기 중인 다운로드가 있어요.\n지금 종료하면 다음에 켤 때 이어서 받아요.")
            b_quit = box.addButton("종료", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("계속 받기", QMessageBox.ButtonRole.RejectRole)
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
        self._remember_splitter()
        self.settings.save()
        if self.tray is not None:
            self.tray.hide()
        event.accept()
        QApplication.quit()
