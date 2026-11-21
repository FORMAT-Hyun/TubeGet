@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "tubegetapp\__init__.py" (
    echo 프로그램 파일^(tubegetapp 폴더^)이 없어요.
    echo 압축 파일을 '모두 압축 풀기'로 새 폴더에 전부 푼 다음 다시 실행해 주세요.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [TubeGet] 처음 실행: 파이썬 가상환경을 만드는 중...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo 파이썬을 찾지 못했어요. https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치해 주세요.
        echo 설치할 때 "Add python.exe to PATH" 를 꼭 체크하세요.
        pause
        exit /b 1
    )
    echo [TubeGet] 필요한 패키지 설치 중... ^(처음 한 번, 1~2분^)
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

start "" ".venv\Scripts\pythonw.exe" main.py
