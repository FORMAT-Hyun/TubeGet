"""`yt-dlp -J --flat-playlist` 결과(JSON) 해석."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entry:
    id: str
    title: str
    url: str
    duration: Optional[float] = None
    uploader: str = ""
    thumbnail: Optional[str] = None
    available: bool = True


@dataclass
class MediaInfo:
    kind: str                              # "video" | "playlist"
    id: str = ""
    title: str = ""
    uploader: str = ""
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    url: str = ""
    is_live: bool = False
    heights: list[int] = field(default_factory=list)
    size_by_height: dict[int, int] = field(default_factory=dict)
    audio_size: Optional[int] = None
    entries: list[Entry] = field(default_factory=list)
    nested_tabs: bool = False              # 채널 주소처럼 탭 목록만 온 경우
    track: str = ""
    artist: str = ""
    album: str = ""
    release_year: Optional[int] = None
    upload_date: str = ""
    subtitles: dict[str, str] = field(default_factory=dict)      # 올린 자막: 코드 → 이름
    auto_captions: dict[str, str] = field(default_factory=dict)  # 자동 생성 자막: 코드 → 이름

    def estimated_size(self, height: int, mode: str = "video") -> Optional[int]:
        """대략적인 파일 크기 (영상 + 음성)."""
        if mode == "audio":
            return self.audio_size
        if not self.size_by_height:
            return None
        if height:
            cands = [h for h in self.size_by_height if h <= height]
            h = max(cands) if cands else min(self.size_by_height)
        else:
            h = max(self.size_by_height)
        v = self.size_by_height.get(h)
        if v is None:
            return None
        return v + (self.audio_size or 0)


_UNAVAILABLE_TITLES = {"[private video]", "[deleted video]", "[unavailable video]"}


def pick_thumbnail(data: dict) -> Optional[str]:
    """JPEG 를 우선해서 적당히 큰 썸네일 고르기."""
    thumbs = data.get("thumbnails") or []
    best, best_key = None, None
    for t in thumbs:
        url = t.get("url")
        if not url:
            continue
        is_jpg = ".jpg" in url.split("?")[0].lower()
        width = t.get("width") or 0
        # 너무 큰 것(maxres)보다 640 근처가 로딩이 빠름
        size_score = -abs(width - 480) if width else -1000
        key = (is_jpg, size_score, t.get("preference") or 0)
        if best_key is None or key > best_key:
            best, best_key = url, key
    return best or data.get("thumbnail")


def _entry_url(e: dict) -> str:
    url = e.get("url") or e.get("webpage_url") or ""
    ie = (e.get("ie_key") or "").lower()
    vid = e.get("id") or ""
    if (not url or not url.startswith("http")) and vid and ie in ("youtube", ""):
        url = f"https://www.youtube.com/watch?v={vid}"
    return url


def _sub_names(raw) -> dict[str, str]:
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for code, fmts in raw.items():
        if not code or code == "live_chat" or not isinstance(fmts, list) or not fmts:
            continue
        name = ""
        for f in fmts:
            if isinstance(f, dict) and f.get("name"):
                name = str(f["name"])
                break
        out[str(code)] = name
    return out


def parse_info(data: dict) -> MediaInfo:
    if not isinstance(data, dict):
        raise ValueError("잘못된 정보 형식")

    if data.get("_type") in ("playlist", "multi_video"):
        info = MediaInfo(
            kind="playlist",
            id=str(data.get("id") or ""),
            title=data.get("title") or data.get("id") or "재생목록",
            uploader=data.get("uploader") or data.get("channel") or "",
            thumbnail=pick_thumbnail(data),
            url=data.get("webpage_url") or data.get("original_url") or "",
        )
        tabs = 0
        for raw in data.get("entries") or []:
            if not isinstance(raw, dict):
                continue
            ie = (raw.get("ie_key") or "").lower()
            if raw.get("_type") == "playlist" or ie == "youtubetab":
                tabs += 1
                continue
            title = raw.get("title") or raw.get("id") or "(제목 없음)"
            url = _entry_url(raw)
            if not url:
                continue
            info.entries.append(Entry(
                id=str(raw.get("id") or ""),
                title=title,
                url=url,
                duration=raw.get("duration"),
                uploader=raw.get("uploader") or raw.get("channel") or "",
                thumbnail=pick_thumbnail(raw),
                available=title.strip().lower() not in _UNAVAILABLE_TITLES
                and raw.get("availability") not in ("private", "needs_auth", "premium_only", "subscriber_only"),
            ))
        info.nested_tabs = tabs > 0 and not info.entries
        if not info.thumbnail and info.entries:
            info.thumbnail = info.entries[0].thumbnail
        return info

    info = MediaInfo(
        kind="video",
        id=str(data.get("id") or ""),
        title=data.get("title") or data.get("id") or "(제목 없음)",
        uploader=data.get("uploader") or data.get("channel") or "",
        duration=data.get("duration"),
        thumbnail=pick_thumbnail(data),
        url=data.get("webpage_url") or data.get("original_url") or "",
        is_live=bool(data.get("is_live")) or data.get("live_status") in ("is_live", "is_upcoming"),
        track=str(data.get("track") or ""),
        artist=str(data.get("artist") or data.get("creator") or ""),
        album=str(data.get("album") or ""),
        release_year=data.get("release_year") if isinstance(data.get("release_year"), int) else None,
        upload_date=str(data.get("upload_date") or ""),
    )

    heights: set[int] = set()
    sizes: dict[int, int] = {}
    audio_best: Optional[int] = None
    for f in data.get("formats") or []:
        if not isinstance(f, dict):
            continue
        if f.get("ext") == "mhtml" or (f.get("protocol") or "").startswith("mhtml"):
            continue  # 스토리보드
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        size = f.get("filesize") or f.get("filesize_approx")
        h = f.get("height")
        if vcodec and vcodec != "none" and isinstance(h, int) and h > 0:
            heights.add(h)
            if size:
                sizes[h] = max(sizes.get(h, 0), int(size))
        elif vcodec == "none" and acodec and acodec != "none":
            if size:
                audio_best = max(audio_best or 0, int(size))
    # 형식 목록이 없으면(일부 사이트) height 필드라도 사용
    if not heights and isinstance(data.get("height"), int):
        heights.add(data["height"])
    info.subtitles = _sub_names(data.get("subtitles"))
    info.auto_captions = _sub_names(data.get("automatic_captions"))
    info.heights = sorted(heights, reverse=True)
    info.size_by_height = sizes
    info.audio_size = audio_best
    return info
