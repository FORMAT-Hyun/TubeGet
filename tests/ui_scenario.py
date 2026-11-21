"""새 화면(툴바 / 정보 패널 / 필터 탭 / 알림 / 바로 받기)이 제대로 동작하는지 확인.

사용법: QT_QPA_PLATFORM=offscreen python tests/ui_scenario.py <서버 URL> <서버 폴더> <스크린샷 폴더>
"""
import os
import sys
import tempfile
import time
from pathlib import Path

home = tempfile.mkdtemp(prefix="tubeget-ui-")
os.environ["TUBEGET_HOME"] = home
os.environ.setdefault("TUBEGET_LANG", "ko")   # 화면 글 비교는 한국어 기준
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
base, srv, shots = sys.argv[1].rstrip("/"), sys.argv[2], Path(sys.argv[3])
shots.mkdir(parents=True, exist_ok=True)
os.environ.update(FAKE_BASE=base, FAKE_SRV=srv, FAKE_INFO=str(Path(home) / "fake_info.json"))

from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tubegetapp.config import Settings  # noqa: E402
from tubegetapp.core.metadata import Entry, MediaInfo  # noqa: E402
from tubegetapp.core.options import DownloadOptions  # noqa: E402
from tubegetapp.core.runner import DONE, DownloadJob  # noqa: E402
from tubegetapp.paths import bin_dir  # noqa: E402
from tubegetapp.ui.theme import apply_theme  # noqa: E402

wrapper = bin_dir() / "yt-dlp"
wrapper.write_text(f'#!/bin/sh\nexec {sys.executable} {ROOT / "tests" / "fake_youtube.py"} "$@"\n')
wrapper.chmod(0o755)
out = Path(home) / "My Music"
s = Settings()
s.download_dir = str(out)
s.auto_update_ytdlp = False
s.rate_limit = "2M"
s.save()

from tubegetapp.ui.main_window import MainWindow  # noqa: E402

app = QApplication([])
apply_theme(app)
errors = []


def check(cond, msg):
    print(("  ok  " if cond else "  FAIL") + " " + msg)
    if not cond:
        errors.append(msg)


def pump(cond=lambda: False, seconds=60.0):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def shot(name):
    app.processEvents()
    w.grab().save(str(shots / f"{name}.png"))


w = MainWindow()
w.resize(1000, 780)
w.show()
pump(lambda: w.deps_ready, 20)
check(w.deps_ready, "도구 확인 끝")

# --- 시작 화면 ---------------------------------------------------------------
check(not w.panel.isVisible(), "처음에는 정보 패널이 숨겨져 있음")
check(w.q_empty.isVisible(), "빈 목록 안내가 보임")
check(w.dest_btn.text() == "My Music", f"저장 위치 칩에 폴더 이름만 표시: {w.dest_btn.text()!r}")
check(w.dest_btn.toolTip() == str(out), "저장 위치 칩 툴팁에 전체 경로")
check(w.minimumSizeHint().width() <= w.minimumWidth(), f"툴바가 최소 너비({w.minimumWidth()})에 들어감: {w.minimumSizeHint().width()}")
check(not w.auto_toggle.isChecked(), "바로 받기는 기본 꺼짐")
shot("u01_start")

# --- 앱 정보 창 -------------------------------------------------------------------
from tubegetapp import APP_VERSION  # noqa: E402
from tubegetapp.ui.about_dialog import AboutDialog  # noqa: E402
check(APP_VERSION in w.about_btn.text(), "상태 표시줄에 앱 버전 버튼: " + w.about_btn.text())
_ab = AboutDialog(w.deps, w); _ab.show(); app.processEvents()
check("0.1.7" in _ab.version.text() and "베타" in _ab.version.text(), "앱 정보 창에 버전/단계: " + _ab.version.text())
_ab._copy()
check(QGuiApplication.clipboard().text().startswith("TubeGet 0.1.7"), "정보 복사 → 클립보드")
shot("u00_about")
_ab.close(); _ab.deleteLater()

# --- 링크 붙여넣기: 클립보드에 주소가 없을 때 ------------------------------------
QGuiApplication.clipboard().setText("그냥 글자")
w._paste()
check(not w.panel.isVisible(), "클립보드에 링크가 없어도 입력 칸이 갑자기 나타나지 않음")
check(len(w.toasts._toasts) == 1, "클립보드에 링크가 없다는 알림")
check(not w._ready and w.info is None, "정보 없이 입력 칸만 보임")
w.toasts.clear()
w._escape()
check(not w.panel.isVisible(), "Esc로 패널 닫기")

# --- 링크 붙여넣기: 주소가 있을 때 (미리 보고 고르기) -------------------------------
QGuiApplication.clipboard().setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
w._paste()
check(w.url_edit.text().endswith("dQw4w9WgXcQ"), "클립보드 주소가 입력 칸에 들어감")
pump(lambda: w.info is not None and not w.fetcher.busy, 30)
check(w.info is not None and len(w._ready) == 1 and w._ready[0].isVisible() and w._ready[0].b_download.isEnabled(),
      "불러오면 목록에 영상 카드(썸네일·정보·다운로드 버튼)가 생김")
check(not w.panel.isVisible() and not w.q_empty.isVisible(), "주소 입력 칸은 닫히고 빈 목록 안내는 사라짐")
check("예상 크기" in w._ready[0].est_label.text(), "카드에 예상 크기: " + w._ready[0].est_label.text())
check(len(w.queue.jobs) == 0, "바로 받기가 꺼져 있으면 목록에 자동으로 넣지 않음")
check(w.quality.currentData() == 0 and w.quality.itemData(0, 256 + 11) == "최고", "화질 칩은 짧은 값('최고')을 보여줌")
long_text = w.quality.itemText(w.quality.findData(1080))
check("≈" in long_text, f"펼친 목록에는 예상 크기까지: {long_text!r}")
shot("u02_info")

# 오디오로 바꾸면 화질 칩이 숨겨짐
w.mode.setValue("audio")
w._on_mode_changed("audio")
check(not w.quality.isVisible() and not w.l_quality.isVisible(), "오디오에서는 화질 칩 숨김")
check(w.fmt.currentData() == "mp3" and w.b_tags.isVisible() and w.l_tags.isVisible(), "오디오 형식/태그 버튼")
check(w.b_subs.isVisible() and w.l_subs.isVisible(), "자막 칩이 위쪽 바에 보임")
from tubegetapp.ui.subtitle_dialog import SubtitleDialog  # noqa: E402
_d = SubtitleDialog(w.info, [], False, "embed", False, dub="ko")
check(_d.dub_combo.count() >= 2 and _d.result_dub() == "ko", "더빙 선택 창: 영상의 음성 트랙 목록 + 선택값")
_d.dub_combo.setCurrentIndex(0)
check(_d.result_dub() == "", "더빙 '원본 음성'은 빈 값")
_d.deleteLater()
w.dub_lang = "ko"; w._update_subs_button()
check("한국어 더빙" in w.b_subs.text() or "더빙" in w.b_subs.text(), "칩에 더빙 표시: " + w.b_subs.text())
check(w._current_options().dub_lang == "ko", "다운로드 옵션에 더빙 언어 전달")
w.dub_lang = ""; w._update_subs_button()
shot("u03_audio")
w.mode.setValue("video")
w._on_mode_changed("video")
check(w.b_tags.isVisible() and w.b_subs.isVisible(), "영상 모드: 태그·자막 칩 모두 보임")
check(w.quality.isVisible(), "영상으로 돌아오면 화질 칩 보임")
_before = w._ready[0].est_label.text()
w.quality.setCurrentIndex(w.quality.findData(720))
check(w._ready[0].est_label.text() != _before, "화질을 바꾸면 카드 예상 크기도 바뀜")
w.quality.setCurrentIndex(0)

# --- 바로 받기 -----------------------------------------------------------------
w.auto_toggle.click()
check(w.auto_toggle.isChecked() and Settings.load().auto_download, "바로 받기 켜면 설정에 저장")
w._close_panel()
check(not w.panel.isVisible() and not w.url_edit.text(), "패널 닫으면 입력 칸 초기화")
w._remove_ready(w._ready[0])
check(not w._ready and w.info is None, "카드를 지우면 선택 정보도 비워짐")
QGuiApplication.clipboard().setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
w._paste()
pump(lambda: len(w.queue.jobs) == 1, 30)
check(len(w.queue.jobs) == 1, "바로 받기: 붙여넣자마자 목록에 추가")
check(not w.panel.isVisible(), "바로 받기: 정보 패널은 열리지 않고 닫힘")
check(any(t._key[1] == "다운로드 목록에 추가했어요" for t in w.toasts._toasts), "추가했다는 알림")
job = w.queue.jobs[0]
check(job.duration == 216, f"작업에 영상 길이 저장됨: {job.duration}")
shot("u04_auto_added")

# 재생목록은 바로 받지 않고 고르게 한다
pl = MediaInfo(kind="playlist", id="PL", title="목록", entries=[Entry(id="a", title="A", url="https://youtu.be/a")])
w._auto_pending = True
w._on_info(pl, "https://www.youtube.com/playlist?list=PL")
check(len(w.queue.jobs) == 1 and len(w._ready) == 1 and w._ready[0].info.kind == "playlist", "재생목록은 자동으로 받지 않고 카드로 보여줌")
w._remove_ready(w._ready[0])

# 직접 입력해서 [불러오기]는 항상 미리 보기
w.url_edit.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
w._fetch_clicked()
pump(lambda: w.info is not None and not w.fetcher.busy, 30)
check(len(w.queue.jobs) == 1 and len(w._ready) == 1, "직접 입력은 바로 받기와 상관없이 카드로 미리 보기")
# 카드의 [다운로드] 버튼으로 바로 받기
w.quality.setCurrentIndex(w.quality.findData(720))   # 같은 설정이면 '이미 목록에 있어요' 물음이 떠서 화질을 바꿔둠
w._ready[0].b_download.click()
check(len(w.queue.jobs) == 2 and not w._ready and w.info is None, "카드의 다운로드 버튼 → 목록에 추가되고 카드는 사라짐")
w.quality.setCurrentIndex(0)
w.queue.remove(w.queue.jobs[1], delete_partials=True)   # 아래 필터 시험을 위해 정리
w._close_panel()
w.auto_toggle.click()

# --- 끝나면 알림 + 방금 끝난 항목 강조 -----------------------------------------------
pump(lambda: not job.is_active, 90)
check(job.state == DONE, f"다운로드 완료 ({job.detail})")
check(any(t._key[1] == "다운로드 완료" for t in w.toasts._toasts), "완료 알림")
item = w._item_widgets[job.id]
check(bool(item.property("fresh")), "방금 끝난 항목은 연한 노란 테두리")
check("MB" in item.meta.fullText() and "MP4" in item.meta.fullText() and "3:36" in item.meta.fullText(),
      f"완료 줄: {item.meta.fullText()!r}")
check(item.btn_open.isVisible() and item.btn_more.isVisible() and not item.btn_cancel.isVisible(), "완료 항목 버튼: 폴더 + 더보기")
shot("u05_done_toast")
w.toasts.clear()

# --- 필터 탭 ----------------------------------------------------------------------
a = DownloadJob("https://x/a", "음원 하나", DownloadOptions(mode="audio", output_dir=str(out)))
a.state = DONE
w._on_job_added(a)
check(w._item_widgets[job.id].isVisible() and w._item_widgets[a.id].isVisible(), "전체: 둘 다 보임")
w._set_filter("audio")
check(not w._item_widgets[job.id].isVisible() and w._item_widgets[a.id].isVisible(), "오디오 탭: 음원만")
w._set_filter("video")
check(w._item_widgets[job.id].isVisible() and not w._item_widgets[a.id].isVisible(), "동영상 탭: 영상만")
w.queue.jobs.remove(job)
w._on_job_removed(job)
check(w.q_empty.isVisible() and "받은" in w.q_empty_title.text(), f"해당 항목이 없으면 안내: {w.q_empty_title.text()!r}")
w._set_filter("history")
check(w.stack.currentIndex() == 1 and not w.b_list_menu.isVisible(), "기록 탭: 기록 화면, 목록 메뉴 숨김")
w._set_filter("all")
check(w.stack.currentIndex() == 0 and w._filter_btns["all"].isChecked(), "전체 탭으로 돌아옴")

# --- 설정 창 --------------------------------------------------------------------------
from PySide6.QtWidgets import QScrollArea  # noqa: E402
from tubegetapp.ui.settings_dialog import SettingsDialog  # noqa: E402

d = SettingsDialog(w.settings, w)
d.show()
app.processEvents()
sa = d.findChild(QScrollArea)
check(not sa.horizontalScrollBar().isVisible(), "설정 창에 가로 스크롤이 생기지 않음")
d.close()
d.deleteLater()

print("ERRORS:", errors or "없음")
w._closing = True
w.queue.jobs.clear()
w.hide()
w.deleteLater()
app.processEvents()
sys.exit(1 if errors else 0)
