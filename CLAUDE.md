# LG HelloDoctor — 프로젝트 전체 지침

## 프로젝트 개요
시니어(어르신) 대상 음성 의료 AI 서비스.
사용자가 음성으로 증상을 말하면 AI가 의도를 파악하고 병원 정보·의료 정보를 안내한다.

## 아키텍처 요약

```
사용자 음성
    ↓
[A팀] STT (Whisper + Silero VAD)
    ↓
[B팀] 의도 분류 & 다중턴 (Groq LLM)
    ↓
[C팀] RAG + 병원 검색 + 응급 판단 (ChromaDB + Kakao API)
    ↓
[D팀] 답변 생성 (Groq LLM)
    ↓
프론트엔드 (React + Vite)
```

## 구조

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
│   │   ├── hooks/           # useMedicalChat, useVoiceInput, useWakeWord
│   │   └── types/
│   ├── Dockerfile
│   └── nginx.conf
├── RAG/db/                  # ChromaDB PersistentClient 데이터
├── docker-compose.yml
└── .env                     # API 키 (KAKAO_API_KEY, GROQ_API_KEY)
```

## 환경 변수 (.env)
| 변수 | 용도 | 필수 |
|------|------|------|
| `KAKAO_API_KEY` | 병원 위치 검색 (Kakao Map API) | ✅ |
| `GROQ_API_KEY` | LLM 추론 (llama-3.3-70b-versatile) | ✅ |
| `WHISPER_MODEL_PATH` | Whisper 모델 경로 (기본: openai/whisper-small) | 선택 |
| `DB_PATH` | ChromaDB 경로 (기본: /app/RAG/db) | 선택 |

## Docker 실행
```bash
docker compose up --build   # 최초 빌드 포함
docker compose up -d        # 백그라운드 실행
docker compose logs -f backend  # 로그 확인
```

## 세부 지침 파일
- [백엔드 지침](.github/instructions/backend.instructions.md)
- [프론트엔드 지침](.github/instructions/frontend.instructions.md)
- [RAG 지침](.github/instructions/rag.instructions.md)
- [AI 모델 지침](.github/instructions/ai-model.instructions.md)

---

## 컨텍스트 엔지니어링 (Few-shot 예시)

Claude가 이 프로젝트에서 올바르게 동작하도록 하는 예시 패턴입니다.

### 예시 1 — 금지어 필터 수정 요청

**사용자:** `format_response`에서 "치료" 단어가 응답에 포함되고 있어.

**올바른 대응:**
1. `backend/main.py`의 `FORBIDDEN_WORDS` 리스트 확인
2. `format_response()` 함수 내 필터 로직 확인
3. `tests/test_ai_model.py`의 `test_금지어_필터링` 실행
4. 필터가 동작 안 하면 정규식 수정 후 재테스트

**잘못된 대응:** 금지어 리스트에서 "치료"를 삭제한다 → 의료법 위반

---

### 예시 2 — 새 진료과명 보정 추가

**사용자:** "안과가"를 "안과"로 보정하는 항목이 없어.

**올바른 대응:**
```python
# backend/main.py — MEDICAL_CORRECTIONS 딕셔너리에 추가
MEDICAL_CORRECTIONS = {
    ...
    "안과가": "안과",   # 추가
}
```
→ `tests/test_ai_model.py`의 `test_진료과명_보정`에 케이스 추가 후 pytest 실행

---

### 예시 3 — Docker 재빌드 없이 코드 수정 확인

**사용자:** 코드 수정했는데 반영이 안 돼.

**올바른 대응:**
```bash
docker compose restart backend   # 재빌드 없이 컨테이너만 재시작
docker compose logs -f backend   # 로그 확인
```
볼륨 마운트가 없으면 `docker compose up --build -d`로 재빌드 필요

---

### 예시 4 — 응급 감지 실패

**사용자:** "쓰러졌어요"를 입력했는데 emergency가 아닌 symptom_inquiry로 분류돼.

**올바른 대응:**
1. `backend/main.py`의 `classify_intent()` 내 응급 키워드 리스트 확인
2. "쓰러졌어요" 키워드 추가
3. `tests/test_ai_model.py`의 `EMERGENCY_CASES` 리스트에 케이스 추가
4. `test_응급_키워드_100퍼센트_감지` 테스트 실행

---

## 하네스 엔지니어링 (.claude/)

| 파일 | 역할 |
|------|------|
| `.claude/settings.json` | 훅(Hook) — 위험 명령어 차단, 편집 후 알림 |
| `.claude/commands/deploy.md` | `/deploy` — Docker 배포 자동화 |
| `.claude/commands/test.md` | `/test` — 전체 TDD 테스트 실행 |
| `.claude/commands/validate.md` | `/validate` — 통합 검증 체크리스트 |

### 커스텀 슬래시 명령어 사용법
```
/deploy   # Docker 배포 가이드 실행
/test     # pytest 전체 스위트 실행
/validate # 배포 전 통합 검증
```

---

## AI Native Engineering 6단계 구조

```
1단계 — 지침 (Instructions)
   .github/instructions/{backend,frontend,rag,ai-model}.instructions.md

2단계 — 프롬프트 (Prompts)
   .github/prompts/{backend,frontend,rag,ai-model}.prompt.md

3단계 — 에이전트 (Agents)
   .github/agents/{backend,frontend,rag,ai-model,TDD-*}.agent.md

4단계 — 컨텍스트 (Context Engineering)
   docs/PRODUCT.md
   docs/context-packet.md
   CLAUDE.md (이 파일)

5단계 — TDD (Test-Driven Development)
   tests/test_{backend,frontend,rag,ai_model}.py
   tests/test_manager.py

6단계 — 통합 검증 (Integration Validation)
   src/todo/manager.py
   docs/test-report.md
```
