"""실제 yt-dlp 로 로컬 HTTP 서버의 DASH 영상을 받아보는 통합 테스트.

사용법: python tests/integration_local.py <서버 기본 URL>
(서버에는 dash.mpd 가 있어야 함. 유튜브 접속 없이 엔진 전체 흐름을 검증)
"""
import os
import sys
import tempfile
from pathlib import Path

home = os.environ.get("TUBEGET_HOME") or tempfile.mkdtemp(prefix="tubeget-it-")
os.environ.setdefault("TUBEGET_LANG", "ko")   # 화면 글 비교는 한국어 기준
os.environ["TUBEGET_HOME"] = home
USE_EXISTING = os.environ.get("USE_EXISTING_BIN") == "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

from tubegetapp.core.deps import check_all  # noqa: E402
from tubegetapp.core.fetcher import InfoFetcher  # noqa: E402
from tubegetapp.core.options import DownloadOptions  # noqa: E402
from tubegetapp.core.queue import QueueManager  # noqa: E402
from tubegetapp.core.runner import DownloadJob  # noqa: E402
from tubegetapp.paths import bin_dir  # noqa: E402

base = sys.argv[1].rstrip("/")
if not USE_EXISTING:
    wrapper = bin_dir() / "yt-dlp"
    wrapper.write_text(f'#!/bin/sh\nexec {sys.executable} -m yt_dlp "$@"\n')
    wrapper.chmod(0o755)

app = QCoreApplication([])
deps = check_all()
print("deps:", deps.ytdlp.path, deps.ytdlp.version, "| ffmpeg", deps.ffmpeg.version,
      "| js", deps.js and (deps.js.name, deps.js.version))
out = Path(home) / "out"
results = {}

fetcher = InfoFetcher()


def on_info(info, url):
    results["info"] = info
    print("info:", info.kind, info.title, info.heights, info.duration)
    start_queue()


def on_fail(msg, url):
    results["info_err"] = msg
    print("info failed:", msg)
    app.quit()


fetcher.succeeded.connect(on_info)
fetcher.failed.connect(on_fail)

qm = QueueManager(lambda: deps, max_concurrent=2)
jobs = {}


def start_queue():
    url = f"{base}/dash.mpd"
    common = dict(output_dir=str(out))
    jobs["video"] = DownloadJob(url, "video", DownloadOptions(**common, max_height=1080))
    jobs["audio"] = DownloadJob(url, "audio", DownloadOptions(**common, mode="audio", audio_format="mp3"))
    jobs["cut"] = DownloadJob(url, "cut", DownloadOptions(**common, section_start=5, section_end=12,
                                                         subfolder="재생목록: 테스트", index=7))
    jobs["slow"] = DownloadJob(url, "slow", DownloadOptions(output_dir=str(out / "slow"), rate_limit="20K"))
    jobs["bad"] = DownloadJob(f"{base}/nope.mp4", "bad", DownloadOptions(**common))
    for j in jobs.values():
        j.changed.connect(lambda j=j: results.setdefault("details_" + j.title, set()).add(j.detail.split(" · ")[0]))
        qm.add(j)


def on_job_finished(job):
    print(f"finished: {job.title:6s} state={job.state:9s} file={job.filepath} err={job.error}")


qm.jobFinished.connect(on_job_finished)


def maybe_cancel_slow():
    j = jobs.get("slow")
    if j and j.state == "running":
        print("canceling slow job at:", j.detail)
        j.cancel()
    else:
        QTimer.singleShot(300, maybe_cancel_slow)


def on_all_done(ok, fail):
    print("allDone:", ok, fail)
    app.quit()


qm.allDone.connect(on_all_done)
fetcher.fetch(f"{base}/dash.mpd", deps, playlist=False)
QTimer.singleShot(1500, maybe_cancel_slow)
QTimer.singleShot(120_000, app.quit)
app.exec()

print("\n--- 결과 ---")
for name, j in jobs.items():
    print(name, j.state, j.filepath)
    print("   stages seen:", sorted(results.get("details_" + j.title, [])))
import subprocess  # noqa: E402
for f in sorted(out.rglob("*")):
    if f.is_file():
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name",
                                "-of", "compact", str(f)], capture_output=True, text=True).stdout.strip().replace("\n", " ; ")
        print(f.relative_to(out), f.stat().st_size, probe)
