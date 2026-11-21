"""다운로드 옵션 → yt-dlp 명령줄 인자 변환."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from typing import Optional

from ..utils import format_timecode, sanitize_filename
from . import tags
from .deps import Deps
from .progress import PRINT_ARGS, PROGRESS_TEMPLATE

VIDEO_CONTAINERS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = [
    ("mp3", "MP3"),
    ("m4a", "M4A (AAC)"),
    ("opus", "Opus"),
    ("flac", "FLAC (무손실)"),
    ("wav", "WAV (무압축)"),
    ("best", "원본 그대로"),
]
AUDIO_QUALITIES = [
    ("0", "최고 (VBR)"),
    ("320K", "320 kbps"),
    ("192K", "192 kbps"),
    ("128K", "128 kbps"),
]
HEIGHT_CHOICES = [2160, 1440, 1080, 720, 480, 360, 240, 144]

_LOSSY_AUDIO = {"mp3", "m4a", "opus"}
_THUMB_AUDIO = {"mp3", "m4a", "opus", "flac", "best"}
_THUMB_VIDEO = {"mp4", "mkv"}


def height_label(h: int) -> str:
    names = {4320: " (8K)", 2160: " (4K)", 1440: " (QHD)", 1080: " (FHD)", 720: " (HD)"}
    return f"{h}p{names.get(h, '')}"


@dataclass
class DownloadOptions:
    mode: str = "video"                 # video | audio
    max_height: int = 0                 # 0 = 최고
    container: str = "mp4"
    compat_h264: bool = False
    audio_format: str = "mp3"
    audio_quality: str = "0"
    sub_langs: str = ""                 # 받을 자막 언어 코드 (쉼표). 비면 자막 없음
    auto_subs: bool = False             # 자동 생성 자막 허용
    dub_lang: str = ""                  # 더빙(음성 언어) 코드. 비면 원본 음성
    sub_mode: str = "embed"             # embed(영상에 넣기) | file(.srt 따로) | both
    overwrite: bool = False             # 이미 있는 파일 덮어쓰기
    audio_tags: bool = True             # 음원: 태그 넣기 (끄면 태그를 모두 비움)
    tag_values: Optional[dict] = None   # 음원: 직접 정한 태그 값 {title, artist, album, year}
    tag_smart: bool = False             # 음원: 영상마다 '아티스트 - 곡명' 자동 정리 (재생목록용)
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    output_dir: str = "."
    filename_template: str = "%(title)s [%(id)s].%(ext)s"
    subfolder: str = ""                 # 재생목록 폴더 이름
    index: Optional[int] = None         # 재생목록 번호 (파일명 앞에 붙음)
    index_width: int = 2
    cookies_browser: str = ""
    rate_limit: str = ""
    section_start: Optional[float] = None
    section_end: Optional[float] = None

    def copy(self, **changes) -> "DownloadOptions":
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DownloadOptions":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in names})

    @property
    def has_subs(self) -> bool:
        return bool(self.sub_langs.strip())

    def effective_sub_mode(self) -> str:
        # 음원에는 자막을 넣을 수 없으니 파일로만
        return "file" if self.mode == "audio" else self.sub_mode

    @property
    def has_dub(self) -> bool:
        return bool(self.dub_lang.strip())

    def dub_selector(self) -> str:
        """음성 트랙 선택 조건. 그 언어 트랙이 없는 영상은 원본 음성으로 받는다."""
        lang = "".join(ch for ch in self.dub_lang.strip() if ch.isalnum() or ch in "-_")
        return f"[language^={lang}]" if lang else ""

    def subs_summary(self) -> str:
        if not self.has_subs:
            return ""
        mode = {"embed": "넣기", "file": "파일", "both": "넣기+파일"}.get(self.effective_sub_mode(), "")
        return f"자막 {self.sub_langs} ({mode})"

    def summary(self) -> str:
        """큐에 표시할 짧은 설명."""
        if self.mode == "audio":
            label = dict(AUDIO_FORMATS).get(self.audio_format, self.audio_format)
            text = f"음원 · {label}"
            if not self.audio_tags:
                text += " · 태그 끔"
            elif self.tag_values:
                text += " · 태그 편집"
            elif self.tag_smart:
                text += " · 태그 자동정리"
            if self.has_dub:
                text += f" · 더빙 {self.dub_lang}"
            if self.has_subs:
                text += " · " + self.subs_summary()
        else:
            q = height_label(self.max_height) if self.max_height else "최고 화질"
            text = f"영상 · {q} · {self.container.upper()}"
            if self.compat_h264:
                text += " · H.264"
            if not self.embed_metadata:
                text += " · 태그 끔"
            elif self.tag_values:
                text += " · 태그 편집"
            if self.has_dub:
                text += f" · 더빙 {self.dub_lang}"
            if self.has_subs:
                text += " · " + self.subs_summary()
        if self.section_start is not None or self.section_end is not None:
            text += " · 구간"
        return text

    def output_template(self) -> str:
        template = self.filename_template or "%(title)s [%(id)s].%(ext)s"
        if self.section_start is not None or self.section_end is not None:
            stem, dot, ext = template.rpartition(".")
            if dot and "%(ext)s" in ext:
                template = f"{stem} (구간 %(section_start)d-%(section_end)d).{ext}"
        if self.index is not None:
            template = f"{self.index:0{max(self.index_width, 2)}d} - {template}"
        if self.subfolder:
            folder = sanitize_filename(self.subfolder).replace("%", "%%")
            template = f"{folder}/{template}"
        return template


def build_args(opts: DownloadOptions, url: str, deps: Optional[Deps] = None) -> list[str]:
    args: list[str] = [
        "--ignore-config",
        "--newline",
        "--color", "never",
        "--encoding", "utf-8",
        "--progress",
        "--progress-template", PROGRESS_TEMPLATE,
        *PRINT_ARGS,
        "--no-simulate",
        "--no-playlist",
        "--continue",
        "--no-mtime",
        "-P", opts.output_dir,
        "-o", opts.output_template(),
    ]

    if opts.mode == "audio":
        sel = opts.dub_selector()
        args += ["-f", f"ba{sel}/ba/b" if sel else "ba/b", "-x"]
        if opts.audio_format != "best":
            args += ["--audio-format", opts.audio_format]
        if opts.audio_format in _LOSSY_AUDIO:
            args += ["--audio-quality", opts.audio_quality or "0"]
        if opts.audio_tags:
            if opts.embed_thumbnail and opts.audio_format in _THUMB_AUDIO:
                args += ["--embed-thumbnail"]
            args += ["--embed-metadata"]
            if opts.tag_values:
                args += tags.custom_args(opts.tag_values)
            elif opts.tag_smart:
                args += tags.smart_args()
        else:
            # 원본에 붙어 있던 정보까지 모두 비운 깨끗한 파일
            args += ["--postprocessor-args", "ExtractAudio:-map_metadata -1"]
    else:
        sort: list[str] = []
        if opts.compat_h264:
            sort += ["vcodec:h264"]
        if opts.max_height:
            sort += [f"res:{opts.max_height}"]
        if opts.compat_h264:
            sort += ["acodec:aac"]
        if opts.container == "mp4":
            sort += ["ext:mp4:m4a"]
        elif opts.container == "webm":
            sort += ["ext:webm:webm"]
        sel = opts.dub_selector()
        args += ["-f", f"bv*+ba{sel}/bv*+ba/b" if sel else "bv*+ba/b"]
        if sort:
            args += ["-S", ",".join(sort)]
        args += ["--merge-output-format", opts.container]
        if opts.embed_thumbnail and opts.container in _THUMB_VIDEO:
            args += ["--embed-thumbnail"]

    args += subtitle_args(opts)

    if opts.mode != "audio" and opts.embed_metadata:
        args += ["--embed-metadata"]
        if opts.tag_values:
            args += tags.custom_args(opts.tag_values)
        elif opts.tag_smart:
            args += tags.smart_args()
    if opts.overwrite:
        args += ["--force-overwrites"]

    if opts.section_start is not None or opts.section_end is not None:
        start = format_timecode(opts.section_start or 0)
        end = format_timecode(opts.section_end) if opts.section_end is not None else "inf"
        args += ["--download-sections", f"*{start}-{end}", "--force-keyframes-at-cuts"]

    args += common_args(opts.cookies_browser, deps)
    if opts.rate_limit.strip():
        args += ["-r", opts.rate_limit.strip()]

    args += ["--", url]
    return args


def subtitle_args(opts: DownloadOptions) -> list[str]:
    """자막 인자.

    --write-subs 를 항상 함께 넘긴다. yt-dlp 는 --write-subs 를 직접 지정하면 영상에 넣은 뒤에도
    자막 파일을 남기고, 지정하지 않으면 지운다. 그래서 '넣기만' 일 때는 no-keep-subs 로 지우게 한다.
    """
    if not opts.has_subs:
        return []
    langs = ",".join(x.strip() for x in opts.sub_langs.split(",") if x.strip())
    args = ["--write-subs", "--sub-langs", langs]
    if opts.auto_subs:
        args += ["--write-auto-subs"]
    mode = opts.effective_sub_mode()
    embed = mode in ("embed", "both") and opts.container in ("mp4", "mkv", "webm")
    if embed:
        args += ["--embed-subs"]
        if mode == "embed":
            args += ["--compat-options", "no-keep-subs"]
    # WebM 은 vtt 자막만 넣을 수 있어서 '둘 다'일 때는 vtt 그대로 둔다
    if mode in ("file", "both") and not (embed and opts.container == "webm"):
        args += ["--convert-subs", "srt"]
    return args


def common_args(cookies_browser: str = "", deps: Optional[Deps] = None) -> list[str]:
    """정보 조회와 다운로드에 공통으로 붙는 인자."""
    args: list[str] = []
    if cookies_browser:
        args += ["--cookies-from-browser", cookies_browser]
    if deps is not None:
        loc = deps.ffmpeg_location()
        if loc:
            args += ["--ffmpeg-location", loc]
        js = deps.js_runtime_arg()
        if js:
            args += ["--js-runtimes", js]
    return args


def info_args(url: str, playlist: bool, cookies_browser: str = "", deps: Optional[Deps] = None) -> list[str]:
    args = [
        "--ignore-config",
        "--color", "never",
        "--encoding", "utf-8",
        "-J",
        "--flat-playlist",
        "--yes-playlist" if playlist else "--no-playlist",
    ]
    args += common_args(cookies_browser, deps)
    args += ["--", url]
    return args
