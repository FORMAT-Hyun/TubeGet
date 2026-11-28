"""사용자 설정 (JSON 저장)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .paths import data_dir, default_download_dir
from .i18n import AUTO, LANGUAGES, tr

FILENAME_PRESETS = {
    tr("제목 [영상ID]"): "%(title)s [%(id)s].%(ext)s",
    tr("제목"): "%(title)s.%(ext)s",
    tr("채널 - 제목"): "%(uploader)s - %(title)s.%(ext)s",
    tr("업로드 날짜 제목"): "%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s",
}

COOKIE_BROWSERS = [
    ("", tr("사용 안 함")),
    ("firefox", tr("Firefox (가장 잘 됨)")),
    ("chrome", "Chrome"),
    ("edge", "Edge"),
    ("whale", "Whale"),
    ("brave", "Brave"),
    ("opera", "Opera"),
    ("vivaldi", "Vivaldi"),
    ("chromium", "Chromium"),
    ("safari", "Safari (macOS)"),
]


@dataclass
class Settings:
    language: str = "auto"         # auto(시스템 언어) | ko | en  (바꾸면 다시 시작해야 적용)
    download_dir: str = field(default_factory=lambda: str(default_download_dir()))
    max_concurrent: int = 2

    # 메인 창 옵션 (마지막 선택이 기억됨)
    mode: str = "video"            # video | audio
    max_height: int = 0            # 0 = 최고 화질
    container: str = "mp4"         # mp4 | mkv | webm
    compat_h264: bool = False
    audio_format: str = "mp3"      # mp3 | m4a | opus | flac | wav | best
    embed_thumbnail: bool = True
    sub_mode: str = "embed"        # 마지막으로 고른 자막 저장 방식
    auto_download: bool = False    # 바로 받기: 링크를 붙여넣자마자 지금 설정으로 다운로드

    # 설정 창
    audio_quality: str = "0"       # 0(최고 VBR) | 320K | 192K | 128K
    embed_metadata: bool = True
    sub_default_langs: str = ""    # 영상을 불러올 때 자동으로 골라둘 자막 언어 (비우면 안 고름)
    sub_default_auto: bool = False # 올린 자막이 없으면 자동 생성 자막으로 골라두기
    dub_default: str = ""          # 재생목록에서 기본으로 받을 더빙(음성 언어) 코드. 비우면 원본 음성
    overwrite_existing: bool = False
    audio_tags_default: bool = True      # 음원 태그 기본으로 넣기
    audio_tag_clean: bool = True         # 음원 태그 자동 정리 ('아티스트 - 곡명' 나누기, 꼬리표 지우기)
    delete_partials_on_remove: bool = True
    filename_template: str = FILENAME_PRESETS[tr("제목 [영상ID]")]
    cookies_browser: str = ""
    rate_limit: str = ""
    playlist_folder: bool = True
    playlist_numbering: bool = True
    prefer_playlist: bool = False
    auto_update_ytdlp: bool = True
    # 기본은 꺼짐. 예전 설정 파일의 clipboard_watch(True)는 이름이 달라서 무시됨
    clipboard_autofetch: bool = False
    notify_on_finish: bool = True
    last_update_check: str = ""    # 마지막 yt-dlp 업데이트 확인 시각 (ISO)
    splitter_sizes: str = ""       # "위,아래" 픽셀
    options_collapsed: bool = False

    # 구독 (자동 백업)
    subs_auto_check: bool = True   # 구독한 채널·재생목록을 자동으로 확인
    subs_interval_hours: int = 3   # 자동 확인 간격 (시간)
    subs_last_check: str = ""      # 마지막으로 전체를 확인한 시각 (ISO)
    close_to_tray: bool = False    # 창을 닫아도 트레이에서 계속 실행 (구독 확인·다운로드 계속)

    @classmethod
    def path(cls) -> Path:
        return data_dir() / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        try:
            raw = json.loads(cls.path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return s
        if not isinstance(raw, dict):
            return s
        for f in fields(cls):
            if f.name in raw:
                value = raw[f.name]
                default = getattr(s, f.name)
                if isinstance(default, bool):
                    value = bool(value)
                elif isinstance(default, int):
                    try:
                        value = int(value)
                    except (TypeError, ValueError):
                        continue
                elif isinstance(default, str):
                    value = str(value)
                setattr(s, f.name, value)
        s.max_concurrent = min(max(s.max_concurrent, 1), 5)
        if s.language != AUTO and s.language not in LANGUAGES:
            s.language = AUTO
        if s.mode not in ("video", "audio"):
            s.mode = "video"
        if s.sub_mode not in ("embed", "file", "both"):
            s.sub_mode = "embed"
        return s

    def save(self) -> None:
        try:
            tmp = self.path().with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path())
        except OSError:
            pass
