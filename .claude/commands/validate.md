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
| 4. 컨텍스트 | `docs/PRODUCT.md`, `docs/context-packet.md` | ✅ |
| 5. TDD | `tests/test_*.py` | ✅ |
| 6. 통합 검증 | `src/todo/manager.py` | ✅ |
