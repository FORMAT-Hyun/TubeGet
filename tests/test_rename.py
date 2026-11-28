"""이름 변경(TubeGet → Acortube): 예전 데이터 폴더를 새 이름으로 옮기는지 확인."""
import importlib
import os

os.environ.setdefault("TUBEGET_LANG", "ko")

import tubegetapp  # noqa: E402
import tubegetapp.paths as paths  # noqa: E402


def _fresh(monkeypatch, tmp_path):
    monkeypatch.delenv("TUBEGET_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return importlib.reload(paths)


def test_app_name():
    assert tubegetapp.APP_NAME == "Acortube"


def test_old_folder_is_moved(monkeypatch, tmp_path):
    old = tmp_path / ("TubeGet" if paths.IS_WINDOWS else "tubeget")
    (old / "bin").mkdir(parents=True)
    (old / "settings.json").write_text('{"a": 1}', encoding="utf-8")
    p = _fresh(monkeypatch, tmp_path)
    d = p.data_dir()
    assert d.name.lower() == "acortube"
    assert (d / "settings.json").read_text(encoding="utf-8") == '{"a": 1}'
    assert (d / "bin").is_dir() and not old.exists()
    assert p.data_dir() == d


def test_new_install_uses_new_folder(monkeypatch, tmp_path):
    p = _fresh(monkeypatch, tmp_path)
    assert p.data_dir().name.lower() == "acortube"


def test_existing_new_folder_wins(monkeypatch, tmp_path):
    old = tmp_path / ("TubeGet" if paths.IS_WINDOWS else "tubeget")
    new = tmp_path / ("Acortube" if paths.IS_WINDOWS else "acortube")
    old.mkdir()
    new.mkdir()
    p = _fresh(monkeypatch, tmp_path)
    assert p.data_dir() == new and old.exists()


def teardown_module(_module):
    importlib.reload(paths)
