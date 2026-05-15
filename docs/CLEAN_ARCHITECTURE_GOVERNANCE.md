# LG HelloDoctor — Clean Architecture (AI-Native Governance 관점)

기존 [CLEAN_ARCHITECTURE.md](./CLEAN_ARCHITECTURE.md) 가 **"무엇을 하는가(기능)"** 를 동심원으로 그렸다면,
이 문서는 **"AI 가 어떻게 통제·검증되는가(거버넌스)"** 를 같은 4계층 동심원으로 그립니다.

> 핵심 질문: *Claude Code · Copilot · LLaMA 가 내일 다른 도구로 바뀌어도, 우리의 의료법 준수와 환자 안전 약속은 그대로인가?*

답이 "예" 가 되도록 안쪽에 **불변 가치**, 바깥쪽에 **교체 가능한 AI 도구** 를 배치합니다.

---

## 거버넌스 의존성 규칙

> **AI 도구는 가치를 따라야지, 가치가 도구를 따르면 안 된다.**

- ✅ "의료법 준수" → 이를 강제하기 위해 FORBIDDEN_WORDS 정책을 만들고 → 이를 enforce 하는 pytest 케이스를 작성하고 → 이를 자동 실행하는 hook 을 etc.
- ❌ "Claude Code 가 이걸 잘 못하니까 의료법 기준을 완화하자" — 절대 금지

밖에서 안으로의 의존은 자연스럽지만, **안쪽이 바깥 도구의 한계에 맞춰 휘어지면 거버넌스가 무너집니다**.

---

## 동심원 4계층 — 거버넌스 시각화

```
              ╔══════════════════════════════════════════════════════╗
              ║  ④ AI Tools & Observability  (도구 — 언제든 교체)     ║
              ║  Claude Code · Copilot · Cursor                      ║
              ║  Ollama · LangSmith · Groq · pytest · Docker · GHA   ║
              ║  ┌────────────────────────────────────────────────┐  ║
              ║  │  ③ Specifications & Harness  (강제 메커니즘)    │  ║
              ║  │  AI Native 6단계: Instructions·Prompts·Agents  │  ║
              ║  │   Context·TDD·Validation                      │  ║
              ║  │  Hooks · Slash Commands · Session Scripts     │  ║
              ║  │  ┌──────────────────────────────────────────┐ │  ║
              ║  │  │  ② Policies & Quality Gates  (정책)      │ │  ║
              ║  │  │  FORBIDDEN_WORDS · EMERGENCY_KEYWORDS   │ │  ║
              ║  │  │  MEDICAL_CORRECTIONS · 평가 임계값       │ │  ║
              ║  │  │  HITL 체크포인트 7개                     │ │  ║
              ║  │  │  ┌────────────────────────────────────┐ │ │  ║
              ║  │  │  │  ① Values & Principles  (불변)      │ │ │  ║
              ║  │  │  │  의료법 준수 · 환자 안전 (119)      │ │ │  ║
              ║  │  │  │  시니어 친화 · HITL · 출처 투명성   │ │ │  ║
              ║  │  │  │  데이터 프라이버시                   │ │ │  ║
              ║  │  │  └────────────────────────────────────┘ │ │  ║
              ║  │  └──────────────────────────────────────────┘ │  ║
              ║  └────────────────────────────────────────────────┘  ║
              ╚══════════════════════════════════════════════════════╝
                          ↑                                ↓
                  외부 도구는 안쪽 가치를 강제하기 위해서만 존재
```

PowerPoint/Figma 색상 가이드:
- **중앙(짙은 레드)**: ① 불변 가치 — 가장 진하게, 흔들리면 안 됨
- **2번째 링(주황)**: ② 정책 — 가치를 측정 가능한 규칙으로
- **3번째 링(파랑)**: ③ 강제 메커니즘 — 정책을 자동화
- **바깥 링(연그레이)**: ④ AI 도구 — 교체 가능

---

## ① Values & Principles — 불변의 가치 (가장 안쪽)

> "AI 도구가 모두 사라져도 우리가 지킬 약속"

### 6대 원칙

| # | 원칙 | 의미 | 위반 시 결과 |
|---|---|---|---|
| 1 | **의료법 준수** | 단정적 진단·처방 금지. 권유형으로만 안내 | 의료법 위반 — 서비스 폐쇄 사유 |
| 2 | **환자 안전 우선** | 응급 발화 → 무조건 119 안내 | 인명 사고 위험 |
| 3 | **시니어 친화** | 존댓말, 1~3문장, 어려운 용어 풀어쓰기 | 사용자 이해 실패 → 서비스 무용지물 |
| 4 | **HITL (Human-in-the-Loop)** | AI 단독 결정 금지, 사람이 주요 지점 검토·승인 | AI hallucination 그대로 운영 반영 |
| 5 | **출처 투명성** | 답변에 RAG 검색 출처(KDCA 국가건강정보포털) 표기 | 신뢰 상실, 책임 소재 불명 |
| 6 | **데이터 프라이버시** | 환자 발화 비저장. API 키는 `.env` 분리, 코드 하드코딩 금지 | PII 유출 사고 |

### 책임 모델 (Responsibility Model)

```
사용자 (어르신)
   │ 의료 자문 요청
   ↓
[ AI ]
   │ "병원 진료를 권해드려요" (권유 only)
   │ "지금 119에 전화해주세요" (응급 알림)
   │ 절대 X: "이건 무슨 병이에요" (진단)
   │ 절대 X: "이 약 드세요" (처방)
   ↓
[ 사람 의사 ]  ← 최종 의료 판단은 항상 여기
```

> 📁 코드 위치: 코드에 있지 않고 **이 문서·CLAUDE.md·README** 에 명시. 모든 PR/코드 리뷰의 판단 기준.

---

## ② Policies & Quality Gates — 정책 (가치를 측정 가능하게)

> "가치를 코드가 검증할 수 있는 구체적 규칙으로"

### 데이터 정책

| 정책 | 위치 | 역할 |
|---|---|---|
| `FORBIDDEN_WORDS` (10개) | `backend/main.py` | 단정적 진단·처방 어휘 차단 (예: "치료해드릴게요") |
| `EMERGENCY_KEYWORDS` | `backend/main.py` | 119 즉시 안내 트리거 (쓰러짐, 흉통, 의식소실 등) |
| `MEDICAL_CORRECTIONS` | `backend/main.py` | 진료과명 오인식 보정 ("안과가" → "안과") |

### 출력 품질 기준

| 기준 | 임계값 | 측정 방법 |
|---|---|---|
| 한국어 비율 | ≥ 40% | 정규식 카운트 |
| 답변 길이 | 1~3 문장 | 마침표 카운트 |
| 응급 키워드 → "119" 포함 | 100% | `tests/test_ai_model.py::test_응급_키워드_100퍼센트_감지` |

### Judge 평가 임계값 (Groq Llama 3.1 8B as Judge)

| 축 | 최소 통과 | 의미 |
|---|---|---|
| Faithfulness | ≥ 0.7 | RAG context 근거, hallucination 없음 |
| Helpfulness | ≥ 0.7 | 시니어가 다음 행동을 알 수 있게 도움 |
| **Safety** | **= 1.0** | 단정 진단·처방 없음 + 응급 시 119 (가장 엄격) |
| Retrieval Recall@3 | ≥ 0.85 | top-3 안에 정답 문서 |

### HITL 3-Tier 거버넌스 — *"누구나 사람"* 이 아닌 *"역할별 사람"*

```
                ┌─────────────────────────────────┐
                │  ① 도메인 자문단 (4 역할)         │
                │  ─────────────────────           │
                │  · 의사 (응급의학·일반의)         │
                │  · 약사                          │
                │  · 노년학·시니어 UX              │
                │  · 법률·컴플라이언스             │
                └─────────────────────────────────┘
                            ↑ 도메인 정확성
                            │
        ┌───────────────────┴───────────────────┐
        │                                        │
   ┌─────────────────┐                  ┌──────────────────┐
   │  ② 개발팀        │                  │  ③ 시니어 사용자  │
   │  ────────       │                  │       베타       │
   │  PR·테스트·배포  │                  │  ──────────      │
   │  위험 명령 차단  │                  │  이해도·UX 피드백 │
   └─────────────────┘                  └──────────────────┘
       기술 정합성                          사용성 보증
```

#### 7 체크포인트 × 1차 책임자 매트릭스

| # | 체크포인트 | 위치 | 1차 책임자 | 검수 주기 |
|---|---|---|---|---|
| 1 | 위험 명령어 차단 | `.claude/settings.json` PreToolUse | 개발팀 | 자동 (실시간) |
| 2 | 배포 전 통합 검증 | `/validate` | 개발팀 | 배포 시마다 |
| 3 | 테스트 결과 검토 | `/test` | 개발팀 | PR 마다 |
| 4 | **응급 키워드 큐레이션** | `EMERGENCY_KEYWORDS` | **의사 (응급의학)** | 분기 1회 + 사고 시 |
| 5 | **금지어 목록 관리** | `FORBIDDEN_WORDS` | **법률·컴플라이언스** | 의료법 개정 시 + 분기 1회 |
| 6 | **약물 답변 검수** | `medication_inquiry` 답변 | **약사** | 출시 전 + 분기 1회 |
| 7 | **시니어 친화 검증** | 답변 어조·UI | **노년학** + **시니어 베타** | 출시 전 + 월 1회 샘플 |

> 📌 도메인 자문단은 설계 단계에서 정립. MVP 는 KDCA 공공자료 + 개발자 검토로 출범, 정식 출시 전 자문단 도입.

> 📋 자문단 운영 프로세스 상세는 [`HITL_3TIER.md`](./HITL_3TIER.md) 참조.

> 📁 코드 위치: `backend/main.py` 상수 + `tests/test_*.py` + `.claude/settings.json` + `CLAUDE.md` HITL 표

---

## ③ Specifications & Harness — 강제 메커니즘 (정책을 자동화)

> "사람이 매번 검사하는 대신 시스템이 자동으로 강제"

이 계층이 곧 **AI Native Engineering 6단계** 입니다.

### 6단계 매핑

| 단계 | 역할 | 위치 | 강제하는 가치 |
|---|---|---|---|
| **1. Instructions** | AI 에게 도메인 규칙 알리기 | `.github/instructions/{backend,frontend,rag,ai-model}.instructions.md` | 의료법, 시니어 친화 |
| **2. Prompts** | 작업 단위 행동 지시 | `.github/prompts/*.prompt.md` | 출력 품질, 출처 표기 |
| **3. Agents** | 페르소나 + 책임 분리 | `.github/agents/{TDD-,일반}*.agent.md` | 역할별 의무 (TDD agent → 테스트 강제) |
| **4. Context Engineering** | 도메인 맥락·예시 주입 | `CLAUDE.md`, `docs/PRODUCT.md`, `docs/context-packet.md` | 모든 가치 (메타 문서) |
| **5. TDD** | 정책을 테스트로 고정 | `tests/test_{backend,frontend,rag,ai_model}.py` | 회귀 방지 |
| **6. Validation** | 출시 전 통합 점검 | `/validate`, `docs/test-report.md` | 7개 항목 합격 후 배포 |

### Harness — 자동 강제 도구

| 메커니즘 | 파일 | 차단·검증 대상 |
|---|---|---|
| **PreToolUse Hook** | `.claude/settings.json` | `rm -rf`, `drop table`, `force-push`, `DELETE FROM` |
| **PostToolUse Hook** | `.claude/settings.json` | 편집 후 알림 — 사람 diff 확인 유도 |
| **SessionStart Hook** | `.claude/scripts/session-start.sh` | 세션 시작 시 추적 중인 지침 파일 자동 안내 |
| **/deploy** | `.claude/commands/deploy.md` | Docker 배포 가이드 — 검증 절차 강제 |
| **/test** | `.claude/commands/test.md` | pytest 전체 스위트 — 회귀 차단 |
| **/validate** | `.claude/commands/validate.md` | 7개 항목 체크리스트 — 출시 게이트 |

### Few-shot 예시 (Context Engineering 의 일부)

CLAUDE.md 안의 4개 예시는 **AI 가 잘못된 행동을 학습하지 않도록 가드레일** 역할:

| 예시 | 가르치는 것 |
|---|---|
| 금지어 필터 수정 요청 | "의료법 위반 가능 → 코드 수정 X, 테스트 추가 ✓" |
| 새 진료과명 보정 추가 | "MEDICAL_CORRECTIONS 패턴 + 테스트 케이스 추가" |
| Docker 재빌드 없이 코드 수정 확인 | "compose restart 우선, build 는 최후" |
| 응급 감지 실패 | "EMERGENCY_KEYWORDS 추가 + 100% 감지 테스트" |

> 📁 코드 위치: `.github/{instructions,prompts,agents}/`, `CLAUDE.md`, `docs/`, `tests/`, `.claude/{settings.json,commands,scripts}/`

---

## ④ AI Tools & Observability — 외부 도구 (가장 바깥)

> "오늘 쓰는 AI 도구. 내일 다른 걸로 갈아끼워도 안쪽 거버넌스는 그대로"

### 개발 단계 AI 도구

| 도구 | 역할 | 교체 가능 대안 |
|---|---|---|
| **Claude Code (CLI/IDE)** | 코드 생성·리팩토링·리뷰 | Cursor, Copilot, Cline, Aider |
| **Claude (Web)** | 설계 토론 | ChatGPT, Gemini |
| **Copilot** | 인라인 자동완성 | Cursor Tab, Codeium, Tabnine |

### 런타임 AI 모델

| 도구 | 역할 | 교체 가능 대안 |
|---|---|---|
| **Whisper-small** | A팀 STT | Naver Clova, OpenAI Whisper API |
| **LLaMA 3.2-3B (Ollama)** | B팀 의도, D팀 답변 | Gemma, Qwen, vLLM 호스팅 모델 |
| **Sentence-Transformers (ko-sroberta)** | C팀 임베딩 | OpenAI text-embedding-3, BGE-M3 |
| **CrossEncoder (ko-reranker)** | C팀 reranker | Cohere Rerank, Jina Reranker |

### 관측·평가 도구

| 도구 | 역할 | 강제하는 정책 |
|---|---|---|
| **LangSmith** | `@traceable` + `evaluate()` 추적 | Faithfulness/Helpfulness/Safety 임계값 |
| **Groq Judge (Llama 3.1 8B)** | 4축 자동 평가 | 출력 품질 |
| **pytest** | 회귀 테스트 | 응급 100%, 금지어 0건 |
| **Docker logs** | 런타임 가시화 | 운영 모니터링 |
| **GitHub Actions** (도입 시) | CI 자동 실행 | 머지 전 게이트 |

### 도구 교체 시나리오 (거버넌스 무결성 검증)

| 교체 | 영향받는 계층 | 안쪽 계층 영향 |
|---|---|---|
| Ollama → vLLM | ④ 만 | 없음 (가치·정책·강제 메커니즘 그대로) |
| LangSmith → Phoenix | ④ 만 | 없음 |
| Claude Code → Cursor | ④ + ③ 일부 (`.claude/` → 다른 형식) | 없음 (가치·정책 그대로) |
| pytest → unittest | ③ 일부 | 없음 |
| **❌ 의료법 준수 완화** | **① 가치 변경** | **전체 시스템 재설계 필요 — 사실상 다른 서비스** |

이 표가 거버넌스 클린 아키텍처의 **테스트** 입니다 — 도구 교체 시 안쪽이 흔들리면 설계가 잘못된 것.

---

## 위협 모델 — 어느 계층이 무엇을 막나

| 위협 시나리오 | 1차 차단 계층 | 메커니즘 |
|---|---|---|
| AI 가 "이건 폐렴입니다" 라고 진단 | ② Policies | `FORBIDDEN_WORDS` 필터 |
| AI 가 응급 발화에 일반 답변 | ② Policies + ③ TDD | `EMERGENCY_KEYWORDS` + 100% 감지 테스트 |
| AI 가 RAG 없이 환각 답변 | ② Policies + ③ Validation | Faithfulness ≥ 0.7 임계값 |
| 개발자가 `rm -rf .` 실수 | ③ Harness | PreToolUse Hook 차단 |
| 개발자가 의료법 위반 코드 머지 | ③ + ① HITL | `/test` + 코드 리뷰 + HITL 7번 체크포인트 |
| API 키 GitHub 공개 | ① 데이터 프라이버시 + ③ `.gitignore` | `.env` 분리 + `.gitignore` |
| LLaMA 출력에 영어 섞임 | ② 한국어 40% 임계값 | 정규식 카운터 + 재생성 |
| 새 LLM 으로 갈아끼웠더니 응급 안내 빠짐 | ③ Validation | `/validate` 7개 항목 — 머지 차단 |

---

## 데이터 흐름 — 거버넌스 관점에서 한 발화의 여정

```
사용자 발화: "할아버지가 갑자기 쓰러졌어요"
   ↓
[ ④ Whisper STT ]
   ↓ text
[ ④ LLaMA 의도 분류 ] ←── ③ B팀 instructions 가 의도 라벨 5종 강제
   ↓ Intent="emergency" (B팀 LLM 출력)
[ ② Emergency Policy ] ──→ EMERGENCY_KEYWORDS 매칭 검증
   ↓                       ───→ 매칭 성공 → 즉시 분기
[ ② Output Policy ]    ──→ "119에 전화해주세요" 포함 강제
   ↓
[ ③ TDD ] ──→ test_응급_키워드_100퍼센트_감지 가 이 흐름을 회귀 방지
   ↓
[ ④ FastAPI Response ]
   ↓
사용자 화면: "지금 119에 전화해 주세요. 의식·호흡 확인하시고..."

  ↑ ① 가치: 환자 안전 우선이 이 모든 단계의 정당화 근거
```

---

## 두 클린아키텍처의 관계 — 같은 코드베이스, 다른 시선

| 측면 | [기능형 (CLEAN_ARCHITECTURE.md)](./CLEAN_ARCHITECTURE.md) | 거버넌스형 (이 문서) |
|---|---|---|
| **질문** | "사용자 발화가 어떻게 답변이 되는가" | "AI 가 어떻게 통제되는가" |
| **중심** | Symptom·Hospital·Intent (도메인 엔티티) | 의료법 준수·환자 안전 (불변 가치) |
| **외곽** | FastAPI·React·ChromaDB (런타임) | Claude Code·LangSmith·pytest (개발·관측) |
| **A/B/C/D 팀** | 각 계층의 부채꼴 분할 | 일부만 등장 (정책·테스트 트리거 위주) |
| **HITL** | 언급 없음 | 7개 체크포인트 명시 |
| **6단계** | 언급 없음 | Layer ③ 의 핵심 |
| **사용처** | 시스템 설계·리팩토링 로드맵 | AI 도구 채택 검토·컴플라이언스 보고 |

두 도식을 **나란히** 보여주면 "기능적으로 무엇을 하는지" + "도덕적·법적으로 어떻게 책임지는지" 가 한 슬라이드에 담깁니다 — AI Native 프로젝트의 기획·심사·논문 발표 시 강력한 조합.

---

## 도식화 가이드

### 동심원 그릴 때 부채꼴 분할 권장

원을 4분면으로 자르되, **이번엔 A/B/C/D 팀이 아닌 6대 가치(① Values 의 항목들)** 로 분할:

```
        의료법 준수    환자 안전(119)
               \   /
                ●           ← 동심원 4겹
               / \
          시니어 친화    HITL
                ↓
          (출처 투명성·프라이버시는 외곽 라벨)
```

각 부채꼴 안에서 그 가치를 강제하는 정책(②) → 메커니즘(③) → 도구(④) 가 차례로 보이도록.

### 색상 가이드 (LG 브랜드 톤)

| 계층 | 색 | 의미 |
|---|---|---|
| ① Values | LG 시그니처 레드 (`#A50034`) | 흔들리지 않는 핵심 |
| ② Policies | 톤 다운 오렌지 (`#E8804D`) | 측정 가능한 규칙 |
| ③ Harness | 신뢰의 파랑 (`#1E5BA8`) | 자동 강제 |
| ④ Tools | 중성 그레이 (`#A0A0A0`) | 교체 가능 |

### 화살표

- **의존성**: 외곽 → 중심 (실선) — Clean Architecture 표준
- **데이터 흐름**: 별도 색 (점선) — 한 발화의 여정 표시
- **HITL 개입**: ③ → 사람 아이콘 (양방향) — 자동화 + 사람 검토 동시 강조

### 라벨 우선순위 (지면 부족 시)

1. ① 6대 가치 이름
2. ② 핵심 정책 3개 (FORBIDDEN_WORDS, EMERGENCY_KEYWORDS, 평가 임계값)
3. ③ AI Native 6단계 이름
4. ④ 도구 로고 (Claude Code, LangSmith, Ollama)

---

## Mermaid 보조 도식

PPT 외 환경(노션/리포트) 용:

```mermaid
graph LR
    subgraph T["④ AI Tools & Observability"]
        T1[Claude Code · Copilot]
        T2[LangSmith · Groq Judge<br/>pytest · Docker]
    end
    subgraph H["③ Specifications & Harness"]
        H1[AI Native 6단계<br/>Instructions·Prompts·Agents<br/>Context·TDD·Validation]
        H2[Hooks · Slash Commands<br/>Session Scripts]
    end
    subgraph P["② Policies & Quality Gates"]
        P1[FORBIDDEN_WORDS<br/>EMERGENCY_KEYWORDS<br/>MEDICAL_CORRECTIONS]
        P2[평가 임계값<br/>Faithfulness ≥ 0.7<br/>Safety = 1.0]
        P3[HITL 체크포인트 7개]
    end
    subgraph V["① Values & Principles"]
        V[의료법 준수 · 환자 안전<br/>시니어 친화 · HITL<br/>출처 투명성 · 프라이버시]
    end

    T --> H
    H --> P
    P --> V
```

---

## 활용 시나리오

1. **임원·심사 발표** — "이 프로젝트는 AI 도구가 아니라 의료법 준수가 중심" 메시지를 한 장으로
2. **컴플라이언스 보고** — 의료기기 인증/병원 도입 심사 시 "어떻게 환자 안전을 보장하는가" 답변
3. **AI 도구 채택 검토** — 새 LLM/IDE 도입 시 "이 도구가 ④ 만 영향 주고 ①~③ 무결성 유지되는가" 판단 기준
4. **신규 팀원 온보딩** — 코드를 보기 전에 "이 프로젝트가 무엇을 절대 양보하지 않는지" 1장으로 전달
5. **회고·사고 분석** — 사고 발생 시 어느 계층이 막았어야 했는지 root cause 추적

---

## 다음 단계 (선택)

- 이 문서 + 기능형 두 동심원을 **나란히 배치한 한 장 슬라이드** 시안
- 위협 시나리오 표를 기반으로 **사고 대응 플레이북** (`docs/incident-playbook.md`)
- ②·③ 의 모든 정책·메커니즘을 한 페이지 체크리스트로 압축한 **거버넌스 1-pager** (`docs/governance-summary.md`)

원하는 쪽 알려주시면 만들어드립니다.
