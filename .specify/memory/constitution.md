# LG HelloDoctor Constitution

본 헌법은 *시니어 의료 안내 음성 AI 에이전트* HelloDoctor의 모든 사양·계획·태스크·구현에 우선 적용되는 거버넌스 원칙이다. 모든 `/speckit-*` 명령은 본 헌법을 자동 참조한다.

---

## Core Principles

### I. Safety-First (NON-NEGOTIABLE)

의료 도메인의 단일 실수는 인명 사고로 직결된다. 다음 4개 안전 지표는 정확도·속도·UX보다 절대 우선한다.

- **응급 감지율 100%** — `EMERGENCY_KEYWORDS` 룰 매칭이 LLM 분류를 wrap 한다. 한 건이라도 누락 시 머지 차단 (`test_응급_키워드_100퍼센트_감지` 게이트).
- **금지어 0건 머지** — `FORBIDDEN_WORDS` 10개 (진단·처방·치료 등)는 출력에 절대 포함될 수 없다. 후처리 + 단위 테스트 이중 차단.
- **한국어 비율 ≥ 40%** — 시니어 사용자가 영어 단어를 이해 못 하는 위험 방지. Evaluator 자동 검증.
- **의료법 §27 컴플라이언스** — 무면허 의료행위·의료광고 금지. 단정적 진단/처방 어휘 사용 불가.

모든 신규 기능은 위 4개 게이트를 통과해야 머지 가능.

### II. Human-in-the-Loop Governance (NON-NEGOTIABLE)

**"AI 단독 결정 0건"** — 모든 의료 정책은 사람이 검토·승인한다. 자동화는 패턴이, 의사결정은 사람이.

- **3-Tier × 6 역할 구조**: ① 도메인 자문단 (의사·약사·노년학·법률) · ② 개발팀 · ③ 시니어 베타 사용자
- **7 체크포인트** 가 코드·테스트·훅·PR 4계층에 침투 (상세: [`docs/HITL_3TIER.md`](../../docs/HITL_3TIER.md))
- **PreToolUse 훅** 이 `EMERGENCY_*`/`FORBIDDEN_*`/`MEDICAL_CORRECTIONS` 패턴 수정 시 자문 경고 자동 출력
- **자문 충돌 우선순위**: 법률 > 의사(응급의학) > 의사(일반의) = 약사 > 노년학·UX

신규 기능 사양(`/speckit-specify`)은 7 체크포인트 중 어디에 해당하는지 명시해야 한다.

### III. Test-Driven Development (NON-NEGOTIABLE)

TDD 사이클은 강제다: **Tests written → User approved → Tests fail → Then implement**.

- **단위 테스트** (`tests/test_*.py`) 6 파일 · 100+ 케이스 · 매 PR 실행
- **통합 테스트** (`/validate` 7항목) 매 배포 실행 → 현재 7/7
- **스모크 테스트** (`docs/smoke_test.md` 9개) 스테이징 시 → 현재 9/9
- **E2E 테스트** (`tests/test_e2e.py` 4 시나리오) 출시 전 → 현재 4/4
- **회귀 차단 절대 기준**: 응급 100% · 금지어 0건 · 한국어 ≥ 40% · `/validate` 7/7

빨강→초록→리팩토링 사이클을 위반하면 PR 차단.

### IV. Agent Workflow Patterns

Anthropic *Building Effective Agents* 5가지 패턴을 모든 신규 에이전트 기능의 설계 기준으로 채택한다.

| # | 패턴 | 적용 위치 |
|---|---|---|
| ① | Prompt Chaining | `full_pipeline` A→B→C→D 게이트 체인 |
| ② | Routing | `tool_router` 의도별 분기 |
| ③ | Parallelization | C팀 RAG·Hospital·Emergency 병렬 (ThreadPoolExecutor) |
| ④ | Orchestrator-Worker | `full_pipeline` 중앙 조율 |
| ⑤ | Evaluator-Optimizer | D팀 답변 자동 평가·재생성 (max 2회) |

신규 LLM 호출 추가 시 위 5패턴 중 어느 것을 적용했는지 사양에 명시.

### V. AI Native Engineering (6-Stage Asset Strategy)

지침·프롬프트·에이전트·컨텍스트·TDD·통합 검증을 git 추적 자산으로 정착시킨다.

| 단계 | 위치 |
|---|---|
| 1. Instructions | `.github/instructions/*.instructions.md` (4) |
| 2. Prompts | `.github/prompts/*.prompt.md` (4) |
| 3. Agents | `.github/agents/*.agent.md` (8 — 일반 4 + TDD 4) |
| 4. Context | `CLAUDE.md` · `docs/PRODUCT.md` · `docs/context-packet.md` |
| 5. TDD | `tests/test_*.py` (6) |
| 6. Validation | `src/todo/manager.py` + `docs/test-report.md` |

자동화 강제 훅(5종): SessionStart · PreToolUse (위험·HITL) · PostToolUse (편집 알림·테스트 권고).
슬래시 명령(3종): `/deploy` · `/test` · `/validate`.

신규 모듈 추가 시 위 6단계 자산을 모두 생성하거나, 생략 시 이유를 사양에 명시.

---

## Medical Compliance & Safety Constraints

- **출처 명시**: 모든 RAG 답변은 *질병관리청 국가건강정보포털 (KDCA)* 출처를 citation으로 포함해야 한다.
- **응급 분기 우선**: `emergency_check()` 결과가 `severity=HIGH`이면 다른 모든 로직(RAG·병원 검색)을 건너뛰고 119 안내로 즉시 응답.
- **약물 정보 제한**: `medication_inquiry` 의도는 *일반 안전사용정보(DUR)* 만 제공. 처방·복용량·중단 권고 금지.
- **개인정보 비저장**: 사용자 음성·텍스트는 메모리 외 저장 금지. `conversation_state`는 세션 종료 시 폐기.
- **면책 조항**: 모든 답변에 *"의료 전문가 상담 권고"* 톤 유지. 단정적 진단/처방 어휘는 `FORBIDDEN_WORDS`로 차단.

기술 스택은 다음을 유지한다:

- **STT**: Whisper (`SungBeom/whisper-small-ko`) + Silero VAD + 의료 보정 사전 50+
- **LLM**: LLaMA 3.2-3B (Ollama GGUF Q4_K_M) + LoRA · Groq llama-3.3-70b 폴백
- **Retrieval**: ChromaDB + BM25 + ko-reranker (Hybrid v2)
- **Service**: FastAPI + React 19 + Vite + Docker Compose
- **Tracing**: LangSmith `@traceable` (B팀·D팀 LLM 호출)
- **Engineering**: Claude Code (hooks·slash commands·subagents) + Spec Kit

---

## Development Workflow (SDLC 7-Stage + Spec Kit)

본 프로젝트는 자체 SDLC 7단계와 Spec Kit 5단계를 다음과 같이 통합한다.

| SDLC 단계 | 산출물 | Spec Kit 대응 |
|---|---|---|
| 1. PRD | `docs/PRODUCT.md` · `docs/requirements.md` | `/speckit-specify` |
| 2. Task 분해 | `docs/backlog.md` | `/speckit-tasks` |
| 3. TDD | `tests/test_*.py` + `coverage_report.md` | `/speckit-implement` (TDD 모드) |
| 4. 통합 | `/validate` 7/7 | `/speckit-analyze` |
| 5. 스모크 | `docs/smoke_test.md` 9/9 | (기존 유지) |
| 6. E2E | `tests/test_e2e.py` 4/4 | `/speckit-checklist` |
| 7. 배포 | `RELEASE_NOTES.md` + `RETROSPECTIVE.md` | (기존 유지) |

**Quality Gates** (모두 통과해야 머지):

1. 단위 테스트 14/14
2. 응급 100% 감지
3. 금지어 0건
4. 한국어 ≥ 40%
5. `/validate` 7/7
6. HITL 자문 영역 수정 시 자문 검토 첨부

**PR 게이트** ([`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md)):
- 자문 영역(의사·약사·노년학·법률) 자가 신고 체크리스트
- 5패턴 적용 위치 명시
- 테스트 추가/갱신 명시

---

## Governance

### Constitution Authority

본 헌법은 모든 코딩 컨벤션·기술 선택·CLAUDE.md 지침에 우선한다. 충돌 시 헌법 우선.

### Amendment Process

1. 헌법 변경 제안 → PR 작성
2. 의료 도메인 영역(원칙 I·II)은 의사 또는 법률 자문 첨부 필수
3. 기술 영역(원칙 III·IV·V)은 개발팀 만장일치
4. 헌법 갱신 후 SDLC 7단계 산출물도 동기화 (특히 [`docs/HITL_3TIER.md`](../../docs/HITL_3TIER.md), [`docs/SDLC_DELIVERABLES.md`](../../docs/SDLC_DELIVERABLES.md))

### Compliance Verification

모든 PR 리뷰는 다음을 검증한다:

- [ ] 응급/금지어/한국어 회귀 테스트 통과
- [ ] HITL 1차 책임자 영역 수정 시 자문 검토 첨부
- [ ] 5패턴 중 어느 것을 적용했는지 PR 본문 명시 (신규 LLM 호출 시)
- [ ] `/validate` 7/7 통과
- [ ] 면책 조항·KDCA 출처 표기 유지

### Runtime Guidance

상세 운영 가이드는 다음 파일을 참조한다:

- [`CLAUDE.md`](../../CLAUDE.md) — 프로젝트 헌법 + 컨텍스트 (Claude Code 자동 로드)
- [`docs/HITL_3TIER.md`](../../docs/HITL_3TIER.md) — 자문단 운영 매뉴얼
- [`docs/AGENT_PATTERNS.md`](../../docs/AGENT_PATTERNS.md) — 5패턴 ↔ 코드 매핑
- [`docs/SDLC_DELIVERABLES.md`](../../docs/SDLC_DELIVERABLES.md) — 7단계 산출물 인덱스
- [`docs/technical-report.md`](../../docs/technical-report.md) — 기술 의사결정·트러블슈팅 기록
- [`docs/SPEC_KIT_GUIDE.md`](../../docs/SPEC_KIT_GUIDE.md) — Spec Kit 통합 가이드

---

**Version**: 1.0.0 | **Ratified**: 2026-05-27 | **Last Amended**: 2026-05-27
