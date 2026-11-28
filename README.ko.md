# Acortube

[English](README.md) | **한국어**

**yt-dlp 기반 유튜브 다운로더 (GUI) · Windows / macOS**

주소를 붙여넣고 화질과 형식을 고르면 받아주는 데스크톱 프로그램이에요.
다운로드는 [yt-dlp](https://github.com/yt-dlp/yt-dlp)가 하고, Acortube는 그걸 편하게 쓰게 해 주는 화면이에요.

## 주요 기능

- **영상 받기**: 최고 화질부터 4K, 1440p, 1080p, 720p까지 고를 수 있고, 화질마다 예상 크기를 보여줘요. MP4, MKV, WebM을 지원해요.
- **음원만 받기**: MP3, M4A, Opus, FLAC, WAV, 원본 그대로
- **재생목록**: 목록에서 체크하거나 범위(`1-10, 15, 20-`)로 골라요. 폴더 만들기와 번호 붙이기는 선택이에요.
- **자막 / 더빙**: 영상마다 실제로 있는 자막(올린 자막, 자동 생성·번역 자막)과 더빙(다른 언어 음성 트랙, 유튜브 자동 더빙 등)을 골라요.
  - 저장 방식: 영상에 넣기, `.srt` 파일로 따로 저장, 둘 다
  - 고른 언어 음성이 없는 영상은 원본 음성으로 받아요.
- **태그**: 음원(MP3, M4A)과 영상(MP4, MKV)의 제목, 아티스트, 앨범, 연도, 표지를 영상마다 정하거나 끌 수 있어요.
  - "AJR - Way Less Sad (Official Video)" 같은 제목을 아티스트 `AJR`, 제목 `Way Less Sad`로 자동 정리해서 미리 채워줘요. 직접 고칠 수도 있어요.
  - 끄면 태그와 표지가 전혀 없는 깨끗한 파일로 저장해요.
  - 재생목록은 영상마다 자동으로 정리해요.
- **편집 호환 (H.264)**: 편집 프로그램이나 오래된 기기에서 잘 열리는 코덱을 우선해요.
- **다운로드 큐**: 여러 개를 동시에 받고, 취소하고, 이어받아요. 실패하면 원인을 알려주고 로그를 볼 수 있어요.
  - 영상과 음성을 따로 받아도 진행률 막대는 하나로 보여줘요.
  - 껐다 켜도 대기 중인 목록을 다시 불러와서 이어서 받아요.
  - 이미 받은 파일은 '건너뜀'으로 표시하고 [덮어쓰기] 버튼을 보여줘요.
  - 목록에서 지우면 받다 만 파일(`.part` 등)도 함께 정리해요.
- **바로 받기**: 툴바의 스위치를 켜면 [링크 붙여넣기]를 누르자마자 지금 설정으로 받아요. 재생목록은 고르는 창이 떠요.
- **기록**: 받은 파일 열기, 폴더 열기, 다시 받기
- **도구 자동 설치**: 처음 실행할 때 yt-dlp, ffmpeg, Deno를 버튼 하나로 설치해요. yt-dlp 업데이트는 하루에 한 번만 확인해요.
- **다국어**: 한국어와 English를 지원해요. [설정 → 언어 / Language]에서 고르거나 '자동'(시스템 언어)으로 둘 수 있고, 다시 켜면 적용돼요.
- **그 밖에**: 어두운 테마, 창에 주소 끌어다 놓기, 다 받으면 알림, 한 번에 하나만 실행, 앱 정보(F1)에서 문제 신고용 정보 복사

## 설치하기

**[Releases](https://github.com/FORMAT-Hyun/Acortube/releases/latest)에서 최신 버전을 받으세요.** 파이썬 같은 다른 프로그램은 필요 없어요.

| 파일 | 어디에 | 설명 |
|---|---|---|
| `Acortube-<버전>-Setup-win64.exe` | Windows 10/11 | **설치 버전 (추천)**. 일반 프로그램처럼 설치하고 시작 메뉴에서 켜요. |
| `Acortube-<버전>-Portable-win64.zip` | Windows 10/11 | **포터블**. 설치 없이 새 폴더에 압축을 풀고 `Acortube.exe`를 실행해요. |
| `Acortube-<버전>-macOS-arm64.dmg` | macOS 12 이상 (Apple Silicon: M1/M2/M3/M4) | **Mac 앱**. Apple Silicon Mac용이에요. |
| `Acortube-<버전>-macOS-x64.dmg` | macOS 12 이상 (Intel) | **Mac 앱**. Intel Mac용이에요. |

### Windows

1. 설치 파일을 실행해요. '나만 설치'를 고르면 관리자 권한이 필요 없어요.
   - 코드 서명이 없어서 SmartScreen 경고가 뜰 수 있어요. **추가 정보 → 실행**을 누르세요.
2. 처음 켜면 **[도구 상태]** 창이 떠요. **[없는 도구 설치]**를 누르면 yt-dlp, ffmpeg, Deno를 자동으로 받아요 (약 200MB, 한 번만).

- 새 버전은 그냥 새 설치 파일을 실행하면 돼요. 설정, 기록, 설치된 도구는 `%APPDATA%\Acortube`에 있어서 그대로 남아요.
- 제거는 [설정 → 앱 → 설치된 앱]에서 해요. 제거할 때 설정과 도구 폴더도 지울지 물어봐요.

### macOS

1. DMG를 열고 **Acortube**를 **응용 프로그램(Applications)** 폴더로 끌어다 놓아요. (어느 걸 받을지 모르겠으면: Apple 메뉴 → 이 Mac에 관하여에서 "Apple M…"이면 arm64, "Intel"이면 x64)
2. Apple 서명이 없어서 처음에는 macOS가 실행을 막아요. 이렇게 열어 주세요:
   - Acortube를 한 번 열고 경고를 닫은 뒤, **시스템 설정 → 개인정보 보호 및 보안**에서 Acortube 옆의 **그래도 열기**를 눌러요. 또는
   - 터미널에서: `xattr -dr com.apple.quarantine /Applications/Acortube.app`
3. 처음 켜면 **[없는 도구 설치]**를 눌러 yt-dlp, ffmpeg, Deno를 자동으로 받아요 (한 번만).

- 설정, 기록, 도구는 `~/Library/Application Support/Acortube`에 있어요.

### 아이폰

아이폰 버전은 없어요. 앱스토어가 유튜브 다운로더를 허용하지 않고, iOS는 앱 안에서 yt-dlp·ffmpeg 같은 도구를 실행할 수 없게 막아 두었어요.

### 안드로이드 (휴대폰)

휴대폰 앱은 **[Acortube Mobile](https://github.com/FORMAT-Hyun/Acortube-Mobile)** 저장소로 분리됐어요. APK는 [그쪽 Releases](https://github.com/FORMAT-Hyun/Acortube-Mobile/releases/latest)에서 받으세요.

## 사용법

1. 유튜브 주소를 복사하고 위쪽 빨간 **[링크 붙여넣기]** 버튼을 눌러요. 주소를 직접 입력하려면 Ctrl+L, 창에 끌어다 놓아도 돼요.
2. 위쪽 툴바에서 다운로드 종류(영상/오디오), 화질(오디오는 음질), 포맷, 저장 위치, 자막/더빙, 태그를 골라요.
3. 목록 맨 위에 영상 카드(썸네일, 정보, 예상 크기)가 생기면 카드의 **[다운로드]**를 눌러요. 여러 링크를 불러 두고 카드마다 설정을 따로 정할 수도 있어요.

[바로 받기]를 켜 두면 2~3번 없이 바로 시작해요.

### 문제가 생기면

| 상황 | 해결 방법 |
|---|---|
| "봇 확인" 오류 | VPN(Cloudflare WARP 등)을 켜 두었다면 끄고 다시 시도하세요. 그래도 안 되면 [설정 → 브라우저 쿠키]에서 Firefox를 고르세요 |
| "연령 제한", "멤버십 전용" 오류 | [설정 → 브라우저 쿠키]에서 유튜브에 로그인된 Firefox를 고르세요. Windows의 최신 크롬·엣지·웨일은 쿠키를 암호화해서 보통 읽을 수 없어요 |
| 403 오류, 갑자기 안 받아짐 | 유튜브가 바뀐 경우가 많아요. [도구 상태] → [yt-dlp 업데이트] |
| 화질이 360p까지만 나옴 | Deno가 없을 때 자주 생겨요. [도구 상태]에서 설치하세요 |
| 편집 프로그램에서 영상이 안 열림 | 설정에서 **편집 호환 (H.264)**을 켜고 다시 받으세요 |
| 취소한 다운로드 이어받기 | 목록에서 **[다시 시도]**를 누르면 받던 부분부터 이어받아요 |
| 화질 목록이나 크기가 이상함 | [도구 상태] → [진단 정보 폴더]의 `last_info.json`, `last_error.txt`를 확인하세요 |

## 파일 위치

| 무엇 | Windows | macOS | Linux |
|---|---|---|---|
| 설정, 기록, 설치된 도구(`bin`) | `%APPDATA%\Acortube` | `~/Library/Application Support/Acortube` | `~/.config/tubeget` |
| 기본 저장 위치 | `다운로드\Acortube` | 같음 | 같음 |

## 구조

```
main.py                    진입점
installer/Acortube.iss      설치 마법사 스크립트 (Inno Setup)
build_installer.bat        exe 빌드부터 설치 파일 생성까지 한 번에
tubegetapp/
  config.py                설정 (JSON)
  i18n.py                  다국어: tr("한국어 원문") → 현재 언어
  locales/en.py            영어 번역
  paths.py / utils.py      경로, 포맷팅, 파일명 정리
  core/
    deps.py                yt-dlp/ffmpeg/JS 런타임 찾기, 버전 확인
    installer.py           도구 자동 설치, yt-dlp -U 업데이트 (백그라운드)
    options.py             다운로드 옵션 → yt-dlp 명령줄 인자
    progress.py            yt-dlp 출력 파싱
    runner.py              다운로드 1개 = yt-dlp 프로세스 1개 (QProcess)
    fetcher.py             영상·재생목록 정보 조회 (yt-dlp -J --flat-playlist)
    metadata.py            JSON 해석 (화질 목록, 예상 크기, 재생목록 항목)
    queue.py               동시 실행 제한 큐
    errors.py              yt-dlp 오류 → 알기 쉬운 안내
    tags.py                태그 추측(아티스트 - 곡명 나누기, 꼬리표 지우기)
    history.py             기록 저장
  ui/                      PySide6 화면
tests/
  test_core.py             단위 테스트 (pytest)
  test_i18n.py             번역 누락·자리표시자 검사
  integration_local.py     로컬 서버로 실제 yt-dlp 다운로드 흐름 테스트
  fake_youtube.py          유튜브 응답을 흉내 내는 yt-dlp 대역
  gui_smoke.py, gui_scenario.py, tag_scenario.py, ui_scenario.py   화면 흐름 테스트
```

yt-dlp를 라이브러리로 넣지 않고 **별도 실행 파일로 호출**해요. 유튜브가 자주 바뀌어도 프로그램을 다시 빌드하지 않고 `yt-dlp -U`만으로 바로 대응할 수 있어요.

## 번역 추가하기

화면 글은 한국어 원문을 키로 쓰는 `tr("한국어 문장")`으로 감싸져 있어요 (`tubegetapp/i18n.py`).

1. `tubegetapp/locales/en.py`를 복사해 `ja.py` 같은 파일을 만들고, `STRINGS`의 값(오른쪽)을 번역해요. `{name}` 같은 자리표시자는 그대로 두세요.
2. `tubegetapp/i18n.py`의 `LANGUAGES`에 `"ja": "日本語"`를 넣고, `_load()`에서 새 파일을 불러오게 해요.
3. `python -m pytest tests/test_i18n.py`로 빠진 번역과 자리표시자 오류를 확인해요.

번역이 없는 문장은 한국어 원문이 그대로 나와요. 개발할 때는 환경 변수 `TUBEGET_LANG=en`으로 언어를 정할 수 있어요.

## 라이선스

Acortube 코드는 [MIT 라이선스](LICENSE)예요. 자유롭게 쓰고 고치고 나눌 수 있어요.

- 함께 쓰는 도구(yt-dlp, FFmpeg, PySide6 등)는 각자의 라이선스를 따라요. 자세한 내용은 [NOTICE.md](NOTICE.md)에 있어요.
- 저작권이 있는 콘텐츠는 저장할 권리가 있을 때만 받아 주세요. 사용에 대한 책임은 사용자에게 있어요.
