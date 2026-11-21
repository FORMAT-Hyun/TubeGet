"""유튜브 흉내 yt-dlp 대역.

- `-J` 요청에는 유튜브와 같은 형태의 JSON(여러 화질, 자막, 자동 자막)을 돌려준다.
- 다운로드 요청은 진짜 yt-dlp 에 `--load-info-json` 으로 넘겨서 로컬 서버 파일을 실제로 받는다.
환경 변수: FAKE_BASE (로컬 서버 주소), FAKE_SRV (서버 폴더), FAKE_INFO (생성할 JSON 경로)
"""
import json
import os
import sys


def build_info(base: str, srv: str) -> dict:
    vsize = os.path.getsize(os.path.join(srv, "v.mp4"))
    asize = os.path.getsize(os.path.join(srv, "a.m4a"))
    fmts = [{"format_id": "sb0", "ext": "mhtml", "protocol": "mhtml", "vcodec": "none", "acodec": "none",
             "url": f"{base}/none", "height": 90}]
    fmts += [
        {"format_id": "139", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.5", "abr": 48, "filesize": 1_400_000},
        {"format_id": "140", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129, "filesize": asize},
        {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 135, "filesize": 3_800_000},
        {"format_id": "140-0", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129, "filesize": asize,
         "language": "en", "format_note": "English (US) - original (default), medium"},
        {"format_id": "140-1", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129, "filesize": asize,
         "language": "ko", "format_note": "Korean - dubbed-auto, medium"},
    ]
    for fid, h, codec, ext, size in [
        ("160", 144, "avc1.4d400c", "mp4", 1_900_000), ("133", 240, "avc1.4d4015", "mp4", 3_600_000),
        ("134", 360, "avc1.4d401e", "mp4", 6_500_000), ("135", 480, "avc1.4d401f", "mp4", 11_200_000),
        ("136", 720, "avc1.4d401f", "mp4", 21_900_000), ("137", 1080, "avc1.640028", "mp4", vsize),
        ("248", 1080, "vp9", "webm", 38_100_000), ("271", 1440, "vp9", "webm", 102_000_000),
        ("313", 2160, "vp9", "webm", 221_000_000), ("401", 2160, "av01.0.12M.08", "mp4", 198_000_000),
    ]:
        fmts.append({"format_id": fid, "ext": ext, "vcodec": codec, "acodec": "none", "height": h,
                     "width": h * 16 // 9, "fps": 30, "filesize": size})
    for f in fmts:
        if f["format_id"] == "sb0":
            continue
        f["url"] = f"{base}/a.m4a" if f["vcodec"] == "none" else f"{base}/v.mp4"
        f["protocol"] = "https"
    sub = lambda code, name: [{"ext": "vtt", "url": f"{base}/{'ko' if code.startswith('ko') else 'en'}.vtt", "name": name}]  # noqa: E731
    autos = {"en-orig": "English (Original)", "en": "English", "ko": "Korean", "ja": "Japanese",
             "fr": "French", "de": "German", "es": "Spanish", "vi": "Vietnamese", "th": "Thai",
             "zh-Hans": "Chinese (Simplified)", "ar": "Arabic", "hi": "Hindi", "id": "Indonesian"}
    return {
        "id": "dQw4w9WgXcQ", "title": "AJR - Way Less Sad (Official Video)", "uploader": "AJR",
        "channel": "AJR", "duration": 216, "ext": "mp4", "extractor": "generic", "extractor_key": "Generic",
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "live_status": "not_live",
        "thumbnail": f"{base}/thumb.jpg",
        "thumbnails": [{"url": f"{base}/thumb.jpg", "width": 480, "height": 360, "preference": -7}],
        "formats": fmts,
        "subtitles": {"en": sub("en", "English"), "ko": sub("ko", "Korean"),
                      "live_chat": [{"ext": "json", "url": f"{base}/x"}]},
        "automatic_captions": {c: sub(c, n) for c, n in autos.items()},
    }


def main() -> None:
    base, srv, path = os.environ["FAKE_BASE"], os.environ["FAKE_SRV"], os.environ["FAKE_INFO"]
    args = sys.argv[1:]
    if "--version" in args or "-U" in args:
        os.execv(sys.executable, [sys.executable, "-m", "yt_dlp", *args])
    info = build_info(base, srv)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False)
    if "-J" in args:
        print(json.dumps(info, ensure_ascii=False))
        return
    if "--" in args:
        args = args[:args.index("--")]
    os.execv(sys.executable, [sys.executable, "-m", "yt_dlp", *args, "--load-info-json", path])


if __name__ == "__main__":
    main()
