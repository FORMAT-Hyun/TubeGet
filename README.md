# TubeGet

**English** | [한국어](README.ko.md)

**A desktop YouTube downloader (GUI) powered by yt-dlp**

Paste a link, pick the quality and format, and TubeGet downloads it.
The downloading is done by [yt-dlp](https://github.com/yt-dlp/yt-dlp); TubeGet is the friendly window on top of it.

## Features

- **Video**: Best quality down to 4K, 1440p, 1080p or 720p, with an estimated file size for each. MP4, MKV and WebM.
- **Audio only**: MP3, M4A, Opus, FLAC, WAV, or the original stream as is
- **Playlists**: Tick items in the list or select a range (`1-10, 15, 20-`). Creating a folder and numbering files are optional.
- **Subtitles / dubbing**: Choose from the subtitles each video actually has (uploaded, auto-generated or auto-translated) and from its dubbed audio tracks (other-language audio, YouTube auto-dubbing, etc.).
  - Save subtitles embedded in the video, as a separate `.srt` file, or both.
  - Videos without audio in the chosen language fall back to the original audio.
- **Tags**: Set or turn off title, artist, album, year and cover for audio (MP3, M4A) and video (MP4, MKV), per video.
  - Titles like "AJR - Way Less Sad (Official Video)" are pre-filled as artist `AJR` and title `Way Less Sad`. You can edit them.
  - Turn tags off to save a clean file with no tags or cover.
  - Playlists are cleaned up automatically for each video.
- **Editing-friendly (H.264)**: Prefers a codec that opens well in video editors and older devices.
- **Download queue**: Several downloads at once, cancel and resume, a clear reason when something fails, and a log viewer.
  - One progress bar per item, even when video and audio are downloaded separately.
  - Waiting downloads are restored and resumed after a restart.
  - Files that already exist are marked "skipped", with an [Overwrite] button.
  - Removing an item from the list also cleans up its partial files (`.part`, etc.).
- **Instant download**: With the toolbar switch on, clicking [Paste link] starts downloading right away with the current settings. Playlists open a selection window.
- **History**: Open downloaded files or their folder, or download again
- **Automatic tool setup**: On first run, install yt-dlp, ffmpeg and Deno with one click. yt-dlp updates are checked once a day.
- **Languages**: English and Korean. Choose under [Settings → Language], or leave it on "Auto" to follow the system language. Takes effect after a restart.
- **Also**: Dark theme, drag and drop links onto the window, a notification when downloads finish, single-instance app, and an About window (F1) with "Copy info" for bug reports

## Running (Windows)

1. Install [Python 3.10 or later](https://www.python.org/downloads/). In the installer, **check "Add python.exe to PATH"**.
2. **Double-click `run_windows.bat`**. The first run takes a minute or two to install the required package (PySide6).
3. The **[Tool status]** window opens on first launch. Click **[Install missing tools]** to download yt-dlp, ffmpeg and Deno automatically (about 200 MB, only once).

On macOS and Linux, run `./run.sh`. On macOS, install ffmpeg separately with `brew install ffmpeg`.

> When you get a new version, extract it into a new folder instead of over the old one. Settings, history and installed tools live separately in `%APPDATA%\TubeGet`, so they are kept.

### Building an installer (recommended)

**Double-click `build_installer.bat`** to create `dist\TubeGet-Setup-<version>.exe`.
The first run takes a few minutes to set up PyInstaller and Inno Setup (installed automatically with winget).

- The default install location is `C:\Program Files\TubeGet`. Choose "Install for me only" to install to `%LOCALAPPDATA%\Programs\TubeGet` without admin rights.
- A Start menu shortcut is always created. A desktop shortcut and starting with Windows are optional.
- Uninstall from [Settings → Apps → Installed apps]. The uninstaller asks whether to remove settings and tools too.

The installer works on PCs without Python.

### Building just the exe

Run `build_windows.bat` to create a portable `dist\TubeGet\TubeGet.exe` (the whole `dist\TubeGet` folder is needed).

## Android (phone)

From 0.1.5 there is also an Android app with a phone-friendly UI (Android 7.0 or later). It downloads on the phone itself; no PC needed.

1. From [Releases](https://github.com/FORMAT-Hyun/TubeGet/releases), download `TubeGet-<version>-Android-arm64.apk` (almost every phone). Very old 32-bit phones need `-armv7.apk`.
2. Open the file and allow "Install unknown apps" for your browser or file manager when asked.
3. In the YouTube app, tap **Share → TubeGet**, or copy a link and tap **[Paste link]**. On the video card, pick video/audio, quality (bitrate for audio), format, save location, subtitles/dubbing and tags, then tap **[Download]**. With **Instant download** on, it starts right away.

- Files are saved to `Download/TubeGet` and show up in your gallery and music apps.
- yt-dlp, Python and FFmpeg are included in the app. yt-dlp updates itself once a day (or from Settings).
- Downloads keep going with the screen off; progress is shown in a notification.
- The source is in the [`android/`](android) folder on the `mobile` branch. Build with `cd android` → `gradlew assembleRelease` (needs Android SDK 35 and JDK 17+).

## Usage

1. Copy a YouTube link and click the red **[Paste link]** button at the top. Press Ctrl+L to type a link, or drag one onto the window.
2. In the toolbar, choose the download type (video/audio), quality (bitrate for audio), format, save location, subtitles/dubbing and tags.
3. A video card (thumbnail, info, estimated size) appears at the top of the list. Click **[Download]** on the card. You can load several links and set options per card.

With [Instant] on, steps 2 and 3 are skipped.

### Troubleshooting

| Problem | Solution |
|---|---|
| "Bot check" error | If you use a VPN (Cloudflare WARP, etc.), turn it off and try again. If that doesn't help, choose Firefox under [Settings → Browser cookies] |
| "Age-restricted" or "members-only" errors | Under [Settings → Browser cookies], choose Firefox logged in to YouTube. Recent Chrome, Edge and Whale on Windows encrypt their cookies, so they usually can't be read |
| 403 errors, downloads suddenly stop working | YouTube has often changed. [Tool status] → [Update yt-dlp] |
| Only up to 360p is available | Often happens when Deno is missing. Install it from [Tool status] |
| The video won't open in an editor | Turn on **Prefer editing-friendly (H.264)** in Settings and download again |
| Resume a canceled download | Click **[Retry]** in the list; it resumes where it stopped |
| Quality list or sizes look wrong | Check `last_info.json` and `last_error.txt` in [Tool status] → [Diagnostics folder] |

## File locations

| What | Windows | macOS | Linux |
|---|---|---|---|
| Settings, history, installed tools (`bin`) | `%APPDATA%\TubeGet` | `~/Library/Application Support/TubeGet` | `~/.config/tubeget` |
| Default save location | `Downloads\TubeGet` | same | same |

## Project structure

```
main.py                    Entry point
installer/TubeGet.iss      Installer script (Inno Setup)
build_installer.bat        Builds the exe and the installer in one go
tubegetapp/
  config.py                Settings (JSON)
  i18n.py                  Translation: tr("Korean source") → current language
  locales/en.py            English translations
  paths.py / utils.py      Paths, formatting, file name cleanup
  core/
    deps.py                Finds yt-dlp / ffmpeg / JS runtime, checks versions
    installer.py           Automatic tool install, yt-dlp -U updates (background)
    options.py             Download options → yt-dlp command-line arguments
    progress.py            Parses yt-dlp output
    runner.py              One download = one yt-dlp process (QProcess)
    fetcher.py             Video / playlist info (yt-dlp -J --flat-playlist)
    metadata.py            Parses the JSON (qualities, estimated sizes, playlist items)
    queue.py               Queue with a concurrency limit
    errors.py              yt-dlp errors → readable messages
    tags.py                Tag guessing (splitting "Artist - Song", removing labels)
    history.py             Download history
  ui/                      PySide6 user interface
tests/
  test_core.py             Unit tests (pytest)
  test_i18n.py             Checks for missing translations and placeholder mismatches
  integration_local.py     Real yt-dlp download flow against a local server
  fake_youtube.py          A yt-dlp stand-in that mimics YouTube responses
  gui_smoke.py, gui_scenario.py, tag_scenario.py, ui_scenario.py   UI flow tests
```

yt-dlp is **called as a separate executable** rather than bundled as a library. YouTube changes often, and this way `yt-dlp -U` is enough to keep up without rebuilding the app.

## Adding a translation

UI text is wrapped in `tr("Korean text")`, using the Korean source as the key (`tubegetapp/i18n.py`).

1. Copy `tubegetapp/locales/en.py` to a new file such as `ja.py` and translate the values (right-hand side) of `STRINGS`. Keep placeholders like `{name}` as they are.
2. Add `"ja": "日本語"` to `LANGUAGES` in `tubegetapp/i18n.py`, and load the new file in `_load()`.
3. Run `python -m pytest tests/test_i18n.py` to check for missing translations and placeholder errors.

Text without a translation falls back to the Korean source. During development you can force a language with the environment variable `TUBEGET_LANG=en`.
