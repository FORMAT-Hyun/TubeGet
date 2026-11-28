"""이름 변경(TubeGet → Acortube): 예전 데이터 폴더를 새 이름으로 옮기는지 확인 (Windows / macOS / Linux)."""
import importlib
import os
import pathlib

os.environ.setdefault("TUBEGET_LANG", "ko")

import tubegetapp  # noqa: E402
import tubegetapp.paths as paths  # noqa: E402


def _fresh(monkeypatch, tmp_path):
    """모든 사용자 폴더를 tmp_path 아래로 돌려서 진짜 홈 폴더를 건드리지 않는다."""
    monkeypatch.delenv("TUBEGET_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    return importlib.reload(paths)


def _dirs(p, tmp_path):
    """(예전 폴더, 새 폴더)"""
    if p.IS_WINDOWS:
        return tmp_path / "TubeGet", tmp_path / "Acortube"
    if p.IS_MAC:
        base = tmp_path / "Library" / "Application Support"
        return base / "TubeGet", base / "Acortube"
    return tmp_path / "tubeget", tmp_path / "acortube"


OUR_SETTINGS = '{"download_dir": "C:/x", "filename_template": "%(title)s.%(ext)s", "mode": "video"}'


def test_app_name():
    assert tubegetapp.APP_NAME == "Acortube"


def test_old_folder_is_moved(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    old, new = _dirs(p, tmp_path)
    (old / "bin").mkdir(parents=True)
    (old / "settings.json").write_text(OUR_SETTINGS, encoding="utf-8")
    d = p.data_dir()
    assert d == new
    assert (d / "settings.json").read_text(encoding="utf-8") == OUR_SETTINGS
    assert (d / "bin").is_dir() and not old.exists()
    assert p.data_dir() == d


def test_new_install_uses_new_folder(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    _old, new = _dirs(p, tmp_path)
    assert p.data_dir() == new


def test_existing_new_folder_wins(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    old, new = _dirs(p, tmp_path)
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    assert p.data_dir() == new and old.exists()


def test_other_programs_folder_is_left_alone(monkeypatch, tmp_path):
    """같은 이름의 다른 프로그램(원조 TubeGet)이 쓰는 폴더는 옮기지 않는다."""
    p = _fresh(monkeypatch, tmp_path)
    old, new = _dirs(p, tmp_path)
    old.mkdir(parents=True)
    (old / "settings.json").write_text('{"theme": "light", "server": "x"}', encoding="utf-8")
    (old / "other.db").write_bytes(b"data")
    d = p.data_dir()
    assert d == new and new.is_dir()
    assert (old / "other.db").exists() and (old / "settings.json").exists()
    assert p.data_dir() == new


def test_folder_without_settings_is_left_alone(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    old, new = _dirs(p, tmp_path)
    (old / "cache").mkdir(parents=True)
    assert p.data_dir() == new and (old / "cache").is_dir()


def teardown_module(_module):
    importlib.reload(paths)
