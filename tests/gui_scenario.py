"""유튜브 흉내 대역(fake_youtube.py)으로 전체 시나리오를 화면에서 검증.

사용법: QT_QPA_PLATFORM=offscreen python tests/gui_scenario.py <서버 URL> <서버 폴더> <스크린샷 폴더>
"""
import os
import sys
import tempfile
import time
from pathlib import Path

home = tempfile.mkdtemp(prefix="tubeget-sc-")
os.environ["TUBEGET_HOME"] = home
os.environ.setdefault("TUBEGET_LANG", "ko")   # 화면 글 비교는 한국어 기준
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
base, srv, shots = sys.argv[1].rstrip("/"), sys.argv[2], Path(sys.argv[3])
shots.mkdir(parents=True, exist_ok=True)
os.environ.update(FAKE_BASE=base, FAKE_SRV=srv, FAKE_INFO=str(Path(home) / "fake_info.json"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from tubegetapp.config import Settings  # noqa: E402
from tubegetapp.paths import bin_dir  # noqa: E402
from tubegetapp.single_instance import InstanceServer, notify_running_instance  # noqa: E402
from tubegetapp.ui.theme import apply_theme  # noqa: E402

w_ = bin_dir() / "yt-dlp"
w_.write_text(f'#!/bin/sh\nexec {sys.executable} {ROOT / "tests" / "fake_youtube.py"} "$@"\n')
w_.chmod(0o755)
out = Path(home) / "out"
s = Settings()
s.download_dir = str(out)
s.auto_update_ytdlp = True
s.last_update_check = time.strftime("%Y-%m-%dT%H:%M:%S")   # 오늘 이미 확인함 → 업데이트 건너뛰어야 함
s.rate_limit = "300K"
s.sub_default_langs = "ko"
s.save()

from tubegetapp.ui.main_window import MainWindow  # noqa: E402

app = QApplication([])
apply_theme(app)
results, errors = {}, []


def check(cond, msg):
    print(("  ok  " if cond else "  FAIL") + " " + msg)
    if not cond:
        errors.append(msg)


# --- 단일 실행 -------------------------------------------------------------
check(notify_running_instance() is False, "실행 중인 프로그램이 없으면 False")
server = InstanceServer(app)
check(notify_running_instance() is True, "이미 실행 중이면 True (두 번째 실행 차단)")

w = MainWindow()
w.resize(960, 920)
w.show()


def shot(name, widget=None):
    (widget or w).grab().save(str(shots / f"{name}.png"))


def wait(cond, then, n=[0], limit=600):
    if cond() or n[0] > limit:
        n[0] = 0
        then()
        return
    n[0] += 1
    QTimer.singleShot(100, lambda: wait(cond, then, n, limit))


def step_fetch():
    check(w._updater is None, "하루 안에 확인했으면 yt-dlp 자동 업데이트 생략")
    w.url_edit.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    w.fetch()
    wait(lambda: not w.fetcher.busy and w.info is not None, step_info)


def step_info():
    info = w.info
    check(info.heights == [2160, 1440, 1080, 720, 480, 360, 240, 144], f"화질 목록 {info.heights}")
    check(set(info.subtitles) == {"en", "ko"}, "올린 자막 en, ko (live_chat 제외)")
    check(len(info.auto_captions) == 13, f"자동 자막 {len(info.auto_captions)}개")
    check(w.sub_langs == ["ko"], f"설정 기본 언어(ko) 미리 선택됨: {w.sub_langs}")
    check(w.b_subs.text().startswith("한국어") and w.b_subs.isVisible(), "자막 버튼 표시: " + w.b_subs.text())
    qtexts = [w.quality.itemText(i) for i in range(w.quality.count())]
    print("     화질 항목:", qtexts[:4], "…")
    w.quality.setCurrentIndex(w.quality.findData(1080))
    w.settings.compat_h264 = True
    QTimer.singleShot(400, lambda: (shot("s01_info"), step_subs()))   # 썸네일 로딩 대기


def step_subs():
    def handle():
        dlg = next((x for x in app.topLevelWidgets() if isinstance(x, QDialog) and x.isVisible()), None)
        if dlg is None:
            QTimer.singleShot(100, handle)
            return
        # 자동 자막에서 일본어 추가, 저장 방식 '둘 다'
        for i in range(dlg.auto_list.count()):
            it = dlg.auto_list.item(i)
            if it.data(256) == "ja":
                it.setCheckState(it.checkState().Checked)
        order = [dlg.auto_list.item(i).data(256) for i in range(dlg.auto_list.count())]
        check(order[0] == "en-orig" and "en" not in order and "ko" not in order,
              f"자동 자막 정렬(원본 먼저, 올린 자막과 중복 제외): {order[:4]}")
        dlg.mode_buttons["both"].setChecked(True)
        shot("s02_subtitle_dialog", dlg)
        dlg.accept()

    QTimer.singleShot(100, handle)
    w._choose_subs()
    check(w.sub_langs == ["ko", "ja"] and w.sub_auto, f"선택 결과 {w.sub_langs}, auto={w.sub_auto}")
    check(w.settings.sub_mode == "both", "저장 방식 기억")
    step_download()


fractions = []


def step_download():
    w.add_download()
    job = w.queue.jobs[-1]
    results["job1"] = job
    job.changed.connect(lambda: job.fraction is not None and fractions.append(round(job.fraction, 3)))
    QTimer.singleShot(1500, lambda: shot("s03_downloading"))
    wait(lambda: not job.is_active, step_after_download)


def step_after_download():
    job = results["job1"]
    check(job.state == "done" and not job.skipped, f"다운로드 완료 ({job.detail})")
    mono = all(b >= a - 1e-9 for a, b in zip(fractions, fractions[1:]))
    check(mono and len(fractions) > 5, f"전체 진행률이 되돌아가지 않음 ({len(fractions)}번 갱신, 마지막 {fractions[-3:]})")
    files = sorted(p.name for p in out.iterdir())
    print("     파일:", files)
    check(any(f.endswith(".ko.srt") for f in files) and any(f.endswith(".ja.srt") for f in files), "자막 .srt 파일 저장")
    import subprocess
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "s", "-show_entries", "stream_tags=language",
                            "-of", "csv=p=0", job.filepath], capture_output=True, text=True).stdout.split()
    check(sorted(probe) == ["jpn", "kor"], f"영상 안 자막 트랙 {probe}")
    # 같은 영상 다시 → 이미 있음
    w.queue.add(type(job)(job.url, job.title, job.options.copy(), job.thumbnail))
    job2 = w.queue.jobs[-1]
    results["job2"] = job2
    wait(lambda: not job2.is_active, step_skipped)


def step_skipped():
    job2 = results["job2"]
    check(job2.state == "done" and job2.skipped, f"이미 있는 파일 → '건너뜀' 표시 ({job2.detail})")
    item = w._item_widgets[job2.id]
    check(item.btn_overwrite.isVisible(), "덮어쓰기 버튼 보임")
    shot("s04_skipped")
    item.btn_overwrite.click()
    wait(lambda: not job2.is_active and job2.options.overwrite, step_overwritten)


def step_overwritten():
    job2 = results["job2"]
    check(job2.state == "done" and not job2.skipped, f"덮어쓰기로 다시 받음 ({job2.detail})")
    # 느린 다운로드 취소 후 목록에서 지우면 .part 삭제
    w.settings.rate_limit = "60K"
    w.settings.overwrite_existing = True
    w.add_download()
    job3 = w.queue.jobs[-1]
    results["job3"] = job3
    wait(lambda: job3.fraction is not None and job3.fraction > 0.05, step_cancel)


def step_cancel():
    job3 = results["job3"]
    job3.cancel()
    wait(lambda: not job3.is_active, step_remove)


def step_remove():
    job3 = results["job3"]
    parts = [p.name for p in out.iterdir() if ".part" in p.name or ".f1" in p.name]
    check(job3.state == "canceled" and parts, f"취소 후 임시 파일 남아 있음 {parts}")
    item3 = w._item_widgets[job3.id]
    item3.removeRequested.emit(item3.job)
    QTimer.singleShot(300, step_after_remove)


def step_after_remove():
    left = [p.name for p in out.iterdir() if ".part" in p.name or ".ytdl" in p.name or ".f1" in p.name]
    check(not left, f"목록에서 지우면 임시 파일 삭제 (남은 것: {left})")
    check(not hasattr(w, "options_box") and not hasattr(w, "sec_start"), "옵션 상자·구간 자르기 UI 없음")
    shot("s05_after_remove")
    step_persist()


def step_persist():
    # 대기 중 2개를 걸어둔 상태로 저장 → 새 창에서 복원되는지
    w.queue.set_paused(True)
    w.settings.rate_limit = ""
    w.add_download()
    j = w.queue.jobs[-1]
    w.queue.add(type(j)(j.url, j.title + " (2)", j.options.copy(), j.thumbnail))
    w._save_queue()
    saved = [j.title for j in w.queue.jobs if j.state == "queued"]
    w.queue.jobs.clear()
    w2 = MainWindow()
    restored = [j for j in w2.queue.jobs if j.state == "queued"]
    check(len(restored) == len(saved) == 2, f"껐다 켜면 대기 목록 복원 ({len(restored)}개)")
    check("이어서" in w2.status_msg.text(), "복원 안내: " + w2.status_msg.text())
    results["w2"] = w2
    # 도구 확인이 끝나기 전에는 시작하지 않아야 함
    check(all(j.state == "queued" for j in w2.queue.jobs), "도구 확인 전에는 대기 유지")
    wait(lambda: not w2.queue.has_active(), step_end)


def step_end():
    w2 = results["w2"]
    check(all(j.state == "done" for j in w2.queue.jobs),
          "복원된 작업 이어서 완료 " + str([(j.state, j.error, j.detail) for j in w2.queue.jobs]))
    w2.resize(960, 920)
    w2.show()
    QTimer.singleShot(300, lambda: (shot("s06_restored_done", w2), finish()))


def finish():
    w._update_due  # noqa: B018
    w.settings.last_update_check = "2000-01-01T00:00:00"
    check(w._update_due(), "하루 지나면 업데이트 확인")
    w.settings.last_update_check = time.strftime("%Y-%m-%dT%H:%M:%S")
    check(not w._update_due(), "오늘 확인했으면 생략")
    print("\nERRORS:", errors or "없음")
    app.quit()


def start():
    if not w.deps_ready:
        QTimer.singleShot(100, start)
        return
    step_fetch()


QTimer.singleShot(200, start)
QTimer.singleShot(300_000, app.quit)
app.exec()
sys.exit(1 if errors else 0)
