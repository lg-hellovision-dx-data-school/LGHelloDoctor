# LG HelloDoctor — Task 백로그 & 인수 조건 (AC)

> **SDLC 단계 2 산출물** — PRD(`docs/PRODUCT.md`, `docs/requirements.md`)를 실행 가능한 Task 단위로 분해하고, 각 Task의 인수 조건(Acceptance Criteria)·테스트 전략·실행 순서를 명시한다.

| 항목 | 값 |
|---|---|
| 작성일 | 2026-04-20 |
| 갱신일 | 2026-05-26 |
| 총 Task | 22개 (A팀 5 · B팀 5 · C팀 6 · D팀 4 · Infra 2) |
| 실행 기간 | 2026-04-20 ~ 2026-05-22 (4주 + 검증 1주) |
| 자동화 도구 | TaskCreate · TaskList · `/test` · `/validate` |

---

## A팀 — STT (Speech-to-Text)

| # | Task | 인수 조건 (AC) | 테스트 | 우선순위 | 의존 |
|---|---|---|---|---|---|
| A-1 | Whisper 베이스 모델 통합 | `stt_pipeline()` 호출 시 CER ≤ 5%, WER ≤ 15% | `test_ai_model.py::test_stt_basic` | P0 | - |
| A-2 | Silero VAD 무음 제거 | threshold 0.4 적용 시 무음 구간 ≥ 95% 제거 | `test_backend.py::test_vad` | P0 | A-1 |
| A-3 | 시니어 한국어 LoRA 파인튜닝 | CER 3.4% → 2.9% 개선 | manual eval (AI Hub 노인 데이터셋) | P1 | A-1 |
| A-4 | 의료 용어 보정 사전 (50+) | `MEDICAL_CORRECTIONS`에 정의된 패턴 100% 보정 | `test_ai_model.py::test_진료과명_보정` | P0 | A-2 |
| A-5 | 호출어·간투어 제거 | 출력 텍스트에 "헬로비", "어~", "음~" 0건 | `test_ai_model.py::test_전처리` | P0 | A-4 |

## B팀 — Intent Classification & Multi-turn

| # | Task | 인수 조건 (AC) | 테스트 | 우선순위 | 의존 |
|---|---|---|---|---|---|
| B-1 | 4개 의도 분류 (emergency/symptom/hospital/medication) | 정확도 ≥ 90% (50 케이스) | `test_ai_model.py::TestIntentClassification` | P0 | A-5 |
| B-2 | 응급 키워드 룰 wrap (`EMERGENCY_KEYWORDS` 9개) | 응급 감지율 100% (단 1건도 누락 X) | `test_ai_model.py::test_응급_키워드_100퍼센트_감지` | **P0** | B-1 |
| B-3 | LLaMA 3.2-3B 파인튜닝 (Ollama GGUF) | 분류 정확도 57.0% → 94.9% | manual eval | P1 | B-1 |
| B-4 | Groq 폴백 (파인튜닝 실패 시) | timeout 30s 후 Groq 자동 전환 | `test_backend.py::test_groq_fallback` | P1 | B-3 |
| B-5 | 다중턴 followup 질문 (24 부위) | 부위 인식 → 2턴째 컨텍스트 누적 | `test_backend.py::test_multiturn` | P1 | B-1 |

## C팀 — RAG + 도구 호출

| # | Task | 인수 조건 (AC) | 테스트 | 우선순위 | 의존 |
|---|---|---|---|---|---|
| C-1 | ChromaDB 벡터 검색 (V2) | Top-3 정확도 ≥ 55% | `test_rag.py::test_vector_only` | P0 | - |
| C-2 | BM25 키워드 검색 | 희소 키워드 매칭 ≥ 80% | `test_rag.py::test_bm25` | P0 | - |
| C-3 | RRF Fusion (k=60) | Vector + BM25 결합 → recall@3 +10%p | `test_rag.py::test_rrf` | P0 | C-1, C-2 |
| C-4 | Cross-Encoder 리랭킹 (ko-reranker) | top-3 재순위화 후 정확도 62.1% | `test_rag.py::test_rerank` | P1 | C-3 |
| C-5 | Kakao Local API 병원 검색 | radius 3km 내 상위 3개 반환 (HP8) | `test_backend.py::test_kakao` | P0 | - |
| C-6 | **병렬 실행 (ThreadPoolExecutor)** | RAG + Hospital + Emergency 동시 → 직렬 대비 1.5x↑ | `test_agent_patterns.py::test_세_도구_병렬_실행이_직렬보다_빠름` | P1 | C-4, C-5 |

## D팀 — Answer Generation + Evaluator

| # | Task | 인수 조건 (AC) | 테스트 | 우선순위 | 의존 |
|---|---|---|---|---|---|
| D-1 | LLaMA 답변 생성 (시니어 친화 어조) | 3~4문장, 한국어 ≥ 40% | `test_ai_model.py::test_한국어_중심_응답` | P0 | B-5, C-6 |
| D-2 | 금지어 후처리 (`FORBIDDEN_WORDS` 10개) | "진단/처방/치료" 등 0건 머지 | `test_ai_model.py::test_금지어_필터링` | **P0** | D-1 |
| D-3 | **Evaluator-Optimizer 루프** | 한국어/길이/금지어 검증 실패 시 최대 2회 재생성 | `test_agent_patterns.py::TestGenerateWithEvaluator` (4개) | P1 | D-1, D-2 |
| D-4 | 응급 시 119 메시지 강제 | severity=HIGH → answer 무조건 119 안내 | `test_backend.py::test_emergency_response` | **P0** | B-2, D-1 |

## Infra — 배포 · 검증

| # | Task | 인수 조건 (AC) | 테스트 | 우선순위 | 의존 |
|---|---|---|---|---|---|
| I-1 | Docker Compose 단일 호스트 배포 | `docker compose up` 한 줄로 배포 완료 | manual smoke | P0 | 전체 |
| I-2 | `/validate` 7항목 통합 검증 | 7/7 통과 시에만 배포 승인 | `src/todo/manager.py` | **P0** | 전체 |

---

## 테스트 전략

| 레벨 | 도구 | 대상 | 빈도 |
|---|---|---|---|
| 단위 테스트 | pytest | 함수·클래스 단위 (5 파일, 100+ 케이스) | 매 PR |
| 통합 테스트 | `/validate` | API · DB · 응급 분기 · 한국어 응답 7항목 | 매 배포 |
| 스모크 테스트 | manual checklist | 핵심 경로 (음성→답변) | 스테이징 시 |
| E2E 테스트 | `test_e2e.py` | 4개 의도 시나리오 (Docker) | 출시 전 |

## 실행 순서 (의존 그래프 → 4주 일정)

```
주차 1: A팀 (STT)        — A-1 → A-2 → A-3 → A-4 → A-5
주차 2: B팀 (Intent)      — B-1 → B-2 → B-3 → B-4 → B-5
주차 3: C팀 (RAG+Tools)   — (C-1, C-2 병렬) → C-3 → C-4 → C-5 → C-6
주차 4: D팀 (Answer)      — D-1 → D-2 → D-3 → D-4
주차 5: Infra & 검증      — I-1 → I-2 → 스모크 → E2E → 릴리즈
```

---

## 자동화 — Claude Code 통합

- **TaskCreate/TaskList**: 본 백로그의 각 Task를 세션 내 TaskList에 등록 → in_progress / completed 추적
- **`/test`**: pytest 전체 스위트 실행 (PR 마다)
- **`/validate`**: 7항목 통합 검증 (배포 마다)
- **PreToolUse 훅**: `EMERGENCY_*`/`FORBIDDEN_*` 수정 시 자문 경고 → HITL 거버넌스 자동 연계
