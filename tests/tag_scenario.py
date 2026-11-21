"""음원 태그 시나리오: 화면에서 태그 편집/끄기/재생목록 자동 정리 후 실제 파일 태그 확인.

사용법: QT_QPA_PLATFORM=offscreen python tests/tag_scenario.py <서버 URL> <서버 폴더> <스크린샷 폴더>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

home = tempfile.mkdtemp(prefix="tubeget-tag-")
os.environ["TUBEGET_HOME"] = home
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
base, srv, shots = sys.argv[1].rstrip("/"), sys.argv[2], Path(sys.argv[3])
shots.mkdir(parents=True, exist_ok=True)
os.environ.update(FAKE_BASE=base, FAKE_SRV=srv, FAKE_INFO=str(Path(home) / "fake_info.json"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from tubegetapp.config import Settings  # noqa: E402
from tubegetapp.core.metadata import parse_info  # noqa: E402
from tubegetapp.paths import bin_dir  # noqa: E402
from tubegetapp.ui.theme import apply_theme  # noqa: E402

wr = bin_dir() / "yt-dlp"
wr.write_text(f'#!/bin/sh\nexec {sys.executable} {ROOT / "tests" / "fake_youtube.py"} "$@"\n')
wr.chmod(0o755)
out = Path(home) / "out"
s = Settings()
s.download_dir = str(out)
s.auto_update_ytdlp = False
s.mode = "audio"
s.filename_template = "%(title)s [%(id)s] %(autonumber)s.%(ext)s"
s.save()

from tubegetapp.ui.main_window import MainWindow  # noqa: E402

app = QApplication([])
apply_theme(app)
errors = []
w = MainWindow()
w.resize(960, 920)
w.show()


def check(cond, msg):
    print(("  ok  " if cond else "  FAIL") + " " + msg)
    if not cond:
        errors.append(msg)


def tags_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream=codec_type", "-of", "json", path],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    t = {k.lower(): v for k, v in (d.get("format", {}).get("tags") or {}).items()}
    t["_video_streams"] = sum(1 for st in d.get("streams", []) if st.get("codec_type") == "video")
    return t


def wait(cond, then, n=[0]):
    if cond() or n[0] > 600:
        n[0] = 0
        then()
        return
    n[0] += 1
    QTimer.singleShot(100, lambda: wait(cond, then, n))


def dialog_then(action):
    def handle():
        dlg = next((x for x in app.topLevelWidgets() if isinstance(x, QDialog) and x.isVisible()), None)
        if dlg is None:
            QTimer.singleShot(100, handle)
            return
        action(dlg)
    QTimer.singleShot(100, handle)


def start():
    if not w.deps_ready:
        QTimer.singleShot(100, start)
        return
    w.url_edit.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    w.fetch()
    wait(lambda: not w.fetcher.busy and w.info is not None, step_info)


def step_info():
    check(w.b_tags.isVisible() and w.l_tags.isVisible(), "음원 모드: 위쪽 바에 [태그] 보임")
    check(w.tag_state.values == {"title": "Way Less Sad", "artist": "AJR", "album": "", "year": ""},
          f"자동 정리 값 미리 채움 {w.tag_state.values}")
    check(w.b_tags.text().startswith("AJR"), "버튼 표시: " + w.b_tags.text())
    QTimer.singleShot(300, lambda: (w.grab().save(str(shots / "t01_audio_mode.png")), step_edit()))


def step_edit():
    if os.environ.get("STOP") == "0":
        app.quit(); return

    def edit(dlg):
        dlg.edits["album"].setText("OK ORCHESTRA")
        dlg.edits["year"].setText("2021")
        dlg.edits["title"].setText("Way Less Sad: 100% 진짜")
        dlg.grab().save(str(shots / "t02_tag_dialog.png"))
        dlg.accept()
    dialog_then(edit)
    w._choose_tags()
    w.add_download()
    job = w.queue.jobs[-1]
    wait(lambda: not job.is_active, lambda: step_edit_check(job))


def step_edit_check(job):
    if os.environ.get("STOP") == "1":
        app.quit(); return
    t = tags_of(job.filepath)
    check(job.state == "done", f"편집한 태그로 받기 완료 ({job.detail})")
    check(t.get("title") == "Way Less Sad: 100% 진짜" and t.get("artist") == "AJR"
          and t.get("album") == "OK ORCHESTRA" and t.get("date") == "2021", f"파일 태그 {t}")
    check(t["_video_streams"] == 1, "앨범 커버 들어감")
    # 태그 끄기
    def off(dlg):
        dlg.cb_on.setChecked(False)
        check(not dlg.body.isEnabled(), "끄면 나머지 항목 비활성")
        dlg.accept()
    dialog_then(off)
    w._choose_tags()
    w.settings.overwrite_existing = True   # 같은 이름 파일이 있으니 덮어쓰기
    check(w.b_tags.text() == "끔", "버튼 표시: " + w.b_tags.text())
    w.add_download()
    job2 = w.queue.jobs[-1]
    wait(lambda: not job2.is_active, lambda: step_off_check(job2))


def step_off_check(job):
    if os.environ.get("STOP") == "2":
        app.quit(); return
    t = tags_of(job.filepath)
    meaningful = {k: v for k, v in t.items() if k in ("title", "artist", "album", "date", "comment", "purl")}
    check(job.state == "done" and not meaningful and t["_video_streams"] == 0, f"태그 끔 → 태그·커버 없음 {t}")
    # 다른 영상을 불러오면 다시 기본값(켬)
    w._set_info(w.info)
    check(w.tag_state.on, "새 영상을 불러오면 기본값(켬)으로")
    # 재생목록: 자동 정리
    data = {"_type": "playlist", "id": "PL1", "title": "Mix", "entries": [
        {"_type": "url", "ie_key": "Youtube", "id": "a1", "url": "https://www.youtube.com/watch?v=a1",
         "title": "AJR - Way Less Sad (Official Video)"}]}
    w._set_info(parse_info(data))
    check(w.tag_state.smart and w.tag_state.values is None, "재생목록은 자동 정리 모드")
    check(w.b_tags.text() == "켬 (자동 정리)", "버튼 표시: " + w.b_tags.text())

    def pl(dlg):
        dlg.accept()
    dialog_then(pl)
    w.add_download()
    job3 = w.queue.jobs[-1]
    check(job3.options.tag_smart and not job3.options.tag_values, "재생목록 작업에 자동 정리 적용")
    wait(lambda: not job3.is_active, lambda: step_pl_check(job3))


def step_pl_check(job):
    t = tags_of(job.filepath)
    check(job.state == "done" and t.get("title") == "Way Less Sad" and t.get("artist") == "AJR",
          f"재생목록 자동 정리 태그 {t.get('artist')} / {t.get('title')}")
    w.grab().save(str(shots / "t03_queue.png"))
    print("\nERRORS:", errors or "없음")
    app.quit()


QTimer.singleShot(200, start)
QTimer.singleShot(200_000, app.quit)
app.exec()
w.hide()
w.deleteLater()
app.processEvents()
sys.exit(1 if errors else 0)
