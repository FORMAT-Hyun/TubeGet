"""재생목록에서 받을 영상 고르기."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QVBoxLayout, QWidget)

from ..core.metadata import Entry, MediaInfo
from ..utils import human_duration
from .widgets import make_button


def _parse_ranges(text: str, n: int) -> Optional[set[int]]:
    """'1-5, 8, 10-' → {1..5, 8, 10..n}. 잘못되면 None."""
    picked: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                start = int(a) if a else 1
                end = int(b) if b else n
            except ValueError:
                return None
            if start > end:
                start, end = end, start
            picked.update(range(max(1, start), min(n, end) + 1))
        else:
            try:
                k = int(part)
            except ValueError:
                return None
            if 1 <= k <= n:
                picked.add(k)
    return picked


class PlaylistDialog(QDialog):
    def __init__(self, info: MediaInfo, make_folder: bool, numbering: bool,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("재생목록에서 선택")
        self.resize(640, 560)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        head = QLabel(f"<b>{_esc(info.title)}</b>")
        head.setWordWrap(True)
        lay.addWidget(head)
        self.count_label = QLabel()
        self.count_label.setObjectName("Muted")
        lay.addWidget(self.count_label)

        tools = QHBoxLayout()
        b_all = make_button("전체 선택", ghost=True)
        b_none = make_button("전체 해제", ghost=True)
        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText("범위 선택 (예: 1-10, 15, 20-)")
        b_range = make_button("범위 적용")
        tools.addWidget(b_all)
        tools.addWidget(b_none)
        tools.addStretch(1)
        tools.addWidget(self.range_edit, 1)
        tools.addWidget(b_range)
        lay.addLayout(tools)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        width = len(str(len(info.entries)))
        for i, e in enumerate(info.entries, start=1):
            dur = human_duration(e.duration)
            text = f"{i:0{width}d}.  {e.title}" + (f"   ({dur})" if dur else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            if e.available:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setText(text + "   — 볼 수 없음")
            self.list.addItem(item)
        lay.addWidget(self.list, 1)

        self.cb_folder = QCheckBox("재생목록 이름으로 폴더 만들기")
        self.cb_folder.setChecked(make_folder)
        self.cb_number = QCheckBox("파일 이름 앞에 재생목록 번호 붙이기")
        self.cb_number.setChecked(numbering)
        lay.addWidget(self.cb_folder)
        lay.addWidget(self.cb_number)

        self.box = QDialogButtonBox()
        self.ok_btn = make_button("선택한 영상 받기", primary=True)
        self.box.addButton(self.ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        self.box.addButton("취소", QDialogButtonBox.ButtonRole.RejectRole)
        self.box.accepted.connect(self.accept)
        self.box.rejected.connect(self.reject)
        lay.addWidget(self.box)

        b_all.clicked.connect(lambda: self._set_all(True))
        b_none.clicked.connect(lambda: self._set_all(False))
        b_range.clicked.connect(self._apply_range)
        self.range_edit.returnPressed.connect(self._apply_range)
        self.list.itemChanged.connect(self._update_count)
        self._update_count()

    def _items(self):
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                yield item

    def _set_all(self, on: bool) -> None:
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for item in self._items():
            item.setCheckState(state)

    def _apply_range(self) -> None:
        picked = _parse_ranges(self.range_edit.text(), len(self.info.entries))
        if picked is None:
            self.range_edit.setStyleSheet("border-color: #d33a3a;")
            return
        self.range_edit.setStyleSheet("")
        for item in self._items():
            idx = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(Qt.CheckState.Checked if idx in picked else Qt.CheckState.Unchecked)

    def _update_count(self, *_):
        n = sum(1 for it in self._items() if it.checkState() == Qt.CheckState.Checked)
        total = len(self.info.entries)
        self.count_label.setText(f"전체 {total}개 중 {n}개 선택")
        self.ok_btn.setEnabled(n > 0)
        self.ok_btn.setText(f"선택한 {n}개 받기" if n else "선택한 영상 받기")

    def selected(self) -> list[tuple[int, Entry]]:
        out = []
        for item in self._items():
            if item.checkState() == Qt.CheckState.Checked:
                idx = item.data(Qt.ItemDataRole.UserRole)
                out.append((idx, self.info.entries[idx - 1]))
        return out


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
