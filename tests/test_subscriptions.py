"""구독 자동 백업: 주소 판별, 새 영상 고르기, 저장, 실제 확인 흐름(가짜 yt-dlp)."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("TUBEGET_LANG", "ko")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TUBEGET_HOME", tempfile.mkdtemp(prefix="acortube-subs-"))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tubegetapp.core import subscriptions as S  # noqa: E402
from tubegetapp.core.deps import Deps, Tool  # noqa: E402


# ---- 주소 판별 ---------------------------------------------------------------

def test_classify_channel_urls():
    assert S.classify_url("https://www.youtube.com/@ajr") == ("channel", "https://www.youtube.com/@ajr/videos")
    assert S.classify_url("youtube.com/@ajr/featured") == ("channel", "https://www.youtube.com/@ajr/videos")
    assert S.classify_url("https://m.youtube.com/@ajr/shorts") == ("channel", "https://www.youtube.com/@ajr/shorts")
    assert S.classify_url("https://www.youtube.com/channel/UC123/") == ("channel", "https://www.youtube.com/channel/UC123/videos")


def test_classify_playlist_and_others():
    assert S.classify_url("https://www.youtube.com/playlist?list=PLabc&si=x") == \
        ("playlist", "https://www.youtube.com/playlist?list=PLabc")
    assert S.classify_url("https://www.youtube.com/watch?v=abc&list=PLxyz")[0] == "playlist"
    assert S.classify_url("https://www.youtube.com/watch?v=abc")[0] is None        # 영상 하나
    assert S.classify_url("https://www.youtube.com/watch?v=abc&list=RDabc")[0] is None  # 믹스
    assert S.classify_url("https://youtu.be/abc")[0] is None
    assert S.classify_url("https://example.com/@x")[0] is None


# ---- 새 영상 고르기 ------------------------------------------------------------

def _e(i, **kw):
    return S.FoundEntry(id=f"v{i}", url=f"https://www.youtube.com/watch?v=v{i}", title=f"T{i}", **kw)


def test_first_check_future_only_marks_everything_seen():
    sub = S.Subscription(url="u", kind="channel", initial=S.INITIAL_FUTURE)
    assert S.select_new(sub, [_e(3), _e(2), _e(1)]) == []
    assert set(sub.seen) == {"v1", "v2", "v3"} and sub.initialized
    # 다음 확인: 새로 올라온 v4 만, 최신순으로 와도 오래된 것부터
    got = S.select_new(sub, [_e(5), _e(4), _e(3), _e(2)])
    assert [e.id for e in got] == ["v4", "v5"]
    assert S.select_new(sub, [_e(5), _e(4)]) == []   # 두 번 받지 않음


def test_first_check_recent_and_all():
    ch = S.Subscription(url="u", kind="channel", initial=S.INITIAL_RECENT)
    entries = [_e(i) for i in range(10, 0, -1)]            # 최신순 v10..v1
    assert [e.id for e in S.select_new(ch, entries)] == ["v6", "v7", "v8", "v9", "v10"]
    pl = S.Subscription(url="u", kind="playlist", initial=S.INITIAL_RECENT)
    entries = [_e(i) for i in range(1, 11)]                # 재생목록 순서 v1..v10 (끝이 최근)
    assert [e.id for e in S.select_new(pl, entries)] == ["v6", "v7", "v8", "v9", "v10"]
    allsub = S.Subscription(url="u", kind="playlist", initial=S.INITIAL_ALL)
    assert len(S.select_new(allsub, entries)) == 10


def test_filters_shorts_and_live():
    sub = S.Subscription(url="u", kind="channel", initialized=True)
    entries = [_e(1, is_short=True), _e(2, live_status="was_live"), _e(3, live_status="is_upcoming"), _e(4)]
    assert [e.id for e in S.select_new(sub, entries)] == ["v4"]
    assert "v3" not in sub.seen          # 예정된 라이브는 다음에 다시 본다
    assert {"v1", "v2", "v4"} <= set(sub.seen)
    keep = S.Subscription(url="u", kind="channel", initialized=True, skip_shorts=False, skip_live=False)
    assert {e.id for e in S.select_new(keep, entries)} == {"v1", "v2", "v4"}


def test_seen_is_capped():
    sub = S.Subscription(url="u", kind="channel")
    sub.mark_seen([f"x{i}" for i in range(S.SEEN_LIMIT + 50)])
    assert len(sub.seen) == S.SEEN_LIMIT and sub.seen[-1] == f"x{S.SEEN_LIMIT + 49}"


def test_parse_entries_skips_private_and_cleans_title():
    data = {"title": "AJR - Videos", "entries": [
        {"id": "a", "title": "Song", "url": "https://www.youtube.com/watch?v=a"},
        {"id": "b", "title": "[Private video]"},
        {"id": "c", "title": "Short", "url": "https://www.youtube.com/shorts/c"},
        {"_type": "playlist", "id": "tab"},
    ]}
    title, entries = S.parse_entries(data)
    assert title == "AJR"
    assert [e.id for e in entries] == ["a", "c"] and entries[1].is_short


# ---- 저장 ---------------------------------------------------------------------

def test_store_roundtrip():
    store = S.SubscriptionStore()
    store.items = []
    sub = S.Subscription(url="https://www.youtube.com/@x/videos", kind="channel", title="X",
                         options={"mode": "audio"})
    store.add(sub)
    again = S.SubscriptionStore()
    got = again.get(sub.id)
    assert got is not None and got.title == "X" and got.options == {"mode": "audio"}
    assert again.find_url("https://www.youtube.com/@x") is not None
    again.remove(sub.id)
    assert S.SubscriptionStore().get(sub.id) is None


# ---- 실제 확인 흐름 (가짜 yt-dlp) ----------------------------------------------

def _fake_ytdlp(tmp: Path, payload: dict) -> str:
    """-J 결과로 payload 를 내보내는 가짜 yt-dlp (파이썬 스크립트를 실행 파일처럼)."""
    script = tmp / "fake_ytdlp.py"
    script.write_text("import json, sys\nprint(json.dumps(" + repr(payload) + "))\n", encoding="utf-8")
    if sys.platform == "win32":
        exe = tmp / "fake_ytdlp.bat"
        exe.write_text(f'@"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    else:
        exe = tmp / "fake_ytdlp"
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        exe.chmod(0o755)
    return str(exe)


def test_checker_finds_new_videos(tmp_path):
    app = QApplication.instance() or QApplication([])  # 다른 테스트가 창을 쓰므로 QApplication
    payload = {"title": "Chan - Videos", "entries": [
        {"id": "n2", "title": "New 2", "url": "https://www.youtube.com/watch?v=n2"},
        {"id": "n1", "title": "New 1", "url": "https://www.youtube.com/watch?v=n1"},
        {"id": "old", "title": "Old", "url": "https://www.youtube.com/watch?v=old"},
    ]}
    deps = Deps()
    deps.ytdlp = Tool("yt-dlp", _fake_ytdlp(tmp_path, payload), "2026.10.26")
    store = S.SubscriptionStore()
    store.items = []
    sub = S.Subscription(url="https://www.youtube.com/@chan/videos", kind="channel",
                         initialized=True, seen=["old"])
    store.add(sub)

    found, checked = [], []
    checker = S.SubscriptionChecker(store, lambda: deps)
    checker.found.connect(lambda s, new: found.append((s.id, [e.id for e in new])))
    checker.checked.connect(lambda s, ok, msg: checked.append((ok, msg)))
    loop = QEventLoop()
    checker.finished.connect(loop.quit)
    guard = QTimer()                 # 20초 안에 끝나지 않으면 멈춤 (테스트가 끝나면 꼭 정지)
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)
    guard.start(20000)
    checker.check([sub])
    loop.exec()
    guard.stop()
    checker.stop()
    checker.deleteLater()
    app.processEvents()

    assert checked and checked[0][0], checked
    assert found == [(sub.id, ["n1", "n2"])]
    saved = S.SubscriptionStore().get(sub.id)
    assert saved.title == "Chan" and saved.folder == "Chan"
    assert {"n1", "n2", "old"} <= set(saved.seen) and saved.last_checked and saved.last_new == 2
