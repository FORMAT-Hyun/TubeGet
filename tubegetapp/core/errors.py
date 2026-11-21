"""yt-dlp 오류 메시지를 이해하기 쉬운 한국어 안내로 바꾼다."""
from __future__ import annotations

import re
from typing import Optional
from ..i18n import tr

# (정규식, 안내 문구) - 위에서부터 먼저 맞는 것을 사용. 맨 앞 _COOKIE_RULES 개는 쿠키 문제
_COOKIE_RULES = 2
_RULES: list[tuple[str, str]] = [
    # 쿠키 문제가 진짜 원인이면 봇 확인 안내보다 먼저 알려준다
    (r"Could not copy .* cookie database|cookies? .*(?:locked|permission)",
     tr("브라우저가 켜져 있어서 쿠키를 읽지 못했어요. 그 브라우저를 완전히 종료한 뒤 다시 시도하거나, [설정 → 브라우저 쿠키]를 '사용 안 함'으로 바꿔 주세요.")),
    (r"App.?Bound|v20 cookies?|Failed to decrypt with DPAPI|could not find .* cookies database",
     tr("이 브라우저의 쿠키는 읽을 수 없어요. Windows의 최신 크롬·엣지·웨일은 쿠키를 암호화해서 막아 둬요. Firefox를 고르거나 '사용 안 함'으로 바꿔 주세요.")),
    (r"No supported JavaScript runtime|JS runtime",
     tr("유튜브 처리를 위한 JavaScript 런타임(Deno)이 없어요. [도구 상태]에서 Deno를 설치해 주세요.")),
    (r"ffmpeg (?:is )?not (?:installed|found)|ffprobe (?:is )?not (?:installed|found)|You have requested merging",
     tr("ffmpeg가 없어서 영상과 음성을 합치거나 변환할 수 없어요. [도구 상태]에서 ffmpeg를 설치해 주세요.")),
    (r"confirm you.?re not a bot|Sign in to confirm you",
     tr("유튜브가 봇 확인을 요구해요. VPN(Cloudflare WARP 등)을 켜 두었다면 끄고 다시 시도해 보세요. 그래도 안 되면 [설정 → 브라우저 쿠키]에서 Firefox를 골라 보세요.")),
    (r"confirm your age|age.?restricted|inappropriate for some users",
     tr("연령 제한 영상이에요. [설정 → 브라우저 쿠키]에서 로그인된 브라우저를 고르면 받을 수 있어요.")),
    (r"Private video|This video is private",
     tr("비공개 영상이라 받을 수 없어요.")),
    (r"members.?only|Join this channel|available to this channel's members",
     tr("채널 멤버십 전용 영상이에요. 멤버 계정의 브라우저 쿠키가 필요해요.")),
    (r"Premieres in|This live event will begin|will begin in",
     tr("아직 시작하지 않은 최초 공개/라이브 영상이에요.")),
    (r"(?:video|stream) is (?:currently )?live|is a live (?:stream|broadcast)|live streams? (?:are|is) not supported",
     tr("진행 중인 라이브 방송은 지원하지 않아요. 방송이 끝난 뒤 다시 시도해 주세요.")),
    (r"DRM",
     tr("DRM으로 보호된 영상이라 받을 수 없어요.")),
    (r"not available in your country|blocked it in your country|geo.?restrict",
     tr("이 지역에서 볼 수 없는 영상이에요.")),
    (r"Video unavailable|This video is unavailable|has been removed|account associated with this video has been terminated",
     tr("삭제되었거나 볼 수 없는 영상이에요.")),
    (r"Requested format is not available",
     tr("선택한 화질/형식이 이 영상에 없어요. 화질을 '최고 화질'로 바꿔서 다시 시도해 보세요.")),
    (r"HTTP Error 403|403: Forbidden",
     tr("유튜브가 접근을 막았어요(403). [도구 상태]에서 yt-dlp를 업데이트한 뒤 다시 시도해 보세요.")),
    (r"HTTP Error 429|Too Many Requests",
     tr("요청이 너무 많아 잠시 차단됐어요(429). 잠시 후 다시 시도하거나 동시 다운로드 수를 줄여 주세요.")),
    (r"HTTP Error 404|404: Not Found",
     tr("영상을 찾을 수 없어요(404). 주소를 다시 확인해 주세요.")),
    (r"Unsupported URL|is not a valid URL",
     tr("지원하지 않는 주소예요. 주소를 다시 확인해 주세요.")),
    (r"getaddrinfo failed|Name or service not known|Temporary failure in name resolution|Failed to resolve|Connection refused|timed out|Unable to download webpage",
     tr("인터넷 연결을 확인해 주세요. 연결이 정상이라면 잠시 후 다시 시도해 보세요.")),
    (r"No space left on device|disk is full|\[Errno 28\]",
     tr("저장 공간이 부족해요.")),
    (r"Permission denied|\[Errno 13\]|Access is denied",
     tr("저장 폴더에 쓸 권한이 없어요. 다른 저장 위치를 선택해 주세요.")),
    (r"File name too long|\[Errno 36\]",
     tr("파일 이름이 너무 길어요. 설정에서 파일 이름 규칙을 짧게 바꿔 주세요.")),
]


def last_error_line(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in reversed(lines):
        if ln.startswith("ERROR:"):
            return ln[len("ERROR:"):].strip()
    return lines[-1] if lines else None


def explain(text: str) -> str:
    """오류 로그 전체를 받아 한 줄 한국어 안내를 돌려준다."""
    text = text or ""
    err = last_error_line(text) or ""
    # 쿠키를 못 읽은 경우는 경고 줄에만 나오고 ERROR 는 '봇 확인'이 되기도 해서 로그 전체에서 먼저 본다
    for pattern, message in _RULES[:_COOKIE_RULES]:
        if re.search(pattern, text, re.IGNORECASE):
            return message
    # ERROR 줄을 먼저 보고, 없으면 전체 로그에서 찾는다
    for haystack in (err, text):
        if not haystack:
            continue
        for pattern, message in _RULES:
            if re.search(pattern, haystack, re.IGNORECASE):
                return message
    if err:
        short = re.sub(r"^\[[^\]]+\]\s*", "", err)
        short = re.sub(r"\s*;?\s*please report this issue.*$", "", short, flags=re.IGNORECASE)
        return tr("다운로드에 실패했어요: {v}").format(v=short[:200])
    return tr("알 수 없는 오류로 실패했어요. yt-dlp를 업데이트한 뒤 다시 시도해 보세요.")
