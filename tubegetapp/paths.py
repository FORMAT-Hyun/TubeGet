"""앱 데이터/바이너리/리소스 경로."""
from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def data_dir() -> Path:
    """설정, 기록, 내려받은 도구(bin)를 두는 사용자별 폴더."""
    override = os.environ.get("TUBEGET_HOME")
    if override:
        p = Path(override)
    elif IS_WINDOWS:
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        p = Path(base) / "TubeGet"
    elif IS_MAC:
        p = Path.home() / "Library" / "Application Support" / "TubeGet"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        p = Path(base) / "tubeget"
    p.mkdir(parents=True, exist_ok=True)
    return p


def bin_dir() -> Path:
    p = data_dir() / "bin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_root() -> Path:
    """실행 파일(빌드 시) 또는 프로젝트 루트."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """assets 등 번들 리소스 경로 (PyInstaller 대응)."""
    base = Path(getattr(sys, "_MEIPASS", app_root()))
    return base.joinpath(*parts)


def default_download_dir() -> Path:
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path.home()
    return downloads / "TubeGet"
