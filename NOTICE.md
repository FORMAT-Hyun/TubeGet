# NOTICE

TubeGet's own code is licensed under the [MIT License](LICENSE).
This file has additional notes. They are not part of the license terms.

[한국어 요약](#한국어-요약)

## Scope

The MIT License covers TubeGet's own source code, artwork and documentation in this repository.
It does not cover the third-party software listed below, which keeps its own license.

## Third-party software

| Software | License | Used in |
|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | The Unlicense | Windows (downloaded at runtime), Android (bundled) |
| [FFmpeg](https://ffmpeg.org/legal.html) | LGPL-2.1+ / GPL-2.0+ (depending on the build) | Windows (downloaded at runtime), Android (bundled) |
| [Deno](https://github.com/denoland/deno) | MIT | Windows (downloaded at runtime) |
| [Qt for Python (PySide6)](https://www.qt.io/qt-for-python) | LGPL-3.0 | Windows |
| [youtubedl-android](https://github.com/yausername/youtubedl-android) | GPL-3.0 | Android |
| [Python](https://docs.python.org/3/license.html) | PSF License | Windows, Android (bundled) |
| QuickJS | MIT | Android (bundled in youtubedl-android) |
| Jetpack Compose, AndroidX, Coil | Apache-2.0 | Android |

The Windows app downloads yt-dlp, FFmpeg and Deno at runtime; they are not part of this repository.
The Android APK bundles youtubedl-android, which includes Python, yt-dlp, FFmpeg and QuickJS.
Because youtubedl-android is GPL-3.0, **the distributed Android APK as a whole is provided under the terms of the GPL-3.0**.
TubeGet's own code remains available under the MIT License, which is compatible with the GPL-3.0.

## Responsible use

TubeGet is a tool. Download only content that you own or have permission to save,
and follow YouTube's Terms of Service and the copyright laws of your country.
The authors are not responsible for how the software is used.

## Trademarks

"YouTube" is a trademark of Google LLC. TubeGet is an independent project
and is not affiliated with, endorsed by or sponsored by Google or YouTube.

## 한국어 요약

참고용이에요. 법적 효력은 [LICENSE](LICENSE)의 영어 원문에 있어요.

- TubeGet 코드는 MIT 라이선스예요. 누구나 무료로 쓰고, 고치고, 나누고, 팔 수도 있어요. 단, 저작권 표시와 라이선스 글을 함께 넣어 주세요.
- 아무 보증 없이 "있는 그대로" 제공돼요. 쓰다가 생긴 문제에 대해 만든 사람은 책임지지 않아요.
- yt-dlp, FFmpeg, PySide6, youtubedl-android 같은 외부 도구는 각자의 라이선스를 따라요 (위 표 참고).
- 안드로이드 APK는 GPL-3.0인 youtubedl-android를 포함하므로 **APK 전체는 GPL-3.0 조건**을 따라요.
- 저장할 권리가 있는 콘텐츠만 받아 주세요. 사용에 대한 책임은 사용자에게 있어요.
- TubeGet은 Google·YouTube와 관계없는 개인 프로젝트예요.
