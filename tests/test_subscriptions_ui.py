"""구독: 메인 창 연결 (구독 탭, 새 영상 → 다운로드 목록, 자동 확인 시점)."""
import os
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TUBEGET_LANG", "ko")
os.environ.setdefault("TUBEGET_HOME", tempfile.mkdtemp(prefix="acortube-subsui-"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from tubegetapp.core.options import DownloadOptions  # noqa: E402
from tubegetapp.core.subscriptions import FoundEntry, Subscription  # noqa: E402
from tubegetapp.ui.main_window import MainWindow  # noqa: E402


def _window():
    w = MainWindow()
    # 도구 확인 결과를 받지 않는다: 받으면 도구가 없다는 창(모달)이 뜨거나 다운로드가 실제로 시작된다
    checker = getattr(w, "_checker", None)
    if checker is not None:
        try:
            checker.done.disconnect()
        except (RuntimeError, TypeError):
            pass
        checker.wait(15000)
    w.queue.set_paused(True)
    w.subs.items = []
    w.subs.save()
    _clear_queue(w)
    return w


def _clear_queue(w):
    for j in list(w.queue.jobs):
        w.queue.remove(j)


def _close(w):
    """테스트용으로 닫기: 남은 작업을 비워서 '받는 중인 작업' 확인 창이 뜨지 않게 한다."""
    w.sub_checker.stop()
    _clear_queue(w)
    checker = getattr(w, "_checker", None)   # 창을 만들 때 시작한 도구 확인 스레드
    if checker is not None:
        checker.wait(15000)
    app.processEvents()
    w._quit_requested = True
    w.close()
    w.deleteLater()
    app.processEvents()


def test_subs_tab_and_found_videos_go_to_queue(tmp_path):
    w = _window()
    try:
        w.settings.download_dir = str(tmp_path)
        w._set_filter("subs")
        assert w.stack.currentWidget() is w.subs_view
        assert not w.b_list_menu.isVisibleTo(w)

        opts = DownloadOptions(mode="audio", audio_format="m4a").to_dict()
        sub = Subscription(url="https://www.youtube.com/@chan/videos", kind="channel", title="Chan",
                           folder="Chan Backup", options=opts, initialized=True)
        w.subs.add(sub)
        w.subs_view.reload()
        assert w.subs_view.tree.topLevelItemCount() == 1
        assert "M4A" in w.subs_view.tree.topLevelItem(0).text(1).upper()

        entries = [FoundEntry(id="a", url="https://www.youtube.com/watch?v=a", title="A", duration=60),
                   FoundEntry(id="b", url="https://www.youtube.com/watch?v=b", title="B")]
        w._on_sub_found(sub, entries)
        jobs = [j for j in w.queue.jobs if j.url.endswith(("=a", "=b"))]
        assert [j.title for j in jobs] == ["A", "B"]
        o = jobs[0].options
        assert o.mode == "audio" and o.audio_format == "m4a"
        assert o.subfolder == "Chan Backup" and o.output_dir == str(tmp_path)
        # 같은 영상이 이미 목록에서 받는 중이면 또 넣지 않는다
        w._on_sub_found(sub, entries)
        assert len([j for j in w.queue.jobs if j.url.endswith(("=a", "=b"))]) == 2
    finally:
        _close(w)


def test_auto_check_only_when_due(monkeypatch):
    w = _window()
    try:
        calls = []
        monkeypatch.setattr(w.sub_checker, "check_enabled", lambda: calls.append(1))
        w.deps_ready = True
        w.subs.add(Subscription(url="https://www.youtube.com/@x/videos", kind="channel"))
        w.settings.subs_auto_check = True
        w.settings.subs_interval_hours = 3
        w.settings.subs_last_check = (datetime.now() - timedelta(hours=1)).isoformat()
        w._maybe_check_subs()
        assert calls == []                     # 아직 3시간이 안 됨
        w.settings.subs_last_check = (datetime.now() - timedelta(hours=4)).isoformat()
        w._maybe_check_subs()
        assert calls == [1]
        w.settings.subs_auto_check = False
        w.settings.subs_last_check = ""
        w._maybe_check_subs()
        assert calls == [1]                    # 자동 확인을 끄면 안 함
    finally:
        _close(w)
