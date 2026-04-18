# LG HelloDoctor — 컨텍스트 패킷

> AI 에이전트가 작업 시작 전 반드시 파악해야 할 핵심 정보 모음

## 현재 시스템 상태

### 실행 환경
- **배포 방식**: Docker Compose (backend + frontend)
- **백엔드 포트**: 8000
- **프론트엔드 포트**: 80
- **디바이스**: CPU 전용 (GPU 없음)

### 데이터 현황
- ChromaDB 문서 수: **132개**
- ChromaDB 버전: **1.5.5** (변경 금지)
- DB 위치: `RAG/db/` (Docker 볼륨 마운트)

### 외부 API
| API | 상태 | 용도 |
|-----|------|------|
| Ollama | 운영 중 | 파인튜닝 LLaMA 3.2-3B 서빙 |
| Kakao Map API | 운영 중 | 병원 검색 |

## 파이프라인 데이터 흐름

```
사용자 입력 (text/audio)
    ↓
[A팀] stt_pipeline()
    - 오디오면 Whisper로 STT
    - 텍스트면 preprocess_text()로 전처리
    ↓
[B팀] chat_with_followup()
    - classify_intent(): emergency / symptom_inquiry / hospital_search / medication_info
    - ready_for_c=False → 추가 질문 반환 (다중턴)
    - ready_for_c=True → output_for_c 생성
    ↓
[C팀] tool_router()
    - full_rag_pipeline(): 벡터 검색
    - search_hospital(): Kakao 병원 검색
    - emergency_check(): 응급 판단
    ↓
    - 파인튜닝 LLaMA 3.2-3B (Ollama)로 시니어 맞춤 답변 생성
    - 금지어·영어 단어 제거
    ↓
ChatResponse 반환
    { answer, intent, hospitals, is_emergency, ready_for_c, session_id }
```

## 핵심 의사결정 기록

| 결정 | 이유 |
|------|------|
| unsloth 파인튜닝 LLaMA 3.2-3B 적용 | Ollama (hellodoctor-intent) 로 D팀 답변 생성에 통합 |
| Whisper small 사용 | 커스텀 모델이 Google Drive에만 존재, 볼륨 마운트로 교체 가능 |
| ChromaDB 1.5.5 고정 | 로컬 DB 생성 버전과 일치 필요 |
| httpx<0.28.0 고정 | 라이브러리 proxies 파라미터 호환성 |
| CPU 전용 빌드 | 현재 환경에 GPU 없음 |

## 알려진 이슈

| 이슈 | 상태 | 해결법 |
|------|------|--------|
| LLM 영어 단어 혼입 | 부분 해결 | 시스템 프롬프트 + 후처리 정규식 |
| 세션 메모리 | 미해결 | 서버 재시작 시 대화 이력 초기화 |

## 환경 변수 현황
```
KAKAO_API_KEY=설정됨
WHISPER_MODEL_PATH=openai/whisper-small (기본값)
DB_PATH=/app/RAG/db (Docker 기본값)
OLLAMA_URL=http://localhost:11434 (기본값)
```
