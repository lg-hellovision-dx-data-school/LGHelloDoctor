---
applyTo: "backend/main.py"
---

# AI 모델 지침 (Groq LLM + Whisper STT + Silero VAD)

## 개요
LG HelloDoctor에서 사용하는 AI 모델 구성.
모든 모델은 서버 시작 시 로드되며, CPU 환경에서 동작한다.

## 사용 모델 목록

| 모델 | 용도 | 로드 방식 |
|------|------|-----------|
| `llama-3.3-70b-versatile` (Groq) | 의도 분류, 엔티티 추출, 답변 생성 | 클라우드 API |
| `openai/whisper-small` | 한국어 음성 → 텍스트 | HuggingFace 자동 다운로드 |
| `snakers4/silero-vad` | 음성 활동 감지 (무음 제거) | torch.hub 자동 다운로드 |
| `jhgan/ko-sroberta-multitask` | 문장 임베딩 (RAG 검색) | HuggingFace 자동 다운로드 |

## Groq LLM

### 초기화
```python
from langchain_groq import ChatGroq

llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
)
```
- `temperature=0`: 일관된 분류 결과를 위해 고정
- 모델명 변경 금지 (API 호환성)

### 사용 함수
- `classify_intent()`: 4가지 의도 분류
- `extract_entities()`: 증상·신체부위 JSON 추출
- `generate_answer()`: 시니어 맞춤 한국어 답변 생성

### 프롬프트 원칙
- 반드시 한국어 전용 명시
- 영어 단어·접속사 사용 금지 문구 포함
- 답변 3~4문장 이내 제한
- Groq 무료 플랜 한도: 분당 30 요청 / 일 14,400 요청

## Whisper STT

### 초기화
```python
from transformers import WhisperForConditionalGeneration, WhisperProcessor

WHISPER_MODEL_PATH = os.environ.get('WHISPER_MODEL_PATH', 'openai/whisper-small')
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

stt_model = WhisperForConditionalGeneration.from_pretrained(WHISPER_MODEL_PATH).to(DEVICE).float()
stt_processor = WhisperProcessor.from_pretrained(WHISPER_MODEL_PATH)
```

### 커스텀 모델 교체 방법
```yaml
# docker-compose.yml
environment:
  - WHISPER_MODEL_PATH=/app/models/whisper-ko-elderly
volumes:
  - ./models:/app/models
```

### STT 파이프라인 흐름
```
오디오 파일
    ↓ remove_silence()  — Silero VAD로 무음 제거
    ↓ librosa.load()    — 16kHz 리샘플링
    ↓ stt_processor()   — 입력 특징 추출
    ↓ stt_model.generate() — 텍스트 생성
    ↓ preprocess_text() — 후처리 (호출어·간투어·용어 보정)
```

## Silero VAD

### 초기화
```python
vad_model, vad_utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
    trust_repo=True,
)
(get_speech_timestamps, *_) = vad_utils
```
- `threshold=0.4`: 음성 감지 민감도 (낮을수록 민감)
- Docker 환경에서 첫 실행 시 자동 다운로드 (캐시: `/root/.cache/torch/hub/`)

## STT 전처리 상수

### MEDICAL_CORRECTIONS (50개 이상)
노인 음성 오인식 패턴을 보정하는 사전.
```python
MEDICAL_CORRECTIONS = {
    "정형외가": "정형외과",
    "무릅": "무릎",
    ...
}
```

### WAKE_WORDS
호출어 목록 — `preprocess_text()`에서 제거됨.
```python
WAKE_WORDS = ['헬로비야', '헬로비이', '헬로 비', '헬로비']
```

### FILLER_PATTERN
간투어 제거 정규식.
```python
FILLER_PATTERN = re.compile(r'(?<!\w)(어+~*|음+~*|에+~*|그+~*|뭐+~*|저+~*|아+~*)(?=\s|$)(?!\w)')
```

## 응답 품질 관리

### FORBIDDEN_WORDS (의료법 준수)
```python
FORBIDDEN_WORDS = ['예후', '처방전', '투약', '병변', '진단', '확정', '완치', '확신', '치료', '부작용']
```

### 영어 단어 제거 (format_response 후처리)
```python
answer = re.sub(r'\b[a-zA-Z]+\b', '', answer)
```

### 답변 길이 제한
- 최대 6문장 (`combined[:6]`)
- 시니어 친화적 어조: "어르신", 존댓말 필수

## 주의사항
- `temperature` 0.5 이상 설정 금지 (분류 일관성 저하)
- LLM 모델명 임의 변경 금지
- `FORBIDDEN_WORDS` 항목 임의 삭제 금지 (의료법)
- TTS(`gTTS`) 생성 실패 시 `None` 반환 — 프론트는 `ttsUrl` 없으면 텍스트만 표시
