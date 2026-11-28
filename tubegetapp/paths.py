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
        base = Path(os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
        p = _migrate(base / "TubeGet", base / "Acortube")
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
        p = _migrate(base / "TubeGet", base / "Acortube")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config"))
        p = _migrate(base / "tubeget", base / "acortube")
    p.mkdir(parents=True, exist_ok=True)
    return p


_migrated = False


def _migrate(old: Path, new: Path) -> Path:
    """예전 이름(TubeGet)의 폴더가 있으면 새 이름(Acortube)으로 한 번 옮긴다.

    설정·기록·설치된 도구를 그대로 이어 쓰기 위해서. 옮기지 못하면(다른 프로그램이 쓰는 중 등)
    예전 폴더를 그대로 쓴다.
    """
    global _migrated
    if _migrated or new.exists() or not old.is_dir():
        _migrated = True
        return new if new.exists() or not old.is_dir() or not _looks_like_ours(old) else old
    _migrated = True
    if not _looks_like_ours(old):
        # 같은 이름의 다른 프로그램('TubeGet')이 쓰는 폴더일 수 있으니 건드리지 않는다
        return new
    try:
        old.rename(new)
        return new
    except OSError:
        return old


# 우리 앱의 settings.json 에만 있는 항목들 (둘 이상 있으면 우리 폴더로 본다)
_OUR_SETTING_KEYS = {"download_dir", "filename_template", "auto_update_ytdlp", "embed_thumbnail",
                     "sub_mode", "clipboard_autofetch", "audio_tags_default", "max_concurrent"}


def _looks_like_ours(folder: Path) -> bool:
    """예전 TubeGet 폴더가 우리 앱(Acortube 의 예전 이름)이 만든 것인지 settings.json 으로 확인."""
    import json
    try:
        raw = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(raw, dict) and len(_OUR_SETTING_KEYS & set(raw)) >= 2


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
    return downloads / "Acortube"
