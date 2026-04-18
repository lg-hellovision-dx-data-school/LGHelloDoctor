# LG HelloDoctor 통합 검증 리포트

> 이 파일은 `python src/todo/manager.py` 실행 시 자동 갱신됩니다.

## 실행 방법
```bash
# Docker 실행 중인 상태에서
python src/todo/manager.py

# 외부 서버 대상
BASE_URL=http://your-server:8000 python src/todo/manager.py
```

## 검증 항목 설명

| 항목 | 설명 |
|------|------|
| 환경 변수 설정 | KAKAO_API_KEY, GROQ_API_KEY 존재 여부 |
| ChromaDB 문서 수 | 의료 지식 문서 100개 이상 유지 여부 |
| 백엔드 서버 응답 | GET / → 200 OK |
| 채팅 API 응답 형식 | POST /chat 필수 필드 포함 여부 |
| 응급 감지 정확도 | "숨이 안 쉬어요" → intent: emergency |
| 한국어 전용 응답 | 답변에 영어 단어 혼입 없음 |
| 프론트엔드 서버 응답 | GET http://localhost:80 → 200 OK |

## 최근 검증 결과

*아직 실행되지 않았습니다. `python src/todo/manager.py`를 실행하세요.*
