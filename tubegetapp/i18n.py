"""다국어(i18n) 지원.

화면에 보이는 글은 한국어 원문을 그대로 키로 쓰는 `tr("한국어 문장")` 으로 감싼다.
- 한국어를 쓰면 원문을 그대로 돌려주고, 다른 언어면 `locales/<언어>.py` 의 번역을 찾는다.
- 번역이 없으면 한국어 원문이 그대로 나온다 (빈 글자가 되는 일은 없음).
- 값이 들어가는 문장은 `tr("{n}개 선택").format(n=3)` 처럼 자리표시자를 쓴다.

언어는 프로그램을 켤 때 한 번 정해진다 (설정에서 바꾸면 다시 시작해야 적용).
우선순위: 환경변수 TUBEGET_LANG > 설정 파일의 language > 시스템 언어(한국어 외에는 영어).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .paths import data_dir

# 코드: 그 언어 이름(그 언어로 쓴 것)
LANGUAGES: dict[str, str] = {
    "ko": "한국어",
    "en": "English",
}
DEFAULT_LANGUAGE = "ko"
AUTO = "auto"   # 설정값: 시스템 언어를 따라감

_translations: dict[str, str] = {}
_current = DEFAULT_LANGUAGE


def _stored_preference() -> str:
    """settings.json 의 language 값 (없으면 'auto')."""
    try:
        raw = json.loads((data_dir() / "settings.json").read_text(encoding="utf-8"))
        value = raw.get("language", AUTO) if isinstance(raw, dict) else AUTO
    except (OSError, ValueError):
        return AUTO
    return value if isinstance(value, str) else AUTO


def system_language() -> str:
    """운영체제 언어 → 지원하는 언어 코드. 한국어가 아니면 영어."""
    try:
        from PySide6.QtCore import QLocale
        name = QLocale.system().name()   # 예: ko_KR, en_US
    except Exception:  # noqa: BLE001
        name = os.environ.get("LANG", "")
    return "ko" if name.lower().startswith("ko") else "en"


def resolve(preference: Optional[str]) -> str:
    """설정값('auto' 포함) → 실제로 쓸 언어 코드."""
    if preference in LANGUAGES:
        return preference  # type: ignore[return-value]
    return system_language()


def _load(code: str) -> dict[str, str]:
    if code == "en":
        from .locales import en
        return en.STRINGS
    return {}


def set_language(code: str) -> str:
    """언어를 바꾼다 (이미 만들어진 화면은 그대로이므로 보통 시작할 때만 호출)."""
    global _current, _translations
    _current = code if code in LANGUAGES else DEFAULT_LANGUAGE
    _translations = _load(_current)
    return _current


def current_language() -> str:
    return _current


def tr(text: str) -> str:
    """한국어 원문 → 현재 언어의 글. 번역이 없으면 원문."""
    if not _translations:
        return text
    return _translations.get(text, text)


def _init() -> None:
    set_language(resolve(os.environ.get("TUBEGET_LANG") or _stored_preference()))


_init()
