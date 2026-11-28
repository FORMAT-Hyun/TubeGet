"""오프스크린 GUI 스모크 테스트: 창을 띄워 실제 흐름을 돌리고 스크린샷 저장.

사용법: QT_QPA_PLATFORM=offscreen python tests/gui_smoke.py <서버 URL> <스크린샷 폴더>
"""
import os
import sys
import tempfile
from pathlib import Path

home = tempfile.mkdtemp(prefix="acortube-gui-")
os.environ["TUBEGET_HOME"] = home
os.environ.setdefault("TUBEGET_LANG", "ko")   # 화면 글 비교는 한국어 기준
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from tubegetapp.config import Settings  # noqa: E402
from tubegetapp.core.metadata import parse_info  # noqa: E402
from tubegetapp.paths import bin_dir  # noqa: E402
from tubegetapp.ui.theme import apply_theme  # noqa: E402

base = sys.argv[1].rstrip("/")
shots = Path(sys.argv[2])
shots.mkdir(parents=True, exist_ok=True)

wrapper = bin_dir() / "yt-dlp"
wrapper.write_text(f'#!/bin/sh\nexec {sys.executable} -m yt_dlp "$@"\n')
wrapper.chmod(0o755)
s = Settings()
s.download_dir = str(Path(home) / "out")
s.auto_update_ytdlp = False
s.clipboard_autofetch = False
s.save()

from tubegetapp.ui.main_window import MainWindow  # noqa: E402

app = QApplication([])
apply_theme(app)
w = MainWindow()
w.resize(940, 860)
w.show()
errors = []


def shot(name):
    w.grab().save(str(shots / f"{name}.png"))
    print("shot", name)


def step1():
    if not w.deps_ready:
        QTimer.singleShot(200, step1)
        return
    print("deps:", w.deps_btn.text())
    shot("01_empty")
    w.url_edit.setText(f"{base}/dash.mpd")
    w.fetch()
    wait_info()


def wait_info(n=[0]):
    n[0] += 1
    if w.fetcher.busy and n[0] < 100:
        QTimer.singleShot(200, wait_info)
        return
    print("info:", w.info and (w.info.kind, w.info.title), "| download enabled:", w._sel is not None and w._sel.b_download.isEnabled())
    if not w.info:
        errors.append("info not loaded: " + w.v_notice.text())
    # 실제 유튜브처럼 보이게 가짜 메타데이터로 화질 목록도 확인
    w.info.heights = [2160, 1440, 1080, 720, 480, 360]
    w.info.size_by_height = {2160: 812_000_000, 1440: 401_000_000, 1080: 120_000_000, 720: 61_000_000,
                             480: 30_000_000, 360: 18_000_000}
    w.info.audio_size = 4_100_000
    w.info.uploader = "Test Channel"
    w.info.duration = 245
    w._set_info(w.info)
    shot("02_info")
    w.add_download()
    # 음원도 하나
    w.mode.setValue("audio")
    w._on_mode_changed("audio")
    w.add_download()
    w.mode.setValue("video")
    w._on_mode_changed("video")
    QTimer.singleShot(400, lambda: shot("03_downloading"))
    wait_done()


def wait_done(n=[0]):
    n[0] += 1
    if w.queue.has_active() and n[0] < 300:
        QTimer.singleShot(200, wait_done)
        return
    for j in w.queue.jobs:
        print("job:", j.state, j.filepath, j.error)
        if j.state != "done":
            errors.append(f"job failed: {j.error}")
    shot("04_done")
    playlist_step()


def playlist_step():
    data = {"_type": "playlist", "id": "PLx", "title": "AJR 플레이리스트 테스트", "uploader": "Someone",
            "entries": [{"_type": "url", "ie_key": "Youtube", "id": f"id{i:02d}", "title": t,
                         "url": f"{base}/dash.mpd" if i < 3 else f"https://www.youtube.com/watch?v=id{i:02d}",
                         "duration": 150 + i * 7}
                        for i, t in enumerate(["Bang!", "Way Less Sad", "World's Smallest Violin", "[Private video]",
                                               "Weak", "Sober Up", "100 Bad Days"], start=1)]}
    w.info_url = "https://www.youtube.com/playlist?list=PLx"
    w._set_info(parse_info(data))
    shot("05_playlist_info")

    def handle_dialog():
        dlg = next((x for x in app.topLevelWidgets() if isinstance(x, QDialog) and x.isVisible()), None)
        if dlg is None:
            QTimer.singleShot(100, handle_dialog)
            return
        dlg.range_edit.setText("1-2")
        dlg._apply_range()
        dlg.grab().save(str(shots / "06_playlist_dialog.png"))
        print("dialog selected:", [e.title for _, e in dlg.selected()])
        dlg.accept()

    QTimer.singleShot(100, handle_dialog)
    w.add_download()
    wait_playlist()


def wait_playlist(n=[0]):
    n[0] += 1
    if w.queue.has_active() and n[0] < 300:
        QTimer.singleShot(200, wait_playlist)
        return
    for j in w.queue.jobs[2:]:
        print("pl job:", j.state, j.filepath)
        if j.state != "done":
            errors.append(f"playlist job failed: {j.error}")
    shot("07_playlist_done")
    w._set_filter("history")
    QTimer.singleShot(200, lambda: (shot("08_history"), settings_shot()))


def settings_shot():
    from tubegetapp.ui.settings_dialog import SettingsDialog
    d = SettingsDialog(w.settings, w)
    d.show()
    QTimer.singleShot(200, lambda: (d.grab().save(str(shots / "09_settings.png")), d.close(), deps_shot()))


def deps_shot():
    from tubegetapp.ui.deps_dialog import DepsDialog
    d = DepsDialog(w.deps, w)
    d.show()
    QTimer.singleShot(200, lambda: (d.grab().save(str(shots / "10_deps.png")), d.close(), finish()))


def finish():
    w._set_filter("all")
    w.url_edit.setText("not a url")
    w.fetch()
    print("bad url notice:", w.v_notice.text())
    shot("11_bad_url")
    print("ERRORS:", errors or "none")
    for f in sorted((Path(home) / "out").rglob("*")):
        if f.is_file():
            print("  file:", f.relative_to(Path(home) / "out"), f.stat().st_size)
    w.queue.jobs.clear()
    app.quit()


QTimer.singleShot(300, step1)
QTimer.singleShot(180_000, app.quit)
app.exec()
