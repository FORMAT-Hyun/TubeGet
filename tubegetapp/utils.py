"""포맷팅/파일/URL 관련 작은 도우미들."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from .i18n import tr

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def human_size(n: Optional[float]) -> str:
    if n is None or n < 0:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}" if size < 100 else f"{size:.0f} {unit}"
        size /= 1024
    return "?"


def human_speed(bps: Optional[float]) -> str:
    if not bps:
        return ""
    return f"{human_size(bps)}/s"


def human_duration(sec: Optional[float]) -> str:
    if sec is None:
        return ""
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def human_eta(sec: Optional[float]) -> str:
    if sec is None:
        return ""
    return tr("남은 시간 {human_duration}").format(human_duration=human_duration(sec))


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """윈도우에서도 안전한 폴더/파일 이름으로 정리."""
    name = _INVALID_CHARS.sub("_", name or "").strip().rstrip(". ")
    if not name:
        name = "untitled"
    if name.upper().split(".")[0] in _RESERVED:
        name = f"_{name}"
    return name[:max_len].rstrip(". ") or "untitled"


def parse_timecode(text: str) -> Optional[float]:
    """'90', '1:30', '01:02:03', '1:30.5' -> 초. 빈 값/잘못된 값은 None."""
    text = (text or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) > 3:
        return None
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return total


def format_timecode(sec: float) -> str:
    """yt-dlp --download-sections 에 넘길 형식."""
    whole = int(sec)
    frac = sec - whole
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    base = f"{h:02d}:{m:02d}:{s:02d}"
    if frac > 1e-6:
        base += f"{frac:.3f}"[1:]
    return base


_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_YT_RE = re.compile(
    r"^https?://(?:(?:www|m|music)\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/\S*",
    re.IGNORECASE,
)


def is_url(text: str) -> bool:
    return bool(_URL_RE.match((text or "").strip()))


def is_youtube_url(text: str) -> bool:
    return bool(_YT_RE.match((text or "").strip()))


def has_playlist_param(url: str) -> bool:
    return bool(re.search(r"[?&]list=[\w-]+", url or ""))


def has_video_param(url: str) -> bool:
    return bool(re.search(r"[?&]v=[\w-]+", url or "")) or "youtu.be/" in (url or "")


def no_window_flags() -> int:
    """윈도우에서 콘솔 창이 깜빡이지 않게 하는 subprocess 플래그."""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return 0


def reveal_in_explorer(path: str) -> None:
    """파일이면 선택된 상태로, 폴더면 그 폴더를 연다."""
    p = Path(path)
    try:
        if sys.platform == "win32":
            if p.is_file():
                subprocess.Popen(["explorer", "/select,", str(p)], creationflags=no_window_flags())
            else:
                subprocess.Popen(["explorer", str(p if p.exists() else p.parent)])
        elif sys.platform == "darwin":
            if p.is_file():
                subprocess.Popen(["open", "-R", str(p)])
            else:
                subprocess.Popen(["open", str(p if p.exists() else p.parent)])
        else:
            target = p.parent if p.is_file() else p
            subprocess.Popen(["xdg-open", str(target)])
    except OSError:
        pass
