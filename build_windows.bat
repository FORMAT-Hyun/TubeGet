@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv 2>nul || python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo 파이썬을 찾지 못했어요. Python 3.10 이상을 설치해 주세요.
    pause
    exit /b 1
)

echo [TubeGet] 빌드 도구 설치 중...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt pyinstaller

echo [TubeGet] exe 만드는 중... (몇 분 걸려요)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed ^
    --name TubeGet ^
    --icon assets\icon.ico ^
    --add-data "assets;assets" ^
    --paths "%CD%" ^
    --collect-submodules tubegetapp ^
    main.py

if exist "dist\TubeGet\TubeGet.exe" (
    echo.
    echo 완료! dist\TubeGet 폴더 전체가 프로그램이에요. TubeGet.exe 를 실행하세요.
    explorer "dist\TubeGet"
) else (
    echo 빌드에 실패했어요. 위 메시지를 확인해 주세요.
)
pause
