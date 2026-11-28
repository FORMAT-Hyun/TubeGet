"""핵심 로직 단위 테스트 (pytest)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("TUBEGET_HOME", tempfile.mkdtemp(prefix="tubeget-test-"))
os.environ.setdefault("TUBEGET_LANG", "ko")   # 화면 글 비교는 한국어 기준
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tubegetapp.core.errors import explain  # noqa: E402
from tubegetapp.core.metadata import parse_info  # noqa: E402
from tubegetapp.core.options import DownloadOptions, build_args, info_args  # noqa: E402
from tubegetapp.core.progress import overall_fraction, parse_line  # noqa: E402
from tubegetapp.core.options import subtitle_args  # noqa: E402
from tubegetapp.utils import format_timecode, parse_timecode, sanitize_filename  # noqa: E402


def _after(args, flag):
    return args[args.index(flag) + 1]


def test_progress_bytes():
    kind, p = parse_line("TGP|downloading|512|1024|NA|2048.5|3|NA|NA|avc1.640028|none")
    assert kind == "progress"
    assert p.fraction == 0.5 and p.speed == 2048.5 and p.eta == 3
    assert p.stream_kind == "video"


def test_progress_estimate_and_fragments():
    _, p = parse_line("TGP|downloading|100|NA|400|NA|NA|NA|NA|none|opus")
    assert p.fraction == 0.25 and p.stream_kind == "audio"
    _, p = parse_line("TGP|downloading|NA|NA|NA|NA|NA|3|6|avc1|mp4a")
    assert p.fraction == 0.5 and p.stream_kind == "both"
    _, p = parse_line("TGP|finished|10|10|NA|NA|NA|NA|NA|NA|NA")
    assert p.fraction == 1.0


def test_stage_and_file_lines():
    assert parse_line("TGS|postprocess") == ("stage", "postprocess")
    assert parse_line("TGF|C:\\Videos\\a b [x].mp4") == ("file", "C:\\Videos\\a b [x].mp4")
    assert parse_line("[download] something") is None


def test_build_args_video_default():
    o = DownloadOptions(output_dir="/tmp/out")
    a = build_args(o, "https://youtu.be/abc")
    assert a[-2:] == ["--", "https://youtu.be/abc"]
    assert _after(a, "-f") == "bv*+ba/b"
    assert _after(a, "--merge-output-format") == "mp4"
    assert _after(a, "-S") == "ext:mp4:m4a"
    assert "--embed-thumbnail" in a and "--embed-metadata" in a
    assert "--no-playlist" in a and "--ignore-config" in a


def test_build_args_video_1080_compat_subs_mkv():
    o = DownloadOptions(output_dir="/o", max_height=1080, compat_h264=True, container="mkv",
                        auto_subs=True, sub_langs="ko")
    a = build_args(o, "u")
    assert _after(a, "-S") == "vcodec:h264,res:1080,acodec:aac"
    assert _after(a, "--merge-output-format") == "mkv"
    assert "--embed-subs" in a and "--write-auto-subs" in a and _after(a, "--sub-langs") == "ko"


def test_build_args_webm_no_thumbnail():
    a = build_args(DownloadOptions(container="webm"), "u")
    assert "--embed-thumbnail" not in a


def test_build_args_audio():
    a = build_args(DownloadOptions(mode="audio", audio_format="mp3", audio_quality="320K"), "u")
    assert _after(a, "-f") == "ba/b" and "-x" in a
    assert _after(a, "--audio-format") == "mp3" and _after(a, "--audio-quality") == "320K"
    assert "--merge-output-format" not in a
    a = build_args(DownloadOptions(mode="audio", audio_format="wav"), "u")
    assert "--audio-quality" not in a and "--embed-thumbnail" not in a
    a = build_args(DownloadOptions(mode="audio", audio_format="best"), "u")
    assert "--audio-format" not in a


def test_sections_and_template():
    o = DownloadOptions(section_start=90, section_end=None, subfolder='My: "Mix" 100%', index=3)
    a = build_args(o, "u")
    assert _after(a, "--download-sections") == "*00:01:30-inf"
    tpl = _after(a, "-o")
    assert tpl.startswith("My_ _Mix_ 100%%/03 - ")
    assert "(구간 %(section_start)d-%(section_end)d).%(ext)s" in tpl


def test_cookies_and_rate():
    a = build_args(DownloadOptions(cookies_browser="firefox", rate_limit=" 5M "), "u")
    assert _after(a, "--cookies-from-browser") == "firefox" and _after(a, "-r") == "5M"
    b = info_args("u", playlist=True, cookies_browser="edge")
    assert "--yes-playlist" in b and "-J" in b and "--flat-playlist" in b


def test_parse_video_info():
    data = {
        "id": "abc", "title": "노래", "uploader": "AJR", "duration": 200,
        "thumbnail": "https://i.ytimg.com/vi_webp/abc/maxresdefault.webp",
        "thumbnails": [
            {"url": "https://i.ytimg.com/vi/abc/hqdefault.jpg", "width": 480, "preference": -7},
            {"url": "https://i.ytimg.com/vi_webp/abc/maxresdefault.webp", "width": 1920, "preference": 0},
        ],
        "formats": [
            {"format_id": "sb0", "ext": "mhtml", "vcodec": "none", "acodec": "none", "height": 90},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2", "filesize": 3_000_000},
            {"format_id": "137", "vcodec": "avc1", "acodec": "none", "height": 1080, "filesize": 50_000_000},
            {"format_id": "248", "vcodec": "vp9", "acodec": "none", "height": 1080, "filesize_approx": 40_000_000},
            {"format_id": "136", "vcodec": "avc1", "acodec": "none", "height": 720, "filesize": 20_000_000},
            {"format_id": "18", "vcodec": "avc1", "acodec": "mp4a", "height": 360},
        ],
    }
    info = parse_info(data)
    assert info.kind == "video" and info.heights == [1080, 720, 360]
    assert info.thumbnail.endswith("hqdefault.jpg")
    assert info.estimated_size(0) == 53_000_000
    assert info.estimated_size(900) == 23_000_000
    assert info.estimated_size(0, "audio") == 3_000_000


def test_parse_playlist_info():
    data = {
        "_type": "playlist", "id": "PL1", "title": "My Mix",
        "entries": [
            {"_type": "url", "ie_key": "Youtube", "id": "a1", "url": "https://www.youtube.com/watch?v=a1",
             "title": "One", "duration": 61},
            {"_type": "url", "ie_key": "Youtube", "id": "a2", "url": "a2", "title": "[Private video]"},
            {"_type": "url", "ie_key": "Youtube", "id": "a3", "title": "Three"},
        ],
    }
    info = parse_info(data)
    assert info.kind == "playlist" and len(info.entries) == 3
    assert info.entries[1].available is False
    assert info.entries[2].url == "https://www.youtube.com/watch?v=a3"
    assert info.entries[1].url == "https://www.youtube.com/watch?v=a2"


def test_parse_channel_tabs():
    data = {"_type": "playlist", "title": "Chan", "entries": [
        {"_type": "url", "ie_key": "YoutubeTab", "url": "https://www.youtube.com/@x/videos", "title": "Videos"}]}
    info = parse_info(data)
    assert info.nested_tabs and not info.entries


def test_errors():
    assert "Deno" in explain("WARNING: [youtube] No supported JavaScript runtime could be found.\nERROR: something")
    assert "비공개" in explain("ERROR: [youtube] abc: Private video. Sign in if you've been granted access")
    assert "봇" in explain("ERROR: [youtube] x: Sign in to confirm you’re not a bot. Use --cookies")
    assert "VPN" in explain("ERROR: [youtube] x: Sign in to confirm you’re not a bot. Use --cookies")
    # 브라우저가 켜져 있어 쿠키 DB 복사 실패 (실제 웨일 로그)
    locked = explain("ERROR: Could not copy Chrome cookie database. See  https://github.com/yt-dlp/yt-dlp/issues/7271")
    assert "켜져 있어서" in locked
    # 최신 크롬 계열의 App-Bound 암호화
    assert "암호화" in explain("WARNING: cannot decrypt v20 cookies: AppBound encryption is not supported\n"
                             "ERROR: [youtube] x: Sign in to confirm you’re not a bot.")
    assert "403" in explain("ERROR: unable to download video data: HTTP Error 403: Forbidden")
    msg = explain("ERROR: [generic] weird thing happened; please report this issue on https://x")
    assert msg.startswith("다운로드에 실패했어요: weird thing happened")


def test_utils():
    assert parse_timecode("1:30") == 90 and parse_timecode("01:02:03") == 3723
    assert parse_timecode("abc") is None and parse_timecode("") is None
    assert format_timecode(90) == "00:01:30" and format_timecode(1.5) == "00:00:01.500"
    assert sanitize_filename('a<b>:"c"/d\\e|f?g*') == "a_b___c__d_e_f_g_"
    assert sanitize_filename("CON") == "_CON" and sanitize_filename("  ...  ") == "untitled"


def test_progress_tmpfilename_with_pipe():
    _, p = parse_line("TGP|downloading|1|2|NA|NA|NA|NA|NA|avc1|none|C:\\v\\a|b.f137.mp4.part")
    assert p.tmpfilename == "C:\\v\\a|b.f137.mp4.part" and p.fraction == 0.5


def test_streams_line():
    assert parse_line("TGR|954476|177461|1131937") == ("streams", parse_line("TGR|954476|177461|1")[1])
    _, st = parse_line("TGR|954476|177461|1131937")
    assert st.sizes == [954476.0, 177461.0]
    _, st = parse_line("TGR|NA|NA|5000")
    assert st.sizes == [5000.0]
    _, st = parse_line("TGR|NA|300|NA")
    assert st.sizes == [None, 300.0]


def test_overall_fraction():
    assert overall_fraction([900, 100], 0, 0.5) == 0.45
    assert abs(overall_fraction([900, 100], 1, 0.5) - 0.95) < 1e-9
    assert abs(overall_fraction([None, 100], 1, 0.0) - 0.85) < 1e-9
    assert overall_fraction([None], 0, 0.3) == 0.3


def test_subtitle_modes():
    base = DownloadOptions(sub_langs="en, ko", container="mp4")
    a = subtitle_args(base.copy(sub_mode="embed"))
    assert a[:3] == ["--write-subs", "--sub-langs", "en,ko"] and "--embed-subs" in a
    assert "no-keep-subs" in a and "--convert-subs" not in a
    a = subtitle_args(base.copy(sub_mode="file"))
    assert "--embed-subs" not in a and _after(a, "--convert-subs") == "srt"
    a = subtitle_args(base.copy(sub_mode="both"))
    assert "--embed-subs" in a and "no-keep-subs" not in a and "--convert-subs" in a
    a = subtitle_args(base.copy(sub_mode="both", container="webm"))
    assert "--embed-subs" in a and "--convert-subs" not in a
    a = subtitle_args(base.copy(mode="audio", sub_mode="embed", auto_subs=True))
    assert "--embed-subs" not in a and "--convert-subs" in a and "--write-auto-subs" in a
    assert subtitle_args(DownloadOptions()) == []
    assert "--force-overwrites" in build_args(DownloadOptions(overwrite=True), "u")


def test_options_roundtrip():
    o = DownloadOptions(mode="audio", sub_langs="ko", index=3, section_start=1.5)
    d = o.to_dict()
    d["unknown_future_field"] = 1
    assert DownloadOptions.from_dict(d) == o


def test_parse_subtitles():
    info = parse_info({"id": "x", "title": "t", "formats": [],
                       "subtitles": {"en": [{"ext": "vtt", "name": "English"}], "live_chat": [{"ext": "json"}]},
                       "automatic_captions": {"ko": [{"ext": "vtt", "name": "Korean"}], "fr": []}})
    assert info.subtitles == {"en": "English"} and info.auto_captions == {"ko": "Korean"}


def _info(**kw):
    from tubegetapp.core.metadata import MediaInfo
    base = dict(kind="video", title="", uploader="", track="", artist="", album="", upload_date="")
    base.update(kw)
    return MediaInfo(**base)


def test_guess_tags():
    from tubegetapp.core.tags import guess_tags, raw_tags
    g = guess_tags(_info(title="AJR - Way Less Sad (Official Video)", uploader="AJR", upload_date="20210512"))
    assert g == {"title": "Way Less Sad", "artist": "AJR", "album": "", "year": "2021"}
    g = guess_tags(_info(title="아이유(IU) – 밤편지 [MV] 【Lyrics】", uploader="이지금 [IU Official]"))
    assert g["artist"] == "아이유(IU)" and g["title"] == "밤편지"
    g = guess_tags(_info(title="Bang!", track="Bang!", artist="AJR", album="Neotheater", release_year=2019,
                         uploader="AJR - Topic"))
    assert g == {"title": "Bang!", "artist": "AJR", "album": "Neotheater", "year": "2019"}
    g = guess_tags(_info(title="Just A Song (Audio)", uploader="Some Artist - Topic"))
    assert g["artist"] == "Some Artist" and g["title"] == "Just A Song"
    assert raw_tags(_info(title="A - B (MV)", uploader="ch"))["title"] == "A - B (MV)"


def test_tag_args():
    from tubegetapp.core.tags import custom_args
    a = custom_args({"title": "AJR: 100% 진짜", "artist": "AJR", "album": "", "year": "2019"})
    assert a[1] == "#AJR\\: 100%% 진짜:#(?P<meta_title>.*)"
    assert ":(?P<meta_album>)" in a and "#2019:#(?P<meta_date>.*)" in a
    on = build_args(DownloadOptions(mode="audio", tag_values={"title": "x"}), "u")
    assert "--embed-metadata" in on and "--embed-thumbnail" in on and "#x:#(?P<meta_title>.*)" in on
    off = build_args(DownloadOptions(mode="audio", audio_tags=False), "u")
    assert "--embed-metadata" not in off and "--embed-thumbnail" not in off
    assert _after(off, "--postprocessor-args") == "ExtractAudio:-map_metadata -1"
    smart = build_args(DownloadOptions(mode="audio", tag_smart=True), "u")
    assert "--replace-in-metadata" in smart
    assert DownloadOptions(mode="audio", audio_tags=False).summary().endswith("태그 끔")
    vid = build_args(DownloadOptions(mode="video", audio_tags=False), "u")
    assert "--embed-metadata" in vid   # 영상은 설정의 메타데이터 옵션을 따름


def test_dub_args_and_parse():
    o = DownloadOptions(dub_lang="ko")
    a = build_args(o, "https://x/y")
    assert a[a.index("-f") + 1] == "bv*+ba[language^=ko]/bv*+ba/b"
    a = build_args(DownloadOptions(mode="audio", dub_lang="en-US"), "https://x/y")
    assert a[a.index("-f") + 1] == "ba[language^=en-US]/ba/b"
    assert build_args(DownloadOptions(), "https://x/y")[build_args(DownloadOptions(), "u").index("-f") + 1] == "bv*+ba/b"
    # 이상한 문자는 걸러냄
    assert DownloadOptions(dub_lang="ko]/x[").dub_selector() == "[language^=kox]"
    assert "더빙 ko" in o.summary()
    assert DownloadOptions.from_dict(o.to_dict()).dub_lang == "ko"
    info = parse_info({"id": "a", "title": "t", "formats": [
        {"format_id": "1", "vcodec": "none", "acodec": "aac", "language": "en", "format_note": "English - original (default)"},
        {"format_id": "2", "vcodec": "none", "acodec": "aac", "language": "ko", "format_note": "Korean - dubbed-auto"},
        {"format_id": "3", "vcodec": "none", "acodec": "aac"}]})
    assert info.dubs == {"en": "original", "ko": "dubbed"} and info.dub_original == "en"


def test_video_tag_args():
    a = build_args(DownloadOptions(tag_values={"title": "곡", "artist": "A", "album": "", "year": "2020"}), "u")
    assert "--embed-metadata" in a and a.count("--parse-metadata") == 4
    off = build_args(DownloadOptions(embed_metadata=False), "u")
    assert "--embed-metadata" not in off and "--parse-metadata" not in off
    assert "태그 끔" in DownloadOptions(embed_metadata=False).summary()


def test_version_and_about_text():
    import tubegetapp
    from tubegetapp.core.deps import Deps, Tool
    assert tubegetapp.APP_VERSION == "0.2.0" and tubegetapp.APP_STAGE == "베타"
    from tubegetapp.ui.about_dialog import report_text, tool_line, version_text
    assert version_text() == "0.2.0 (베타)"
    d = Deps(ytdlp=Tool("yt-dlp", "/x/yt-dlp", "2026.10.26", True), ffmpeg=Tool("ffmpeg"))
    assert tool_line(d.ytdlp) == "2026.10.26 · Acortube 폴더" and tool_line(d.ffmpeg) == "없음"
    t = report_text(d)
    assert t.startswith("Acortube 0.2.0 (베타)") and "yt-dlp: 2026.10.26" in t and "ffmpeg: 없음" in t
