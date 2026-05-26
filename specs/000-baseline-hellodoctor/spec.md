# Feature Specification: HelloDoctor v1.0 Baseline System

**Feature Branch**: `main`
**Created**: 2026-05-27 (retrospective documentation of shipped v1.0)
**Status**: Shipped (v1.0.0 released 2026-05-22)
**Input**: 시니어가 음성으로 의료 정보·진료과·인근 병원을 즉시 받을 수 있는 IPTV 셋톱박스 기반 의료 안내 음성 AI 에이전트.

> **Purpose**: 이미 출시된 v1.0 시스템을 Spec Kit 형식으로 retrospective 정리. 신규 기능 추가 시 본 baseline을 참조해 일관성 유지.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 응급 발화 즉시 119 안내 (Priority: P1)

70세 어르신이 갑작스러운 흉통/호흡곤란 등 응급 증상을 음성으로 호소했을 때, AI가 즉시 119 안내를 우선 반환한다.

**Why this priority**: 인명 직결. 한 건이라도 누락되면 사고. *모든 다른 기능에 우선*.

**Independent Test**: `tests/test_e2e.py::test_e2e_scenario[emergency]` 단독 실행 — "갑자기 가슴이 너무 아프고 숨이 안 쉬어져요" → intent=emergency + answer에 "119" 포함.

**Acceptance Scenarios**:

1. **Given** 사용자가 `EMERGENCY_KEYWORDS` (9개) 중 하나 발화, **When** intent classifier 호출, **Then** intent=`emergency` (룰이 LLM 분류 wrap)
2. **Given** intent=emergency, **When** D팀 답변 생성, **Then** `format_response(is_emergency=True)` 강제 호출 → "지금 바로 119에 전화해 주세요"
3. **Given** `EMERGENCY_SCORES` 합산 ≥ 80 (HIGH), **When** C팀 도구 호출, **Then** RAG·병원 검색 건너뛰고 즉시 119 안내

---

### User Story 2 — 진료과 안내 + 인근 병원 정보 (Priority: P1)

어르신이 "무릎이 아파요" 처럼 증상을 호소했을 때, 적절한 진료과(정형외과)를 안내하고 3km 내 병원 3곳을 거리·전화번호와 함께 제공.

**Why this priority**: 핵심 가치 제안. 시니어가 스마트폰 검색 없이 음성 한 마디로 해결.

**Independent Test**: "근처 내과 알려주세요" → intent=hospital_search + hospitals 배열 ≥ 1.

**Acceptance Scenarios**:

1. **Given** 증상 발화, **When** B팀 의도 분류, **Then** intent=`symptom_inquiry` 또는 `hospital_search`
2. **Given** 다중턴 1턴째 부위 인식, **When** `FOLLOWUP_QUESTIONS` 매칭, **Then** "걷기가 힘드신가요?" 추가 질문
3. **Given** C팀 호출, **When** Kakao Local API 응답, **Then** HP8 카테고리 + radius 3km + 상위 3개 반환

---

### User Story 3 — 의료 정보 RAG 답변 (Priority: P2)

어르신이 "혈압약 부작용 알려주세요" 처럼 일반 의료 정보를 물었을 때, KDCA 국가건강정보포털 데이터 기반으로 시니어 친화 답변 생성.

**Why this priority**: 의료 접근성 핵심 시나리오. 단, 응급/병원 안내 시나리오보다 빈도 낮음.

**Independent Test**: "혈압약" → intent=medication_info + 한국어 비율 ≥ 40% + 금지어 0건.

**Acceptance Scenarios**:

1. **Given** 약물·증상 질의, **When** Hybrid RAG v2 호출, **Then** Vector + BM25 → RRF → ko-reranker → top-3 + KDCA citation
2. **Given** 답변 생성, **When** Evaluator 검증, **Then** 한국어 ≥ 0.4 + 길이 ≥ 15자 + 금지어 미포함 → pass / fail 시 최대 2회 재생성
3. **Given** 응답 반환, **When** `format_response()` 후처리, **Then** 영어 단어 제거 + `FORBIDDEN_WORDS` 0건

---

### Edge Cases

- **호출어 누락**: 사용자가 "헬로비" 호출어 없이 발화 → STT는 동작, 프론트엔드가 마이크 버튼 직접 누름 안내 fallback
- **STT 오인식**: "안과가" 같은 시니어 발음 변이 → `MEDICAL_CORRECTIONS` 사전 50+ 패턴 자동 보정
- **다중 응급 키워드**: 2개 이상 매칭 시 `EMERGENCY_SCORES`를 1.2배 가산 → severity HIGH 강제
- **파인튜닝 LLM 실패**: 30s timeout → Groq llama-3.3-70b 폴백 자동 전환
- **답변 평가 3회 연속 실패**: 마지막 답변 반환 + `eval_passed=False` 메타 기록 (LangSmith 추적)
- **Kakao API 실패**: 빈 배열 반환 + "병원 정보를 가져오지 못했어요" 답변
- **Cold start**: 첫 호출 30s+ → uvicorn timeout 120s + Ollama warmup 스크립트로 마스킹

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 사용자가 자연어 음성으로 의료 질의 시, 시스템은 STT → Intent 분류 → 도구 호출 → 답변 생성 4단계 파이프라인을 수행한다. **(적용 패턴: ① Prompt Chaining + ④ Orchestrator-Worker)**
- **FR-002**: 응급 키워드 9개 (`EMERGENCY_KEYWORDS`) 매칭 시 시스템은 LLM 분류 결과와 무관하게 intent=emergency를 강제한다.
- **FR-003**: 시스템은 4가지 의도 (emergency / symptom_inquiry / hospital_search / medication_info)로 분류한다.
- **FR-004**: 시스템은 의도가 symptom_inquiry / medication_info일 때 Hybrid RAG v2를 호출하고, hospital_search일 때 Kakao Local API를 호출한다. **(적용 패턴: ② Routing)**
- **FR-005**: C팀의 RAG·Hospital·Emergency 3개 도구는 ThreadPoolExecutor로 병렬 실행되어야 한다. **(적용 패턴: ③ Parallelization)**
- **FR-006**: 답변 생성 후 Evaluator가 한국어 비율·길이·금지어 검증을 수행하고, 실패 시 최대 2회 재생성한다. **(적용 패턴: ⑤ Evaluator-Optimizer)**
- **FR-007**: 모든 답변은 출처를 citation으로 포함한다. **citation 형식: 답변 끝에 한국어 인용구로 표기** (예: *"출처: 질병관리청 국가건강정보포털"*)
- **FR-008**: 시스템은 다중턴 대화에서 `conversation_state[session_id]` 로 컨텍스트를 누적한다.

### Non-Functional Requirements

- **NFR-001 (안전성)**: 응급 감지율 100% · 금지어 0건 머지 · 한국어 비율 ≥ 40%
- **NFR-002 (정확도)**: STT CER ≤ 3% · 의도 분류 정확도 ≥ 90% · RAG Top-3 ≥ 60%
- **NFR-003 (응답 시간)**: **p95 응답 시간 ≤ 5초** (cold start 제외) · **p99 ≤ 10초** · cold start 평균 30~60초 (Whisper + LLaMA + ChromaDB 동시 로딩)
- **NFR-004 (가용성)**: Docker Compose 단일 호스트 배포 · `docker compose up` 한 줄로 기동
- **NFR-005 (관찰가능성)**: LangSmith `@traceable` 데코레이터로 B팀·D팀 LLM 호출 추적 — **4개 메트릭 수집**: ① latency (ms) · ② token usage (input/output) · ③ error rate (%) · ④ eval retry count
- **NFR-006 (컴플라이언스)**: 의료법 §27 (무면허 의료행위 금지) · 의료광고법 준수 · 단정적 진단/처방 어휘 차단

#### NFR-007 (거버넌스) — HITL 7 체크포인트 매트릭스

총 원칙: *"AI 단독 결정 0건"*. 7 체크포인트별 1차 책임자와 baseline 적용 상태:

- **NFR-007a**: 위험 명령어 차단 (`.claude/settings.json` PreToolUse) — 개발팀 · ✅ 적용
- **NFR-007b**: 배포 전 통합 검증 (`/validate` 7항목) — 개발팀 · ✅ 7/7 통과
- **NFR-007c**: 테스트 결과 검토 (`/test`) — 개발팀 · ✅ 매 PR 실행
- **NFR-007d**: **응급 키워드 큐레이션** (`EMERGENCY_KEYWORDS`) — 의사(응급의학) · ⚠️ MVP는 개발자 수동 (자문 위촉 v1.1)
- **NFR-007e**: **금지어 목록 관리** (`FORBIDDEN_WORDS`) — 법률·컴플라이언스 · ⚠️ MVP는 정책 매트릭스 (자문 위촉 v1.1)
- **NFR-007f**: **약물 답변 검수** (`medication_inquiry`) — 약사 · ⚠️ MVP는 DUR 가이드 인용 (자문 위촉 v1.1)
- **NFR-007g**: **시니어 친화 검증** (답변 어조·UI) — 노년학 + 시니어 베타 · ⚠️ MVP는 한국어 비율 자동 검증 (베타 v1.1)

- **NFR-008 (확장성)**: 신규 의도 추가 시 `IntentRouter.register()` 한 줄로 확장

- **NFR-009 (AI Native Engineering)**: 모든 신규 모듈은 6단계 자산을 모두 생성해야 한다 — ① Instructions (`.github/instructions/`) · ② Prompts (`.github/prompts/`) · ③ Agents (`.github/agents/`) · ④ Context (`CLAUDE.md` 갱신) · ⑤ TDD (`tests/`) · ⑥ Validation (`/validate` 항목 추가). 생략 시 사양에 이유 명시 필수.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**출시 전 정량 지표 (SC-001 ~ SC-005)** — 배포 게이트로 작동:

- **SC-001**: STT CER 2.9% / WER 12.9% (baseline whisper-small-ko 대비 14.7% / 9.2% 개선)
- **SC-002**: LLM 의도 분류 정확도 94.9% / Macro-F1 0.9901 (베이스 LLaMA 57.0% 대비 +37.9%p)
- **SC-003**: 응급 감지율 90% (LLM 단독) → 100% (룰 보강 후)
- **SC-004**: RAG Top-3 정확도 62.1% (Hybrid v2 V4 채택, V1~V6 중 최고)
- **SC-005**: 통합 검증 `/validate` 7/7 통과 · 스모크 9/9 · E2E 4/4 · 단위 14/14

**출시 후 결과 지표 (SC-006)** — 운영 모니터링:

- **SC-006**: 운영 결과 — AI 단독 의사결정 **0건** · 응급 회귀 사고 **0건** · 금지어 머지 **0건** · 머지 전 게이트 차단 **8건** (관찰 기간: v1.0.0 배포 후 ~ 회고일)

---

## Key Entities

- **MEDICAL_CORRECTIONS** (dict, 50+ 항목): STT 오인식 보정 사전 (진료과·증상·약물·검사·질병)
- **EMERGENCY_KEYWORDS** (list, 9개): 즉시 119 트리거 키워드
- **EMERGENCY_SCORES** (dict, 10 항목): 응급도 가중치 (0~100점)
- **FORBIDDEN_WORDS** (list, 10개): 의료법 위반 가능 단정성 어휘
- **SYMPTOM_DEPT_MAP** (dict, 12 항목): 증상 → 진료과 매핑
- **QUERY_REWRITE_MAP** (dict, 8 항목): 시니어 어휘 → RAG 친화 표현
- **FOLLOWUP_QUESTIONS** (dict, 6 항목): 부위 → 다중턴 질문
- **ChromaDB collection** (132 문서): KDCA 의료 데이터 벡터·키워드 인덱스

---

## Constitution Compliance

본 baseline은 [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) 원칙을 모두 충족한다:

- ✅ Principle I (Safety-First): 응급 100% · 금지어 0건 · 한국어 ≥ 40% · 의료법 컴플라이언스
- ✅ Principle II (HITL Governance): 3-Tier × 6 역할 · 7 체크포인트 · `AI 단독 결정 0건`
- ✅ Principle III (TDD): 14 단위 + 7 통합 + 9 스모크 + 4 E2E
- ✅ Principle IV (Agent Patterns): 5패턴 모두 적용 ([`docs/AGENT_PATTERNS.md`](../../docs/AGENT_PATTERNS.md))
- ✅ Principle V (AI Native Engineering): 6단계 자산 24+ 파일 + 5 자동 훅 + 3 슬래시 명령

---

## References

- 시스템 아키텍처: [`docs/system_architecture.drawio`](../../docs/system_architecture.drawio)
- 거버넌스: [`docs/HITL_3TIER.md`](../../docs/HITL_3TIER.md)
- 기술 보고서: [`docs/technical-report.md`](../../docs/technical-report.md)
- SDLC 인덱스: [`docs/SDLC_DELIVERABLES.md`](../../docs/SDLC_DELIVERABLES.md)
- 릴리즈 노트: [`docs/RELEASE_NOTES.md`](../../docs/RELEASE_NOTES.md)
- 회고: [`docs/RETROSPECTIVE.md`](../../docs/RETROSPECTIVE.md)
