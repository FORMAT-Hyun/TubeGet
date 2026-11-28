"""macOS: ffmpeg/ffprobe 자동 설치 주소와, 파일 여러 개짜리 설치(extra) 처리."""
import os
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("TUBEGET_LANG", "ko")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("TUBEGET_HOME", tempfile.mkdtemp(prefix="acortube-mac-"))

from tubegetapp.core import deps  # noqa: E402
from tubegetapp.core import installer  # noqa: E402


def _as_mac(monkeypatch, machine):
    monkeypatch.setattr(deps, "IS_MAC", True)
    monkeypatch.setattr(deps, "IS_WINDOWS", False)
    monkeypatch.setattr(deps.platform, "machine", lambda: machine)


def test_mac_ffmpeg_spec_apple_silicon(monkeypatch):
    _as_mac(monkeypatch, "arm64")
    spec = deps.download_spec("ffmpeg")
    assert spec["url"].endswith("/macos/arm64/release/ffmpeg.zip") and spec["members"] == ["ffmpeg"]
    assert spec["extra"][0]["url"].endswith("/macos/arm64/release/ffprobe.zip")
    assert spec["extra"][0]["members"] == ["ffprobe"]


def test_mac_ffmpeg_spec_intel(monkeypatch):
    _as_mac(monkeypatch, "x86_64")
    spec = deps.download_spec("ffmpeg")
    assert "/macos/amd64/" in spec["url"] and "/macos/amd64/" in spec["extra"][0]["url"]


def test_mac_other_tools(monkeypatch):
    _as_mac(monkeypatch, "arm64")
    assert deps.download_spec("yt-dlp")["url"].endswith("/yt-dlp_macos")
    assert deps.download_spec("deno")["url"].endswith("deno-aarch64-apple-darwin.zip")


def _zip(path: Path, name: str, data: bytes) -> str:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(name, data)
    return path.resolve().as_uri()


def test_install_with_extra_parts(tmp_path):
    a = _zip(tmp_path / "ffmpeg.zip", "ffmpeg", b"ff")
    b = _zip(tmp_path / "ffprobe.zip", "sub/ffprobe", b"fp")
    spec = {"url": a, "archive": "zip", "members": ["ffmpeg"],
            "extra": [{"url": b, "archive": "zip", "members": ["ffprobe"]}]}
    worker = installer.DepInstaller(["ffmpeg"])
    worker._install("ffmpeg", spec)
    bin_dir = installer.bin_dir()
    assert (bin_dir / "ffmpeg").read_bytes() == b"ff"
    assert (bin_dir / "ffprobe").read_bytes() == b"fp"
