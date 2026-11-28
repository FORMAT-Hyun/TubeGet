"""구독 탭: 구독 목록, 추가, 지금 확인, 구독 취소. 그리고 구독 추가 창."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QRadioButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ..core.options import DownloadOptions
from ..core.subscriptions import (INITIAL_ALL, INITIAL_FUTURE, INITIAL_RECENT, RECENT_COUNT, Subscription,
                                  SubscriptionChecker, SubscriptionStore, classify_url)
from ..utils import reveal_in_explorer, sanitize_filename
from .widgets import make_button
from ..i18n import tr

_COL_NAME, _COL_SET, _COL_LAST, _COL_STATE = range(4)


def _ago(iso: str) -> str:
    if not iso:
        return tr("아직 안 함")
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    mins = int((datetime.now() - dt).total_seconds() // 60)
    if mins < 1:
        return tr("방금")
    if mins < 60:
        return tr("{n}분 전").format(n=mins)
    if mins < 60 * 24:
        return tr("{n}시간 전").format(n=mins // 60)
    return dt.strftime("%m-%d %H:%M")


def options_summary(sub: Subscription) -> str:
    try:
        return DownloadOptions.from_dict(sub.options).summary()
    except Exception:  # noqa: BLE001
        return ""


class SubscribeDialog(QDialog):
    """구독 추가: 처음에 무엇을 받을지, 쇼츠·라이브 제외, 저장 폴더."""

    def __init__(self, url: str, kind: str, title: str, summary: str, base_dir: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("구독하기"))
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        head = QLabel(title or url)
        head.setObjectName("VideoTitle")
        head.setWordWrap(True)
        lay.addWidget(head)
        kind_text = tr("채널") if kind == "channel" else tr("재생목록")
        sub = QLabel(f"{kind_text} · {url}")
        sub.setObjectName("Muted")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addWidget(QLabel(tr("처음 구독할 때")))
        self.group = QButtonGroup(self)
        self.r_future = QRadioButton(tr("지금 있는 영상은 건너뛰고, 앞으로 올라오는 영상만 받기"))
        self.r_recent = QRadioButton(tr("최근 영상 {n}개도 받기").format(n=RECENT_COUNT))
        self.r_all = QRadioButton(tr("지금 있는 영상도 모두 받기"))
        if kind == "channel":
            self.r_all.setText(tr("최근 영상 30개까지 모두 받기"))
        for i, r in enumerate((self.r_future, self.r_recent, self.r_all)):
            self.group.addButton(r, i)
            lay.addWidget(r)
        self.r_future.setChecked(True)

        self.cb_shorts = QCheckBox(tr("쇼츠 제외"))
        self.cb_shorts.setChecked(True)
        self.cb_live = QCheckBox(tr("지난 라이브 방송 제외"))
        self.cb_live.setChecked(True)
        row = QHBoxLayout()
        row.addWidget(self.cb_shorts)
        row.addWidget(self.cb_live)
        row.addStretch(1)
        lay.addLayout(row)

        form = QFormLayout()
        self.folder = QLineEdit(title)
        self.folder.setPlaceholderText(tr("비우면 채널·재생목록 이름"))
        form.addRow(tr("저장 폴더"), self.folder)
        lay.addLayout(form)
        where = QLabel(tr("{base} 안의 이 폴더에 받아요.").format(base=base_dir))
        where.setObjectName("Small")
        where.setWordWrap(True)
        lay.addWidget(where)
        how = QLabel(tr("받을 설정: {summary} (지금 위쪽 툴바에서 고른 설정)").format(summary=summary))
        how.setObjectName("Small")
        how.setWordWrap(True)
        lay.addWidget(how)

        box = QDialogButtonBox()
        ok = make_button(tr("구독하기"), primary=True)
        box.addButton(ok, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addButton(tr("취소"), QDialogButtonBox.ButtonRole.RejectRole)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def initial(self) -> str:
        return {0: INITIAL_FUTURE, 1: INITIAL_RECENT, 2: INITIAL_ALL}.get(self.group.checkedId(), INITIAL_FUTURE)


class SubscriptionsView(QWidget):
    """구독 탭. 추가는 addRequested 로 메인 창에 맡긴다 (지금 툴바 설정이 필요해서)."""

    addRequested = Signal(str)         # 주소
    resetOptionsRequested = Signal(str)  # 구독 id: 지금 툴바 설정으로 바꾸기

    def __init__(self, store: SubscriptionStore, checker: SubscriptionChecker, base_dir_provider,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.store = store
        self.checker = checker
        self._base_dir = base_dir_provider
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        add_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(tr("구독할 채널 또는 재생목록 주소 (예: https://www.youtube.com/@채널이름)"))
        self.url_edit.returnPressed.connect(self._add)
        add_row.addWidget(self.url_edit, 1)
        b_add = make_button(tr("구독 추가"), primary=True)
        b_add.clicked.connect(self._add)
        add_row.addWidget(b_add)
        lay.addLayout(add_row)

        top = QHBoxLayout()
        self.info = QLabel()
        self.info.setObjectName("Muted")
        top.addWidget(self.info, 1)
        self.b_check = make_button(tr("모두 지금 확인"), ghost=True)
        self.b_check.clicked.connect(self.checker.check_enabled)
        top.addWidget(self.b_check)
        lay.addLayout(top)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("이름"), tr("받을 설정"), tr("마지막 확인"), tr("상태")])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        h = self.tree.header()
        h.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        for c in (_COL_SET, _COL_LAST, _COL_STATE):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemDoubleClicked.connect(lambda item, _c: self._open_folder(self._sub(item)))
        self.tree.customContextMenuRequested.connect(self._menu)
        lay.addWidget(self.tree, 1)

        self.empty = QLabel(tr("아직 구독한 채널이나 재생목록이 없어요.\n"
                               "위에 주소를 넣거나, 재생목록·채널을 불러온 카드에서 [구독하기]를 누르세요.\n"
                               "새 영상이 올라오면 정해 둔 설정으로 자동으로 받아요."))
        self.empty.setObjectName("Empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.empty)

        checker.checked.connect(lambda *_: self.reload())
        checker.started.connect(self.reload)
        checker.finished.connect(self.reload)
        self.reload()

    # ------------------------------------------------------------------
    def reload(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        for s in self.store.items:
            item = QTreeWidgetItem([s.display_title(), options_summary(s), _ago(s.last_checked), self._state(s)])
            item.setData(_COL_NAME, Qt.ItemDataRole.UserRole, s.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(_COL_NAME, Qt.CheckState.Checked if s.enabled else Qt.CheckState.Unchecked)
            item.setToolTip(_COL_NAME, s.url)
            if s.last_error:
                item.setForeground(_COL_STATE, QColor("#ff6b6b"))
                item.setToolTip(_COL_STATE, s.last_error)
            self.tree.addTopLevelItem(item)
        self.tree.blockSignals(False)
        has = bool(self.store.items)
        self.tree.setVisible(has)
        self.empty.setVisible(not has)
        on = sum(1 for s in self.store.items if s.enabled)
        text = tr("구독 {n}개 (켜짐 {on}개) · 체크를 끄면 확인하지 않아요").format(n=len(self.store.items), on=on)
        if self.checker.busy:
            text = tr("확인하는 중…") + "  " + text
        self.info.setText(text)
        self.b_check.setEnabled(on > 0 and not self.checker.busy)

    def _state(self, s: Subscription) -> str:
        if self.checker.is_checking(s.id):
            return tr("확인 중…")
        if not s.enabled:
            return tr("꺼짐")
        if s.last_error:
            return tr("오류")
        if not s.last_checked:
            return tr("확인 대기")
        if s.last_new:
            return tr("새 영상 {n}개").format(n=s.last_new)
        return tr("새 영상 없음")

    def _sub(self, item: Optional[QTreeWidgetItem]) -> Optional[Subscription]:
        if item is None:
            return None
        return self.store.get(item.data(_COL_NAME, Qt.ItemDataRole.UserRole))

    def _on_item_changed(self, item: QTreeWidgetItem, col: int) -> None:
        s = self._sub(item)
        if s is None or col != _COL_NAME:
            return
        s.enabled = item.checkState(_COL_NAME) == Qt.CheckState.Checked
        self.store.save()
        self.reload()

    def _add(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        kind, _norm = classify_url(url)
        if kind is None:
            QMessageBox.information(self, tr("구독할 수 없는 주소"),
                                    tr("유튜브 채널(@이름) 또는 재생목록(list=) 주소만 구독할 수 있어요."))
            return
        self.url_edit.clear()
        self.addRequested.emit(url)

    def folder_of(self, s: Subscription) -> Path:
        return Path(self._base_dir()) / sanitize_filename(s.folder or s.title or "")

    def _open_folder(self, s: Optional[Subscription]) -> None:
        if s is None:
            return
        path = self.folder_of(s)
        reveal_in_explorer(str(path if path.exists() else path.parent))

    def _menu(self, pos: QPoint) -> None:
        s = self._sub(self.tree.itemAt(pos))
        if s is None:
            return
        m = QMenu(self)
        a_check = m.addAction(tr("지금 확인"))
        a_check.setEnabled(not self.checker.is_checking(s.id))
        a_folder = m.addAction(tr("저장 폴더 열기"))
        a_reset = m.addAction(tr("지금 툴바 설정으로 바꾸기"))
        a_copy = m.addAction(tr("주소 복사"))
        m.addSeparator()
        a_del = m.addAction(tr("구독 취소"))
        act = m.exec(self.tree.viewport().mapToGlobal(pos))
        if act is a_check:
            self.checker.check([s])
        elif act is a_folder:
            self._open_folder(s)
        elif act is a_reset:
            self.resetOptionsRequested.emit(s.id)
        elif act is a_copy:
            QGuiApplication.clipboard().setText(s.url)
        elif act is a_del:
            if QMessageBox.question(self, tr("구독 취소"),
                                    tr("'{title}' 구독을 취소할까요? 이미 받은 파일은 지워지지 않아요.")
                                    .format(title=s.display_title())) == QMessageBox.StandardButton.Yes:
                self.store.remove(s.id)
                self.reload()
