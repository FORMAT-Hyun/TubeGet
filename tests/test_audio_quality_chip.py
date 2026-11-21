"""음원일 때 툴바의 화질 칸이 '음질'로 바뀌고, 설정 창에서는 음질이 빠졌는지 확인."""
import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TUBEGET_LANG", "ko")
os.environ["TUBEGET_HOME"] = tempfile.mkdtemp(prefix="tubeget-aq-")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from tubegetapp.config import Settings  # noqa: E402

_s = Settings()
_s.auto_update_ytdlp = False
_s.clipboard_autofetch = False
_s.mode = "video"
_s.max_height = 1080
_s.audio_format = "mp3"
_s.audio_quality = "0"
_s.save()

from tubegetapp.ui.main_window import MainWindow  # noqa: E402
from tubegetapp.ui.settings_dialog import SettingsDialog  # noqa: E402


def test_quality_chip_becomes_audio_quality():
    w = MainWindow()
    try:
        assert w.l_quality.text() == "화질"
        w.mode.setValue("audio")
        w._on_mode_changed("audio")
        assert w.l_quality.text() == "음질"
        assert w.quality.isVisible() or not w.isVisible()
        assert [w.quality.itemData(i) for i in range(w.quality.count())] == ["0", "320K", "192K", "128K"]

        w.quality.setCurrentIndex(w.quality.findData("320K"))
        assert w.settings.audio_quality == "320K"
        assert w.settings.max_height == 1080            # 영상 화질은 그대로
        assert w._current_options().audio_quality == "320K"
        assert w._current_options().max_height == 1080

        w.fmt.setCurrentIndex(w.fmt.findData("flac"))   # 무손실은 음질 칸을 끈다
        assert not w.quality.isEnabled()
        w.fmt.setCurrentIndex(w.fmt.findData("mp3"))
        assert w.quality.isEnabled() and w.quality.currentData() == "320K"

        w.mode.setValue("video")
        w._on_mode_changed("video")
        assert w.l_quality.text() == "화질" and w.quality.currentData() == 1080
    finally:
        w.close()
        w.deleteLater()


def test_settings_dialog_has_no_audio_quality():
    d = SettingsDialog(Settings())
    assert not hasattr(d, "audio_q")
    d.close()
