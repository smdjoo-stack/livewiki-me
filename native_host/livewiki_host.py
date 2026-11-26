#!/usr/bin/env python3
"""
크롬 확장 ↔ summarize.py 연결 프로그램 (크롬 '네이티브 메시징' 호스트)
크롬이 필요할 때 자동으로 실행합니다. 직접 실행할 일은 없습니다.

받는 메시지:  {"action": "summarize", "url": "...", "force": false}
             {"action": "save", "path": "...", "other": false}  ← 임시 요약을 기본 폴더(또는 고른 폴더)에 저장
             {"action": "settings"} / {"action": "set_save_dir"}  ← 기본 저장 폴더 보기/바꾸기
             {"action": "chat", "path": "...", "history": [...], "question": "..."}
             {"action": "reveal", "path": "..."}   ← Finder에서 파일 보기
보내는 메시지: {"ok": true, "markdown": "...", "path": "...", "cached": false}
             {"ok": false, "error": "..."}
"""
import json
import struct
import shutil
import subprocess
import sys
from pathlib import Path

# 크롬과의 대화 통로(stdout)를 따로 잡아 두고, summarize.py의 print는 stderr로 보냄
CHANNEL_OUT = sys.stdout.buffer
CHANNEL_IN = sys.stdin.buffer
sys.stdout = sys.stderr

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import summarize  # noqa: E402


def read_message():
    raw = CHANNEL_IN.read(4)
    if len(raw) < 4:
        return None
    size = struct.unpack("<I", raw)[0]
    return json.loads(CHANNEL_IN.read(size).decode("utf-8"))


def send_message(obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    CHANNEL_OUT.write(struct.pack("<I", len(data)))
    CHANNEL_OUT.write(data)
    CHANNEL_OUT.flush()


DRAFT_DAYS = 14  # 저장 안 한 임시 요약은 이 기간이 지나면 지움


# ── 저장 위치 설정 (settings.json) ─────────────────────
SETTINGS = BASE_DIR / "settings.json"


def load_settings():
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("save_dir", str(summarize.OUT_DIR))
    data.setdefault("known_dirs", [])
    return data


def store_settings(data):
    SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_dir(data, folder):
    folder = str(folder)
    if folder not in data["known_dirs"]:
        data["known_dirs"].append(folder)


def saved_dirs():
    """요약을 저장한 적 있는 모든 폴더 (기본 summaries 포함)"""
    data = load_settings()
    dirs = [summarize.OUT_DIR, Path(data["save_dir"])] + [Path(d) for d in data["known_dirs"]]
    out = []
    for d in dirs:
        if d not in out:
            out.append(d)
    return out


IS_WIN = sys.platform == "win32"


def choose_folder(prompt, start):
    """폴더 선택 창(맥: Finder 창, 윈도우: 폴더 찾아보기 창). 취소하면 None"""
    if IS_WIN:
        def ps_quote(t):
            return "'" + str(t).replace("'", "''") + "'"
        ps = (
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$o=New-Object System.Windows.Forms.Form -Property @{TopMost=$true};"
            "$d=New-Object System.Windows.Forms.FolderBrowserDialog;"
            f"$d.Description={ps_quote(prompt)};"
            f"$d.SelectedPath={ps_quote(start)};"
            "if($d.ShowDialog($o) -eq 'OK'){[Console]::Out.Write($d.SelectedPath)}"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.stdout.strip() or None
    script = [
        "-e", "activate",
        "-e", f'set f to choose folder with prompt "{prompt}" default location (POSIX file "{start}")',
        "-e", "POSIX path of f",
    ]
    r = subprocess.run(["osascript", *script], capture_output=True, text=True)
    if r.returncode != 0:
        return None  # 취소(-128) 등
    return r.stdout.strip().rstrip("/") or None


def reveal(path):
    """파일 위치를 Finder(맥) / 탐색기(윈도우)에서 보여 줌"""
    if IS_WIN:
        subprocess.run(["explorer", "/select,", str(path)])
    else:
        subprocess.run(["open", "-R", str(path)])


def is_ours(path):
    """요약을 저장한 폴더나 임시 폴더 안의 파일인지 (엉뚱한 파일 접근 방지)"""
    path = Path(path)
    if not path.exists():
        return False
    return any(d in path.parents for d in saved_dirs() + [summarize.DRAFT_DIR])


def is_saved(path):
    return summarize.DRAFT_DIR not in Path(path).parents


def find_existing(vid):
    """저장 폴더들 + 임시 폴더에서 이 영상의 가장 최근 요약을 찾음 (구독 사용량 절약)"""
    marker = f"watch?v={vid}"
    found = []
    for folder in saved_dirs() + [summarize.DRAFT_DIR]:
        if not folder.exists():
            continue
        for p in folder.glob("*.md"):
            try:
                if marker in p.read_text(encoding="utf-8")[:600]:
                    found.append(p)
            except OSError:
                continue
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def clean_drafts():
    import time
    if not summarize.DRAFT_DIR.exists():
        return
    limit = time.time() - DRAFT_DAYS * 86400
    for p in summarize.DRAFT_DIR.glob("*.md"):
        try:
            if p.stat().st_mtime < limit:
                p.unlink()
        except OSError:
            pass


def reply_for(path, cached):
    return {
        "ok": True,
        "markdown": Path(path).read_text(encoding="utf-8"),
        "path": str(path),
        "cached": cached,
        "saved": is_saved(path),
        "folder": str(Path(path).parent),
    }


def handle(msg):
    action = msg.get("action")
    if action == "reveal":
        path = Path(msg.get("path", ""))
        if is_ours(path):
            reveal(path)
            return {"ok": True}
        return {"ok": False, "error": "파일을 찾지 못했습니다."}

    if action == "status":
        # ⚙️ 설정 화면용: 지금 어떤 방식으로 Claude에 연결되는지
        import shutil as _sh
        has_key = bool(summarize.load_api_key())
        has_token = (BASE_DIR / "claude_token.txt").exists()
        has_cli = _sh.which("claude") is not None or any(
            (Path.home() / ".local" / "bin" / n).exists() for n in ("claude", "claude.exe"))
        # api: API 키 / token: 구독 토큰 / cli: Claude Code에 로그인된 상태 그대로 사용 / none: 없음
        mode = "api" if has_key else ("token" if has_token and has_cli else ("cli" if has_cli else "none"))
        return {"ok": True, "mode": mode, "has_api_key": has_key, "has_token": has_token,
                "has_cli": has_cli, "save_dir": load_settings()["save_dir"], "model": summarize.MODEL,
                "os": sys.platform}

    if action == "set_credential":
        # 패널에서 붙여넣은 구독 토큰/API 키를 파일로 저장 (빈 값이면 삭제)
        import re
        kind = msg.get("kind")
        files = {"token": "claude_token.txt", "api": "api_key.txt"}
        prefix = {"token": "sk-ant-oat", "api": "sk-ant-api"}
        if kind not in files:
            return {"ok": False, "error": "알 수 없는 종류"}
        target = BASE_DIR / files[kind]
        # 터미널에서 복사하면 줄바꿈·공백이 끼어들 수 있어 모두 제거
        value = re.sub(r"\s+", "", msg.get("value") or "")
        if not value:
            target.unlink(missing_ok=True)
            return {"ok": True, "deleted": True}
        if any(ch in value for ch in "•●·*…"):
            return {"ok": False, "error": "가려진 값(•••)이 들어 있어요. Claude 앱 안이 아니라 맥 기본 '터미널' 앱"
                                          "(윈도우는 PowerShell)에서 다시 실행해 복사해 주세요."}
        m = re.search(r"sk-ant-[a-z]+\d*-[A-Za-z0-9_\-]+", value)
        # 여러 번 붙여넣어 이어 붙은 경우 첫 번째 것만 사용
        if m and value.count("sk-ant-") > 1:
            m = re.match(r"(sk-ant-.+?)(?=sk-ant-|$)", m.group(0))
        if not m or not m.group(0).startswith(prefix[kind]):
            hint = "sk-ant-oat…로 시작하는 구독 토큰을" if kind == "token" else "sk-ant-api…로 시작하는 API 키를"
            return {"ok": False, "error": f"형식이 맞지 않아요. {hint} 붙여넣어 주세요."}
        if len(m.group(0)) < 90:
            return {"ok": False, "error": "값이 너무 짧아요. 앞부분만 복사된 것 같아요. 끝까지 전부 복사해 주세요."}
        target.write_text(m.group(0), encoding="utf-8")
        target.chmod(0o600)
        return {"ok": True}

    if action == "test":
        # 아주 짧은 질문으로 연결 확인
        try:
            answer = summarize.ask_claude("'연결 성공'이라고만 답하세요.", max_tokens=20)
        except SystemExit as e:
            return {"ok": False, "error": str(e.code or "알 수 없는 오류")}
        return {"ok": True, "answer": answer}

    if action == "settings":
        return {"ok": True, "save_dir": load_settings()["save_dir"]}

    if action == "set_save_dir":
        # 기본 저장 폴더 바꾸기 (폴더 선택 창)
        data = load_settings()
        folder = choose_folder("요약을 저장할 기본 폴더를 고르세요", data["save_dir"])
        if not folder:
            return {"ok": False, "cancelled": True}
        data["save_dir"] = folder
        remember_dir(data, folder)
        store_settings(data)
        return {"ok": True, "save_dir": folder}

    if action == "save":
        # 임시 요약 → 저장 폴더로 옮김. other=True면 폴더 선택 창에서 고른 곳에 (이미 저장된 것은 복사)
        path = Path(msg.get("path", ""))
        if not is_ours(path):
            return {"ok": False, "error": "요약 파일을 찾지 못했습니다."}
        data = load_settings()
        if msg.get("other"):
            folder = choose_folder("이 요약을 저장할 폴더를 고르세요", data["save_dir"])
            if not folder:
                return {"ok": False, "cancelled": True}
        else:
            if is_saved(path):
                return reply_for(path, True)
            folder = data["save_dir"]
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / path.name
        if dest != path:
            if is_saved(path):
                shutil.copy2(path, dest)  # 이미 저장된 요약을 다른 곳에 한 부 더
            else:
                shutil.move(str(path), str(dest))
        remember_dir(data, folder)
        store_settings(data)
        return reply_for(dest, True)

    if action == "chat":
        path = Path(msg.get("path", ""))
        if not is_ours(path):
            return {"ok": False, "error": "요약 파일을 찾지 못했습니다. 먼저 요약해 주세요."}
        question = (msg.get("question") or "").strip()
        if not question:
            return {"ok": False, "error": "질문이 비어 있습니다."}
        try:
            answer = summarize.chat_answer(path.read_text(encoding="utf-8"), msg.get("history") or [], question)
        except SystemExit as e:
            return {"ok": False, "error": str(e.code or "알 수 없는 오류")}
        return {"ok": True, "answer": answer}

    if action == "summarize":
        url = msg.get("url", "")
        vid = summarize.video_id_from(url)
        if not vid:
            return {"ok": False, "error": "유튜브 영상 주소가 아닙니다."}
        path = None if msg.get("force") else find_existing(vid)
        if path:
            return reply_for(path, True)
        if msg.get("cached_only"):
            return {"ok": True, "found": False}  # 요약해 둔 것이 없음 (새로 요약하지 않음)
        clean_drafts()
        try:
            # 새 요약은 임시 폴더에. 패널에서 '저장'을 눌러야 summaries로 옮겨짐
            path = summarize.do_youtube(url, out_dir=summarize.DRAFT_DIR)
        except SystemExit as e:  # summarize.py는 오류 때 sys.exit("메시지")를 씀
            return {"ok": False, "error": str(e.code or "알 수 없는 오류")}
        return reply_for(path, False)

    return {"ok": False, "error": f"모르는 요청: {action}"}


def main():
    msg = read_message()
    if msg is None:
        return
    try:
        reply = handle(msg)
    except Exception as e:  # 어떤 오류든 크롬 쪽에 알려 줌
        reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    send_message(reply)


if __name__ == "__main__":
    main()
