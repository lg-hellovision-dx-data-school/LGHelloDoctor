# LG HelloDoctor — AI Native 거버넌스 적용 증거 (1-pager)

발표·심사·논문에서 *"AI 가 도구가 아니라 체계로 통제됨"* 을 한 장으로 보여주는 슬라이드 컨텐츠.

---

## 한 줄 메시지

> **"AI 단독 결정 0건 — 3-Tier × 6 역할 × 7 체크포인트로 의료 도메인 책임을 코드·테스트·훅·PR 절차에 내장"**

---

## 슬라이드 구성안 (3 박스 + HITL 4번째 박스)

### 박스 1 — Prompt Engineering

| 자산 | 수 | 위치 |
|---|---|---|
| 작업 프롬프트 | 4 | `.github/prompts/{backend,frontend,rag,ai-model}.prompt.md` |
| 런타임 시스템 프롬프트 | 4 (A·B·C·D 팀) | `backend/main.py` |
| Judge 프롬프트 | 4 축 | `finetune/rag_evaluation.ipynb` |
| Few-shot 예시 | 4 패턴 | `CLAUDE.md` |

**메트릭**: **12 운영 프롬프트 / 4축 Judge 평가**

---

### 박스 2 — Context Engineering

| 자산 | 수 | 위치 |
|---|---|---|
| 프로젝트 헌법 | 1 | `CLAUDE.md` |
| 모듈별 지침 | 4 | `.github/instructions/*.instructions.md` |
| 에이전트 (페르소나·TDD) | 8 | `.github/agents/*.agent.md` |
| 도메인 컨텍스트 | 8 | `docs/{PRODUCT,context-packet,requirements,diagrams,test-report,CLEAN_ARCHITECTURE,CLEAN_ARCHITECTURE_GOVERNANCE,HITL_3TIER}.md` |
| 커스텀 명령어 | 3 | `.claude/commands/{deploy,test,validate}.md` |

**메트릭**: **24 git 추적 컨텍스트 파일 / 매 세션 자동 로드** (SessionStart 훅)

---

### 박스 3 — Harness Engineering

| 자산 | 수 | 위치 |
|---|---|---|
| 자동 차단 훅 | 2 | `.claude/settings.json` PreToolUse (위험명령·HITL 트리거) |
| 자동 안내 훅 | 1 + 1 | SessionStart + PostToolUse |
| 슬래시 명령 | 3 | `/deploy`, `/test`, `/validate` |
| TDD 회귀 차단 | 4 클래스 | `tests/test_ai_model.py` |
| PR 게이트 | 1 | `.github/PULL_REQUEST_TEMPLATE.md` |

**메트릭**: **응급 100% 감지 / 금지어 0건 / 위험명령 0건 머지**

---

### 박스 4 — Human-in-the-Loop (HITL) ★ 핵심

```
👥  3-Tier 거버넌스

✓ 도메인 자문단 (4 역할)
  의사(응급의학·일반의) · 약사 · 노년학·시니어UX · 법률·컴플라이언스

✓ 개발팀
  PR · /test · /validate · 위험명령 차단

✓ 시니어 사용자 베타
  이해도 · UX 피드백
```

**메트릭**: **6 역할 / 7 체크포인트 / AI 단독 결정 0건**

---

## 적용 증거 (코드·문서 흔적)

발표 시 *"이게 슬로건이 아니라 코드에 박혀있다"* 를 보여주는 8개 변경 흔적:

| # | 파일 | 무엇이 들어갔나 |
|---|---|---|
| 1 | `CLAUDE.md` | HITL 3-Tier 매트릭스 (7 체크포인트 × 1차 책임자) |
| 2 | `docs/CLEAN_ARCHITECTURE_GOVERNANCE.md` | 동심원 거버넌스 + 위협 모델 + HITL 다이어그램 |
| 3 | `docs/HITL_3TIER.md` | 자문단 운영 매뉴얼 (역할별·주기별·MVP→정식 마일스톤) |
| 4 | `backend/main.py` | 4개 상수 (`EMERGENCY_KEYWORDS`/`FORBIDDEN_WORDS`/`MEDICAL_CORRECTIONS`/`EMERGENCY_SCORES`)에 1차 책임자 docstring |
| 5 | `tests/test_ai_model.py` | 4개 테스트 클래스에 책임자 매핑 |
| 6 | `.claude/settings.json` | PreToolUse 훅 — `EMERGENCY_*`/`FORBIDDEN_*`/`MEDICAL_CORRECTIONS` 수정 시 자동 경고 |
| 7 | `.github/PULL_REQUEST_TEMPLATE.md` | PR 마다 자동 표시되는 HITL 자문 체크리스트 |
| 8 | `.claude/commands/validate.md` | 배포 게이트에 HITL Tier① / Tier② / Tier③ 통과 기준 명시 |
| 9 | `docs/test-report.md` | HITL 검토 이력 로그 (자동 검증 + 자문 검토) |

---

## 발표 대본 (60초 분량)

```
[0~10초] 슬라이드 좌측 터미널 보여주며
"git ls-files 결과, 24개 파일이 우리의 AI Native 자산입니다.
 단순한 문서가 아니라 매 세션에 자동 로드되는 *작동하는* 거버넌스입니다."

[10~25초] 박스 1·2·3 순서대로 클릭
"Prompt 12개로 AI 행동을 명세하고,
 Context 24 파일로 도메인 맥락을 주입하고,
 Harness 로 자동 차단·검증합니다."

[25~50초] 박스 4 (HITL) 강조
"하지만 핵심은 4번째 박스 — AI 단독 결정 0건.
 의사·약사·노년학·법률 4 자문단이 7 체크포인트를 책임지고,
 개발팀이 자동화하고, 시니어 사용자가 검증합니다.
 backend/main.py 의 응급 키워드 한 줄이라도 수정되면
 자동으로 '의사 자문 필요' 경고가 뜨고
 PR 템플릿이 자가 신고를 강제합니다."

[50~60초] 마무리
"AI Native 는 도구를 잘 쓰는 게 아니라 도구가 가치를 침범하지 못하게 하는 체계입니다."
```

---

## 한 슬라이드 레이아웃 권장

```
┌────────────────────────────────────────────────────────────────────────┐
│  LG HelloDoctor  AI-Native 개발 체계                Team Leader 안주연  │
│  시니어를 위한 음성 입력 기반 의료 안내 AI 에이전트                    │
├──────────────────┬─────────────────────────────────────────────────────┤
│                  │  ┌──────────────┐  ┌──────────────┐                 │
│   터미널         │  │  Prompt      │  │  Context     │                 │
│   git ls-files   │  │  Engineering │  │  Engineering │                 │
│   24 파일 출력   │  │              │  │              │                 │
│                  │  │  12 prompts  │  │  24 files    │                 │
│                  │  │  4축 Judge   │  │  자동 로드   │                 │
│                  │  └──────────────┘  └──────────────┘                 │
│                  │  ┌──────────────┐  ┌──────────────┐                 │
│                  │  │  Harness     │  │  HITL ★      │                 │
│                  │  │  Engineering │  │  3-Tier      │                 │
│                  │  │              │  │              │                 │
│                  │  │  훅·명령·TDD │  │  6 역할      │                 │
│                  │  │  응급 100%   │  │  AI 단독 0건 │                 │
│                  │  └──────────────┘  └──────────────┘                 │
└──────────────────┴─────────────────────────────────────────────────────┘
```

→ 4 박스 균등 분할, **HITL 박스에 ★ 마크 + 살짝 더 진한 색** 으로 강조.

---

## 부록 — 숫자만 모아보기 (슬라이드 메트릭 영역에 큰 폰트로)

| 자산 | 수치 |
|---|---|
| AI Native 자산 파일 | **24** |
| 운영 프롬프트 | **12** |
| Judge 평가 축 | **4** |
| HITL 역할 | **6** |
| HITL 체크포인트 | **7** |
| 자동 강제 훅 | **5** (PreTool 2 + PostTool 2 + SessionStart 1) |
| 슬래시 명령 | **3** |
| TDD 회귀 차단 | **응급 100% / 금지어 0건** |
| AI 단독 결정 | **0 건** |

---

## 관련 문서

- [`CLAUDE.md`](../CLAUDE.md) — 프로젝트 헌법
- [`docs/CLEAN_ARCHITECTURE.md`](./CLEAN_ARCHITECTURE.md) — 기능 동심원
- [`docs/CLEAN_ARCHITECTURE_GOVERNANCE.md`](./CLEAN_ARCHITECTURE_GOVERNANCE.md) — 거버넌스 동심원
- [`docs/HITL_3TIER.md`](./HITL_3TIER.md) — 자문단 운영 매뉴얼
- [`docs/test-report.md`](./test-report.md) — 검증 결과 + HITL 검토 이력
