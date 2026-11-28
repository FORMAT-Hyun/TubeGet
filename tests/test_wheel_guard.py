"""마우스 휠로 드롭다운·숫자 칸 값이 바뀌지 않고, 화면만 스크롤되는지 확인."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TUBEGET_LANG", "ko")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import (QApplication, QComboBox, QScrollArea, QSpinBox, QVBoxLayout,  # noqa: E402
                               QWidget)

from tubegetapp.ui.wheel_guard import install  # noqa: E402

app = QApplication.instance() or QApplication([])
install(app)


def _wheel(w: QWidget, dy: int = -120) -> None:
    pos = QPointF(w.width() / 2, w.height() / 2)
    ev = QWheelEvent(pos, QPointF(w.mapToGlobal(pos.toPoint())), QPoint(0, 0), QPoint(0, dy),
                     Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(w, ev)


def test_wheel_does_not_change_values_but_scrolls():
    area = QScrollArea()
    inner = QWidget()
    lay = QVBoxLayout(inner)
    combo = QComboBox()
    combo.addItems(["a", "b", "c"])
    spin = QSpinBox()
    spin.setRange(1, 10)
    spin.setValue(3)
    lay.addWidget(combo)
    lay.addWidget(spin)
    inner.setMinimumHeight(2000)
    area.setWidget(inner)
    area.resize(300, 200)
    area.show()
    app.processEvents()

    bar = area.verticalScrollBar()
    assert bar.value() == 0
    _wheel(combo)
    _wheel(spin)
    app.processEvents()
    assert combo.currentIndex() == 0
    assert spin.value() == 3
    assert bar.value() > 0  # 값 대신 화면이 내려감
    area.close()


def test_combo_outside_scroll_area_unchanged():
    combo = QComboBox()
    combo.addItems(["a", "b"])
    combo.show()
    app.processEvents()
    _wheel(combo)
    assert combo.currentIndex() == 0
    combo.close()


def test_about_has_github_link():
    from tubegetapp.ui.about_dialog import REPO_URL, AboutDialog, report_text
    dlg = AboutDialog(None)
    assert REPO_URL == "https://github.com/FORMAT-Hyun/Acortube"
    assert REPO_URL in dlg.repo_link.text() and dlg.repo_link.openExternalLinks()
    assert REPO_URL in report_text(None)
    dlg.close()
