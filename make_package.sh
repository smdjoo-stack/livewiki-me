#!/bin/bash
# 테스터에게 보낼 zip 만들기 → dist/LiveWikiMe-테스트판-날짜.zip
# 개인 파일(토큰·API 키·설정·요약·로그·확장 열쇠)은 넣지 않음
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
PKG="$OUT/LiveWikiMe"
rm -rf "$PKG"
mkdir -p "$PKG/app/native_host" "$PKG/app/chrome_extension"

cp "$ROOT/packaging/install.sh" "$ROOT/packaging/uninstall.sh" \
   "$ROOT/packaging/install.command" "$ROOT/packaging/uninstall.command" \
   "$ROOT/packaging/설치 안내.html" "$PKG/"
cp "$ROOT/summarize.py" "$PKG/app/"
cp "$ROOT/native_host/livewiki_host.py" "$ROOT/native_host/run_host.sh" "$PKG/app/native_host/"
for f in manifest.json background.js content.js content.css sidepanel.html sidepanel.css sidepanel.js; do
  cp "$ROOT/chrome_extension/$f" "$PKG/app/chrome_extension/"
done
chmod +x "$PKG"/*.sh "$PKG"/*.command "$PKG/app/native_host/run_host.sh"

# 혹시 개인 파일이 섞였는지 마지막 확인
if find "$PKG" \( -name "claude_token.txt" -o -name "api_key.txt" -o -name "settings.json" \
     -o -name "*.pem" -o -name "host.log" -o -name "*.md" \) | grep -q .; then
  echo "❌ 개인 파일이 포함되어 중단합니다"; exit 1
fi
if grep -rqE "sk-ant-(oat|api)[0-9]{2}-[A-Za-z0-9_-]{20,}" "$PKG"; then
  echo "❌ 토큰/키로 보이는 값이 포함되어 중단합니다"; exit 1
fi

ZIP="$OUT/LiveWikiMe-test-$(date +%Y%m%d).zip"
rm -f "$ZIP"
(cd "$OUT" && ditto -c -k --keepParent --norsrc --noextattr LiveWikiMe "$ZIP")
echo "✅ 만들었어요: $ZIP"
