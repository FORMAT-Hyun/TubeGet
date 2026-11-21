"""다운로드 기록 (JSON)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from ..paths import data_dir

MAX_ITEMS = 500


class History:
    def __init__(self) -> None:
        self.path = data_dir() / "history.json"
        self.items: list[dict] = []
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
        except (OSError, ValueError):
            self.items = []

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.items[:MAX_ITEMS], ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    def add(self, *, title: str, url: str, filepath: Optional[str], summary: str, ok: bool,
            error: Optional[str] = None, thumbnail: Optional[str] = None) -> dict:
        item = {
            "title": title,
            "url": url,
            "filepath": filepath or "",
            "summary": summary,
            "ok": ok,
            "error": error or "",
            "thumbnail": thumbnail or "",
            "time": datetime.now().isoformat(timespec="seconds"),
        }
        self.items.insert(0, item)
        del self.items[MAX_ITEMS:]
        self.save()
        return item

    def remove(self, item: dict) -> None:
        try:
            self.items.remove(item)
        except ValueError:
            return
        self.save()

    def clear(self) -> None:
        self.items = []
        self.save()
