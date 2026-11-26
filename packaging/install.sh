#!/bin/bash
# 나만의 라이브위키 — 설치 / 업데이트 (Mac 전용)
# 사용: bash install.sh   (다시 실행하면 업데이트. 요약·설정·토큰은 그대로 유지)
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/LiveWikiMe"
EXT_ID="objnibninibbakahlbohjbeennapdnnh"
HOST_NAME="com.livewiki.me"

ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
fail() { echo ""; echo "❌ $*"; exit 1; }

echo ""
echo "✨ 나만의 라이브위키 설치를 시작합니다"
echo ""

# 1. 환경 확인 ────────────────────────────────────
echo "1/4 환경 확인"
[ "$(uname)" = "Darwin" ] || fail "Mac에서만 설치할 수 있어요."
[ -d "$SRC/app" ] || fail "설치 파일(app 폴더)을 찾지 못했어요. zip을 푼 폴더 안의 install.sh를 실행해 주세요."

if [ -d "/Applications/Google Chrome.app" ] || [ -d "$HOME/Applications/Google Chrome.app" ]; then
  ok "Google Chrome 있음"
else
  warn "Google Chrome을 찾지 못했어요. (Brave·Edge를 쓰신다면 괜찮아요)"
fi

# Python 3.9 이상 찾기 (최신 우선)
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  p="$(command -v "$c" 2>/dev/null || true)"
  [ -n "$p" ] || continue
  if [ "$p" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1; then
    continue  # 개발자 도구가 없으면 /usr/bin/python3는 설치 창만 띄움
  fi
  if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$p"; break
  fi
done
if [ -z "$PY" ]; then
  echo ""
  echo "Python이 필요해요. 아래 창이 뜨면 '설치'를 눌러 주세요(5~10분)."
  echo "설치가 끝나면 이 설치 프로그램을 다시 실행해 주세요."
  xcode-select --install >/dev/null 2>&1 || true
  fail "Python 3.9 이상을 찾지 못했어요."
fi
ok "Python: $("$PY" --version 2>&1)"

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -z "$CLAUDE_BIN" ] && [ -x "$HOME/.local/bin/claude" ] && CLAUDE_BIN="$HOME/.local/bin/claude"
if [ -n "$CLAUDE_BIN" ]; then
  ok "Claude Code 있음 (구독 토큰으로 사용 가능)"
else
  warn "Claude Code가 없어요 → API 키로 쓰거나, 나중에 Claude Code를 설치하면 구독으로도 쓸 수 있어요"
fi

# 2. 파일 복사 ────────────────────────────────────
echo ""
echo "2/4 프로그램 복사 → $DEST"
mkdir -p "$DEST"
# 코드만 덮어씀. summaries / .drafts / settings.json / 토큰·API 키 파일은 건드리지 않음
cp -R "$SRC/app/." "$DEST/"
cp "$SRC/uninstall.sh" "$SRC/INSTALL-GUIDE.html" "$DEST/" 2>/dev/null || true
chmod +x "$DEST/native_host/run_host.sh" "$DEST/uninstall.sh" 2>/dev/null || true
mkdir -p "$DEST/summaries"
ok "복사 완료"

# 3. 파이썬 패키지 ────────────────────────────────
echo ""
echo "3/4 필요한 패키지 설치 (1~3분)"
if [ ! -x "$DEST/.venv/bin/python" ]; then
  "$PY" -m venv "$DEST/.venv" || fail "가상환경을 만들지 못했어요."
fi
"$DEST/.venv/bin/python" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
"$DEST/.venv/bin/python" -m pip install -q --upgrade youtube-transcript-api anthropic pymupdf \
  || fail "패키지 설치에 실패했어요. 인터넷 연결을 확인하고 다시 실행해 주세요."
"$DEST/.venv/bin/python" -c "import youtube_transcript_api, anthropic" || fail "패키지 확인에 실패했어요."
ok "패키지 설치 완료"

# 4. 브라우저 연결 등록 ───────────────────────────
echo ""
echo "4/4 브라우저 연결 등록"
registered=0
for b in "Google/Chrome" "Google/Chrome Beta" "BraveSoftware/Brave-Browser" "Microsoft Edge" "Chromium"; do
  base="$HOME/Library/Application Support/$b"
  [ -d "$base" ] || continue
  mkdir -p "$base/NativeMessagingHosts"
  cat > "$base/NativeMessagingHosts/$HOST_NAME.json" <<EOF
{
  "name": "$HOST_NAME",
  "description": "나만의 라이브위키 요약기",
  "path": "$DEST/native_host/run_host.sh",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://$EXT_ID/"]
}
EOF
  ok "$b"
  registered=1
done
[ "$registered" = 1 ] || warn "등록할 브라우저를 찾지 못했어요. 크롬을 한 번 실행한 뒤 다시 설치해 주세요."

echo ""
echo "🎉 설치 완료!"
echo ""
echo "남은 단계 (처음 한 번만):"
echo "  1) 크롬 주소창에  chrome://extensions  입력"
echo "  2) 오른쪽 위 '개발자 모드' 켜기"
echo "  3) '압축해제된 확장 프로그램을 로드합니다' → 아래 폴더 선택"
echo "       $DEST/chrome_extension"
echo "     (폴더 선택 창에서 ⌘+Shift+H 를 누르면 홈 폴더로 가요 → LiveWikiMe → chrome_extension)"
echo "  4) 유튜브 영상을 열고 ✨ 요약 → 패널의 ⚙️ 설정에서 구독 토큰 또는 API 키 넣기"
echo ""
open "$DEST" >/dev/null 2>&1 || true
