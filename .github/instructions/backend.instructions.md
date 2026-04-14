---
applyTo: "backend/**"
---

# 백엔드 지침 (backend/main.py)

## 개요
FastAPI 기반 의료 AI 서버. 노트북(`pipeline_integrated_최종.ipynb`)을 독립 실행 가능한 서버로 변환한 형태.

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 헬스체크 |
| POST | `/chat` | 텍스트 의료 상담 |
| POST | `/api/stt` | 음성 파일 → 텍스트 변환 |

### /chat 요청/응답
```json
// 요청
{ "text": "머리가 아파요", "session_id": "user-123", "lat": 37.5012, "lng": 127.0396 }

// 응답
{
  "answer": "어르신, 머리가 많이 아프시군요...",
  "intent": "symptom_inquiry",
  "hospitals": [{ "name": "...", "address": "...", "phone": "...", "distance": 300, "navi_url": "..." }],
  "is_emergency": false,
  "ready_for_c": true,
  "session_id": "user-123"
}
```

## 파이프라인 구조

### A팀 — STT
- `stt_pipeline(audio_path)`: Whisper + Silero VAD로 음성 → 텍스트
- `remove_silence()`: VAD로 무음 제거
- `preprocess_text()`: 호출어 제거, 간투어 필터, 의료 용어 보정

### B팀 — 의도 분류 & 다중턴
- `classify_intent(text)`: Groq LLM으로 4가지 의도 분류
  - `symptom_inquiry` / `hospital_search` / `medication_info` / `emergency`
- `extract_entities(text)`: 증상·신체부위 추출
- `chat_with_followup(text, session_id)`: 다중턴 상태 관리
  - `step=1`: 신체부위 파악 → 추가 질문
  - `step=2`: 답변 수집 → C팀으로 전달
- `conversation_state`: 전역 dict (session_id 키)

### C팀 — 도구 활용
- `full_rag_pipeline(query)`: ChromaDB 벡터 검색 (cosine distance ≤ 0.45)
- `search_hospital(symptom, lat, lng)`: Kakao Map API로 반경 3km 병원 검색
- `emergency_check(text)`: 키워드 점수 합산 → HIGH/MEDIUM/LOW 판정
- `tool_router(output_from_B)`: 의도에 따라 RAG/병원검색/응급 분기

### D팀 — 답변 생성
- `generate_answer(query, context, entities)`: Groq LLM으로 시니어 맞춤 답변
- `format_response(raw_answer)`: 금지어 제거, 영어 단어 제거, 문장 수 제한(6문장)
- `generate_tts(text)`: gTTS로 한국어 음성 파일 생성 (임시 mp3)

## 핵심 상수
```python
FOLLOWUP_QUESTIONS  # 신체부위별 추가 질문 사전
MEDICAL_CORRECTIONS # 노인 음성 오류 보정 사전 (50개 이상)
SYMPTOM_DEPT_MAP    # 증상 → 진료과 매핑
EMERGENCY_SCORES    # 응급 키워드별 점수
FORBIDDEN_WORDS     # 의료법상 금지 표현
```

## 모델 로딩 순서 (서버 시작 시)
1. Groq LLM 연결
2. Whisper 모델 로드 (HuggingFace 또는 로컬 경로)
3. Silero VAD 로드 (torch.hub)
4. SentenceTransformer 로드 (`jhgan/ko-sroberta-multitask`)
5. ChromaDB PersistentClient 연결

## 주의사항
- `conversation_state`는 메모리 내 전역 dict — 서버 재시작 시 초기화됨
- Whisper는 CPU 모드로 동작 (CUDA 없는 환경)
- TTS 파일은 임시 경로에 생성되며 요청 후 자동 삭제 안 됨 (운영 시 정리 로직 필요)
- 답변에 영어 단어 혼입 방지: `re.sub(r'\b[a-zA-Z]+\b', '', answer)`

## 의존성 핵심
```
fastapi, uvicorn         # 서버
groq, langchain-groq     # LLM
transformers, torch      # Whisper STT
librosa, soundfile       # 오디오 처리
chromadb==1.5.5          # 벡터DB (로컬 DB 버전과 반드시 일치)
sentence-transformers    # 임베딩
gtts                     # TTS
httpx<0.28.0             # groq 호환성
```
