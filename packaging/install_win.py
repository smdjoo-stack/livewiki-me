"""
나만의 라이브위키 — 윈도우 설치 / 업데이트
install.bat이 실행합니다. (다시 실행하면 업데이트. 요약·설정·토큰은 그대로 유지)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
DEST = Path(os.environ.get("LIVEWIKI_DEST") or (Path.home() / "LiveWikiMe"))
EXT_ID = "objnibninibbakahlbohjbeennapdnnh"
HOST_NAME = "com.livewiki.me"
# 브라우저별 네이티브 메시징 등록 위치 (HKEY_CURRENT_USER 아래)
REG_KEYS = {
    "Chrome": r"Software\Google\Chrome\NativeMessagingHosts",
    "Edge": r"Software\Microsoft\Edge\NativeMessagingHosts",
    "Brave": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    "Chromium": r"Software\Chromium\NativeMessagingHosts",
}
IS_WIN = sys.platform == "win32"


def ok(msg):
    print(f"  ✅ {msg}")


def warn(msg):
    print(f"  ⚠️  {msg}")


def fail(msg):
    print(f"\n❌ {msg}")
    sys.exit(1)


def venv_python():
    return DEST / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")


def register(manifest_path, winreg=None):
    """HKCU\\...\\NativeMessagingHosts\\com.livewiki.me = manifest 경로"""
    if winreg is None:
        import winreg  # 윈도우 전용 모듈
    done = []
    for name, base in REG_KEYS.items():
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + HOST_NAME)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest_path))
            winreg.CloseKey(key)
            done.append(name)
        except OSError as e:
            warn(f"{name} 등록 실패: {e}")
    return done


def main(winreg=None):
    print("\n✨ 나만의 라이브위키 설치를 시작합니다 (Windows)\n")

    print("1/4 환경 확인")
    if not (SRC / "app").is_dir():
        fail("설치 파일(app 폴더)을 찾지 못했어요. zip을 모두 푼 폴더에서 install.bat을 실행해 주세요.")
    if sys.version_info < (3, 9):
        fail("Python 3.9 이상이 필요해요.")
    ok(f"Python {sys.version.split()[0]}")
    claude = shutil.which("claude") or next(
        (str(p) for p in [Path.home() / ".local/bin/claude.exe"] if p.exists()), None)
    if claude:
        ok("Claude Code 있음 (구독 토큰으로 사용 가능)")
    else:
        warn("Claude Code가 없어요 → API 키로 쓰거나, 나중에 Claude Code를 설치하면 구독으로도 쓸 수 있어요")

    print(f"\n2/4 프로그램 복사 → {DEST}")
    DEST.mkdir(parents=True, exist_ok=True)
    # 코드만 덮어씀. summaries / .drafts / settings.json / 토큰·API 키는 건드리지 않음
    shutil.copytree(SRC / "app", DEST, dirs_exist_ok=True)
    for f in ("uninstall.bat", "uninstall_win.py", "INSTALL-GUIDE.html"):
        if (SRC / f).exists():
            shutil.copy2(SRC / f, DEST / f)
    (DEST / "summaries").mkdir(exist_ok=True)
    ok("복사 완료")

    print("\n3/4 필요한 패키지 설치 (1~3분)")
    if not venv_python().exists():
        r = subprocess.run([sys.executable, "-m", "venv", str(DEST / ".venv")])
        if r.returncode != 0:
            fail("가상환경을 만들지 못했어요.")
    py = str(venv_python())
    subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade",
                        "youtube-transcript-api", "anthropic", "pymupdf"])
    if r.returncode != 0:
        fail("패키지 설치에 실패했어요. 인터넷 연결을 확인하고 다시 실행해 주세요.")
    if subprocess.run([py, "-c", "import youtube_transcript_api, anthropic"]).returncode != 0:
        fail("패키지 확인에 실패했어요.")
    ok("패키지 설치 완료")

    print("\n4/4 브라우저 연결 등록")
    host_dir = DEST / "native_host"
    launcher = host_dir / ("run_host.bat" if IS_WIN else "run_host.sh")
    manifest = host_dir / f"{HOST_NAME}.json"
    manifest.write_text(json.dumps({
        "name": HOST_NAME,
        "description": "나만의 라이브위키 요약기",
        "path": str(launcher),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{EXT_ID}/"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    done = register(manifest, winreg)
    if done:
        ok("등록: " + ", ".join(done))
    else:
        fail("브라우저 연결을 등록하지 못했어요.")

    ext = DEST / "chrome_extension"
    print("\n🎉 설치 완료!\n")
    print("남은 단계 (처음 한 번만):")
    print("  1) 크롬 주소창에  chrome://extensions  입력 (엣지는 edge://extensions)")
    print("  2) '개발자 모드' 켜기")
    print("  3) '압축해제된 확장 프로그램을 로드합니다' → 아래 폴더 선택")
    print(f"       {ext}")
    print("  4) 유튜브 영상을 열고 ✨ 요약 → 패널의 ⚙️ 설정에서 구독 토큰 또는 API 키 넣기\n")
    if IS_WIN:
        try:
            os.startfile(str(DEST))  # 탐색기로 설치 폴더 열기
        except OSError:
            pass


if __name__ == "__main__":
    main()
