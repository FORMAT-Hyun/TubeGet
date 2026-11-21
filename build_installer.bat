@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ================================================
echo   TubeGet 설치 파일 만들기
echo ================================================
echo.
if exist "tubegetapp\__init__.py" goto have_src
echo 프로그램 파일(tubegetapp 폴더)이 없어요.
echo 압축 파일을 '모두 압축 풀기'로 새 폴더에 전부 푼 다음 다시 실행해 주세요.
goto fail
:have_src

rem ---- 1. 파이썬 가상환경 ----
if exist ".venv\Scripts\python.exe" goto have_venv
echo [1/4] 파이썬 가상환경 만드는 중...
py -3 -m venv .venv 2>nul
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if exist ".venv\Scripts\python.exe" goto have_venv
echo 파이썬을 찾지 못했어요. https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치해 주세요.
echo 설치할 때 "Add python.exe to PATH" 를 꼭 체크하세요.
goto fail
:have_venv
set "PY=.venv\Scripts\python.exe"

echo [2/4] 빌드 도구 설치 중...
"%PY%" -m pip install -q --upgrade pip
"%PY%" -m pip install -q -r requirements.txt pyinstaller
if errorlevel 1 goto fail

rem ---- 2. exe 빌드 ----
echo [3/4] 프로그램 빌드 중... (몇 분 걸려요)
if exist "dist\TubeGet" rmdir /s /q "dist\TubeGet"
"%PY%" -m PyInstaller --noconfirm --clean --windowed --name TubeGet --icon assets\icon.ico --add-data "assets;assets" --paths "%CD%" --collect-submodules tubegetapp main.py
if not exist "dist\TubeGet\TubeGet.exe" goto fail

rem ---- 3. Inno Setup 찾기 (없으면 winget 으로 설치) ----
call :find_iscc
if defined ISCC goto have_iscc
echo Inno Setup 이 없어서 설치할게요 (winget)...
winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
call :find_iscc
if defined ISCC goto have_iscc
echo.
echo Inno Setup 을 자동으로 설치하지 못했어요.
echo https://jrsoftware.org/isdl.php 에서 Inno Setup 6 을 설치한 뒤 이 파일을 다시 실행해 주세요.
goto fail
:have_iscc

rem ---- 4. 설치 파일 만들기 ----
for /f "usebackq delims=" %%v in (`%PY% -c "import tubegetapp; print(tubegetapp.APP_VERSION)"`) do set "VER=%%v"
if not defined VER (
    echo 버전 정보를 읽지 못했어요.
    goto fail
)
echo [4/4] 설치 파일 만드는 중... ^(버전 %VER%^)
"%ISCC%" /Q "/DMyAppVersion=%VER%" "installer\TubeGet.iss"
if errorlevel 1 goto fail
if not exist "dist\TubeGet-Setup-%VER%.exe" goto fail

echo.
echo 완료! dist\TubeGet-Setup-%VER%.exe 를 실행하면 설치 마법사가 열려요.
explorer /select,"%CD%\dist\TubeGet-Setup-%VER%.exe"
pause
exit /b 0

:find_iscc
set "ISCC="
for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%i"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0

:fail
echo.
echo 실패했어요. 위에 나온 메시지를 확인해 주세요.
pause
exit /b 1
