#!/bin/bash
# 크롬이 실행하는 진입점. 크롬은 터미널과 PATH가 달라서 claude 위치를 직접 알려 줌.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/../.venv/bin/python" -I "$DIR/livewiki_host.py" "$@" 2>>"$DIR/host.log"
