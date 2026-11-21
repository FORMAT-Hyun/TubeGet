"""다운로드 기록 탭."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ..core.history import History
from ..utils import reveal_in_explorer
from .widgets import make_button
from ..i18n import tr


class HistoryView(QWidget):
    redownloadRequested = Signal(str)  # url

    def __init__(self, history: History, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.history = history
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)

        top = QHBoxLayout()
        self.count = QLabel()
        self.count.setObjectName("Muted")
        top.addWidget(self.count)
        top.addStretch(1)
        clear = make_button(tr("기록 모두 지우기"), ghost=True)
        clear.clicked.connect(self._clear)
        top.addWidget(clear)
        lay.addLayout(top)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("제목"), tr("형식"), tr("결과"), tr("날짜")])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        h = self.tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemDoubleClicked.connect(lambda item, _c: self._open(item))
        self.tree.customContextMenuRequested.connect(self._menu)
        lay.addWidget(self.tree, 1)
        self.reload()

    def reload(self) -> None:
        self.tree.clear()
        for rec in self.history.items:
            try:
                when = datetime.fromisoformat(rec.get("time", "")).strftime("%m-%d %H:%M")
            except ValueError:
                when = ""
            item = QTreeWidgetItem([rec.get("title", ""), rec.get("summary", ""),
                                    tr("완료") if rec.get("ok") else tr("실패"), when])
            item.setData(0, Qt.ItemDataRole.UserRole, rec)
            item.setToolTip(0, rec.get("filepath") or rec.get("error") or rec.get("url", ""))
            if not rec.get("ok"):
                item.setForeground(2, QColor("#ff6b6b"))
                item.setToolTip(2, rec.get("error", ""))
            self.tree.addTopLevelItem(item)
        self.count.setText(tr("최근 기록 {len}개 · 두 번 클릭하면 파일이 열려요").format(len=len(self.history.items)))

    def add(self, rec: dict) -> None:
        self.reload()

    def _rec(self, item: Optional[QTreeWidgetItem]) -> Optional[dict]:
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def _open(self, item: QTreeWidgetItem) -> None:
        rec = self._rec(item)
        if not rec:
            return
        path = rec.get("filepath")
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif rec.get("ok"):
            QMessageBox.information(self, tr("파일 없음"), tr("파일이 옮겨졌거나 삭제됐어요."))

    def _menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        rec = self._rec(item)
        if not rec:
            return
        m = QMenu(self)
        path = rec.get("filepath")
        exists = bool(path) and os.path.exists(path)
        a_open = m.addAction(tr("파일 열기"))
        a_open.setEnabled(exists)
        a_reveal = m.addAction(tr("폴더에서 보기"))
        a_reveal.setEnabled(exists)
        m.addSeparator()
        a_again = m.addAction(tr("다시 받기"))
        a_copy = m.addAction(tr("주소 복사"))
        m.addSeparator()
        a_del = m.addAction(tr("기록에서 지우기"))
        act = m.exec(self.tree.viewport().mapToGlobal(pos))
        if act is a_open:
            self._open(item)
        elif act is a_reveal:
            reveal_in_explorer(path)
        elif act is a_again:
            self.redownloadRequested.emit(rec.get("url", ""))
        elif act is a_copy:
            QGuiApplication.clipboard().setText(rec.get("url", ""))
        elif act is a_del:
            self.history.remove(rec)
            self.reload()

    def _clear(self) -> None:
        if not self.history.items:
            return
        if QMessageBox.question(self, tr("기록 지우기"), tr("다운로드 기록을 모두 지울까요? (파일은 지워지지 않아요)")) \
                == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.reload()
