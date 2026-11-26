#!/bin/bash
# 나만의 라이브위키 — 삭제
DEST="$HOME/LiveWikiMe"
HOST_NAME="com.livewiki.me"

echo ""
echo "나만의 라이브위키를 삭제합니다."
for b in "Google/Chrome" "Google/Chrome Beta" "BraveSoftware/Brave-Browser" "Microsoft Edge" "Chromium"; do
  rm -f "$HOME/Library/Application Support/$b/NativeMessagingHosts/$HOST_NAME.json"
done
echo "  ✅ 브라우저 연결 해제"

if [ -d "$DEST" ]; then
  echo ""
  echo "프로그램 폴더: $DEST"
  echo "(이 안의 summaries 폴더에 저장한 요약과 토큰·API 키도 함께 지워집니다.)"
  read -r -p "폴더까지 지울까요? [y/N] " ans
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    rm -rf "$DEST"
    echo "  ✅ 폴더 삭제"
  else
    echo "  폴더는 남겨 두었어요."
  fi
fi
echo ""
echo "마지막으로 크롬의 chrome://extensions 에서 '나만의 라이브위키'를 '삭제'해 주세요."
echo ""
