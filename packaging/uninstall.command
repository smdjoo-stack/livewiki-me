#!/bin/bash
# 더블클릭용 (처음엔 마우스 오른쪽 클릭 → 열기)
cd "$(dirname "$0")" || exit 1
bash ./uninstall.sh
echo
read -r -n 1 -p "아무 키나 누르면 창이 닫힙니다…"
