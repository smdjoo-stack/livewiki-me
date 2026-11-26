"""나만의 라이브위키 — 윈도우 삭제 (uninstall.bat이 실행)"""
import shutil
import sys
from pathlib import Path

DEST = Path.home() / "LiveWikiMe"
HOST_NAME = "com.livewiki.me"
REG_KEYS = [
    r"Software\Google\Chrome\NativeMessagingHosts",
    r"Software\Microsoft\Edge\NativeMessagingHosts",
    r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts",
    r"Software\Chromium\NativeMessagingHosts",
]


def main():
    import winreg
    print("\n나만의 라이브위키를 삭제합니다.")
    for base in REG_KEYS:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base + "\\" + HOST_NAME)
        except OSError:
            pass
    print("  ✅ 브라우저 연결 해제")

    here = Path(__file__).resolve().parent
    if DEST.exists():
        print(f"\n프로그램 폴더: {DEST}")
        print("(이 안의 summaries 폴더에 저장한 요약과 토큰·API 키도 함께 지워집니다.)")
        ans = input("폴더까지 지울까요? [y/N] ").strip().lower()
        if ans == "y":
            if here == DEST or DEST in here.parents:
                print("  설치 폴더 안에서 실행 중이라 직접 지울 수 없어요. 이 창을 닫은 뒤 탐색기에서 폴더를 지워 주세요.")
            else:
                shutil.rmtree(DEST, ignore_errors=True)
                print("  ✅ 폴더 삭제")
        else:
            print("  폴더는 남겨 두었어요.")
    print("\n마지막으로 chrome://extensions 에서 '나만의 라이브위키'를 '삭제'해 주세요.\n")


if __name__ == "__main__":
    main()
