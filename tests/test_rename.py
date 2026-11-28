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


def test_app_name():
    assert tubegetapp.APP_NAME == "Acortube"


def test_old_folder_is_moved(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    old, new = _dirs(p, tmp_path)
    (old / "bin").mkdir(parents=True)
    (old / "settings.json").write_text('{"a": 1}', encoding="utf-8")
    d = p.data_dir()
    assert d == new
    assert (d / "settings.json").read_text(encoding="utf-8") == '{"a": 1}'
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


def teardown_module(_module):
    importlib.reload(paths)
