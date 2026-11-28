"""채널·재생목록 구독 (자동 백업).

구독해 둔 채널/재생목록을 주기적으로 확인해서, 처음 보는 영상만 정해 둔 설정으로 다운로드 목록에 넣는다.
- 목록은 데이터 폴더의 subscriptions.json 에 저장
- 이미 본 영상 ID(seen)를 구독마다 기억해서 같은 영상을 두 번 받지 않는다
- 확인은 yt-dlp -J --flat-playlist (빠르게 목록만). 채널은 최근 영상 몇 개만 본다
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..paths import data_dir
from .deps import Deps
from .errors import explain
from .metadata import _entry_url, pick_thumbnail
from .options import common_args
from .proc import kill_tree, make_process
from ..i18n import tr

CHANNEL_RECENT = 30        # 채널은 최근 영상 이 만큼만 확인
SEEN_LIMIT = 5000          # 구독마다 기억하는 영상 ID 최대 개수
CHECK_TIMEOUT_MS = 120_000
GAP_MS = 3000              # 구독 사이 간격 (유튜브 요청 과다 방지)

INITIAL_FUTURE = "future"  # 지금 있는 영상은 건너뛰고 앞으로 올라오는 것만
INITIAL_RECENT = "recent"  # 최근 몇 개도 받기
INITIAL_ALL = "all"        # 지금 있는 영상도 모두 받기
RECENT_COUNT = 5

_CHANNEL_TABS = ("videos", "shorts", "streams", "playlists", "featured", "live", "community", "releases")
_CHANNEL_RE = re.compile(r"^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)(/.*)?$")


def classify_url(url: str) -> tuple[Optional[str], str]:
    """구독할 수 있는 주소인지: ('channel' | 'playlist' | None, 정리된 주소).

    채널 주소는 업로드 영상 탭(/videos)으로 맞춘다. 영상 하나짜리 주소는 None.
    """
    url = (url or "").strip()
    if not url:
        return None, url
    if not re.match(r"^https?://", url):
        url = "https://" + url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if not (host == "youtube.com" or host.endswith(".youtube.com")):
        return None, url
    qs = parse_qs(p.query)
    lst = (qs.get("list") or [""])[0]
    if lst and p.path in ("/playlist", "/watch"):
        if lst.startswith(("RD", "UL", "LL", "WL")):   # 믹스·좋아요·나중에 볼 동영상은 구독 대상이 아님
            return None, url
        return "playlist", f"https://www.youtube.com/playlist?list={lst}"
    m = _CHANNEL_RE.match(p.path.rstrip("/") or "/")
    if m:
        base = m.group(1)
        tail = (m.group(2) or "").strip("/")
        tab = tail.split("/")[0] if tail else ""
        if tab not in _CHANNEL_TABS or tab in ("featured", "playlists", "community", "releases"):
            tab = "videos"
        return "channel", f"https://www.youtube.com/{base}/{tab}"
    return None, url


@dataclass
class Subscription:
    url: str
    kind: str                                   # channel | playlist
    title: str = ""
    folder: str = ""                            # 저장 폴더 안의 하위 폴더 이름 (비면 제목)
    options: dict = field(default_factory=dict)  # DownloadOptions.to_dict() (저장 폴더 제외)
    enabled: bool = True
    initial: str = INITIAL_FUTURE
    initialized: bool = False                   # 첫 확인을 했는지
    skip_shorts: bool = True
    skip_live: bool = True
    seen: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_checked: str = ""
    last_new: int = 0
    last_error: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in names})

    def to_dict(self) -> dict:
        return asdict(self)

    def display_title(self) -> str:
        return self.title or self.url

    def mark_seen(self, ids: list[str]) -> None:
        known = set(self.seen)
        for vid in ids:
            if vid and vid not in known:
                self.seen.append(vid)
                known.add(vid)
        if len(self.seen) > SEEN_LIMIT:
            self.seen = self.seen[-SEEN_LIMIT:]


@dataclass
class FoundEntry:
    id: str
    url: str
    title: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    live_status: str = ""
    is_short: bool = False


def parse_entries(data: dict) -> tuple[str, list[FoundEntry]]:
    """yt-dlp -J --flat-playlist 결과 → (재생목록/채널 이름, 영상 목록). 비공개·삭제 영상은 뺀다."""
    title = str(data.get("title") or data.get("channel") or data.get("uploader") or "")
    # 채널 이름은 "OOO - Videos" 처럼 탭 이름이 붙어 온다
    title = re.sub(r"\s+-\s+(Videos|Shorts|Live|Streams)$", "", title)
    out: list[FoundEntry] = []
    for raw in data.get("entries") or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("_type") == "playlist":     # 탭 목록이 온 경우는 건너뜀
            continue
        vid = str(raw.get("id") or "")
        name = str(raw.get("title") or "")
        if not vid or name.strip().lower() in ("[private video]", "[deleted video]", "[unavailable video]"):
            continue
        if raw.get("availability") in ("private", "needs_auth", "premium_only", "subscriber_only"):
            continue
        url = _entry_url(raw)
        out.append(FoundEntry(
            id=vid, url=url, title=name or vid, duration=raw.get("duration"),
            thumbnail=pick_thumbnail(raw), live_status=str(raw.get("live_status") or ""),
            is_short="/shorts/" in url,
        ))
    return title, out


def select_new(sub: Subscription, entries: list[FoundEntry]) -> list[FoundEntry]:
    """이번에 받을 영상을 고르고, 본 영상 ID 를 기록한다 (sub 이 바뀜).

    entries 는 채널이면 최신순, 재생목록이면 재생목록 순서.
    """
    def wanted(e: FoundEntry) -> bool:
        if sub.skip_shorts and e.is_short:
            return False
        if e.live_status in ("is_upcoming", "is_live"):
            return False          # 아직 받을 수 없음 (다음 확인 때 다시 봄)
        if sub.skip_live and e.live_status in ("was_live", "post_live"):
            return False
        return True

    seen = set(sub.seen)
    order = {e.id: i for i, e in enumerate(entries)}
    fresh = [e for e in entries if e.id not in seen]
    if not sub.initialized:
        sub.initialized = True
        if sub.initial == INITIAL_ALL:
            picked = [e for e in fresh if wanted(e)]
        elif sub.initial == INITIAL_RECENT:
            ordered = fresh if sub.kind == "channel" else list(reversed(fresh))  # 재생목록은 끝이 최근
            picked = [e for e in ordered if wanted(e)][:RECENT_COUNT]
        else:
            picked = []
    else:
        picked = [e for e in fresh if wanted(e)]
    # 고르지 않은 것도 '본 것'으로 기록 (단, 아직 시작 안 한 라이브는 다음에 다시 본다)
    sub.mark_seen([e.id for e in fresh if e.live_status not in ("is_upcoming", "is_live")])
    # 오래된 것부터 받도록: 채널은 최신순으로 오니 거꾸로, 재생목록은 원래 순서대로
    picked.sort(key=lambda e: order[e.id], reverse=sub.kind == "channel")
    return picked


def check_args(sub: Subscription, cookies_browser: str = "", deps: Optional[Deps] = None) -> list[str]:
    args = ["--ignore-config", "--color", "never", "--encoding", "utf-8",
            "-J", "--flat-playlist", "--yes-playlist", "--ignore-errors"]
    if sub.kind == "channel":
        args += ["--playlist-end", str(CHANNEL_RECENT)]
    args += common_args(cookies_browser, deps)
    args += ["--", sub.url]
    return args


class SubscriptionStore:
    def __init__(self) -> None:
        self.path = data_dir() / "subscriptions.json"
        self.items: list[Subscription] = []
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = []
        self.items = [Subscription.from_dict(d) for d in raw if isinstance(d, dict) and d.get("url")]

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps([s.to_dict() for s in self.items], ensure_ascii=False, indent=1),
                           encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    def get(self, sub_id: str) -> Optional[Subscription]:
        return next((s for s in self.items if s.id == sub_id), None)

    def find_url(self, url: str) -> Optional[Subscription]:
        _kind, norm = classify_url(url)
        return next((s for s in self.items if s.url == norm), None)

    def add(self, sub: Subscription) -> None:
        self.items.append(sub)
        self.save()

    def remove(self, sub_id: str) -> None:
        self.items = [s for s in self.items if s.id != sub_id]
        self.save()


class SubscriptionChecker(QObject):
    """구독을 하나씩 차례로 확인한다. 새 영상은 found 로 알린다."""

    found = Signal(object, object)       # Subscription, list[FoundEntry]
    checked = Signal(object, bool, str)  # Subscription, 성공 여부, 안내 메시지
    started = Signal()
    finished = Signal()

    def __init__(self, store: SubscriptionStore, deps_provider: Callable[[], Optional[Deps]],
                 cookies_provider: Callable[[], str] = lambda: "", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.store = store
        self._deps = deps_provider
        self._cookies = cookies_provider
        self._pending: list[str] = []
        self._proc: Optional[QProcess] = None
        self._current: Optional[Subscription] = None
        self._out = bytearray()
        self._err = bytearray()
        self._timed_out = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._gap = QTimer(self)
        self._gap.setSingleShot(True)
        self._gap.timeout.connect(self._next)

    @property
    def busy(self) -> bool:
        return self._proc is not None or bool(self._pending) or self._gap.isActive()

    def is_checking(self, sub_id: str) -> bool:
        return (self._current is not None and self._current.id == sub_id) or sub_id in self._pending

    def check(self, subs: list[Subscription]) -> None:
        """subs 를 확인 대기열에 넣는다 (이미 있으면 무시)."""
        was_busy = self.busy
        for s in subs:
            if s.id not in self._pending and not (self._current and self._current.id == s.id):
                self._pending.append(s.id)
        if not was_busy and self._pending:
            self.started.emit()
            self._next()

    def check_enabled(self) -> None:
        self.check([s for s in self.store.items if s.enabled])

    def stop(self) -> None:
        self._pending.clear()
        self._gap.stop()
        self._timer.stop()
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.finished.disconnect()
                proc.errorOccurred.disconnect()
            except (RuntimeError, TypeError):
                pass
            kill_tree(proc)
            proc.deleteLater()
        self._current = None

    def _next(self) -> None:
        self._current = None
        while self._pending:
            sub = self.store.get(self._pending.pop(0))
            if sub is not None:
                break
        else:
            self.finished.emit()
            return
        deps = self._deps()
        if deps is None or not deps.ytdlp.ok:
            self._done(sub, False, tr("yt-dlp가 설치되어 있지 않아요. [도구 상태]에서 설치해 주세요."))
            return
        self._current = sub
        self._out, self._err = bytearray(), bytearray()
        self._timed_out = False
        proc = make_process(deps.ytdlp.path, check_args(sub, self._cookies(), deps), self)
        proc.readyReadStandardOutput.connect(lambda: self._out.extend(bytes(proc.readAllStandardOutput())))
        proc.readyReadStandardError.connect(lambda: self._err.extend(bytes(proc.readAllStandardError())))
        proc.finished.connect(lambda code, _st, p=proc: self._on_finished(p, code))
        proc.errorOccurred.connect(lambda err, p=proc: self._on_error(p, err))
        self._proc = proc
        self._timer.start(CHECK_TIMEOUT_MS)
        proc.start()

    def _on_timeout(self) -> None:
        if self._proc is not None:
            self._timed_out = True
            kill_tree(self._proc)

    def _on_error(self, proc: QProcess, err) -> None:
        if proc is not self._proc or err != QProcess.ProcessError.FailedToStart:
            return
        self._proc = None
        self._timer.stop()
        proc.deleteLater()
        self._done(self._current, False, tr("yt-dlp를 실행하지 못했어요. [도구 상태]에서 다시 설치해 주세요."))

    def _on_finished(self, proc: QProcess, code: int) -> None:
        if proc is not self._proc:
            return
        self._proc = None
        self._timer.stop()
        self._out.extend(bytes(proc.readAllStandardOutput()))
        self._err.extend(bytes(proc.readAllStandardError()))
        proc.deleteLater()
        sub = self._current
        if sub is None:
            self._schedule_next()
            return
        err_text = self._err.decode("utf-8", "replace")
        if self._timed_out:
            self._done(sub, False, tr("확인하는 데 너무 오래 걸려서 다음에 다시 확인해요."))
            return
        data = None
        for line in reversed(self._out.decode("utf-8", "replace").splitlines()):
            if line.strip().startswith("{"):
                try:
                    data = json.loads(line)
                    break
                except ValueError:
                    continue
        if not isinstance(data, dict):
            self._done(sub, False, explain(err_text) if err_text.strip() else tr("정보를 읽지 못했어요."))
            return
        title, entries = parse_entries(data)
        if title and not sub.title:
            sub.title = title
        if not sub.folder:
            sub.folder = sub.title
        new = select_new(sub, entries)
        sub.last_new = len(new)
        self._done(sub, True, "", new)

    def _done(self, sub: Subscription, ok: bool, message: str, new: Optional[list] = None) -> None:
        sub.last_checked = datetime.now().isoformat(timespec="seconds")
        sub.last_error = "" if ok else message
        self.store.save()
        if ok and new:
            self.found.emit(sub, new)
        self.checked.emit(sub, ok, message)
        self._schedule_next()

    def _schedule_next(self) -> None:
        self._current = None
        if self._pending:
            self._gap.start(GAP_MS)
        else:
            self.finished.emit()
