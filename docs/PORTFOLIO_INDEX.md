# LG HelloDoctor — 포트폴리오 인덱스

> 📌 **이 페이지의 역할**: 흩어져 있는 26+ 문서·6 테스트·5 시각자료를 *한 곳에서* 탐색할 수 있는 통합 인덱스. 채용 담당자는 30초에, 면접관은 5분에, 도메인 전문가는 30분에 필요한 정보를 찾을 수 있도록 *3 레이어 깊이 점진* 구조로 정리.

---

## 🎯 30초 요약 (Hero)

> **시니어(어르신)가 IPTV 리모컨 음성 버튼만 누르면, "무릎이 아파요" 한 마디로 진료과 안내 + 인근 병원 정보 + 응급 119 안내까지 즉시 받을 수 있는 의료 특화 음성 AI 에이전트.**

| 핵심 결과 | 값 |
|---|---|
| 🚨 응급 감지율 (룰+LLM 이중 안전) | **100%** |
| 🎙️ STT CER (한국어 시니어 발화) | **2.9%** (개선 전 3.4%) |
| 🧠 의도 분류 정확도 (LLaMA 파인튜닝) | **94.9%** (개선 전 57.0%) |
| 📚 RAG Top-3 정확도 (Hybrid v2) | **62.1%** (개선 전 39.7%) |
| 🛡️ AI 단독 의사결정 | **0건** (HITL 3-Tier 거버넌스) |

**역할**: 안주연 (Team Leader · PM · AI 개발) — 의도 분류 LLM 파인튜닝, RAG V1~V6 실험, 5패턴 통합

---

## 🧭 어떻게 읽으세요? (Reading Paths)

당신이 누구냐에 따라 다른 경로를 추천합니다.

### 👔 채용 담당자 / HR (30초 ~ 3분)
1. 위 *Hero* 섹션 → 무엇을 만들었는지·핵심 결과
2. ⬇️ *대표 시각자료* (그림 4개) → 시스템 한눈에
3. ⬇️ *나의 기여* → 본인이 한 일

### 🧑‍💻 기술 면접관 / 시니어 엔지니어 (5분 ~ 30분)
1. 그림 1: [시스템 아키텍처](./system_architecture.drawio) → 입력·시스템·출력 한 장
2. [`docs/AGENT_PATTERNS.md`](./AGENT_PATTERNS.md) → Anthropic 5패턴 매핑
3. [`docs/SDLC_DELIVERABLES.md`](./SDLC_DELIVERABLES.md) → 7단계 산출물 증거
4. [`docs/technical-report.md`](./technical-report.md) → 깊은 기술 의사결정 (LoRA GGUF 5경로 실패 등)
5. [`backend/agent_patterns.py`](../backend/agent_patterns.py) + [`tests/test_agent_patterns.py`](../tests/test_agent_patterns.py) → 실제 코드 (14/14 통과)

### ⚖️ 의료/법률 도메인 전문가 (10분 ~)
1. 그림 2: [HITL 3-Tier 거버넌스](./hitl_governance.drawio) → 의사·약사·노년학·법률 자문 구조
2. [`docs/HITL_3TIER.md`](./HITL_3TIER.md) → 7 체크포인트 매트릭스
3. [`docs/ontology/hellodoctor.ttl`](./ontology/hellodoctor.ttl) → OWL/SKOS 도메인 온톨로지 (SNOMED CT 매핑)
4. `backend/main.py:144-225` → `EMERGENCY_KEYWORDS` · `FORBIDDEN_WORDS` (1차 책임자 명시)

### 🎓 학회 reviewer / 연구자 (논문 검토)
1. [`docs/JICS_paper_v2.md`](./JICS_paper_v2.md) → JICS 투고 논문 v2 (2단 컬럼·9pt)
2. [`docs/fig4_rag_comparison.png`](./fig4_rag_comparison.png) → RAG V1~V6 비교 막대그래프 (그림 4)
3. `JICS_LG_HelloDoctor_논문_확인.docx` (바탕화면) → 논문 완성본 docx

---

## 🖼️ 대표 시각자료 (그림 4종)

| 그림 | 답하는 질문 | 파일 |
|---|---|---|
| **그림 1: 시스템 아키텍처** | 무엇을 받아서 무엇을 만드나? | [`system_architecture.drawio`](./system_architecture.drawio) |
| **그림 2: HITL 3-Tier 거버넌스** | 누가 의료 규칙을 검토하나? | [`hitl_governance.drawio`](./hitl_governance.drawio) |
| **그림 3: SDLC 7-Stage 프로세스** | 어떻게 만들었나? | [`sdlc_process.drawio`](./sdlc_process.drawio) |
| **그림 4: RAG V1~V6 정확도 비교** | 왜 Hybrid를 골랐나? | [`fig4_rag_comparison.png`](./fig4_rag_comparison.png) |

> 모든 drawio 파일은 [diagrams.net](https://app.diagrams.net/) 또는 VS Code drawio 확장에서 열기 가능.

---

## 📂 전체 자산 (Categorized)

### A. 프로덕트 문서

| 파일 | 한 줄 |
|---|---|
| [`PRODUCT.md`](./PRODUCT.md) | 제품 비전·페르소나·코어 시나리오 |
| [`requirements.md`](./requirements.md) | 기능·비기능 요구사항 정의 (v2.0) |
| [`context-packet.md`](./context-packet.md) | 도메인 컨텍스트 요약 (Claude 전달용) |
| [`dev-environment.md`](./dev-environment.md) | 개발 환경 셋업 |

### B. 기술 보고서

| 파일 | 한 줄 |
|---|---|
| [`technical-report.md`](./technical-report.md) | 8개 고도화 영역 상세 (RAG v2·HITL·LoRA·온톨로지 등) |
| [`AGENT_PATTERNS.md`](./AGENT_PATTERNS.md) | Anthropic 5패턴 ↔ 프로젝트 매핑 |
| [`HITL_3TIER.md`](./HITL_3TIER.md) | 자문단 운영 매뉴얼 + 7 체크포인트 |
| [`CLEAN_ARCHITECTURE.md`](./CLEAN_ARCHITECTURE.md) | 기능 동심원 (Entities → Use Cases → Adapters) |
| [`CLEAN_ARCHITECTURE_GOVERNANCE.md`](./CLEAN_ARCHITECTURE_GOVERNANCE.md) | 거버넌스 동심원 (자문단 → 개발팀 → AI 도구) |
| [`governance-evidence.md`](./governance-evidence.md) | 거버넌스 1-pager (발표 자료) |

### C. SDLC 7단계 산출물 (전부 git 추적)

| 단계 | 산출물 |
|---|---|
| 1. PRD | `PRODUCT.md` · `requirements.md` |
| 2. Task 분해 | [`backlog.md`](./backlog.md) · `.github/instructions/` · `.github/agents/` |
| 3. TDD | `tests/test_*.py` (6) · [`coverage_report.md`](./coverage_report.md) (63%) |
| 4. 통합 | [`test-report.md`](./test-report.md) (7/7) |
| 5. 스모크 | [`smoke_test.md`](./smoke_test.md) (9/9) |
| 6. E2E | `tests/test_e2e.py` · [`e2e_test_report.md`](./e2e_test_report.md) (4/4) |
| 7. 배포 | [`RELEASE_NOTES.md`](./RELEASE_NOTES.md) v1.0 · [`RETROSPECTIVE.md`](./RETROSPECTIVE.md) |
| **인덱스** | [`SDLC_DELIVERABLES.md`](./SDLC_DELIVERABLES.md) — 7단계 매핑 한 페이지 |

### D. 코드 (핵심 모듈)

| 파일 | 한 줄 |
|---|---|
| [`backend/main.py`](../backend/main.py) | FastAPI + A→B→C→D 통합 파이프라인 (Orchestrator) |
| [`backend/agent_patterns.py`](../backend/agent_patterns.py) | Anthropic 5패턴 캡슐화 (PromptChain · IntentRouter · Parallel · Orchestrator · Evaluator) |
| [`tests/test_agent_patterns.py`](../tests/test_agent_patterns.py) | 14개 단위 테스트 (전부 통과) |
| [`tests/test_e2e.py`](../tests/test_e2e.py) | 4 시나리오 E2E 자동화 |
| [`backend/Dockerfile`](../backend/Dockerfile) · [`docker-compose.yml`](../docker-compose.yml) | 단일 호스트 컨테이너 배포 |

### E. AI Native Engineering 자산 (Claude Code 하네스)

| 영역 | 파일 |
|---|---|
| **지침 (Instructions)** | `.github/instructions/{backend,frontend,rag,ai-model}.instructions.md` (4) |
| **프롬프트 (Prompts)** | `.github/prompts/{backend,frontend,rag,ai-model}.prompt.md` (4) |
| **에이전트 (Agents)** | `.github/agents/*.agent.md` (8 — 일반 4 + TDD 4) |
| **컨텍스트 (Context)** | `CLAUDE.md` · `docs/PRODUCT.md` · `docs/context-packet.md` |
| **하네스 (Harness)** | `.claude/settings.json` (PreToolUse·PostToolUse·SessionStart 훅) |
| **슬래시 명령** | `.claude/commands/{deploy,test,validate}.md` |

### F. 실험 코드 (논문 인용용)

| 파일 | 한 줄 |
|---|---|
| [`experiment_rag_comparison.py`](./experiment_rag_comparison.py) | RAG V1~V8 8가지 검색 방식 비교 실험 |
| [`experiment_llm_comparison.py`](./experiment_llm_comparison.py) | LLM 의도 분류 모델별 비교 |
| [`fig4_rag_comparison.py`](./fig4_rag_comparison.py) | 그림 4 막대그래프 재생성 스크립트 |

### G. 도메인 온톨로지

| 파일 | 한 줄 |
|---|---|
| [`ontology/hellodoctor.ttl`](./ontology/hellodoctor.ttl) | OWL/SKOS Turtle (79 개체, SNOMED CT 30+ 매핑) |
| [`ontology/README.md`](./ontology/README.md) | SPARQL 예시 + 검증 방법 |

### H. 포트폴리오 페이지 (기존 3장)

| 파일 | 한 줄 |
|---|---|
| [`portfolio_page1.md`](./portfolio_page1.md) | 페이지 1 — 프로젝트 소개·문제·기능 |
| [`portfolio_page2.md`](./portfolio_page2.md) | 페이지 2 — RAG V1~V6 실험·성능 |
| [`portfolio_page3.md`](./portfolio_page3.md) | 페이지 3 — 트러블슈팅·확장 |

### I. 학회 논문

| 파일 | 한 줄 |
|---|---|
| [`JICS_paper_v2.md`](./JICS_paper_v2.md) | JICS 투고용 (Markdown 원본) |
| `JICS_LG_HelloDoctor_논문_확인.docx` (바탕화면) | docx 완성본 (2단 컬럼·바탕 9pt) |

---

## 💎 핵심 차별점 (이 프로젝트가 특별한 이유)

### 1. *"AI 단독 결정 0건"* 을 시스템 수준에서 강제
모델 정확도 94.9%는 의료 도메인에서 부족함. 룰 안전장치(`EMERGENCY_KEYWORDS`) + HITL 3-Tier 거버넌스 + 자동화 훅 4계층으로 응급 100%·금지어 0건 보장.

### 2. Anthropic 5가지 에이전트 워크플로 패턴 실제 적용
이론 → 코드 → 14개 회귀 테스트로 검증. `agent_patterns.py` 한 파일이 *"안전·정확·빠른"* 의 균형 설계 증명.

### 3. SDLC 7단계 전 과정을 git 추적 가능한 산출물로
PRD(1) · 백로그(2) · 단위(3) · 통합(4) · 스모크(5) · E2E(6) · 릴리즈+회고(7) 모두 실제 파일로 존재. *"어쩌다 동작하는 데모"* 가 아닌 엔지니어링 결과물.

### 4. AI Native Engineering 6단계 자산화
지침·프롬프트·에이전트·컨텍스트·TDD·검증 → 24+ git 파일 + 5 자동 강제 훅 + 3 슬래시 명령. 신규 팀원도 CLAUDE.md 하나로 즉시 컨텍스트 흡수.

### 5. 양자화 호환성 한계 진단 (학술 가치)
LoRA bnb-4bit ↔ Q4_K_M GGUF 변환 5경로 모두 실패 → 근본 원인 분석 → 운영 회피 전략 문서화. 후속 연구가 시행착오 반복하지 않도록.

---

## 📊 성과 메트릭 종합

| 영역 | 지표 | 값 |
|---|---|---|
| STT | CER · WER | **2.9% · 12.9%** |
| LLM | 의도 분류 정확도 · 응급 감지 | **94.9% · 100%** |
| RAG | Top-3 정확도 · MRR · 환각률 | **62.1% · 0.86 · 9%** (-50%) |
| 거버넌스 | HITL 체크포인트 · 역할 · AI 단독 결정 | 7 · 6 · **0건** |
| AI Native | git 추적 자산 · 자동 훅 · 슬래시 명령 | 24+ · 5 · 3 |
| 테스트 | 단위 · 통합 · 스모크 · E2E | **14/14 · 7/7 · 9/9 · 4/4** |
| 코드 | agent_patterns 커버리지 | 63% |

---

## 🛠️ 기술 스택

| 영역 | 사용 기술 |
|---|---|
| **Backend** | Python 3.11 · FastAPI · uvicorn |
| **Frontend** | React 19 + Vite + TypeScript · Tailwind CSS |
| **STT** | Whisper (`SungBeom/whisper-small-ko`) + LoRA · Silero VAD |
| **LLM** | LLaMA 3.2-3B + LoRA (Ollama GGUF Q4_K_M) · Groq llama-3.3-70b (Fallback) |
| **RAG** | ChromaDB · rank_bm25 · `Dongjin-kr/ko-reranker` · `jhgan/ko-sroberta-multitask` |
| **External** | Kakao Local API · KDCA 국가건강정보포털 · LangSmith |
| **DevOps** | Docker Compose · nginx:alpine |
| **Engineering** | Claude Code (hooks·slash commands·subagents·memory) · pytest · pytest-cov |
| **Ontology** | OWL 2 DL · SKOS · Turtle · SNOMED CT |

---

## 🙋 나의 기여 (안주연 · Team Leader · PM · AI 개발)

| 영역 | 한 일 |
|---|---|
| **프로젝트 총괄** | 4팀 (A·B·C·D) 일정·역할 분담, 위클리 동기화, PR 리뷰 책임 |
| **B팀: 의도 분류 LLM** | 학습 데이터셋 설계, 시스템 프롬프트 구조화, LLaMA 3.2-3B LoRA 파인튜닝, 응급 키워드 14→30 확장, 다단계 폴백 |
| **C팀: RAG 실험** | V1~V6 8가지 검색 방식 비교 실험 코드·평가, Hybrid v2 (Vector+BM25+RRF+Reranker) 채택 결정 |
| **B팀: 다중턴** | 24 부위 기준 followup 3턴 분기 로직 구현 |
| **5패턴 통합** | Anthropic 5워크플로 패턴 `agent_patterns.py` 모듈화 + 14개 회귀 테스트 |
| **HITL 거버넌스** | 3-Tier × 6 역할 설계, 7 체크포인트 매트릭스, PreToolUse 훅 정책 |
| **AI Native 자산화** | CLAUDE.md 작성, .github/instructions/agents/prompts 24+ 파일 |
| **SDLC 7단계** | 백로그·스모크·E2E·릴리즈노트·회고 작성, /validate /test /deploy 슬래시 명령 |
| **논문 작성** | JICS 투고용 논문 v2 (Whisper·RAG·5패턴 통합) |

---

## 📞 연락 / 데모

- **GitHub**: https://github.com/lg-hellovision-dx-data-school/LGHelloDoctor
- **이메일**: dkswndus6988@naver.com
- **데모 실행**: `docker compose up --build` (단일 명령)

---

> 이 인덱스는 *"30초에 핵심을 잡고, 5분에 깊이를 더하고, 30분에 전체를 이해할 수 있는"* 진입점입니다. 어디부터 보실지 위 *Reading Paths* 를 참고하세요.
