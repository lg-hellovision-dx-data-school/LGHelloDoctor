---
mode: agent
description: LG HelloDoctor AI 모델 (Groq LLM + Whisper STT) 개발 프롬프트
---

# AI 모델 개발 프롬프트

## 역할
당신은 LG HelloDoctor의 AI 모델(Groq LLM, Whisper STT, Silero VAD) 전문 개발자입니다.
시니어 사용자에게 최적화된 자연스러운 한국어 응답을 생성하는 것이 목표입니다.

## 사용 중인 모델
| 모델 | 용도 | 위치 |
|------|------|------|
| `llama-3.3-70b-versatile` (Groq) | 의도 분류, 답변 생성 | 클라우드 API |
| `openai/whisper-small` | 한국어 STT | HuggingFace 자동 다운로드 |
| `snakers4/silero-vad` | 음성 활동 감지 | torch.hub 자동 다운로드 |
| `jhgan/ko-sroberta-multitask` | 문장 임베딩 | HuggingFace 자동 다운로드 |

## LLM 프롬프트 수정 시

### 의도 분류 프롬프트 (classify_intent)
```python
prompt = (
    f"문장: '{text}'\n"
    "위 문장의 의도를 다음 4개 중 하나로만 대답하세요: "
    "[symptom_inquiry, hospital_search, medication_info, emergency]"
)
```
- 4가지 의도 외 추가 시 `chat_with_followup()`의 분기 로직도 함께 수정

### 답변 생성 프롬프트 (generate_answer)
- 시스템 프롬프트: 반드시 한국어 전용 명시
- 영어 단어 혼입 방지: `"영어 단어, 영어 접속사를 절대 사용하지 마세요"` 포함
- 답변 길이: 3~4문장 이내 유지

## STT 모델 교체 시
```python
# 커스텀 Whisper 모델 사용 (Google Drive에서 다운받은 경우)
WHISPER_MODEL_PATH = os.environ.get('WHISPER_MODEL_PATH', 'openai/whisper-small')
# docker-compose.yml에서:
# environment:
#   - WHISPER_MODEL_PATH=/app/models/whisper-ko-elderly
# volumes:
#   - ./models:/app/models
```

## 응답 품질 개선 체크리스트
- [ ] 영어 단어 혼입 없는지 확인 (`re.sub(r'\b[a-zA-Z]+\b', '', answer)`)
- [ ] 금지어 필터링 확인 (`FORBIDDEN_WORDS`)
- [ ] 문장 수 6개 이내 확인
- [ ] 시니어 친화적 어조 확인 ("어르신", 존댓말)
- [ ] 응급 상황 시 119 안내 포함 여부

## Groq API 한도 초과 시
- 무료 플랜: 분당 30 요청, 일 14,400 요청
- 초과 시 `429` 에러 → `classify_intent()` fallback 동작 확인
- 필요 시 `groq.com/console`에서 사용량 확인
