# Spec Kit — LG HelloDoctor 적용 가이드

> **GitHub Spec Kit (spec-driven development)** 을 본 프로젝트에 통합한 결과 정리.
> 설치일: 2026-05-27 · 버전: specify-cli 0.8.15.dev0

---

## 설치된 자산

```
.claude/skills/                      ← Claude Code 슬래시 스킬 9개
   ├── speckit-constitution/         /speckit-constitution  ← 원칙 수립
   ├── speckit-specify/              /speckit-specify       ← 스펙 작성
   ├── speckit-plan/                 /speckit-plan          ← 구현 계획
   ├── speckit-tasks/                /speckit-tasks         ← Task 분해
   ├── speckit-implement/            /speckit-implement     ← 구현 실행
   ├── speckit-clarify/              /speckit-clarify       (선택) 모호점 질문
   ├── speckit-analyze/              /speckit-analyze       (선택) 일관성 검증
   ├── speckit-checklist/            /speckit-checklist     (선택) 품질 체크리스트
   └── speckit-taskstoissues/        /speckit-taskstoissues (선택) GitHub 이슈화

.specify/                            ← Spec Kit 워크스페이스
   ├── memory/constitution.md        ← 프로젝트 헌법 (헬로닥터용)
   ├── templates/
   │   ├── constitution-template.md  Constitution 작성 템플릿
   │   ├── spec-template.md          Specification 작성 템플릿
   │   ├── plan-template.md          Plan 작성 템플릿
   │   ├── tasks-template.md         Tasks 작성 템플릿
   │   └── checklist-template.md     Checklist 작성 템플릿
   ├── scripts/                      자동화 셸 스크립트
   └── workflows/speckit/            워크플로 정의

CLAUDE.md                            ← 끝에 <!-- SPECKIT START/END --> 마커 추가
```

---

## 5단계 Spec-Driven Development 워크플로

```
/speckit-constitution    →  /speckit-specify  →  /speckit-plan  →  /speckit-tasks  →  /speckit-implement
   (원칙 수립)               (요구사항 정의)        (기술 계획)         (Task 분해)        (구현 실행)
```

각 단계는 이전 단계의 산출물을 입력으로 받아 다음 산출물을 생성한다. 모든 산출물은 `.specify/` 또는 사양에 따라 프로젝트 루트에 저장된다.

---

## 우리 기존 SDLC 7단계와의 매핑

본 프로젝트는 이미 SDLC 7단계를 자체 구축했다 ([`SDLC_DELIVERABLES.md`](./SDLC_DELIVERABLES.md)). Spec Kit과의 관계:

| 우리 SDLC 단계 | 우리 산출물 | Spec Kit 대응 명령 | 통합 방식 |
|---|---|---|---|
| 1. PRD | `docs/PRODUCT.md`, `docs/requirements.md` | `/speckit-specify` | 기존 PRD를 spec-template.md에 맞춰 정리하거나, 신규 기능부터 `/speckit-specify` 적용 |
| 2. Task 분해 | `docs/backlog.md`, TaskCreate | `/speckit-tasks` | 신규 기능은 `/speckit-tasks` 로 자동 생성 → backlog.md 갱신 |
| 3. TDD | `tests/test_*.py`, `coverage_report.md` | `/speckit-implement` (TDD 모드) | Spec Kit이 자동으로 단위 테스트 → 구현 순서 강제 |
| 4. 통합 | `/validate` 7항목 | `/speckit-analyze` | 사양·계획·태스크 간 일관성 자동 검증 |
| 5. 스모크 | `docs/smoke_test.md` | (기존 유지) | Spec Kit 외 영역 |
| 6. E2E | `tests/test_e2e.py` | `/speckit-checklist` | 품질 체크리스트로 보강 가능 |
| 7. 배포 | `RELEASE_NOTES.md`, `RETROSPECTIVE.md` | (기존 유지) | Spec Kit 외 영역 |
| **거버넌스** | `HITL_3TIER.md`, CLAUDE.md | `/speckit-constitution` | **프로젝트 헌법으로 통합** |

### 핵심 인사이트

- **Spec Kit = 단계 1·2·3·4의 자동화 도구**: 우리는 이미 수동으로 만들었지만, *신규 기능*은 Spec Kit으로 더 빠르게 생성 가능
- **거버넌스(HITL 3-Tier)는 `/speckit-constitution` 으로 격상**: 기존 정책 매트릭스를 헌법 형태로 재정리하면 모든 후속 사양·계획이 거버넌스 원칙을 자동 참조
- **단계 5·6·7은 Spec Kit 미적용 영역**: 우리 기존 산출물 그대로 유지

---

## 권장 사용 시나리오

### 시나리오 A: 신규 기능 추가 (예: 약물 상호작용 검사)

```
1. /speckit-clarify           ← 모호점 먼저 질문 받기
2. /speckit-specify           ← 약물 상호작용 기능 사양 정의
3. /speckit-plan              ← 기술 스택·구현 계획 (Ollama·약물 DB 등)
4. /speckit-checklist         ← 의료 안전성 체크리스트 생성
5. /speckit-tasks             ← Task 분해 → backlog.md에 추가
6. /speckit-analyze           ← 사양·계획·태스크 일관성 검증
7. /speckit-implement         ← TDD 모드로 구현 실행
```

### 시나리오 B: 기존 코드를 헌법으로 정리

```
1. /speckit-constitution      ← 기존 CLAUDE.md + HITL_3TIER.md를 헌법화
                                 → .specify/memory/constitution.md 생성
2. 헌법 검토 → HITL 자문단 사항 명시
3. 이후 모든 /speckit-* 명령이 헌법 자동 참조
```

### 시나리오 C: 사양 후처리 (배포 직전 검증)

```
1. /speckit-analyze           ← 사양·계획·태스크 간 모순 자동 탐지
2. /speckit-checklist         ← 출시 게이트 체크리스트
3. (기존) /validate           ← 통합 검증 7/7
```

---

## 기존 구조와의 충돌 점검

| 기존 자산 | Spec Kit 자산 | 충돌 여부 | 해결 |
|---|---|---|---|
| `.claude/commands/{deploy,test,validate}.md` | `.claude/skills/speckit-*` | ❌ 다른 영역 (커맨드 vs 스킬) | 공존 가능 |
| `.github/instructions/` | `.specify/templates/` | ❌ 다른 목적 (모듈별 지침 vs 사양 템플릿) | 공존 |
| `docs/backlog.md` | `/speckit-tasks` 산출물 | ⚠️ 중복 가능 | 신규 기능은 Spec Kit, 기존 백로그는 유지 |
| `CLAUDE.md` | `.specify/memory/constitution.md` | ⚠️ 중복 가능 | 헌법은 거버넌스 원칙만, CLAUDE.md는 전체 컨텍스트 |

---

## 다음 단계 제안

1. **`/speckit-constitution` 한 번 실행**해서 HITL 거버넌스·5패턴 적용·금지어/응급 정책을 헌법으로 정리 → 모든 후속 명령이 자동 참조
2. **다음 신규 기능 (예: 약물 상호작용)** 부터 Spec Kit 워크플로 적용 → 실제 효용 체감
3. **`docs/SDLC_DELIVERABLES.md`** 에 Spec Kit 적용 결과를 *"단계 1·2·3·4 자동화 도구로 Spec Kit 통합"* 으로 한 줄 추가

---

## 참고

- Spec Kit 저장소: https://github.com/github/spec-kit
- 본 프로젝트 SDLC 인덱스: [`SDLC_DELIVERABLES.md`](./SDLC_DELIVERABLES.md)
- 본 프로젝트 거버넌스: [`HITL_3TIER.md`](./HITL_3TIER.md)
