#!/bin/bash
# 테스터에게 보낼 zip 만들기 (Mac + Windows 공용) → dist/LiveWikiMe-v버전.zip  (버전은 VERSION 파일)
# 개인 파일(토큰·API 키·설정·요약·로그·확장 열쇠)은 넣지 않음
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
PKG="$OUT/LiveWikiMe"
rm -rf "$PKG"
mkdir -p "$PKG/app/native_host" "$PKG/app/chrome_extension"

# 설치·삭제 (Mac: .sh/.command, Windows: .bat/_win.py) + 안내서
for f in install.sh uninstall.sh install.command uninstall.command \
         install.bat uninstall.bat install_win.py uninstall_win.py INSTALL-GUIDE.html; do
  cp "$ROOT/packaging/$f" "$PKG/"
done
cp "$ROOT/summarize.py" "$PKG/app/"
cp "$ROOT/native_host/livewiki_host.py" "$ROOT/native_host/run_host.sh" "$ROOT/native_host/run_host.bat" "$PKG/app/native_host/"
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

# 버전: VERSION 파일 (크롬 확장 manifest.json의 version과 같아야 함)
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
MANIFEST_VERSION="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$ROOT/chrome_extension/manifest.json")"
if [ "$VERSION" != "$MANIFEST_VERSION" ]; then
  echo "❌ VERSION($VERSION)과 manifest.json의 version($MANIFEST_VERSION)이 달라요. 둘을 맞춘 뒤 다시 실행하세요."; exit 1
fi
echo "$VERSION" > "$PKG/VERSION"
ZIP="$OUT/LiveWikiMe-v$VERSION.zip"
rm -f "$ZIP"
# Python zipfile로 압축: 윈도우에서도 파일 이름(UTF-8)과 맥 실행 권한이 유지됨
python3 - "$OUT" "$ZIP" <<'PY'
import os, sys, zipfile
out, zpath = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(os.path.join(out, "LiveWikiMe")):
        dirs.sort()
        for name in sorted(files):
            if name == ".DS_Store":
                continue
            full = os.path.join(root, name)
            z.write(full, os.path.relpath(full, out))
PY
echo "✅ 만들었어요: $ZIP"
