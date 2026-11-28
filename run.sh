#!/usr/bin/env bash
# macOS / Linux 실행 스크립트
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "[Acortube] 처음 실행: 가상환경과 패키지를 준비하는 중..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python main.py
