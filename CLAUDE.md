# LG HelloDoctor — 프로젝트 전체 지침

## 프로젝트 개요
시니어(어르신) 대상 음성 의료 AI 서비스.
사용자가 음성으로 증상을 말하면 AI가 의도를 파악하고 병원 정보·의료 정보를 안내한다.

## 아키텍처 요약

```
사용자 음성
    ↓
[A팀] STT (Whisper + Silero VAD)
    ↓
[B팀] 의도 분류 & 다중턴 (Groq LLM)
    ↓
[C팀] RAG + 병원 검색 + 응급 판단 (ChromaDB + Kakao API)
    ↓
[D팀] 답변 생성 + TTS (Groq LLM + gTTS)
    ↓
프론트엔드 (React + Vite)
```

## 구조

```
LGHelloDoctor/
├── backend/
│   ├── main.py              # FastAPI 서버 (A→B→C→D 통합 파이프라인)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # chat.ts, stt.ts
│   │   ├── components/      # chat/, tv/
│   │   ├── hooks/           # useMedicalChat, useVoiceInput, useWakeWord
│   │   └── types/
│   ├── Dockerfile
│   └── nginx.conf
├── RAG/db/                  # ChromaDB PersistentClient 데이터
├── docker-compose.yml
└── .env                     # API 키 (KAKAO_API_KEY, GROQ_API_KEY)
```

## 환경 변수 (.env)
| 변수 | 용도 | 필수 |
|------|------|------|
| `KAKAO_API_KEY` | 병원 위치 검색 (Kakao Map API) | ✅ |
| `GROQ_API_KEY` | LLM 추론 (llama-3.3-70b-versatile) | ✅ |
| `WHISPER_MODEL_PATH` | Whisper 모델 경로 (기본: openai/whisper-small) | 선택 |
| `DB_PATH` | ChromaDB 경로 (기본: /app/RAG/db) | 선택 |

## Docker 실행
```bash
docker compose up --build   # 최초 빌드 포함
docker compose up -d        # 백그라운드 실행
docker compose logs -f backend  # 로그 확인
```

## 세부 지침 파일
- [백엔드 지침](.github/instructions/backend.instructions.md)
- [프론트엔드 지침](.github/instructions/frontend.instructions.md)
- [RAG 지침](.github/instructions/rag.instructions.md)
