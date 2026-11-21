"""다국어(i18n) 테스트: 번역 누락, 자리표시자 불일치, 언어 전환."""
import ast
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("TUBEGET_HOME", tempfile.mkdtemp(prefix="tubeget-test-"))
os.environ["TUBEGET_LANG"] = "ko"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tubegetapp import i18n  # noqa: E402
from tubegetapp.locales import en  # noqa: E402

_PLACEHOLDER = re.compile(r"\{\w+\}|%\(\w+\)\w")
# 화면에 안 쓰이는 번역 키는 허용 (예: 단계 이름처럼 tr() 밖에서 쓰는 글)
_EXTRA_OK = {"베타", "알파"}
_BILINGUAL_OK = {"언어 / Language"}   # 잘못된 언어로 바뀌어도 찾을 수 있게 일부러 두 언어 병기


def _source_keys() -> set:
    keys = set()
    for path in (ROOT / "tubegetapp").rglob("*.py"):
        if "locales" in path.parts or path.name == "i18n.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                keys.add(node.args[0].value)
    return keys


def test_every_tr_text_has_english():
    missing = sorted(k for k in _source_keys() if k not in en.STRINGS)
    assert not missing, f"영어 번역이 없는 글 {len(missing)}개: {missing[:5]}"


def test_no_stale_english_keys():
    stale = sorted(k for k in en.STRINGS if k not in _source_keys() and k not in _EXTRA_OK)
    assert not stale, f"코드에서 안 쓰는 번역 키: {stale[:5]}"


def test_placeholders_match():
    bad = [k for k, v in en.STRINGS.items() if sorted(_PLACEHOLDER.findall(k)) != sorted(_PLACEHOLDER.findall(v))]
    assert not bad, f"자리표시자가 다른 번역: {bad[:5]}"


def test_translations_are_not_empty_or_korean():
    hangul = re.compile("[가-힣]")
    bad = [k for k, v in en.STRINGS.items() if not v.strip() or (hangul.search(v) and k not in _BILINGUAL_OK)]
    assert not bad, f"비었거나 한글이 남은 번역: {bad[:5]}"


def test_switching_language():
    try:
        assert i18n.set_language("ko") == "ko"
        assert i18n.tr("설정") == "설정"
        assert i18n.set_language("en") == "en"
        assert i18n.tr("설정") == "Settings"
        assert i18n.tr("번역이 없는 문장") == "번역이 없는 문장"   # 없으면 원문
        assert i18n.tr("{name} 설치 완료").format(name="ffmpeg") == "ffmpeg installed"
        assert i18n.set_language("zz") == "ko"                    # 모르는 언어 → 기본값
    finally:
        i18n.set_language("ko")


def test_resolve_preference():
    assert i18n.resolve("ko") == "ko"
    assert i18n.resolve("en") == "en"
    assert i18n.resolve("auto") in i18n.LANGUAGES
    assert i18n.resolve("nonsense") in i18n.LANGUAGES


def test_settings_language_roundtrip():
    from tubegetapp.config import Settings
    s = Settings()
    assert s.language == "auto"
    s.language = "en"
    s.save()
    assert Settings.load().language == "en"
    s.language = "xx"
    s.save()
    assert Settings.load().language == "auto"   # 모르는 값은 자동으로
