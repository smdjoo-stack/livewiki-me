# ✨ 나만의 라이브위키

유튜브 영상과 뉴스·블로그 글을 Claude로 요약해서 크롬 옆 패널에 보여 주는 개인용 도구입니다. (Mac / Windows · 테스트판)
서비스를 종료한 라이브위키(livewiki.com)의 기능을 개인용으로 다시 만든 프로젝트입니다.

## 기능
- 유튜브 영상 아래 **✨ 요약** 버튼 → 오른쪽 패널에 결과 표시
  - 핵심 요약 3가지 · 아티클 요약(기사형) · 타임라인 요약 · 전체 스크립트
- 시간을 누르면 영상이 그 장면으로 이동, 스크립트 자동 스크롤
- 💬 AI 채팅: 영상 내용에 대해 질문
- 섹션별 복사, 💾 저장(원하는 폴더에 마크다운 .md로)
- 뉴스·블로그 글 요약(네이버 블로그 포함): 툴바 아이콘 → '이 글 요약하기' 또는 오른쪽 클릭 메뉴
- PDF 요약(터미널에서 `summarize.py`로)

## 설치 (테스터용)
1. [Releases](../../releases)에서 `LiveWikiMe-v버전.zip`을 내려받아 풉니다. (Mac·Windows 공용)
2. 폴더 안의 **INSTALL-GUIDE.html**을 열어 순서대로 따라 합니다.
   - Mac: 터미널에서 `bash ~/Downloads/LiveWikiMe/install.sh`
   - Windows: 압축을 모두 푼 뒤 `install.bat` 더블클릭
   - 크롬(또는 엣지) 확장 페이지 → 개발자 모드 → 압축해제된 확장 로드 → `LiveWikiMe/chrome_extension`
   - 패널 ⚙️ 설정에서 **Claude 구독 토큰**(`claude setup-token`) 또는 **API 키** 입력

## 구조
| 경로 | 설명 |
|---|---|
| `summarize.py` | 요약 엔진. 유튜브 자막(youtube-transcript-api) / PDF(PyMuPDF) → Claude. API 키가 있으면 API, 없으면 Claude Code(`claude -p`) |
| `native_host/` | 크롬 ↔ 요약 엔진 연결 (Native Messaging 호스트) |
| `chrome_extension/` | 크롬 확장 (Manifest V3, 옆 패널). `lib/`: 웹 글 본문 추출(Mozilla Readability, Apache-2.0) |
| `packaging/` | 테스터용 설치·삭제 (Mac: `install.sh`, Windows: `install.bat` + `install_win.py`), 안내서 |
| `make_package.sh` | 테스터용 zip 만들기 → `dist/` |

## 개발자 메모
```bash
python3 -m venv .venv
.venv/bin/pip install youtube-transcript-api anthropic pymupdf
.venv/bin/python summarize.py "유튜브 링크 또는 PDF 경로"   # 터미널에서 바로 요약
./make_package.sh                                         # 테스터용 zip
```
토큰·API 키·설정·요약 결과는 `.gitignore`로 저장소에 올라가지 않습니다.

## 알려 드립니다
- 개인이 만든 **비공식 도구**입니다. 서비스를 종료한 라이브위키(livewiki.com)와는 관계가 없습니다.
- 요약할 때 유튜브 자막이나 웹 글 본문이 **Anthropic(Claude)**으로 전송됩니다. 사용자의 Claude 구독 또는 API 키를 쓰며, 개발자에게는 아무 데이터도 전송되지 않습니다. 요약 결과·토큰·설정은 사용자의 컴퓨터(`LiveWikiMe` 폴더)에만 저장됩니다.
- AI 요약은 틀릴 수 있습니다. 중요한 내용은 원문을 확인해 주세요.
- 유튜브 영상과 웹 글의 저작권은 각 원작자에게 있습니다. 요약·원문 저장은 개인 학습·보관 용도로만 사용해 주세요.
- 테스트판입니다. 문제나 제안은 [Issues](../../issues)에 남겨 주세요.
