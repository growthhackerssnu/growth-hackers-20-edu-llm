#!/bin/sh
# 개발 환경 준비. macOS / Linux 는 터미널에서, Windows 는 Git Bash 에서 실행하세요.
#
#   sh init.sh
#
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv 가 없어서 설치합니다..."
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      powershell -NoProfile -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
      ;;
    *)
      curl -LsSf https://astral.sh/uv/install.sh | sh
      ;;
  esac
  # 방금 설치한 uv 를 이번 셸에서 바로 쓰기 위한 PATH
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi

uv sync

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 를 만들었습니다. OPENAI_API_KEY 를 채워 넣으세요."
fi

uv run python mock_api.py

echo
echo "준비 끝. 데모 실행:  uv run streamlit run app.py"
