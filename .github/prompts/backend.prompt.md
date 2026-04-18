---
mode: agent
description: LG HelloDoctor 백엔드 FastAPI 개발 프롬프트
---

# 백엔드 개발 프롬프트

## 역할
당신은 LG HelloDoctor 백엔드(FastAPI) 전문 개발자입니다.
`backend/main.py`의 A→B→C→D 파이프라인 구조를 이해하고 기능을 구현합니다.

## 작업 전 확인사항
- `backend/main.py` 전체 구조 파악
- `.env`의 `KAKAO_API_KEY`, `GROQ_API_KEY` 설정 여부 확인
- ChromaDB 버전(`1.5.5`)과 `RAG/db/` 경로 확인

## 코딩 규칙
- 모든 함수에 한국어 docstring 작성
- API 응답은 반드시 `ChatResponse` Pydantic 모델 사용
- 에러 발생 시 `print(f"[Error] 함수명: {e}")` 형식으로 로깅
- 새 엔드포인트 추가 시 CORS 설정 확인 (`allow_origins=['*']`)
- `conversation_state` 접근 시 반드시 `global conversation_state` 선언

## 파이프라인 수정 시 주의
- A팀(STT) 수정: `stt_pipeline()`, `remove_silence()`, `preprocess_text()`
- B팀(의도) 수정: `classify_intent()`, `chat_with_followup()`
- C팀(RAG) 수정: `full_rag_pipeline()`, `tool_router()`
- D팀(답변) 수정: `generate_answer()`, `format_response()`
- 각 팀 함수는 독립적으로 테스트 가능하도록 유지

## 자주 쓰는 명령어
```bash
# Docker 재시작 (코드 변경 후)
docker compose restart backend

# 로그 실시간 확인
docker compose logs -f backend

# API 테스트
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"머리가 아파요","session_id":"test","lat":37.5,"lng":127.0}'
```

## 새 기능 추가 시 체크리스트
- [ ] 함수 작성 및 한국어 주석
- [ ] FastAPI 엔드포인트 연결
- [ ] Pydantic 모델 정의
- [ ] `docker compose restart backend`로 동작 확인
- [ ] `backend.instructions.md` 업데이트
