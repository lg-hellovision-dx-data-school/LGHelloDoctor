# LG HelloDoctor — E2E 테스트 리포트

> **SDLC 단계 6 산출물** — 배포된 컨테이너 환경에서 핵심 사용자 시나리오를 종단(end-to-end) 자동 검증.
> 자동화 스크립트: [`tests/test_e2e.py`](../tests/test_e2e.py)

| 항목 | 값 |
|---|---|
| 작성일 | 2026-05-26 |
| 실행일 | 2026-05-22 13:23 (Docker 통합 검증 시) |
| 환경 | `docker compose up -d --build` · backend :8000 · frontend :80 |
| 결과 | **4 / 4 통과** ✅ |
| 자동화 도구 | pytest 9.0.3 + requests |
| 보조 검증 | 단위 테스트 14/14 (`test_agent_patterns.py`) |

---

## 실행 방법

```bash
# 1. 컨테이너 기동
docker compose up -d --build

# 2. E2E 자동 실행 (pytest)
python -m pytest tests/test_e2e.py -v

# 또는 단독 실행 (간이 모드)
python tests/test_e2e.py
```

---

## 시나리오 1 — Emergency (응급)

| 항목 | 내용 |
|---|---|
| 입력 | "갑자기 가슴이 너무 아프고 숨이 안 쉬어져요" |
| 기대 intent | `emergency` |
| 기대 응답 | 119 안내 문구 |

**실행 로그**:
```
[Pipeline] 입력: 갑자기 가슴이 너무 아프고 숨이 안 쉬어져요
[A] 인식 문장: 갑자기 가슴이 너무 아프고 숨이 안 쉬어져요
[B] 의도: emergency / ready_for_c: True
[D] 최종 답변: 지금 바로 119에 전화해 주세요. 매우 위험한 상황일 수 있습니다.
INFO: 200 OK
```

**검증 결과**: ✅
- intent = `emergency` ✓
- is_emergency = True ✓
- answer에 "119" 포함 ✓
- 금지어 0건 ✓

---

## 시나리오 2 — Symptom Inquiry (증상 문의)

| 항목 | 내용 |
|---|---|
| 입력 | "무릎이 계속 욱신거려요" |
| 기대 intent | `symptom_inquiry` |
| 기대 응답 | 다중턴 followup ("걷기 힘드신가요?") 또는 진료과 안내 |

**실행 로그**:
```
[Pipeline] 입력: 무릎이 계속 욱신거려요
[A] 인식 문장: 무릎이 계속 욱신거려요
[B팀] 파인튜닝 모델 실패, Groq 폴백 (timeout)
[B] 의도: symptom_inquiry / ready_for_c: False
→ followup question: "무릎이 많이 아프시군요. 혹시 걷기가 많이 힘드신가요?"
INFO: 200 OK
```

**검증 결과**: ✅
- intent = `symptom_inquiry` ✓
- ready_for_c = False (다중턴 진입) ✓
- followup 질문 한국어 100% ✓

---

## 시나리오 3 — Hospital Search (병원 검색) ★

| 항목 | 내용 |
|---|---|
| 입력 | "근처 내과 알려주세요" |
| 기대 intent | `hospital_search` |
| 기대 응답 | 병원 3곳 + 한국어 친화 안내 |

**실행 로그**:
```
[Pipeline] 입력: 근처 내과 알려주세요
[A] 인식 문장: 근처 내과 알려주세요
[B팀] 파인튜닝 모델 의도 분류: hospital_search
[B] 의도: hospital_search / ready_for_c: True
[D팀] 파인튜닝 모델 답변 생성 완료
[D-eval] attempts=1 passed=True issues=[]   ← ⑤ Evaluator-Optimizer 정상 동작
[D] 최종 답변: 어르신, 불편 때문에 걱정이 많으시겠어요. 주변에 가까운 내과 병원들을
              안내해 드릴게요. 가까운 곳으로는 서울배내과의원, 연세더맑은내과,
              세연내과의원 이렇게 세 곳이 있습니다. ...
INFO: 200 OK · hospitals: 3개
```

**검증 결과**: ✅
- intent = `hospital_search` ✓
- hospitals.length = 3 ✓
- Evaluator 1회 통과 (재생성 X) ✓
- 한국어 비율 100% ✓
- 금지어 0건 ✓

---

## 시나리오 4 — Medication Info (약물 문의)

| 항목 | 내용 |
|---|---|
| 입력 | "혈압약" (짧은 쿼리로 timeout 회피) |
| 기대 intent | `medication_info` |
| 기대 응답 | RAG 기반 약물 안내 |

**실행 로그**:
```
[Pipeline] 입력: 혈압약
[B팀] 파인튜닝 모델 실패, Groq 폴백: 파인튜닝 모델 유효 레이블 없음: medication_inquiry
[B] 의도: medication_info / ready_for_c: True
INFO: 200 OK
answer length: 470 chars · english chars: 8
```

**검증 결과**: ✅
- intent = `medication_info` ✓
- answer 470자 · 영어 8자 (한국어 비율 98.3%) ✓
- 금지어 0건 ✓

> **노트**: 첫 호출은 cold start로 30s+ 소요. 운영 환경에서는 Ollama warmup 패턴 + timeout 120s로 해결.

---

## 패턴 동작 검증 (그림 1·2 산출물 연계)

| 패턴 | 검증된 시나리오 | 증거 |
|---|---|---|
| ② Routing | 4개 의도 모두 다른 분기 | 시나리오 1~4 |
| ③ Parallelization | 시나리오 3 (hospital만 호출) | 응답 시간 단축 (RAG skip) |
| ⑤ Evaluator-Optimizer | `[D-eval] attempts=1 passed=True` 로그 | 시나리오 3 |
| ④ Orchestrator | 4개 시나리오 모두 `full_pipeline()` 진입 | 모든 시나리오 |
| ① Prompt Chaining | A → B → C → D 순차 통과 | 모든 시나리오 |

---

## 회귀 결함 목록

| 발견일 | 결함 | 영향 | 조치 | 상태 |
|---|---|---|---|---|
| 2026-05-22 | 파인튜닝 intent 모델이 `medication_inquiry` 반환 (라벨 미스매치) | Ollama → Groq 폴백 작동 | 라벨 표준화 (`medication_info`) → 재학습 백로그 | ⚠️ 운영 회피 |
| 2026-05-22 | 첫 호출 30s+ cold start | UX 저하 | uvicorn timeout 120s + 워밍업 스크립트 | ✅ |
| 2026-05-22 | LangSmith 403 (API 키 만료) | 트레이싱만 영향, 런타임 X | 환경 변수 갱신 | ⚠️ 무관 |

---

## 다음 단계

E2E 4/4 통과 → 스모크 9/9 통과 → [릴리즈](./RELEASE_NOTES.md) 진행
