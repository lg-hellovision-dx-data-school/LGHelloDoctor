# LG HelloDoctor — 아키텍처 다이어그램

## 목차
1. [클래스 다이어그램](#클래스-다이어그램)
   - [FastAPI 스키마](#1-fastapi-스키마)
   - [A팀 STT 모듈](#2-a팀-stt-모듈)
   - [B팀 의도 분류 모듈](#3-b팀-의도-분류-모듈)
   - [C팀 RAG-병원검색 모듈](#4-c팀-rag--병원검색-모듈)
   - [D팀 응답생성 모듈](#5-d팀-응답생성-모듈)
2. [시퀀스 다이어그램](#시퀀스-다이어그램)
   - [전체 채팅 파이프라인](#1-전체-채팅-파이프라인-a→b→c→d)
   - [STT 처리 흐름](#2-stt-처리-흐름)
   - [응급 감지 분기 흐름](#3-응급-감지-분기-흐름)

---

## 클래스 다이어그램

### 1. FastAPI 스키마

```mermaid
classDiagram
    class ChatRequest {
        +str text
        +str session_id
        +float lat
        +float lng
    }

    class ChatResponse {
        +str answer
        +str intent
        +Optional~list~ hospitals
        +bool is_emergency
        +bool ready_for_c
        +str session_id
    }

    class STTResponse {
        +str text
        +str raw_text
        +str status
    }

    class FullPipeline {
        +full_pipeline(raw_text, session_id, lat, lng) dict
    }

    ChatRequest --> FullPipeline : 입력 전달
    FullPipeline --> ChatResponse : POST /chat 응답 조립
    ChatRequest --> STTResponse : POST /api/stt
```

---

### 2. A팀 STT 모듈

```mermaid
classDiagram
    class SileroVAD {
        +threshold : 0.4
        +remove_silence(audio_path) str
    }

    class WhisperSTT {
        +WHISPER_MODEL_PATH : str
        +DEVICE : str
        +SAMPLE_RATE : 16000
        +stt_pipeline(audio_path, raw_text, confidence) dict
    }

    class STTPreprocessor {
        +WAKE_WORDS : list
        +FILLER_PATTERN : Pattern
        +MEDICAL_CORRECTIONS : dict~50개~
        +preprocess_text(raw_text) str
    }

    WhisperSTT --> SileroVAD : 무음 제거
    WhisperSTT --> STTPreprocessor : 후처리
```

---

### 3. B팀 의도 분류 모듈

```mermaid
classDiagram
    class FineTunedLLM {
        +model_name : llama-3.2-3b-instruct.Q4_K_M
        +ollama_url : http://localhost:11434
        +temperature : 0
        +generate(prompt) Response
    }

    class IntentClassifier {
        +EMERGENCY_KEYWORDS : list
        +classify_intent(text) dict
        +extract_entities(text) dict
    }

    class ConversationManager {
        +conversation_state : dict
        +FOLLOWUP_QUESTIONS : dict
        +chat_with_followup(user_input, session_id) dict
    }

    class IntentResult {
        +str intent
        +float confidence
        +bool ready_for_c
        +dict output_for_c
    }

    IntentClassifier --> FineTunedLLM : LLM 호출
    ConversationManager --> IntentClassifier : 의도 분류 요청
    ConversationManager --> IntentResult : 반환
```

---

### 4. C팀 RAG + 병원검색 모듈

```mermaid
classDiagram
    class RAGPipeline {
        +QUERY_REWRITE_MAP : dict
        +query_rewrite(query) str
        +full_rag_pipeline(query) str
    }

    class ChromaDB {
        +collection : medical_knowledge
        +embed_model : ko-sroberta-multitask
        +query(query_embeddings, n_results) dict
    }

    class HospitalSearch {
        +SYMPTOM_DEPT_MAP : dict
        +search_hospital(symptom_text, lat, lng) dict
        +emergency_check(text) dict
    }

    class KakaoAPI {
        +KAKAO_API_KEY : str
        +radius : 3000m
        +search_kakao(dept_name, lat, lng) list
    }

    class ToolRouter {
        +EMERGENCY_SCORES : dict
        +tool_router(output_from_B, lat, lng) dict
    }

    ToolRouter --> RAGPipeline : symptom_inquiry, medication_info
    ToolRouter --> HospitalSearch : symptom_inquiry, hospital_search
    RAGPipeline --> ChromaDB : 벡터 검색
    HospitalSearch --> KakaoAPI : 병원 위치 검색
```

---

### 5. D팀 응답생성 모듈

```mermaid
classDiagram
    class AnswerGenerator {
        +FORBIDDEN_WORDS : list~10개~
        +generate_answer(query, context, confidence, entities) dict
        +format_response(raw_answer, is_emergency) str
    }

    class FineTunedLLM {
        +model_name : llama-3.2-3b-instruct.Q4_K_M
        +system_prompt : 한국어 전용
        +max_sentences : 3~4
        +generate(prompt) Response
    }

    class FormattedResponse {
        +str answer
        +bool is_emergency
    }

    AnswerGenerator --> FineTunedLLM : 답변 생성
    AnswerGenerator --> FormattedResponse : 반환
```

---

## 시퀀스 다이어그램

### 1. 전체 채팅 파이프라인 (A→B→C→D)

```mermaid
sequenceDiagram
    actor 어르신
    participant FastAPI
    participant A_STT
    participant B_Intent
    participant C_RAG
    participant D_Answer

    어르신->>FastAPI: POST /chat {text, session_id, lat, lng}
    FastAPI->>A_STT: stt_pipeline(raw_text)
    A_STT-->>FastAPI: {text, confidence}

    FastAPI->>B_Intent: chat_with_followup(text, session_id)
    B_Intent-->>FastAPI: {answer, intent, ready_for_c}

    alt ready_for_c == False (다중턴 추가 질문)
        FastAPI->>D_Answer: format_response(b_result.answer)
        D_Answer-->>FastAPI: final_answer
        FastAPI-->>어르신: 추가 질문 (예: "걷기가 많이 힘드신가요?")
    else ready_for_c == True
        FastAPI->>C_RAG: tool_router(output_from_B, lat, lng)
        C_RAG-->>FastAPI: {rag_context, hospitals, emergency}

        alt emergency.severity == HIGH
            FastAPI->>D_Answer: format_response("", is_emergency=True)
            Note over D_Answer: generate_answer 생략<br/>즉시 119 안내 문구 반환
            D_Answer-->>FastAPI: "지금 바로 119에 전화해 주세요."
        else 일반 응답
            FastAPI->>D_Answer: generate_answer(text, context, entities)
            D_Answer-->>FastAPI: raw_answer
            FastAPI->>D_Answer: format_response(raw_answer)
            D_Answer-->>FastAPI: final_answer
        end

        FastAPI-->>어르신: ChatResponse {answer, intent, hospitals, is_emergency}
    end
```

---

### 2. STT 처리 흐름

```mermaid
sequenceDiagram
    actor 어르신
    participant STT_Endpoint as POST /api/stt
    participant SileroVAD
    participant Whisper
    participant Preprocessor

    어르신->>STT_Endpoint: 오디오 파일 업로드 (.wav/.mp3)
    STT_Endpoint->>SileroVAD: remove_silence(audio_path)
    Note over SileroVAD: threshold=0.4 으로<br/>무음 구간 탐지 및 제거
    SileroVAD-->>STT_Endpoint: clean_audio_path

    STT_Endpoint->>Whisper: stt_processor(audio_array, 16kHz)
    Whisper-->>STT_Endpoint: input_features

    STT_Endpoint->>Whisper: stt_model.generate(input_features)
    Whisper-->>STT_Endpoint: raw_text

    STT_Endpoint->>Preprocessor: preprocess_text(raw_text)
    Note over Preprocessor: 1. 호출어 제거 (헬로비 등)<br/>2. 간투어 제거 (어~, 음~ 등)<br/>3. MEDICAL_CORRECTIONS 보정<br/>4. 중복 단어 제거
    Preprocessor-->>STT_Endpoint: clean_text

    STT_Endpoint-->>어르신: {text, raw_text, status: "success"}
```

---

### 3. 응급 감지 분기 흐름

```mermaid
sequenceDiagram
    participant B_Intent as B팀 의도분류
    participant C_Emergency as C팀 응급판단
    participant D_Answer as D팀 응답생성
    actor 어르신

    B_Intent->>B_Intent: classify_intent(text)

    alt EMERGENCY_KEYWORDS 즉시 감지<br/>("숨이 안 쉬어", "의식이 없" 등)
        Note over B_Intent: confidence=1.0, ready_for_c=True<br/>answer 필드에 119 안내 문구 포함
        B_Intent->>C_Emergency: tool_router → emergency_check(query)
        C_Emergency-->>D_Answer: severity=HIGH
        D_Answer-->>어르신: format_response(is_emergency=True)<br/>"지금 바로 119에 전화해 주세요."
    else 일반 의도 처리
        B_Intent->>C_Emergency: tool_router → emergency_check(query)
        Note over C_Emergency: EMERGENCY_SCORES 키워드별 점수 합산<br/>2개 이상 매칭 시 1.2배 가중

        alt score ≥ 70 (HIGH)
            C_Emergency-->>D_Answer: severity=HIGH
            D_Answer-->>어르신: format_response(is_emergency=True)<br/>"지금 바로 119에 전화해 주세요."
        else score ≥ 40 (MEDIUM)
            C_Emergency-->>D_Answer: severity=MEDIUM
            D_Answer-->>어르신: generate_answer + 응급실 방문 권고 + 병원 안내
        else score < 40 (LOW)
            C_Emergency-->>D_Answer: is_emergency=False
            D_Answer-->>어르신: generate_answer + 일반 증상 안내 + 병원 정보
        end
    end
```
