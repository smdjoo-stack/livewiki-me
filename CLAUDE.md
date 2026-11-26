# 나만의 라이브위키 (개인용 유튜브/PDF 요약기)

## 배경
- 라이브위키(livewiki.com, 유튜브·PDF AI 요약 서비스)가 서비스를 종료해서 개인용으로 같은 기능을 직접 만드는 프로젝트.
- 사용자는 개발자가 아님. 설명은 한국어로, 쉽게. 명령어는 복사해서 바로 실행할 수 있게 제시.
- 혼자 쓰는 용도. 로그인·결제·서버 배포는 필요 없음.

## 현재 상태
- `summarize.py` 한 파일로 동작 (Python 3).
  - 유튜브 링크 → `youtube-transcript-api`로 자막(ko → en → 아무거나) → 30초 단위로 묶음 → Claude API 요약
  - PDF → PyMuPDF로 페이지별 텍스트 추출 → Claude API 요약
  - 결과: `summaries/날짜 제목.md` — 유튜브: 핵심 요약 3가지 / 아티클 요약 / 타임라인 요약 / 전체 스크립트(원본 자막, AI 가공 없음). PDF: 핵심 3가지 / 아티클 / 구성별 요약
  - 타임라인의 `[mm:ss]`는 `https://youtu.be/ID?t=초` 링크로 자동 변환
  - 12만 자 넘는 대본/문서는 나눠서 요약 후 합침
  - 요약 방식: API 키(환경변수 `ANTHROPIC_API_KEY` 또는 `api_key.txt`)가 있으면 API, **없으면 `claude -p`(Claude Code)를 호출해 사용자의 유료 구독으로 처리** ← 사용자는 구독 사용을 원함
  - 모델: 파일 상단 `MODEL` (기본 `claude-sonnet-5-5`, 저렴하게는 `claude-haiku-5-5`)
- 2026-11-26: 실제 유튜브 영상(LBSXz7L-X8I, 6분)으로 구독 방식 끝까지 성공(약 25초). PDF 실제 테스트는 아직.

## 설치 / 실행
시스템 Python은 pip 설치를 막아서(PEP 668) 프로젝트 안 `.venv` 사용.
```
python3 -m venv .venv
.venv/bin/pip install youtube-transcript-api anthropic pymupdf
.venv/bin/python summarize.py "유튜브링크 또는 PDF경로"
```

## 크롬 확장 (2026-11-26 추가)
- `chrome_extension/` (MV3): 유튜브 영상 제목 아래 "✨ 요약" 버튼 → 오른쪽 옆 패널에 결과 표시. 시간 링크 누르면 보던 영상이 그 장면으로 이동. 이미 요약한 영상은 `summaries`에서 바로 불러옴(다시 요약 버튼 있음).
- 저장 방식(크롬): 새 요약은 `.drafts/`(임시, 14일 지나면 자동 삭제)에 두고 패널에 먼저 보여 줌 → 사용자가 💾 저장을 눌러야 `summaries/`로 이동(호스트 action `save`). 같은 영상을 다시 열면 두 폴더 중 최신 것을 보여 줌. 터미널에서 `summarize.py` 직접 실행은 바로 `summaries/`에 저장.
- 저장 위치: `settings.json`의 `save_dir`(기본 `summaries/`). 패널 💾 저장 ▾ 메뉴에서 '다른 곳에 저장…'(1회), '기본 폴더 바꾸기…'(osascript `choose folder` 창). 저장한 적 있는 폴더는 `known_dirs`에 기억해서 같은 영상 다시 열 때 함께 찾음.
- 패널은 현재 탭의 영상을 따라감(영상 바뀌면 저장/임시 요약 있으면 표시, 없으면 '요약하기' 버튼). 요약 중 다른 영상 요청은 대기 후 이어서 처리.
- 패널 탭: 핵심/아티클/타임라인/스크립트(자동 스크롤) + 💬 AI 채팅. 섹션별 복사(일반 텍스트).
- AI 채팅: 호스트 action `chat` → `summarize.chat_answer(요약 .md 전체, 최근 대화 10개, 질문)` → `claude -p`. 답의 [mm:ss]는 영상 링크로. 대화는 패널 localStorage(`lw-chat-영상ID`)에 저장. 질문 1개에 10초 안팎.
- 아티클 형식은 라이브위키 스타일(흐름 순 명사형 소제목, 4~5분당 1개, 소제목마다 한 문단, 굵게 강조, 수치·인명 보존).
- 연결: 크롬 네이티브 메시징. 호스트 이름 `com.livewiki.me`, `~/Library/Application Support/livewiki/run_host.sh`(문서 폴더 밖, macOS 권한 문제 회피; 로그 `~/Library/Logs/livewiki_host.log`) → `native_host/livewiki_host.py` → `summarize.do_youtube`. 로그는 `native_host/host.log`.
- 확장 ID 고정: `objnibninibbakahlbohjbeennapdnnh` (manifest의 `key`, 원본 키는 `native_host/extension_key.pem`).
- 설치(본인 Mac): 호스트 manifest는 `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.livewiki.me.json` → `~/Library/Application Support/livewiki/run_host.sh`(수동 생성, 프로젝트 경로 고정). 예전 install_chrome.sh는 삭제함(문서 폴더 경로로 되돌려 고장 냄). 다른 Mac은 packaging/install.sh 사용.
- 크롬에서 실행되면 keychain 로그인을 못 읽어서 `claude_token.txt`(`claude setup-token`으로 받은 구독 토큰, 108자 한 줄)를 `CLAUDE_CODE_OAUTH_TOKEN`으로 넘김. 비밀 파일.

## 테스터 배포 (2026-11-26)
- `./make_package.sh` → `dist/LiveWikiMe-테스트판-날짜.zip` (개인 파일·토큰 들어가면 중단). 원본: `packaging/`(install.sh·uninstall.sh·.command·설치 안내.html).
- 테스터 설치 위치: `~/LiveWikiMe` (문서·다운로드 폴더 권한 문제 회피). install.sh 재실행 = 업데이트(요약·설정·토큰 유지). Chrome/Brave/Edge 연결 등록.
- 테스터 연결: 패널 ⚙️ 설정에서 구독 토큰(claude setup-token, Claude Code 필요) 또는 API 키(api_key.txt, 우선 적용) 붙여넣기 → 연결 시험. 호스트 action `status`/`set_credential`/`test`.
- 확인: 가짜 홈 폴더에서 zip→설치→토큰→요약→저장까지 통과, Python 3.9(Mac 기본)에서 패키지·자막 OK. 실제 API 키로는 미시험(키 없음).
- 사용자 본인 Mac은 기존 방식(프로젝트 폴더 + `~/Library/Application Support/livewiki/run_host.sh`) 그대로.

## 다음에 해볼 만한 것 (사용자가 원할 때)
1. 실제 PDF 1개로 동작 확인
2. 자막 없는 영상: yt-dlp로 음성 받아 Whisper로 받아쓰기 (유튜브 약관 주의)
3. 크롬 확장 개선: PDF도 패널에서 요약, 요약 진행 상황 표시
4. summaries 폴더 요약들 검색 기능
