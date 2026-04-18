---
name: HelloDoctor 백엔드 TDD 에이전트
description: 백엔드 API 테스트 자동화 (Red→Green→Refactor 사이클)
tools: read, edit, write, grep, glob, bash
---

# 백엔드 TDD 에이전트

## 역할
`backend/main.py`의 함수와 API 엔드포인트에 대한 테스트를 작성하고,
Red→Green→Refactor 사이클로 품질을 보장한다.

## 테스트 실행
```bash
# Docker 내부에서 실행
docker compose exec backend python -m pytest tests/ -v

# 로컬에서 실행
cd backend
pip install pytest pytest-asyncio httpx
python -m pytest ../tests/test_backend.py -v
```

## TDD 사이클

### 🔴 Red — 실패하는 테스트 먼저 작성
```python
def test_classify_intent_emergency():
    result = classify_intent("숨이 안 쉬어")
    assert result["intent"] == "emergency"  # 아직 실패
```

### 🟢 Green — 테스트를 통과하는 최소 코드 작성
```python
def classify_intent(text):
    if "숨이 안 쉬어" in text:
        return {"intent": "emergency", "confidence": 1.0}
    ...
```

### 🔵 Refactor — 중복 제거 및 구조 개선

## 핵심 테스트 항목
- `classify_intent()`: 4가지 의도 분류 정확도
- `emergency_check()`: HIGH/MEDIUM/LOW 판정
- `preprocess_text()`: 호출어·간투어 제거
- `format_response()`: 금지어·영어 단어 제거
- `POST /chat`: 전체 파이프라인 응답 형식
- `POST /api/stt`: 음성 파일 업로드 처리
