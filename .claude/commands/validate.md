# /validate — 통합 검증

배포 전 전체 파이프라인 유효성을 검사합니다.

## 실행

```bash
python src/todo/manager.py
```

## 검증 체크리스트

### 1. 환경 확인
```bash
test -f .env && grep -q "KAKAO_API_KEY" .env && grep -q "GROQ_API_KEY" .env
```

### 2. 백엔드 헬스체크
```bash
curl -s http://localhost:8000/ | python -m json.tool
```

### 3. 채팅 API 엔드-투-엔드 테스트
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "무릎이 아파요", "session_id": "validate-test", "lat": 37.5012, "lng": 127.0396}' \
  | python -m json.tool
```

### 4. 응답 품질 검증 항목
- [ ] `answer` 필드 존재 및 한국어
- [ ] `intent` 필드: symptom_inquiry / hospital_search / medication_info / emergency
- [ ] `ready_for_c` 필드: boolean
- [ ] `session_id` 필드 에코
- [ ] 응답에 영어 단어 없음
- [ ] 응답에 금지어(진단/치료/완치 등) 없음

### 5. 프론트엔드 확인
```bash
curl -s http://localhost:80 | grep -o '<title>[^<]*</title>'
```

## AI Native Engineering 6단계 검증
| 단계 | 파일 | 상태 |
|------|------|------|
| 1. 지침 | `.github/instructions/*.instructions.md` | ✅ |
| 2. 프롬프트 | `.github/prompts/*.prompt.md` | ✅ |
| 3. 에이전트 | `.github/agents/*.agent.md` | ✅ |
| 4. 컨텍스트 | `docs/PRODUCT.md`, `docs/context-packet.md`, `CLAUDE.md` | ✅ |
| 5. TDD | `tests/test_*.py` | ✅ |
| 6. 통합 검증 | `src/todo/manager.py` | ✅ |

## HITL 3-Tier 거버넌스 게이트 (배포 전 필수)

📋 상세: [`docs/HITL_3TIER.md`](../../docs/HITL_3TIER.md)

### Tier ① 도메인 자문단 (4 역할)

| # | 체크포인트 | 1차 책임자 | 자동 검증 | MVP 상태 |
|---|---|---|---|---|
| 1 | `EMERGENCY_KEYWORDS` 큐레이션 | 🚨 의사 (응급의학) | `test_응급_키워드_100퍼센트_감지` | ⚠️ KDCA 자료 + 자동테스트로 갈음 |
| 2 | `FORBIDDEN_WORDS` 의료법 검토 | ⚖️ 법률·컴플라이언스 | `test_금지어_*` | ⚠️ 면책조항 + 자동필터로 갈음 |
| 3 | `medication_inquiry` 약물 답변 | 💊 약사 | (수동 샘플) | ⚠️ DUR 가이드 인용으로 갈음 |
| 4 | 시니어 친화 어조·UI | 👴 노년학·시니어 UX | `test_한국어_중심_응답` + 베타 | ⚠️ 한국어 40% 임계값으로 갈음 |

### Tier ② 개발팀 (자동화)

```bash
# 5. 전체 회귀 테스트
python -m pytest tests/ -v

# 6. 위험 명령 차단 훅 동작 확인
test -f .claude/settings.json && grep -q "rm -rf\|drop table\|force-push" .claude/settings.json

# 7. HITL 트리거 훅 동작 확인
test -f .claude/settings.json && grep -q "EMERGENCY_KEYWORDS\|FORBIDDEN_WORDS\|MEDICAL_CORRECTIONS" .claude/settings.json
```

### Tier ③ 시니어 사용자 베타 (수동)

- [ ] 사내 50대+ 5명 이상 사용 후 이해도/UX 인터뷰 완료
- [ ] 음성 인식률 ≥ 90% (방언/사투리 포함)
- [ ] 호출어("헬로비") 인식률 ≥ 95%

## 게이트 통과 기준

| 단계 | 통과 조건 |
|---|---|
| **MVP 배포** | 1~5 항목 (자동 검증 + 회귀 테스트) 통과 + Tier① 4항목 *완화 장치* 명시 |
| **베타 출시** | 위 + Tier③ 시니어 베타 5명 인터뷰 완료 |
| **정식 출시** | 위 + Tier① 4 자문단 위촉 + 자문 결과서 첨부 |

## 검증 결과 기록

검증 실행 후 [`docs/test-report.md`](../../docs/test-report.md) 의 `HITL 자문 검토 이력` 섹션에
다음 형식으로 추가:

```
[YYYY-MM-DD] /validate 실행
- 자동 검증: 6/7 통과 (환경변수 X)
- HITL Tier①: MVP 완화 장치 적용 (자문단 미배치)
- HITL Tier②: 회귀 테스트 100% / 훅 동작 확인 ✅
- HITL Tier③: 미실시 (베타 단계 진입 전)
- 게이트: MVP 배포 가능 / 베타 출시 불가
```
