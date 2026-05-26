# LG HelloDoctor — Release Notes

> **SDLC 단계 7 산출물** — 릴리즈 단위로 사용자/운영자에게 *무엇이 바뀌었는지* 와 *어떻게 배포되었는지* 를 공식 기록한다.

---

## v1.0.0 — *Foundation Release* (2026-05-22)

### Highlights

- 🎙️ **음성 의료 안내 AI 에이전트** 첫 정식 출시 — 시니어가 자연어 음성만으로 의료 정보·진료과·인근 병원을 받을 수 있는 End-to-End 파이프라인 완성
- 🧠 **Anthropic 5가지 에이전트 워크플로 패턴** 적용 (Prompt Chaining · Routing · Parallelization · Orchestrator-Worker · Evaluator-Optimizer)
- 🚨 **응급 감지율 100%** — 룰 기반 안전장치 + LLM 분류 wrap 구조로 인명 직결 시나리오 보장
- 🛡️ **HITL 3-Tier 거버넌스** — 의사·약사·노년학·법률 자문단 + 개발팀 + 시니어 베타 사용자 구조 정착

### 새로운 기능

| 기능 | 설명 | 관련 코드 |
|---|---|---|
| Whisper STT 한국어 시니어 특화 | `whisper-small-ko` + LoRA 파인튜닝, 의료 용어 50+ 보정 사전 | `backend/main.py::stt_pipeline` |
| LLaMA 의도 분류 + 응급 룰 | 4 라벨 분류 정확도 94.9% + 응급 키워드 9개 즉시 강제 | `backend/main.py::classify_intent` |
| Hybrid RAG v2 | Vector + BM25 + RRF + ko-reranker → recall@3 0.85 | `backend/main.py::full_rag_pipeline` |
| 병렬 도구 호출 | RAG + Kakao 병원 + Emergency 동시 실행 (~1.6× 단축) | `backend/agent_patterns.py::run_c_team_parallel` |
| 답변 품질 평가-재생성 | 한국어 비율·길이·금지어 검증 실패 시 최대 2회 재생성 | `backend/agent_patterns.py::generate_with_evaluator` |
| Kakao Local API 병원 검색 | 3km 반경 진료과별 병원 상위 3개 | `backend/main.py::search_kakao` |
| 다중턴 followup | 24 부위 인식 → 2턴 컨텍스트 누적 | `backend/main.py::chat_with_followup` |

### 성능 지표 (단계 4·6 검증)

| 영역 | 지표 | 개선 전 | v1.0 |
|---|---|---|---|
| STT | CER | 3.4% | **2.9%** |
| STT | WER | 14.2% | **12.9%** |
| LLM | 의도 분류 정확도 | 57.0% | **94.9%** |
| LLM | 응급 감지율 | 59.5% | **90.0%** (룰 보강 후 100%) |
| RAG | Top-3 정확도 | 39.7% | **62.1%** |
| 통합 검증 | `/validate` | - | **7 / 7 통과** |
| E2E | 4 시나리오 | - | **4 / 4 통과** |
| 단위 테스트 | `test_agent_patterns.py` | - | **14 / 14 통과** |
| 스모크 | 핵심 경로 | - | **9 / 9 통과** |

### 변경된 모듈

```
backend/
  main.py              — A→B→C→D 파이프라인 + Orchestrator (full_pipeline)
  agent_patterns.py    — [신규] 5패턴 캡슐화 모듈
  requirements.txt     — chromadb 1.5.5 · rank_bm25 · sentence-transformers · langchain-groq · langsmith
frontend/
  src/components/      — ChatScreen · MessageList · VoiceInputPanel
  src/hooks/           — useMedicalChat · useVoiceInput · useWakeWord
docs/                  — 26 파일 (지침·아키텍처·온톨로지·리포트)
tests/                 — 6 파일 (단위 5 + E2E 1)
.github/               — instructions·agents·prompts·PR 템플릿
.claude/               — settings·commands·scripts·skills
CLAUDE.md              — 프로젝트 헌법
docker-compose.yml     — backend + frontend (Ollama host)
```

### 배포 환경

| 구성 | 값 |
|---|---|
| 배포 방식 | Docker Compose 단일 호스트 |
| Backend | python:3.11-slim · uvicorn · port 8000 |
| Frontend | nginx:alpine · port 80 |
| LLM 서빙 | Ollama 외부 (host.docker.internal:11434) |
| 모델 | hellodoctor-intent / hellodoctor-answer (GGUF Q4_K_M) |
| 벡터 DB | ChromaDB PersistentClient (132 문서) |
| 외부 API | Kakao Local API · KDCA 국가건강정보포털 |
| 트레이싱 | LangSmith @traceable (B팀·D팀 LLM 호출) |

### 배포 로그

```
2026-05-22 13:23:00  docker compose up -d --build
2026-05-22 13:23:43  backend container Up · ChromaDB 132 docs loaded
2026-05-22 13:23:43  frontend container Up · nginx :80
2026-05-22 13:23:55  smoke test 9/9 PASS
2026-05-22 13:25:30  E2E test 4/4 PASS
2026-05-22 13:26:00  /validate 7/7 PASS
2026-05-22 13:26:15  RELEASE APPROVED · v1.0.0 tagged
```

### Breaking Changes

없음 (최초 릴리즈)

### 알려진 제약사항

- LoRA 파인튜닝 어댑터 GGUF 변환 미완료 (bnb-4bit ↔ Q4_K_M 양자화 호환성) — 베이스 모델 + 강한 프롬프트 + 룰 안전장치로 운영 회피
- 첫 호출 cold start 30s+ — uvicorn timeout 120s + Ollama 사전 워밍업으로 대응
- RAG 지식 기반 132 문서 (확장 백로그 등록)
- 시니어 베타 사용자 인터뷰 미진행 (정식 출시 게이트)

### 모니터링 대시보드

- LangSmith Web: B팀·D팀 LLM 호출 트레이스 (latency · token usage · error rate)
- `docs/test-report.md`: `/validate` 자동 갱신 (배포 시마다)

### 다음 릴리즈 (v1.1 계획)

- LoRA 어댑터 fp16 베이스 재학습 → GGUF 일관성 확보
- 시니어 베타 50명 인터뷰 → UX 피드백 반영
- RAG 지식 기반 1,000+ 문서 확장
- 응급 키워드 분기 응급의학 자문 검토 (분기 1회 정례화)
- BM25 토크나이저 `kiwi` 적용

---

## 회고는 [`docs/RETROSPECTIVE.md`](./RETROSPECTIVE.md) 참조
