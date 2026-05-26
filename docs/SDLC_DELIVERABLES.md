# LG HelloDoctor — SDLC 7단계 산출물 인덱스

> **포트폴리오 한 페이지 요약** — 표준 SDLC 7단계 (PRD → Task 분해 → TDD → 통합 → 스모크 → E2E → 배포) 각 단계의 산출물·형태·실제 파일을 매핑.

---

| 단계 | 주요 산출물 | 형태 | 실제 파일 / 명령 |
|---|---|---|---|
| **1. PRD**<br/>(Product Requirements) | 기능·비기능 요구사항 · 완료 조건(DoD) · 범위 정의 | 문서 | [`docs/PRODUCT.md`](./PRODUCT.md)<br/>[`docs/requirements.md`](./requirements.md)<br/>[`docs/context-packet.md`](./context-packet.md) |
| **2. Task 분해**<br/>(Backlog Decomposition) | Task 목록 (백로그) · 인수 조건(AC) · 테스트 전략 · 실행 순서·일정 | 문서 + 티켓 | [`docs/backlog.md`](./backlog.md)<br/>[`.github/instructions/`](../.github/instructions/) (4)<br/>[`.github/agents/`](../.github/agents/) (8)<br/>TaskCreate / TaskList (세션 내) |
| **3. TDD 단위테스트**<br/>(Unit Test) | 단위 테스트 코드 · 구현 코드 · 리팩터링된 소스 · 테스트 커버리지 리포트 | 코드 + 리포트 | [`tests/test_*.py`](../tests/) (6)<br/>[`backend/agent_patterns.py`](../backend/agent_patterns.py)<br/>[`docs/coverage_report.md`](./coverage_report.md)<br/>`python -m pytest --cov=backend` |
| **4. 통합 테스트**<br/>(Integration Test) | 통합 테스트 코드 · API · DB 연동 검증 결과 · 결함 리포트 | 코드 + 리포트 | [`src/todo/manager.py`](../src/todo/manager.py)<br/>[`docs/test-report.md`](./test-report.md) — **7 / 7 통과**<br/>[`.claude/commands/validate.md`](../.claude/commands/validate.md)<br/>`/validate` 슬래시 |
| **5. 스모크 테스트**<br/>(Smoke Test) | 핵심 경로 체크리스트 · 스테이징 배포 확인 결과 · 롤백 판단 기록 | 체크리스트 + 로그 | [`docs/smoke_test.md`](./smoke_test.md) — **9 / 9 통과**<br/>`docker compose ps` + 체크리스트 실행 |
| **6. E2E 테스트**<br/>(End-to-End Test) | E2E 시나리오 스크립트 · 실행 결과 리포트 · 스크린샷·영상 · 회귀 결함 목록 | 코드 + 리포트 | [`tests/test_e2e.py`](../tests/test_e2e.py)<br/>[`docs/e2e_test_report.md`](./e2e_test_report.md) — **4 / 4 통과**<br/>`python -m pytest tests/test_e2e.py` |
| **7. 배포 완료**<br/>(Release) | 릴리즈 노트 · 배포 로그 · 모니터링 대시보드 · 회고 문서 | 문서 + 로그 | [`docs/RELEASE_NOTES.md`](./RELEASE_NOTES.md) — v1.0.0<br/>[`docs/RETROSPECTIVE.md`](./RETROSPECTIVE.md)<br/>`docker-compose.yml` + LangSmith Web |

---

## 자동화 도구 (Claude Code 하네스)

| 도구 | 역할 | 연계 단계 |
|---|---|---|
| **TaskCreate / TaskList** | 세션 내 Task 추적 (in_progress → completed) | 단계 2 |
| **`/test`** ([`.claude/commands/test.md`](../.claude/commands/test.md)) | pytest 전체 스위트 실행 | 단계 3 |
| **`/validate`** ([`.claude/commands/validate.md`](../.claude/commands/validate.md)) | 7항목 통합 검증 | 단계 4 |
| **`/deploy`** ([`.claude/commands/deploy.md`](../.claude/commands/deploy.md)) | Docker 배포 자동화 | 단계 5·7 |
| **PreToolUse 훅** ([`.claude/settings.json`](../.claude/settings.json)) | 위험 명령 차단 · HITL 자문 경고 | 전 단계 |
| **PostToolUse 훅** | 편집 후 알림 · 테스트 권고 | 단계 3 |
| **SessionStart 훅** ([`.claude/scripts/session-start.sh`](../.claude/scripts/session-start.sh)) | 추적 중인 지침 파일 자동 요약 | 단계 1·2 |

## HITL 3-Tier 거버넌스 (단계 전체 관통)

7개 체크포인트가 SDLC 모든 단계에 침투:

| # | 체크포인트 | 1차 책임자 | 관련 단계 |
|---|---|---|---|
| 1 | 위험 명령어 차단 | 개발팀 | 전 단계 (자동) |
| 2 | 배포 전 통합 검증 | 개발팀 | 단계 4·5·7 |
| 3 | 테스트 결과 검토 | 개발팀 | 단계 3·6 |
| 4 | 응급 키워드 큐레이션 | 의사 (응급의학) | 단계 1·2 |
| 5 | 금지어 목록 관리 | 법률·컴플라이언스 | 단계 1·2 |
| 6 | 약물 답변 검수 | 약사 | 단계 3·6 |
| 7 | 시니어 친화 검증 | 노년학 + 시니어 베타 | 단계 6·7 |

→ 상세: [`docs/HITL_3TIER.md`](./HITL_3TIER.md)

---

## 정량 성과 (v1.0.0 기준)

| SDLC 단계 | 지표 | 값 |
|---|---|---|
| 1. PRD | 요구사항 정의 문서 | 3개 |
| 2. Task 분해 | 백로그 Task | **22개** (4팀 + Infra) |
| 3. TDD | 단위 테스트 | **14 / 14 통과** · 커버리지 63% (agent_patterns) |
| 4. 통합 | `/validate` | **7 / 7 통과** |
| 5. 스모크 | 핵심 경로 | **9 / 9 통과** |
| 6. E2E | 의도 시나리오 | **4 / 4 통과** |
| 7. 배포 | git 추적 자산 | **26 문서 · 6 테스트 · 24 지침/에이전트** |

---

## 시각 자료

| 다이어그램 | 파일 |
|---|---|
| 시스템 아키텍처 (3분할: Input·System·Output) | [`docs/system_architecture.drawio`](./system_architecture.drawio) |
| HITL 3-Tier 거버넌스 | [`docs/hitl_governance.drawio`](./hitl_governance.drawio) |
| SDLC 프로세스 (7-stage 컬러풀) | [`docs/sdlc_process.drawio`](./sdlc_process.drawio) |
| RAG V1~V6 정확도 비교 막대그래프 | [`docs/fig4_rag_comparison.png`](./fig4_rag_comparison.png) |

---

> **포트폴리오 메시지**: 본 프로젝트는 *"어쩌다 동작하는 데모"* 가 아니라 **SDLC 7단계 전 과정을 산출물로 증명하는** 엔지니어링 결과물이다. 각 단계의 코드·문서·리포트·로그가 git에 추적되며, Claude Code 하네스가 자동화·HITL 거버넌스를 단계 전체에 침투시킨다.
