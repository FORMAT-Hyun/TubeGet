"""음원 태그(제목·아티스트·앨범·연도) 추측과 yt-dlp 인자 만들기."""
from __future__ import annotations

import re
from typing import Optional
from ..i18n import tr

# (Official Video), [MV], (Lyrics), 【Official Audio】 같은 꼬리표
_TAIL_WORDS = (r"(?:official\s*)?(?:music\s*)?(?:video|audio|mv|m/v|lyrics?|lyric\s*video|visuali[sz]er"
               r"|performance\s*video|hd|4k)")
CLEAN_RE_TEXT = r"(?i)\s*[\(\[【]" + _TAIL_WORDS + r"[^\)\]】]*[\)\]】]"
_CLEAN_RE = re.compile(CLEAN_RE_TEXT)
_SPLIT_RE = re.compile(r"^(.+?)\s+[-–—]\s+(.+)$")
_TOPIC_RE = re.compile(r"\s*-\s*Topic$")

FIELDS = ["title", "artist", "album", "year"]
LABELS = {"title": tr("제목"), "artist": tr("아티스트"), "album": tr("앨범"), "year": tr("연도")}
_META_KEY = {"title": "meta_title", "artist": "meta_artist", "album": "meta_album", "year": "meta_date"}


def clean_title(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _CLEAN_RE.sub("", text or "")).strip(" -|")


def raw_tags(info) -> dict:
    """yt-dlp 가 기본으로 넣는 값 (정리 전)."""
    year = ""
    if getattr(info, "release_year", None):
        year = str(info.release_year)
    elif getattr(info, "upload_date", ""):
        year = info.upload_date[:4]
    return {
        "title": info.track or info.title or "",
        "artist": info.artist or info.uploader or "",
        "album": info.album or "",
        "year": year,
    }


def guess_tags(info) -> dict:
    """제목에서 '아티스트 - 곡명'을 나누고 꼬리표를 지운 추천 값."""
    tags = raw_tags(info)
    if not info.track:
        m = _SPLIT_RE.match(info.title or "")
        if m:
            tags["artist"], tags["title"] = m.group(1).strip(), m.group(2).strip()
    tags["title"] = clean_title(tags["title"])
    tags["artist"] = _TOPIC_RE.sub("", tags["artist"]).strip()
    return tags


def _literal(value: str) -> str:
    """--parse-metadata 의 FROM 자리에 넣을 '글자 그대로' 템플릿."""
    value = (value or "").replace("\r", " ").replace("\n", " ").rstrip("\\")
    return "#" + value.replace("%", "%%").replace(":", "\\:")


def custom_args(values: dict) -> list[str]:
    args: list[str] = []
    for f in FIELDS:
        if f not in values or values[f] is None:
            continue
        v = str(values[f]).strip()
        key = _META_KEY[f]
        if v:
            args += ["--parse-metadata", f"{_literal(v)}:#(?P<{key}>.*)"]
        else:
            args += ["--parse-metadata", f":(?P<{key}>)"]   # 빈 값 = 그 태그 안 넣음
    return args


def smart_args() -> list[str]:
    """재생목록처럼 영상마다 값을 볼 수 없을 때: yt-dlp 가 영상마다 자동으로 정리."""
    return [
        "--parse-metadata", "%(track,title)s:%(meta_title)s",
        "--parse-metadata", "%(artist,creator,uploader)s:%(meta_artist)s",
        "--parse-metadata", "title:(?P<meta_artist>.+?) [-–—] (?P<meta_title>.+)",
        "--replace-in-metadata", "meta_title", CLEAN_RE_TEXT, "",
        "--replace-in-metadata", "meta_artist", r" - Topic$", "",
    ]


def summary(values: Optional[dict]) -> str:
    if not values:
        return ""
    return " / ".join(v for v in (values.get("artist"), values.get("title")) if v)
