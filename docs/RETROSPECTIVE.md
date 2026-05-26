# LG HelloDoctor v1.0 — 회고 (Retrospective)

> **SDLC 단계 7 산출물** — v1.0.0 출시 후 4주 작업 회고. *Keep / Problem / Try* (KPT) 형식.

| 항목 | 값 |
|---|---|
| 회고일 | 2026-05-26 |
| 대상 릴리즈 | v1.0.0 (2026-05-22 배포) |
| 참여자 | 안주연 (PM·AI) · 김진형 · 권예진 · 이영현 |
| 진행 형식 | 비동기 KPT + 정량 회귀 |

---

## Keep — 다음에도 이어갈 것

### 1. *룰 + LLM 이중 안전 구조* — 응급 100% 감지 달성

LLM 단독 분류 (94.9%)로는 인명 직결 사례(1명이라도 누락 시 사고) 보장이 불가능했다.
`EMERGENCY_KEYWORDS` 룰 매칭이 LLM 출력을 wrap 하는 구조로 **응급 감지율 100%** 회복.

> **인사이트**: 모델 정확도가 높을수록 "룰은 불필요"하다는 유혹이 강해지지만, 의료 도메인에서는 *마지막 1%* 가 사람 목숨이다. 룰은 모델 백업이 아니라 **최종 안전망**.

### 2. *Claude Code 하네스 자동화* — AI 단독 결정 0건 달성

`.claude/settings.json` 의 PreToolUse 훅이 `EMERGENCY_*`·`FORBIDDEN_*` 패턴 수정 시 자문 경고를 자동 출력 → 개발자가 무심코 의료 규칙을 변경하는 것을 시스템 수준에서 차단.

> **인사이트**: 코드 리뷰·테스트만으로는 *잊고 머지하는 사고* 를 막을 수 없다. 자동화 훅이 *기억 보조 장치* 로 작동.

### 3. *Hybrid RAG 점진적 진화* — V1~V6 실험으로 V4(62.1%) 채택

6가지 방식 ablation으로 *"Reranking 추가 = 항상 좋다"* 가 거짓임을 확인 (V5 57.4% vs V4 62.1%). 데이터 기반 의사결정.

### 4. *AI Native Engineering 6단계 자산화*

지침(4) · 프롬프트(4) · 에이전트(8) · 컨텍스트(3) · TDD(5) · 통합 검증(1) → 24+ git 추적 파일.
신규 팀원도 CLAUDE.md 만 읽으면 프로젝트 컨텍스트 즉시 파악 가능.

### 5. *5가지 에이전트 워크플로 패턴 명시화*

Anthropic *Building Effective Agents* 의 5패턴을 `backend/agent_patterns.py` 로 캡슐화 → 14개 회귀 테스트로 동작 보장. 신규 의도 추가 시 IntentRouter 등록 한 줄로 확장.

---

## Problem — 어려웠던 점·아쉬운 점

### 1. LoRA 어댑터 GGUF 변환 실패 (5경로 모두 실패)

| 시도 | 결과 |
|---|---|
| Unsloth `save_pretrained_gguf` | apt-get timeout |
| Unsloth `save_pretrained_merged` | `# saved modules = 0` 검증 실패 |
| `AutoModelForImageTextToText` + PEFT | silent fail (base 응답) |
| `convert_lora_to_gguf.py` | tensor mapping 실패 (multimodal 미지원) |
| Gemma 4 E2B 전환 | 환경 호환성 문제 (~5시간 소요) |

**근본 원인**: `bnb-4bit` 학습 ↔ `Q4_K_M` 배포 양자화 미스매치.
**회피**: 베이스 모델 + 강한 시스템 프롬프트 + 룰 안전장치로 운영. 분류 정확도는 60% 수준이지만 *응급 감지 100%* 핵심 안전 지표는 회복.

> **교훈**: 신규 모델 채택 비용 = 학습 시간 + **toolchain 안정화 시간** (학습 30분 vs 환경 디버깅 5시간 실측).

### 2. Cold Start 30초+

Whisper + LLaMA + ChromaDB + Sentence-Transformers 동시 로딩으로 첫 호출이 30초 초과.
**대응**: uvicorn timeout 120s + Ollama 사전 워밍업 스크립트로 마스킹. 근본 해결 필요.

### 3. 시니어 베타 사용자 미진행

MVP 단계에서 사내 5~10명 비공식 베타 계획했으나 일정상 미진행.
정식 출시 게이트 (50명+ 외부 패널)는 v1.1로 이월.

### 4. 자문단 미위촉

설계 단계에서 자문단 4 역할(의사·약사·노년학·법률) 정립했으나 위촉은 v1.1 마일스톤.
현재는 KDCA 공공자료 + `FORBIDDEN_WORDS` 정책 매트릭스로 운영.

### 5. main.py 통합 테스트 자동화 부재

단위 테스트 14/14 통과지만 main.py 자체는 코드 커버리지 0% (Whisper·Ollama·ChromaDB 의존성).
`/validate` 7항목으로 통합 검증하나, pytest fixture로 자동화하면 회귀 차단 강화 가능.

---

## Try — 다음 릴리즈에 시도할 것

| 우선순위 | 시도 | 측정 지표 | 담당 |
|---|---|---|---|
| **P0** | LoRA fp16 베이스 재학습 → Q4_K_M 일관성 | 의도 분류 정확도 94.9% 회복 | AI |
| **P0** | 시니어 외부 패널 50명 베타 인터뷰 | 이해도 ≥ 80% · 음성 인식률 ≥ 95% | PM · UX |
| **P0** | 응급의학과 자문 위촉 | 분기 1회 `EMERGENCY_KEYWORDS` 검토 정례화 | PM |
| P1 | RAG 지식 기반 1,000+ 문서 확장 | Top-3 정확도 70%+ | RAG |
| P1 | BM25 토크나이저 `kiwi` 적용 | recall@3 +5%p | RAG |
| P1 | Cold start 15초 이내 | uvicorn pre-fork + 모델 lazy load | Infra |
| P2 | main.py 통합 테스트 pytest fixture | coverage 60%+ | TDD |
| P2 | Cypress/Playwright Frontend E2E | UI 회귀 자동 차단 | Frontend |
| P2 | LangSmith Faithfulness Judge 자동화 | 환각률 < 5% 게이트 | AI |

---

## 회고 메트릭

| 영역 | 값 |
|---|---|
| 4주간 PR 수 | 47 |
| 머지 전 회귀 차단 | 8건 (전부 `/test` 또는 `/validate` 게이트) |
| 응급 회귀 사고 | **0건** (룰 안전장치 효과) |
| 금지어 머지 | **0건** (FORBIDDEN_WORDS 게이트 효과) |
| AI 단독 의사결정 | **0건** (HITL 거버넌스 효과) |
| 자동화 훅 트리거 | 23회 (PreToolUse HITL 경고) |
| TaskCreate / TaskUpdate 사용 | 117회 (세션 평균 8.5회) |

---

## 핵심 교훈 3줄

1. **모델 정확도는 "충분히 좋은" 것일 뿐, 핵심 안전 지표(응급 100%·금지어 0건)는 룰·테스트·훅 4계층으로 강제해야 한다.**
2. **신규 모델/toolchain 채택은 학습 시간보다 환경 디버깅 시간이 크다.** 안정된 베이스 + 강한 프롬프트 조합이 종종 더 합리적.
3. **AI Native Engineering 6단계 자산화 + Claude Code 하네스 + HITL 3-Tier 거버넌스 결합이 *"AI 단독 결정 0건"* 을 가능하게 했다.** 다음 프로젝트에도 그대로 이식 가능한 운영 패턴.

---

## 관련 산출물

- [`docs/RELEASE_NOTES.md`](./RELEASE_NOTES.md) — v1.0.0 릴리즈 노트
- [`docs/test-report.md`](./test-report.md) — `/validate` 7/7 결과
- [`docs/coverage_report.md`](./coverage_report.md) — TDD 커버리지
- [`docs/smoke_test.md`](./smoke_test.md) — 스모크 9/9
- [`docs/e2e_test_report.md`](./e2e_test_report.md) — E2E 4/4
- [`docs/technical-report.md`](./technical-report.md) — 기술 디테일 (양자화 호환성 등)
- [`docs/HITL_3TIER.md`](./HITL_3TIER.md) — 3-Tier 거버넌스
- [`docs/SDLC_DELIVERABLES.md`](./SDLC_DELIVERABLES.md) — 7단계 산출물 매핑
