# LG HelloDoctor

> 시니어(어르신) 대상 음성 의료 AI 서비스
> 음성으로 증상을 말하면 AI가 의도를 파악하고 병원 정보·의료 정보를 안내합니다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Infra** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) ![Docker Compose](https://img.shields.io/badge/Docker_Compose-2496ED?style=flat&logo=docker&logoColor=white) |
| **Backend** | ![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![PyTorch](https://img.shields.io/badge/PyTorch_CPU-EE4C2C?style=flat&logo=pytorch&logoColor=white) |
| **AI 모델** | ![Groq](https://img.shields.io/badge/Groq_LLM-F55036?style=flat&logo=groq&logoColor=white) ![Whisper](https://img.shields.io/badge/Whisper_STT-412991?style=flat&logo=openai&logoColor=white) ![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black) |
| **Frontend** | ![React](https://img.shields.io/badge/React_19-61DAFB?style=flat&logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) ![nginx](https://img.shields.io/badge/nginx-009639?style=flat&logo=nginx&logoColor=white) |
| **Database** | ![ChromaDB](https://img.shields.io/badge/ChromaDB_1.5.5-FF6B35?style=flat&logo=databricks&logoColor=white) |
| **External API** | ![Kakao](https://img.shields.io/badge/Kakao_Map_API-FFCD00?style=flat&logo=kakao&logoColor=black) ![gTTS](https://img.shields.io/badge/gTTS-4285F4?style=flat&logo=google&logoColor=white) |
| **UI/Design** | ![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat&logo=figma&logoColor=white) ![html.to.design](https://img.shields.io/badge/html.to.design-9B59B6?style=flat&logo=figma&logoColor=white) ![Claude MCP](https://img.shields.io/badge/Claude_MCP-CC785C?style=flat&logo=anthropic&logoColor=white) |
| **협업** | ![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white) |

---

## 시스템 아키텍처

```
사용자 음성
    ↓
[A팀] STT — Whisper + Silero VAD
         오디오 → 텍스트 변환 / 노인 음성 오인식 보정
    ↓
[B팀] 의도 분류 & 다중턴 — Groq LLM (llama-3.3-70b-versatile)
         증상문의 / 병원검색 / 약정보 / 응급 분류
    ↓
[C팀] RAG + 병원 검색 + 응급 판단 — ChromaDB + Kakao Map API
         의료 지식 검색 / 주변 병원 3곳 안내 / 응급 점수 계산
    ↓
[D팀] 답변 생성 + TTS — Groq LLM + gTTS
         시니어 맞춤 한국어 답변 / 금지어 필터 / 음성 출력
    ↓
프론트엔드 — React 19 + Vite + TypeScript
```

---

## 빠른 시작

### 1. 환경 변수 설정

```bash
# 프로젝트 루트에 .env 파일 생성
KAKAO_API_KEY=your_kakao_api_key
GROQ_API_KEY=your_groq_api_key
```

### 2. Docker로 실행

```bash
# 최초 실행 (이미지 빌드 포함)
docker compose up --build

# 이후 실행
docker compose up -d
```

> 첫 실행 시 Whisper, Silero VAD, ko-sroberta-multitask 모델이 자동 다운로드됩니다 (5~15분 소요).

### 3. 접속

| 서비스 | 주소 |
|--------|------|
| 프론트엔드 | http://localhost:80 |
| 백엔드 API | http://localhost:8000 |
| API 문서 | http://localhost:8000/docs |

---

## API 엔드포인트

### `POST /chat` — 채팅 (핵심 엔드포인트)

```json
// 요청
{
  "text": "무릎이 너무 아파요",
  "session_id": "user-123",
  "lat": 37.5012,
  "lng": 127.0396
}

// 응답
{
  "answer": "어르신, 무릎이 많이 불편하시겠어요. 가까운 정형외과에 가보시는 게 좋겠어요.",
  "intent": "symptom_inquiry",
  "hospitals": [...],
  "is_emergency": false,
  "ready_for_c": true,
  "session_id": "user-123"
}
```

### `POST /api/stt` — 음성 → 텍스트

```bash
curl -X POST http://localhost:8000/api/stt \
  -F "audio=@recording.wav"
```

---

## 프로젝트 구조

```
LGHelloDoctor/
├── backend/
│   ├── main.py              # FastAPI 서버 (A→B→C→D 통합 파이프라인)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # chat.ts, stt.ts
│   │   ├── components/      # chat/, tv/
│   │   └── hooks/           # useMedicalChat, useVoiceInput, useWakeWord
│   ├── Dockerfile
│   └── nginx.conf
├── RAG/db/                  # ChromaDB 벡터 DB 데이터
├── docs/                    # 상세 문서
├── tests/                   # TDD 테스트 스위트
├── .github/                 # AI Native Engineering 지침·프롬프트·에이전트
├── .claude/                 # Claude Code 하네스 설정
├── docker-compose.yml
└── .env                     # API 키 (git 제외)
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [개발 환경](docs/dev-environment.md) | 요구사항, Docker 설정, 의존성 상세, 트러블슈팅 |
| [아키텍처 다이어그램](docs/diagrams.md) | 클래스 다이어그램 5개 + 시퀀스 다이어그램 3개 |
| [프로덕트 정의](docs/PRODUCT.md) | 서비스 목표, 사용자, 핵심 기능 |
| [컨텍스트 패킷](docs/context-packet.md) | AI 파이프라인 흐름 및 알려진 이슈 |
| [테스트 리포트](docs/test-report.md) | TDD 결과 요약 |

---

## AI Native Engineering 6단계 구조

이 프로젝트는 AI Native Engineering 방법론을 적용하여 개발되었습니다.

```
AI Native Engineering
├── 프롬프트 엔지니어링  — LLM에 넣는 프롬프트 자체를 잘 짜는 것
├── 컨텍스트 엔지니어링 — AI가 올바르게 동작하도록 맥락(지침·few-shot·도메인 지식)을 구성하는 것
└── 하네스 엔지니어링   — AI 작업 환경을 자동화·안전장치로 감싸는 것 (훅, 커스텀 명령어)
```

| 단계 | 역할 | 엔지니어링 분류 | 위치 |
|------|------|----------------|------|
| 1. 지침 (Instructions) | AI 모델별 동작 규칙 정의 | 컨텍스트 엔지니어링 | `.github/instructions/` |
| 2. 프롬프트 (Prompts) | 작업별 프롬프트 템플릿 | 프롬프트 엔지니어링 | `.github/prompts/` |
| 3. 에이전트 (Agents) | 자동화 에이전트 설정 | 프롬프트 엔지니어링 | `.github/agents/` |
| 4. 컨텍스트 (Context) | Few-shot 예시 및 도메인 지식 | 컨텍스트 엔지니어링 | `CLAUDE.md`, `docs/` |
| 5. TDD | 품질 기준 코드로 관리 | 하네스 엔지니어링 | `tests/` |
| 6. 통합 검증 | 배포 전 전체 파이프라인 검증 | 하네스 엔지니어링 | `src/todo/manager.py` |

> `.claude/settings.json` (훅·커스텀 슬래시 명령어)도 하네스 엔지니어링의 일부입니다.

---

## 프론트엔드 디자인 워크플로우

Claude Code(MCP) + Figma MCP + html.to.design 플러그인을 활용한 디자인-개발 통합 워크플로우를 적용했습니다.

```
1. React + TypeScript로 컴포넌트 구현
        ↓
2. Claude Code에서 Figma MCP 연결
        ↓
3. html.to.design 플러그인으로 구현된 HTML/CSS를 Figma로 자동 변환
        ↓
4. Figma에서 UI 디자인 문서화 완성
```

| 도구 | 역할 |
|------|------|
| Claude Code (MCP) | Figma와 코드 환경을 연결하는 브릿지 |
| Figma MCP | Claude가 Figma 파일을 읽고 조작 |
| html.to.design | 구현된 HTML/CSS → Figma 컴포넌트 자동 변환 |

---

## 테스트 실행

```bash
# 전체 테스트
python tests/test_manager.py

# 개별 테스트
python -m pytest tests/test_ai_model.py -v   # AI 모델 (STT, 금지어, 응답 품질)
python -m pytest tests/test_backend.py -v    # 백엔드 API
python -m pytest tests/test_rag.py -v        # RAG 파이프라인
python -m pytest tests/test_frontend.py -v  # 프론트엔드 계약
```

---

## 주의사항

- `chromadb==1.5.5` 버전 고정 — 임의 변경 시 DB 스키마 오류 발생
- `temperature=0` 고정 — 의도 분류 일관성 유지
- `FORBIDDEN_WORDS` 항목 삭제 금지 — 의료법 준수
- `.env` 파일 절대 커밋 금지
