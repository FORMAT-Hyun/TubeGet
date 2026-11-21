"""다운로드 목록 저장/복원 (프로그램을 껐다 켜도 이어서 받기)."""
from __future__ import annotations

import json

from ..paths import data_dir
from .runner import DONE, DownloadJob


def _path():
    return data_dir() / "queue.json"


def save_jobs(jobs: list[DownloadJob]) -> None:
    items = [j.to_dict() for j in jobs if j.state != DONE]
    try:
        tmp = _path().with_suffix(".tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(_path())
    except OSError:
        pass


def load_jobs() -> list[DownloadJob]:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    jobs = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and item.get("url"):
            try:
                jobs.append(DownloadJob.from_dict(item))
            except (TypeError, ValueError):
                continue
    return jobs
