# LG HelloDoctor — TDD 테스트 커버리지 리포트

> **SDLC 단계 3 산출물** — pytest-cov 기반 단위 테스트 커버리지 측정.
> HTML 상세 리포트: [`docs/coverage_html/index.html`](./coverage_html/index.html)

| 항목 | 값 |
|---|---|
| 측정일 | 2026-05-26 |
| 실행 환경 | pytest 9.0.3 · pytest-cov 7.1.0 · Python 3.13.12 |
| 실행 명령 | `python -m pytest tests/test_agent_patterns.py --cov=backend --cov-report=html` |
| 통과 테스트 | **14 / 14** ✅ |
| 실행 시간 | 0.97s |

---

## 모듈별 커버리지

| 모듈 | Statements | Missed | Cover | 비고 |
|---|---:|---:|---:|---|
| `backend/agent_patterns.py` | 147 | 54 | **63%** | 단위 테스트 직접 호출 영역 |
| `backend/main.py` | 362 | 362 | 0% | 통합 환경 필요 (Whisper·Ollama·ChromaDB 로딩) → `/validate`로 검증 |
| **합계** | **509** | **416** | **18%** | (main.py 제외 시 agent_patterns 63%) |

### `backend/agent_patterns.py` 63% 커버 영역

| 검증된 함수/클래스 | 테스트 |
|---|---|
| `AnswerEvaluator.evaluate()` | 5 케이스 (정상/빈/영어/짧음/금지어) |
| `generate_with_evaluator()` | 4 케이스 (1회 통과/재생성/최대 시도/금지어 트리거) |
| `run_c_team_parallel()` | 3 케이스 (병렬 속도/intent 필터 2종) |
| `IntentRouter.route()` | 2 케이스 (등록 핸들러/기본 핸들러) |

### 미커버 영역 (37%)

- `PromptChain`, `ChainStep` — main.py에서 함수형 체인으로 대체 사용 중
- `PipelineOrchestrator` — main.py의 `full_pipeline()` 함수가 동일 역할 수행
- 위 두 클래스는 **참조 구현체**로 유지 (향후 리팩토링 시 활용)

---

## 통합 테스트 커버리지 (별도)

main.py는 단위 테스트로는 검증하기 어려운 무거운 의존성(Whisper STT, Ollama LLaMA, ChromaDB 데이터 로딩, Kakao API)을 포함하여, 통합 환경에서 `/validate` 슬래시 명령으로 검증한다.

| 검증 항목 | 결과 | 측정 위치 |
|---|---|---|
| 환경 변수 설정 | ✅ | `src/todo/manager.py` |
| ChromaDB 문서 수 (≥ 100) | ✅ | 동상 |
| 백엔드 헬스체크 (`GET /`) | ✅ | 동상 |
| 채팅 API 응답 형식 | ✅ | 동상 |
| 응급 감지 정확도 (100%) | ✅ | 동상 |
| 한국어 전용 응답 | ✅ | 동상 |
| 프론트엔드 응답 | ✅ | 동상 |

→ 상세: [`docs/test-report.md`](./test-report.md) (7/7 통과)

---

## 회귀 차단 기준 (Merge Gate)

PR은 다음 조건을 모두 만족해야 머지 가능:

1. **단위 테스트** 14/14 통과 (`test_agent_patterns.py`)
2. **응급 감지** 100% (`test_ai_model.py::test_응급_키워드_100퍼센트_감지`)
3. **금지어** 0건 머지 (`test_ai_model.py::test_금지어_*`)
4. **통합 검증** 7/7 통과 (`/validate`)
5. **HITL 자문 영역** (의사·약사·노년학·법률) 수정 시 자문 검토 첨부 — `PreToolUse` 훅 경고 확인

## 향후 개선 (Backlog)

- [ ] main.py 통합 테스트 컨테이너 환경에 pytest fixture 작성 → 커버리지 측정
- [ ] frontend (React) Jest 커버리지 통합
- [ ] CI 파이프라인에 coverage threshold gate 추가 (agent_patterns ≥ 70%)
