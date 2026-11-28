"""외부 도구(yt-dlp, ffmpeg, JS 런타임) 찾기와 버전 확인."""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..paths import IS_MAC, IS_WINDOWS, app_root, bin_dir
from ..utils import no_window_flags
from ..i18n import tr

EXE = ".exe" if IS_WINDOWS else ""

# 도구별로 찾을 실행 파일 이름 후보
_CANDIDATES = {
    "yt-dlp": [f"yt-dlp{EXE}"] + ([] if IS_WINDOWS else ["yt-dlp_macos" if IS_MAC else "yt-dlp_linux"]),
    "ffmpeg": [f"ffmpeg{EXE}"],
    "ffprobe": [f"ffprobe{EXE}"],
    "deno": [f"deno{EXE}"],
    "node": [f"node{EXE}"],
    "bun": [f"bun{EXE}"],
}

LABELS = {
    "yt-dlp": tr("yt-dlp (다운로드 엔진)"),
    "ffmpeg": tr("ffmpeg (영상·음성 합치기/변환)"),
    "deno": tr("Deno (유튜브 JS 처리)"),
}


@dataclass
class Tool:
    name: str
    path: Optional[str] = None
    version: Optional[str] = None
    managed: bool = False  # Acortube bin 폴더에 설치된 것인지

    @property
    def ok(self) -> bool:
        return bool(self.path)


@dataclass
class Deps:
    ytdlp: Tool = field(default_factory=lambda: Tool("yt-dlp"))
    ffmpeg: Tool = field(default_factory=lambda: Tool("ffmpeg"))
    js: Optional[Tool] = None  # deno / node / bun 중 사용 가능한 것

    def ffmpeg_location(self) -> Optional[str]:
        """yt-dlp 가 PATH 에서 못 찾는 경우에만 위치를 알려준다."""
        if self.ffmpeg.ok and self.ffmpeg.managed:
            return str(Path(self.ffmpeg.path).parent)
        return None

    def js_runtime_arg(self) -> Optional[str]:
        """--js-runtimes 인자 값. deno 가 PATH 에 있으면 yt-dlp 가 알아서 찾지만 명시해도 무해."""
        if self.js and self.js.ok:
            return f"{self.js.name}:{self.js.path}"
        return None

    def missing_required(self) -> list[str]:
        missing = []
        if not self.ytdlp.ok:
            missing.append("yt-dlp")
        if not self.ffmpeg.ok:
            missing.append("ffmpeg")
        if not self.js:
            missing.append("deno")
        return missing


def _search_dirs() -> list[Path]:
    dirs = [bin_dir(), app_root() / "bin"]
    out, seen = [], set()
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def find_tool(name: str) -> Tool:
    managed_dir = bin_dir().resolve()
    for d in _search_dirs():
        for cand in _CANDIDATES.get(name, [name]):
            p = d / cand
            if p.is_file() and (IS_WINDOWS or os.access(p, os.X_OK)):
                return Tool(name, str(p), managed=p.resolve().parent == managed_dir)
    for cand in _CANDIDATES.get(name, [name]):
        found = shutil.which(cand)
        if found:
            return Tool(name, found, managed=False)
    return Tool(name)


def _run_version(path: str, flag: str) -> Optional[str]:
    try:
        r = subprocess.run(
            [path, flag],
            capture_output=True,
            timeout=30,
            creationflags=no_window_flags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (r.stdout or b"").decode("utf-8", "replace").strip()
    if r.returncode != 0 and not text:
        return None
    return text.splitlines()[0].strip() if text else None


def tool_version(tool: Tool) -> Optional[str]:
    if not tool.path:
        return None
    if tool.name in ("ffmpeg", "ffprobe"):
        line = _run_version(tool.path, "-version")
        if line:
            m = re.search(r"version\s+(\S+)", line)
            return m.group(1) if m else line
        return None
    line = _run_version(tool.path, "--version")
    if not line:
        return None
    if tool.name == "deno":
        m = re.search(r"deno\s+(\S+)", line)
        return m.group(1) if m else line
    return line.lstrip("v") if tool.name == "node" else line


def _version_tuple(v: Optional[str]) -> tuple:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3])


def check_all() -> Deps:
    """도구를 찾고 버전까지 확인 (블로킹 - 백그라운드 스레드에서 호출)."""
    deps = Deps(ytdlp=find_tool("yt-dlp"), ffmpeg=find_tool("ffmpeg"))
    deps.ytdlp.version = tool_version(deps.ytdlp)
    if deps.ytdlp.path and not deps.ytdlp.version:
        # 실행이 안 되는 깨진 파일
        deps.ytdlp.path = None
    deps.ffmpeg.version = tool_version(deps.ffmpeg)

    # JS 런타임: deno 우선, 없으면 node(22+) / bun
    for name in ("deno", "node", "bun"):
        t = find_tool(name)
        if not t.ok:
            continue
        t.version = tool_version(t)
        if not t.version:
            continue
        if name == "deno" and _version_tuple(t.version) < (2,):
            continue
        if name == "node" and _version_tuple(t.version) < (22,):
            continue
        deps.js = t
        break
    return deps


# ---------------------------------------------------------------------------
# 자동 설치용 다운로드 주소 (GitHub 'latest' 릴리스)
# ---------------------------------------------------------------------------

def _arch() -> str:
    m = platform.machine().lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    return "x64"


def download_spec(name: str) -> Optional[dict]:
    """설치 가능한 도구면 {url, archive, members} 반환. members 는 꺼낼 실행 파일 이름들."""
    arch = _arch()
    gh = "https://github.com"
    if name == "yt-dlp":
        if IS_WINDOWS:
            return {"url": f"{gh}/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
                    "archive": None, "save_as": "yt-dlp.exe"}
        if IS_MAC:
            return {"url": f"{gh}/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
                    "archive": None, "save_as": "yt-dlp"}
        asset = "yt-dlp_linux_aarch64" if arch == "arm64" else "yt-dlp_linux"
        return {"url": f"{gh}/yt-dlp/yt-dlp/releases/latest/download/{asset}",
                "archive": None, "save_as": "yt-dlp"}
    if name == "deno":
        if IS_WINDOWS:
            asset = "deno-aarch64-pc-windows-msvc.zip" if arch == "arm64" else "deno-x86_64-pc-windows-msvc.zip"
        elif IS_MAC:
            asset = "deno-aarch64-apple-darwin.zip" if arch == "arm64" else "deno-x86_64-apple-darwin.zip"
        else:
            asset = "deno-aarch64-unknown-linux-gnu.zip" if arch == "arm64" else "deno-x86_64-unknown-linux-gnu.zip"
        return {"url": f"{gh}/denoland/deno/releases/latest/download/{asset}",
                "archive": "zip", "members": [f"deno{EXE}"]}
    if name == "ffmpeg":
        base = f"{gh}/yt-dlp/FFmpeg-Builds/releases/download/latest"
        if IS_WINDOWS:
            asset = "ffmpeg-master-latest-winarm64-gpl.zip" if arch == "arm64" else "ffmpeg-master-latest-win64-gpl.zip"
            return {"url": f"{base}/{asset}", "archive": "zip",
                    "members": ["ffmpeg.exe", "ffprobe.exe"]}
        if IS_MAC:
            return None  # macOS 는 brew install ffmpeg 안내
        asset = "ffmpeg-master-latest-linuxarm64-gpl.tar.xz" if arch == "arm64" else "ffmpeg-master-latest-linux64-gpl.tar.xz"
        return {"url": f"{base}/{asset}", "archive": "tar.xz", "members": ["ffmpeg", "ffprobe"]}
    return None


MANUAL_HINTS = {
    "ffmpeg": tr("macOS 는 터미널에서 'brew install ffmpeg' 로 설치해 주세요."),
}
