"""yt-dlp 출력 줄 파싱.

yt-dlp 에 직접 정의한 출력 형식을 넘겨서, 사람이 읽는 로그 대신
기계가 읽기 쉬운 줄을 받는다.
  TGP|status|downloaded|total|estimate|speed|eta|frag_i|frag_n|vcodec|acodec|tmpfilename  (진행률)
  TGR|stream0_size|stream1_size|single_size   (다운로드 직전: 받을 스트림 크기)
  TGS|stage                                   (단계)
  TGF|/final/path.mp4                         (최종 파일)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

P_PROGRESS = "TGP|"
P_STREAMS = "TGR|"
P_STAGE = "TGS|"
P_FILE = "TGF|"

PROGRESS_TEMPLATE = (
    "download:" + P_PROGRESS
    + "%(progress.status)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s"
    "|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s"
    "|%(progress.fragment_index)s|%(progress.fragment_count)s"
    "|%(info.vcodec)s|%(info.acodec)s|%(progress.tmpfilename)s"
)

PRINT_ARGS = [
    "-O", "before_dl:" + P_STREAMS
    + "%(requested_formats.0.filesize,requested_formats.0.filesize_approx)s"
    "|%(requested_formats.1.filesize,requested_formats.1.filesize_approx)s"
    "|%(filesize,filesize_approx)s",
    "-O", "post_process:" + P_STAGE + "postprocess",
    "-O", "after_move:" + P_FILE + "%(filepath)s",
]

_N_FIELDS = 11


def _num(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s or s in ("NA", "None", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _text(s: str) -> Optional[str]:
    s = (s or "").strip()
    return None if s in ("", "NA", "None") else s


@dataclass
class Progress:
    status: str
    downloaded: Optional[float] = None
    total: Optional[float] = None
    speed: Optional[float] = None
    eta: Optional[float] = None
    frag_index: Optional[float] = None
    frag_count: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    tmpfilename: Optional[str] = None

    @property
    def fraction(self) -> Optional[float]:
        if self.status == "finished":
            return 1.0
        if self.total and self.downloaded is not None and self.total > 0:
            return max(0.0, min(1.0, self.downloaded / self.total))
        if self.frag_count and self.frag_index is not None and self.frag_count > 0:
            return max(0.0, min(1.0, self.frag_index / self.frag_count))
        return None

    @property
    def stream_kind(self) -> str:
        """'audio' / 'video' / 'both' / 'unknown'"""
        v, a = self.vcodec, self.acodec
        if v == "none" and a and a != "none":
            return "audio"
        if a == "none" and v and v != "none":
            return "video"
        if v and a and v != "none" and a != "none":
            return "both"
        return "unknown"


@dataclass
class Streams:
    """받을 스트림들의 크기. 크기를 모르면 None."""
    sizes: list

    @property
    def count(self) -> int:
        return len(self.sizes)


ParsedLine = Union[Tuple[str, Progress], Tuple[str, str], Tuple[str, Streams], None]


def parse_line(line: str) -> ParsedLine:
    line = line.rstrip("\r\n")
    if line.startswith(P_PROGRESS):
        # 파일 경로는 마지막 칸이라 '|' 가 들어 있어도 안전
        parts = line[len(P_PROGRESS):].split("|", _N_FIELDS - 1)
        parts += [""] * (_N_FIELDS - len(parts))
        total = _num(parts[2])
        if total is None:
            total = _num(parts[3])
        return ("progress", Progress(
            status=parts[0].strip() or "downloading",
            downloaded=_num(parts[1]),
            total=total,
            speed=_num(parts[4]),
            eta=_num(parts[5]),
            frag_index=_num(parts[6]),
            frag_count=_num(parts[7]),
            vcodec=_text(parts[8]),
            acodec=_text(parts[9]),
            tmpfilename=_text(parts[10]),
        ))
    if line.startswith(P_STREAMS):
        parts = (line[len(P_STREAMS):].split("|") + ["", "", ""])[:3]
        first, second, single = (_num(p) for p in parts)
        if parts[0].strip() in ("NA", "") and parts[1].strip() in ("NA", ""):
            sizes = [single]                     # 영상+음성이 합쳐진 하나짜리
        else:
            sizes = [first, second]
        return ("streams", Streams(sizes))
    if line.startswith(P_STAGE):
        return ("stage", line[len(P_STAGE):].strip())
    if line.startswith(P_FILE):
        return ("file", line[len(P_FILE):].strip())
    return None


def overall_fraction(sizes: list, index: int, current: Optional[float]) -> Optional[float]:
    """여러 스트림(영상→음성)을 하나의 진행률로 합친다 (0~1)."""
    n = len(sizes)
    if n == 0:
        return current
    index = min(index, n - 1)
    cur = current or 0.0
    if all(s for s in sizes):
        total = float(sum(sizes))
        done = float(sum(sizes[:index]))
        return max(0.0, min(1.0, (done + sizes[index] * cur) / total))
    # 크기를 모르면 영상이 대부분을 차지한다고 가정
    weights = [0.85, 0.15] if n == 2 else [1.0 / n] * n
    return max(0.0, min(1.0, sum(weights[:index]) + weights[index] * cur))
