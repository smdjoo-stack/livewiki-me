#!/usr/bin/env python3
"""
나만의 라이브위키 — 유튜브 영상 / PDF 요약기 (개인용)

사용법
  python summarize.py https://www.youtube.com/watch?v=XXXX
  python summarize.py 문서.pdf
  python summarize.py            ← 실행 후 링크나 파일 경로를 붙여넣어도 됩니다

결과는 이 파일 옆 'summaries' 폴더에 마크다운(.md)으로 저장됩니다.
API 키(환경변수 ANTHROPIC_API_KEY 또는 api_key.txt)가 있으면 API로, 없으면
Claude Code(claude 명령)를 통해 유료 구독으로 요약합니다.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────
MODEL = "claude-sonnet-5-5"      # 더 저렴하게 쓰려면 "claude-haiku-5-5"
MAX_CHARS_PER_CHUNK = 120_000    # 이보다 긴 대본/문서는 나눠서 요약
LINE_SECONDS = 30                # 자막을 몇 초 단위로 묶을지
BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "summaries"
DRAFT_DIR = BASE_DIR / ".drafts"   # 크롬 확장: 저장 버튼 누르기 전 임시 보관


# ── 공통 ──────────────────────────────────────────────
def load_api_key():
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    key_file = BASE_DIR / "api_key.txt"
    if not key and key_file.exists():
        key = key_file.read_text(encoding="utf-8").strip()
    return key


def ask_claude_subscription(prompt):
    """API 키가 없으면 Claude Code(claude 명령)로 요약 → 유료 구독(Pro/Max) 사용량으로 처리"""
    import os
    import shutil
    import subprocess
    exe = shutil.which("claude")
    if not exe:  # 크롬에서 실행되면 PATH가 짧을 수 있어 기본 설치 위치도 확인
        for cand in (Path.home() / ".local" / "bin" / "claude",
                     Path.home() / ".local" / "bin" / "claude.exe"):
            if cand.exists():
                exe = str(cand)
                break
    if not exe:
        sys.exit("❌ 요약에 쓸 Claude 연결 정보가 없습니다.\n"
                 "크롬 패널의 ⚙️ 설정에서 'API 키'를 넣거나, Claude Code를 설치한 뒤 '구독 토큰'을 넣어 주세요.")
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    # 크롬 확장처럼 터미널 밖에서 실행될 때도 로그인되도록, 'claude setup-token'으로 받은
    # 구독 토큰을 claude_token.txt에 넣어 두면 그걸 씀
    token_file = BASE_DIR / "claude_token.txt"
    if token_file.exists():
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token_file.read_text(encoding="utf-8").strip()
    r = subprocess.run(
        [exe, "-p", "--model", MODEL, "--tools", "", "--output-format", "text"],
        input=prompt, capture_output=True, text=True, env=env, timeout=900,
        encoding="utf-8", errors="replace",  # 한국어 윈도우(CP949)에서도 한글이 깨지지 않게
        cwd=OUT_DIR.parent,
    )
    if r.returncode != 0 or not r.stdout.strip():
        detail = (r.stderr or r.stdout).strip()[:500]
        if "log" in detail.lower() and ("login" in detail.lower() or "logged" in detail.lower()):
            sys.exit("❌ Claude Code에 로그인되어 있지 않거나 로그인이 만료되었습니다.\n"
                     "터미널(윈도우는 PowerShell)에서 claude 를 한 번 실행해 로그인한 뒤 다시 시도해 주세요.\n"
                     "그래도 안 되면 ⚙️ 설정에서 '구독 토큰'이나 'API 키'를 넣어 주세요.\n\n" + detail)
        if "git-bash" in detail.lower() or "git bash" in detail.lower():
            sys.exit("❌ 윈도우에서 Claude Code를 쓰려면 'Git for Windows'가 필요합니다.\n"
                     "https://git-scm.com/download/win 에서 설치한 뒤 다시 시도하거나, ⚙️ 설정에서 API 키를 넣어 주세요.\n\n" + detail)
        if "401" in detail or "invalid" in detail.lower():
            sys.exit("❌ 구독 토큰이 올바르지 않거나 만료되었습니다. ⚙️ 설정에서 새 토큰을 넣어 주세요.\n\n" + detail)
        sys.exit(f"❌ Claude Code 호출 실패: {detail}")
    return r.stdout.strip()


def ask_claude(prompt, max_tokens=16000):
    key = load_api_key()
    if not key:
        return ask_claude_subscription(prompt)
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    try:
        return _ask_api(client, prompt, max_tokens)
    except anthropic.AuthenticationError:
        sys.exit("❌ API 키가 올바르지 않습니다. ⚙️ 설정에서 API 키를 다시 확인해 주세요.")
    except anthropic.APIError as e:
        sys.exit(f"❌ Claude API 오류: {e}")


def _ask_api(client, prompt, max_tokens):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def split_chunks(text, limit=None):
    """줄 단위로 끊어서 limit 글자 이하 덩어리로 나눔"""
    limit = limit or MAX_CHARS_PER_CHUNK
    chunks, cur, size = [], [], 0
    for line in text.splitlines():
        if size + len(line) > limit and cur:
            chunks.append("\n".join(cur))
            cur, size = [], 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", name).strip()
    # 윈도우는 파일 이름 끝의 점·공백을 허용하지 않음
    return re.sub(r"\s+", " ", name)[:80].rstrip(". ") or "summary"


def save(title, body, source, out_dir=None, info=""):
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    path = out_dir / f"{stamp} {safe_filename(title)}.md"
    extra = f"> {info}  \n" if info else ""
    header = f"# {title}\n\n> 출처: {source}  \n{extra}> 요약일: {stamp}\n\n"
    path.write_text(header + body + "\n", encoding="utf-8")
    return path


def summarize_long(text, kind_prompt, part_prompt, merge_prompt):
    """짧으면 한 번에, 길면 나눠서 구간 요약 → 전체 요약 합치기"""
    chunks = split_chunks(text)
    if len(chunks) == 1:
        return ask_claude(kind_prompt.format(body=text))

    print(f"   내용이 길어서 {len(chunks)}부분으로 나눠 요약합니다…")
    parts = []
    for i, ch in enumerate(chunks, 1):
        print(f"   ({i}/{len(chunks)}) 요약 중…")
        parts.append(ask_claude(part_prompt.format(body=ch)))
    timeline = "\n\n".join(parts)
    overview = ask_claude(merge_prompt.format(body=timeline), max_tokens=12000)
    return overview + "\n\n" + timeline


# ── 유튜브 ─────────────────────────────────────────────
def video_id_from(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def video_title(vid):
    try:
        q = urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"})
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?{q}", timeout=10) as r:
            return json.load(r).get("title", vid)
    except Exception:
        return vid


def fmt_time(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fetch_transcript(vid):
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(vid, languages=["ko", "en"])
    except Exception:
        # 한국어/영어가 없으면 있는 자막 아무거나
        transcripts = list(api.list(vid))
        if not transcripts:
            raise
        fetched = transcripts[0].fetch()
    return [(s.start, s.text) for s in fetched]


def group_lines(snippets, every=LINE_SECONDS):
    """짧은 자막 조각을 30초 단위 한 줄로 묶음 → 토큰 절약"""
    lines, cur_start, buf = [], None, []
    for start, text in snippets:
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        if cur_start is None:
            cur_start = start
        if start - cur_start >= every and buf:
            lines.append(f"[{fmt_time(cur_start)}] {' '.join(buf)}")
            cur_start, buf = start, []
        buf.append(text)
    if buf:
        lines.append(f"[{fmt_time(cur_start)}] {' '.join(buf)}")
    return "\n".join(lines)


def link_timestamps(md, vid):
    """[12:34] → 클릭하면 그 시간부터 재생되는 링크"""
    def repl(m):
        parts = [int(p) for p in m.group(1).split(":")]
        sec = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
        return f"[{m.group(1)}](https://youtu.be/{vid}?t={sec})"
    return re.sub(r"\[(\d{1,2}(?::\d{2}){1,2})\](?!\()", repl, md)


HEAD_FORMAT = """## 핵심 요약
1. **(핵심 제목)** — (1~2문장 설명)
2. **(핵심 제목)** — (1~2문장 설명)
3. **(핵심 제목)** — (1~2문장 설명)
(딱 3가지. 가장 중요한 것만)

## 아티클 요약
(아래 규칙대로 쓰는 해설 기사형 요약)
- 구성: 소제목(###)을 내용 순서대로 이어 붙입니다. 소제목 밖의 도입·마무리 문단은 따로 쓰지 않습니다.
  · 원본이 스스로 항목을 나눴다면("13가지 순간", "5단계", "3가지 이유" 등) 그 구조를 그대로 따릅니다:
    첫 섹션은 소개(무엇을 왜 다루는지) → 항목마다 섹션 1개(절대 둘 이상을 합치지 않음) → 마지막 섹션은 정리·메시지.
  · 그런 구조가 없으면 흐름이 바뀌는 지점마다 나누고, 첫 소제목은 "강연 소개 및 ○○의 배경"처럼 시작합니다.
    이때 개수는 분량에 비례(영상이면 약 4~5분당 1개, 최소 3개·최대 15개).
- 소제목: "대상: 의미" 형식으로, 제목만 훑어도 전체 흐름이 보이게 씁니다.
  · 항목형이면 번호와 연도/핵심어를 붙입니다. 예) "1. AD 70년 예루살렘 성전 파괴: 유대교와 기독교의 분리"
  · 일반형 예) "종교개혁과 설교: 설교의 회복 운동", "성도와 목회자: 설교 인식의 차이"
- 본문: 소제목마다 한 문단, 3문장 안팎(많아야 4문장). 불릿 없이
  **배경(왜 그런 일이 생겼나) → 핵심(무슨 일·주장인가) → 의미(무엇이 달라졌나, 왜 중요한가)** 순서로 씁니다.
- 말투: 합니다체. 내용을 기사처럼 바로 서술합니다("~했습니다", "~입니다").
  화자(강사·저자)는 소개 섹션에서 한 번만 밝히고, 그 뒤에는 "~라고 합니다/~고 설명합니다/~고 평가합니다" 같은
  전달 표현을 쓰지 않습니다. 화자 개인의 평가·의견일 때만 "○○은 ~라고 봅니다"처럼 밝힙니다.
- 강조: 문단마다 2~3곳을 **굵게**. 단어보다는 그 섹션의 의미·결론을 담은 구절을 굵게 합니다.
- 구체성: 원본의 수치·통계(예: 38.9%), 연도, 인명, 책·이론·용어('위대한 교환' 등), 인상적인 예시를 살립니다.
  낯선 용어는 괄호로 짧게 풀어 줍니다(예: 사어(死語)).
- 자동 자막은 단어를 잘못 받아쓰는 경우가 있습니다. 문맥상 분명한 오인식은 바로잡아 씁니다
  (예: 화자가 '새로 만든 말'이라고 설명하는데 자막이 흔한 단어로 적혀 있으면 화자가 뜻한 말로)."""

YT_FULL = """다음은 유튜브 영상 「{title}」의 자막입니다. 각 줄 앞의 [시간]은 영상 속 위치입니다.
자막이 외국어여도 결과는 한국어로, 아래 마크다운 형식 그대로 정리하세요. 다른 말은 덧붙이지 마세요.

""" + HEAD_FORMAT + """

## 타임라인 요약
(주제가 바뀌는 지점마다 구간을 나눠서, 각 구간을 아래 형식으로)
### [시간] 구간 제목
- 2~3줄 요약

규칙: 타임라인의 [시간]은 자막에 있는 시간을 그대로 쓰고, 자막에 없는 내용은 지어내지 마세요.

<자막>
{{body}}
</자막>"""

YT_PART = """다음은 유튜브 영상 「{title}」 자막의 일부입니다. 이 부분만 한국어 타임라인으로 정리하세요.
형식(제목 없이 바로 시작):
### [시간] 구간 제목
- 2~3줄 요약
[시간]은 자막의 시간을 그대로 쓰고, 없는 내용은 지어내지 마세요.

<자막>
{{body}}
</자막>"""

MERGE = """다음은 「{title}」의 구간별 요약입니다. 이것을 바탕으로 아래 형식의 한국어 마크다운만 쓰세요. 다른 말은 덧붙이지 마세요.

""" + HEAD_FORMAT + """

그리고 마지막 줄에 "## 타임라인 요약"이라고만 쓰세요.

<구간 요약>
{{body}}
</구간 요약>"""


def full_script(transcript, vid):
    """원본 자막 전체(AI 가공 없음). 시간은 클릭하면 그 장면으로 이동"""
    lines = link_timestamps(transcript, vid).splitlines()
    return "## 전체 스크립트\n\n" + "\n\n".join(lines)


def do_youtube(url, out_dir=None):
    vid = video_id_from(url)
    if not vid:
        sys.exit("❌ 유튜브 링크에서 영상 ID를 찾지 못했습니다.")
    title = video_title(vid)
    print(f"🎬 {title}")
    print("   자막 가져오는 중…")
    try:
        transcript = group_lines(fetch_transcript(vid))
    except Exception as e:
        sys.exit(f"❌ 자막을 가져오지 못했습니다(자막이 없는 영상일 수 있어요): {e}")
    print("   AI 요약 중…")
    t = title.replace("{", "(").replace("}", ")")
    body = summarize_long(transcript, YT_FULL.format(title=t), YT_PART.format(title=t), MERGE.format(title=t))
    body = link_timestamps(body, vid) + "\n\n" + full_script(transcript, vid)
    return save(title, body, f"https://www.youtube.com/watch?v={vid}", out_dir)


# ── 웹 글 (뉴스·블로그) ─────────────────────────────────
WEB_FULL = """다음은 웹 글 「{title}」({info})의 본문입니다.
결과는 한국어로, 아래 마크다운 형식 그대로 정리하세요. 다른 말은 덧붙이지 마세요.

""" + HEAD_FORMAT + """
  (웹 글 분량 기준: 약 1,500자당 소제목 1개. 2,000자 미만의 짧은 글은 소제목 2개, 많아야 15개.
   화자 대신 글쓴이·언론사를 소개 섹션에서 한 번만 밝힙니다.)

## 구성별 요약
(글의 흐름에 따라 구간을 나눠서, 각 구간을 아래 형식으로)
### 구간 제목
- 2~3줄 요약

규칙: 본문에 없는 내용은 지어내지 마세요. 본문에 섞여 들어온 광고·메뉴·사진 설명·구독 안내 같은 군더더기는 무시하세요.

<본문>
{{body}}
</본문>"""

WEB_PART = """다음은 웹 글 「{title}」 본문의 일부입니다. 이 부분만 한국어로 구성별 요약을 쓰세요.
형식(제목 없이 바로 시작):
### 구간 제목
- 2~3줄 요약

<본문>
{{body}}
</본문>"""


def do_page(url, title, text, info="", out_dir=None):
    """브라우저에서 뽑아 온 웹 글 본문을 요약. url은 정리된(추적 꼬리 뗀) 주소"""
    title = (title or url).strip()
    print(f"📰 {title}")
    if len(text.strip()) < 200:
        sys.exit("❌ 본문을 거의 찾지 못했습니다. 로그인이 필요한 글이거나, 글 대부분이 이미지인 페이지일 수 있어요.")
    print("   AI 요약 중…")
    t = title.replace("{", "(").replace("}", ")")
    i = (info or "출처 정보 없음").replace("{", "(").replace("}", ")")
    merge = MERGE.format(title=t).replace('"## 타임라인 요약"', '"## 구성별 요약"')
    body = summarize_long(text, WEB_FULL.format(title=t, info=i), WEB_PART.format(title=t), merge)
    body += "\n\n## 원문\n\n" + text.strip()
    return save(title, body, url, out_dir, info)


# ── AI 채팅 (요약 파일을 바탕으로 질문에 답하기) ─────────────
CHAT_RULES = """당신은 아래 <자료>(영상·문서·웹 글의 요약과 원문/전체 스크립트)를 바탕으로 사용자의 질문에 답하는 도우미입니다.
규칙:
- 한국어 합니다체로, 질문에 바로 답합니다. 필요하면 짧은 목록이나 **굵게**를 씁니다.
- 자료에 있는 내용으로 답하고, 근거가 되는 장면의 시간을 [mm:ss] 형식으로 함께 적습니다(영상인 경우).
- 자료에 없는 내용은 "자료(영상·글)에서는 다루지 않았습니다"라고 먼저 밝힌 뒤, 필요하면 일반 지식임을 표시하고 덧붙입니다.
- 자동 자막의 받아쓰기 오류로 보이는 단어는 문맥에 맞게 바로잡아 씁니다."""


def chat_answer(doc, history, question):
    """doc: 요약 .md 전체, history: [{"role": "user"|"assistant", "content": "..."}]"""
    talk = []
    for h in history[-10:]:
        who = "사용자" if h.get("role") == "user" else "도우미"
        talk.append(f"{who}: {h.get('content', '').strip()}")
    parts = [CHAT_RULES, "<자료>\n" + doc + "\n</자료>"]
    if talk:
        parts.append("<지금까지 대화>\n" + "\n\n".join(talk) + "\n</지금까지 대화>")
    parts.append("사용자의 새 질문: " + question.strip() + "\n\n답변만 쓰세요.")
    answer = ask_claude("\n\n".join(parts), max_tokens=3000)
    m = re.search(r"watch\?v=([A-Za-z0-9_-]{11})", doc[:600])
    return link_timestamps(answer, m.group(1)) if m else answer


# ── PDF ───────────────────────────────────────────────
def pdf_text(path):
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            t = re.sub(r"[ \t]+", " ", page.get_text()).strip()
            if t:
                pages.append(f"[p.{i}]\n{t}")
    return "\n\n".join(pages)


PDF_FULL = """다음은 PDF 문서 「{title}」의 내용입니다. [p.숫자]는 페이지 번호입니다.
결과는 한국어로, 아래 마크다운 형식 그대로 정리하세요. 다른 말은 덧붙이지 마세요.

""" + HEAD_FORMAT + """

## 구성별 요약
(내용 흐름에 따라 구간을 나눠서, 각 구간을 아래 형식으로)
### (p.시작–끝) 구간 제목
- 2~3줄 요약

규칙: 문서에 없는 내용은 지어내지 마세요.

<문서>
{{body}}
</문서>"""

PDF_PART = """다음은 PDF 문서 「{title}」의 일부입니다. 이 부분만 한국어로 구성별 요약을 쓰세요.
형식(제목 없이 바로 시작):
### (p.시작–끝) 구간 제목
- 2~3줄 요약

<문서>
{{body}}
</문서>"""


def do_pdf(path):
    path = Path(path.strip().strip('"').strip("'")).expanduser()
    title = path.stem
    print(f"📄 {title}")
    print("   텍스트 추출 중…")
    text = pdf_text(path)
    if len(text) < 50:
        sys.exit("❌ 텍스트를 거의 못 읽었습니다. 스캔한 이미지 PDF일 수 있어요.")
    print("   AI 요약 중…")
    t = title.replace("{", "(").replace("}", ")")
    merge = MERGE.format(title=t).replace('"## 타임라인 요약"', '"## 구성별 요약"')
    body = summarize_long(text, PDF_FULL.format(title=t), PDF_PART.format(title=t), merge)
    return save(title, body, path.name)


# ── 실행 ──────────────────────────────────────────────
def main():
    target = sys.argv[1] if len(sys.argv) > 1 else input("유튜브 링크 또는 PDF 경로: ").strip()
    if not target:
        sys.exit("입력이 없습니다.")
    if target.strip().strip('"').strip("'").lower().endswith(".pdf"):
        out = do_pdf(target)
    else:
        out = do_youtube(target)
    print(f"✅ 저장 완료: {out}")


if __name__ == "__main__":
    main()
