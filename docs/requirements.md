# LG HelloDoctor — 요구사항 정의서 (Clean Architecture)

| 항목 | 내용 |
|------|------|
| 프로젝트명 | LG HelloDoctor |
| 작성일 | 2026-04-19 |
| 버전 | v2.0 |
| 대상 플랫폼 | TV(LG) |
| 아키텍처 | Clean Architecture (Robert C. Martin) |

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────┐
│  4. Frameworks & Drivers (인프라스트럭처)             │
│  ┌───────────────────────────────────────────────┐  │
│  │  3. Interface Adapters (인터페이스 어댑터)       │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  2. Use Cases (유스케이스)                │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │
│  │  │  │  1. Entities (도메인 엔티티)        │  │  │  │
│  │  │  │  핵심 비즈니스 규칙                  |  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

의존성 방향: 바깥 레이어 → 안쪽 레이어 (단방향)
```

---

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [이해관계자](#2-이해관계자)
3. [Layer 1 — Entities (도메인 엔티티)](#3-layer-1--entities-도메인-엔티티)
4. [Layer 2 — Use Cases (유스케이스)](#4-layer-2--use-cases-유스케이스)
5. [Layer 3 — Interface Adapters (인터페이스 어댑터)](#5-layer-3--interface-adapters-인터페이스-어댑터)
6. [Layer 4 — Frameworks & Drivers (인프라스트럭처)](#6-layer-4--frameworks--drivers-인프라스트럭처)
7. [비기능 요구사항](#7-비기능-요구사항)
8. [시스템 제약사항](#8-시스템-제약사항)
9. [Human-in-the-Loop (HITL) — 하네스 엔지니어링](#9-human-in-the-loop-hitl--하네스-엔지니어링)

---

## 1. 프로젝트 개요

### 1.1 배경
65세 이상 시니어는 디지털 기기 조작에 어려움을 겪어 의료 정보 접근이 제한적이다. 몸이 불편할 때 스마트폰 검색보다 쉬운 **음성 기반 의료 안내 서비스**가 필요하다.

### 1.2 목적
- TV 또는 모바일에서 "헬로비"를 호출해 음성으로 증상을 말하면
- AI가 증상을 분석하고 적절한 의료 정보·병원 안내를 제공
- 응급 상황 즉시 감지 → 119 연결 안내

### 1.3 서비스 범위

| 포함 | 제외 |
|------|------|
| 증상 기반 진료과 안내 | 의료 진단 행위 |
| 반경 3km 병원 검색 | 처방전 발급 |
| 응급 상황 감지 및 119 안내 | 투약·복약 지시 |
| 일반 의약품 복약 정보 안내 | 특정 의사·병원 추천 |
| 음성 → 텍스트 변환 | 원격 진료 |

---

## 2. 이해관계자

| 구분 | 대상 | 특성 |
|------|------|------|
| 주 사용자 | 65세 이상 시니어 | 디지털 리터러시 낮음, 터치 조작 불편, 시력·청력 저하 가능 |
| 보조 사용자 | 시니어 가족 | 서비스 초기 설정, 이상 알림 수신 |
| 운영자 | 서비스 관리자 | 의료 DB 업데이트, 시스템 모니터링 |

---

## 3. Layer 1 — Entities (도메인 엔티티)

> **핵심 비즈니스 규칙.** 외부 시스템(DB, API, 프레임워크)에 의존하지 않는다.  
> 어떤 레이어도 Entities를 변경할 수 없다.

### 3.1 도메인 엔티티 목록

| 엔티티 | 설명 | 주요 속성 |
|--------|------|---------|
| `MedicalQuery` | 사용자의 의료 질의 | text, session_id, lat, lng |
| `Intent` | 의도 분류 결과 | type, confidence |
| `ConversationSession` | 다중턴 대화 상태 | session_id, step(1\|2), body_part |
| `EmergencyLevel` | 응급 위험도 | severity(HIGH\|MEDIUM\|LOW), score |
| `MedicalDocument` | 의료 지식 문서 | content, category, dept, source |
| `Hospital` | 병원 정보 | name, address, phone, distance, map_url |
| `MedicalResponse` | 최종 응답 | answer, intent, hospitals, is_emergency, ready_for_c, session_id |

### 3.2 도메인 비즈니스 규칙

#### 의도 유형 (Intent Type)
| 값 | 의미 | 트리거 |
|----|------|--------|
| `emergency` | 응급 상황 | 즉시 감지 키워드 또는 EMERGENCY_SCORES ≥ 70 |
| `symptom_inquiry` | 증상 문의 | 신체 부위·증상 언급 |
| `hospital_search` | 병원 검색 | 병원 찾기 직접 요청 |
| `medication_info` | 복약 정보 | 약 이름·복약 관련 질의 |

#### 응급 등급 판정 규칙 (EmergencyLevel)
```
1차 즉시 감지 (confidence=1.0):
  "숨이 안 쉬어", "의식이 없", "쓰러", "피를 토",
  "말이 어눌", "입이 돌아", "한쪽이 마비", "갑자기 안 보여"
  → severity: HIGH

2차 점수 합산:
  EMERGENCY_SCORES 키워드 매칭 점수 합계
  2개 이상 매칭 시 × 1.2 가중
  ≥ 70점 → HIGH | ≥ 40점 → MEDIUM | < 40점 → LOW
```

#### 의료법 준수 규칙 (FORBIDDEN_WORDS)
```
금지어 (10개): 예후, 처방전, 투약, 병변, 진단, 확정, 완치, 확신, 치료, 부작용
→ 답변 생성 후 정규식으로 자동 제거
→ 영어 단어 혼입 시 정규식 제거
```

#### 다중턴 전이 규칙 (ConversationSession)
```
Step 1: 증상 접수 → 추가 질문 반환 (ready_for_c: false)
Step 2: 추가 정보 수집 완료 → C팀 파이프라인 진행 (ready_for_c: true)
예외: emergency / medication_info / hospital_search → Step 1 생략, 즉시 ready_for_c: true
```

### 3.3 의료 지식 도메인 데이터

| 항목 | 내용 |
|------|------|
| 출처 | 질병관리청 국가건강정보포털 (health.kdca.go.kr) |
| 수집 방식 | 웹 크롤링 |
| 원본 문서 수 | 132개 |
| 총 청크 수 | 418개 |

| 카테고리 | 청크 수 | 내용 |
|---------|--------|------|
| `증상_진료과` | 380개 | 80여 개 질환별 개요·원인·증상·진단·치료·예후 |
| `복약_안내` | 12개 | 시판 의약품(타이레놀·부루펜 등) 복용법·주의사항 |
| `응급_안내` | 6개 | 응급 상황별 대처 방법 |

---

## 4. Layer 2 — Use Cases (유스케이스)

> **애플리케이션 비즈니스 규칙.** Entities를 사용하여 특정 목표를 달성하는 흐름.  
> 외부 구현체(DB, API)를 직접 참조하지 않고 Port(인터페이스)에 의존한다.

### UC-01. 음성 입력 처리 `ProcessVoiceInputUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-01 |
| 목표 | 오디오 파일을 정제된 한국어 텍스트로 변환 |
| 입력 | audio_file(.wav/.mp3) 또는 raw_text |
| 출력 | `MedicalQuery { text, raw_text, confidence }` |
| 처리 흐름 | ① VAD로 무음 제거 → ② Whisper STT → ③ 호출어·간투어 제거 → ④ MEDICAL_CORRECTIONS 보정(50개 항목) → ⑤ 중복 단어 제거 |
| 사용 Port | `ISpeechToTextPort`, `IVoiceActivityDetectionPort` |
| 우선순위 | 높음 |

### UC-02. 의도 분류 `ClassifyIntentUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-02 |
| 목표 | 사용자 발화를 4가지 Intent 중 하나로 분류 |
| 입력 | `MedicalQuery.text` |
| 출력 | `Intent { type, confidence }` |
| 처리 흐름 | ① 응급 키워드 즉시 감지(LLM 불필요) → ② LLM 의도 분류 → ③ 결과 정규화 |
| 우선 규칙 | 응급 키워드 매칭 시 LLM 호출 없이 즉시 `emergency` 반환 (confidence=1.0) |
| 사용 Port | `IIntentClassifierPort` |
| 우선순위 | 높음 |

### UC-03. 다중턴 세션 관리 `ManageConversationSessionUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-03 |
| 목표 | session_id 기반 2단계 대화 상태 관리 |
| 입력 | `MedicalQuery`, `Intent` |
| 출력 | `ConversationSession`, ready_for_c(bool), follow_up_question(str) |
| Step 1 | 증상 접수 → 신체부위 추출 → 추가 질문 반환 (ready_for_c: false) |
| Step 2 | 추가 답변 수집 → output_for_c 조립 → C파이프라인으로 전달 (ready_for_c: true) |
| 추가 질문 예시 | 무릎: "무릎이 많이 아프시군요. 혹시 걷기가 많이 힘드신가요?" |
| 사용 Port | `ISessionRepositoryPort` |
| 우선순위 | 높음 |

### UC-04. 응급 상황 감지 `DetectEmergencyUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-04 |
| 목표 | 텍스트 분석을 통해 응급 위험도 판정 |
| 입력 | `MedicalQuery.text` |
| 출력 | `EmergencyLevel { severity, score }` |
| HIGH 응답 | "어이구 어르신, 지금 많이 위험하실 수 있어요! 바로 119에 전화하시는 게 좋겠어요." |
| 우선순위 | 최우선 |

### UC-05. 의료 정보 검색 `SearchMedicalKnowledgeUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-05 |
| 목표 | 증상 키워드로 관련 의료 문서를 벡터 검색하여 반환 |
| 입력 | query(str), intent_type |
| 출력 | `List<MedicalDocument>` (상위 N개) |
| 처리 흐름 | ① QUERY_REWRITE_MAP으로 쿼리 재작성 → ② 임베딩 → ③ 코사인 유사도 검색 |
| 쿼리 재작성 예시 | "무릎" → "무릎통증 정형외과 관련 증상 치료 방법" |
| 사용 Port | `IMedicalKnowledgeRepositoryPort` |
| 우선순위 | 높음 |

### UC-06. 주변 병원 검색 `SearchNearbyHospitalsUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-06 |
| 목표 | 사용자 위치 기반 반경 3km 이내 관련 진료과 병원 반환 |
| 입력 | symptom_text, lat, lng |
| 출력 | `List<Hospital>` (최대 3개) |
| 처리 흐름 | ① 증상 → SYMPTOM_DEPT_MAP → 진료과 코드 매핑 → ② Kakao API 검색 → ③ 결과 정렬 |
| 장애 처리 | Kakao API 실패 시 빈 목록 반환 (서비스 중단 없음) |
| 사용 Port | `IHospitalSearchPort` |
| 우선순위 | 높음 |

### UC-07. 시니어 맞춤 답변 생성 `GenerateAnswerUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-07 |
| 목표 | RAG 컨텍스트 기반 시니어 맞춤 한국어 답변 생성 |
| 입력 | query, `List<MedicalDocument>`, entities, confidence |
| 출력 | `MedicalResponse.answer` |
| 처리 흐름 | ① 파인튜닝 LLaMA 3.2-3B 호출 → ② 한국어 비율 검증(>40%) → ③ 미달 시 Groq LLM 폴백 → ④ FORBIDDEN_WORDS 제거 → ⑤ 영어 단어 제거 |
| 출력 제약 | 3~4문장 이내, 어려운 의학 용어 사용 금지 |
| 사용 Port | `IAnswerGeneratorPort` |
| 우선순위 | 높음 |

### UC-08. 전체 파이프라인 실행 `ExecuteFullPipelineUseCase`

| 항목 | 내용 |
|------|------|
| 식별자 | UC-08 |
| 목표 | A→B→C→D 파이프라인을 조율하여 최종 ChatResponse 반환 |
| 입력 | `ChatRequest { text, session_id, lat, lng }` |
| 출력 | `MedicalResponse { answer, intent, hospitals, is_emergency, ready_for_c, session_id }` |
| 처리 흐름 | UC-01 → UC-02 → UC-03 → (ready_for_c: true 시) UC-04 + UC-05 + UC-06 → UC-07 |
| 분기 | ready_for_c: false → UC-07 없이 추가 질문만 반환 |
| 우선순위 | 높음 |

---

## 5. Layer 3 — Interface Adapters (인터페이스 어댑터)

> **포트(Port)와 어댑터(Adapter) 패턴.**  
> Use Case가 정의한 Port 인터페이스를 구현하고, 외부 데이터 형식을 도메인 형식으로 변환한다.

### 5.1 Controllers (입력 어댑터)

| 컨트롤러 | 엔드포인트 | 역할 |
|---------|-----------|------|
| `ChatController` | `POST /chat` | HTTP 요청 → `ChatRequest` 변환 → UC-08 호출 → HTTP 응답 조립 |
| `STTController` | `POST /api/stt` | 오디오 파일 수신 → UC-01 호출 → STT 결과 반환 |
| `HealthController` | `GET /` | 서버 상태 확인 |

**POST /chat 요청/응답 스펙:**
```json
// 요청 (ChatRequest)
{
  "text": "무릎이 너무 아파요",
  "session_id": "user-001",
  "lat": 37.5665,
  "lng": 126.9780
}

// 응답 (MedicalResponse)
{
  "answer": "무릎 통증은 정형외과에서 진료받으시는 것을 권장드려요.",
  "intent": "symptom_inquiry",
  "hospitals": [{ "name": "서울정형외과", "address": "...", "phone": "..." }],
  "is_emergency": false,
  "ready_for_c": true,
  "session_id": "user-001"
}
```

### 5.2 Ports (인터페이스 정의)

| Port 인터페이스 | 역할 | 구현 어댑터 |
|----------------|------|-----------|
| `ISpeechToTextPort` | 오디오 → 텍스트 변환 계약 | `WhisperSTTAdapter` |
| `IVoiceActivityDetectionPort` | 무음 구간 감지 계약 | `SileroVADAdapter` |
| `IIntentClassifierPort` | 의도 분류 계약 | `GroqLLMAdapter` |
| `IAnswerGeneratorPort` | 답변 생성 계약 | `FineTunedLLMAdapter` → `GroqLLMAdapter` |
| `IMedicalKnowledgeRepositoryPort` | 의료 문서 검색 계약 | `ChromaDBAdapter` |
| `IHospitalSearchPort` | 병원 검색 계약 | `KakaoMapAdapter` |
| `ISessionRepositoryPort` | 세션 상태 저장 계약 | `InMemorySessionAdapter` |

### 5.3 Presenters (출력 어댑터)

| 프레젠터 | 역할 |
|---------|------|
| `TVScreenPresenter` | `MedicalResponse` → TV 화면 상태(대기/인식중/응답/응급) 변환 |
| `MobileScreenPresenter` | `MedicalResponse` → 채팅 버블·병원 카드 UI 데이터 변환 |

### 5.4 프론트엔드 컴포넌트 (UI Adapter)

| 컴포넌트 | 화면 | 역할 |
|---------|------|------|
| `HelloBeeTvScreen` | TV (1920×1080) | 대기·인식중·병원 안내·응급 4가지 상태 표시 |
| `MedicalChatScreen` | 모바일 | 채팅 인터페이스 (버블, 병원 카드, 음성 패널) |
| `useWakeWord` | - | 호출어 감지 훅 ("헬로비") |
| `useMedicalChat` | - | 채팅 상태 관리 훅 |
| `useVoiceInput` | - | 마이크 입력 훅 |

---

## 6. Layer 4 — Frameworks & Drivers (인프라스트럭처)

> **외부 시스템과 실제 구현체.** 내부 레이어는 이 레이어를 알지 못한다.

### 6.1 백엔드 프레임워크

| 기술 | 버전 | 역할 |
|------|------|------|
| FastAPI | 0.115.0 | REST API 서버, CORS 미들웨어 |
| Uvicorn | 0.30.6 | ASGI 서버 |
| Pydantic | 2.9.2 | 요청/응답 스키마 검증 |

### 6.2 AI 모델 구현체

| 구현체 | 기술 | 역할 |
|--------|------|------|
| `WhisperSTTAdapter` | OpenAI Whisper (HuggingFace) | 한국어 음성 → 텍스트 |
| `SileroVADAdapter` | Silero VAD (threshold=0.4) | 무음 구간 탐지 및 제거 |
| `GroqLLMAdapter` | Groq API / llama-3.3-70b-versatile, temperature=0 | 의도 분류, 엔티티 추출, 답변 폴백 |
| `FineTunedLLMAdapter` | 파인튜닝 LLaMA 3.2-3B (Unsloth LoRA → GGUF Q4_K_M, Ollama) | 시니어 맞춤 답변 생성 |

### 6.3 데이터 저장소 구현체

| 구현체 | 기술 | 역할 |
|--------|------|------|
| `ChromaDBAdapter` | ChromaDB 1.5.5 + ko-sroberta-multitask | 의료 문서 벡터 검색 (418청크) |
| `InMemorySessionAdapter` | Python dict | 다중턴 세션 상태 (서버 재시작 시 초기화) |

### 6.4 외부 API 구현체

| 구현체 | 기술 | 역할 |
|--------|------|------|
| `KakaoMapAdapter` | Kakao Map API | 반경 3km 병원 위치 검색 |

### 6.5 프론트엔드 프레임워크

| 기술 | 버전 | 역할 |
|------|------|------|
| React | 19.2.4 | UI 라이브러리 |
| TypeScript | 5.9.3 | 타입 안전성 |
| Vite | 8.0.1 | 빌드 도구 |
| nginx | alpine | SPA 서빙 (포트 80) |

### 6.6 하드웨어 드라이버

| 장치 | 브라우저 API | 역할 |
|------|------------|------|
| 마이크 | Web Audio API | 음성 입력 |
| GPS | Geolocation API | 사용자 위치 (lat, lng) |
| 스피커 | Web Speech API | TTS 답변 음성 출력 |

### 6.7 배포 인프라

| 기술 | 역할 |
|------|------|
| Docker Compose | backend(포트 8000) + frontend(포트 80) 멀티 컨테이너 |
| python:3.11-slim | 백엔드 컨테이너 (CPU 전용) |
| node:20-alpine → nginx:alpine | 프론트엔드 멀티스테이지 빌드 |
| model-cache 볼륨 | HuggingFace 모델 캐시 재사용 |

---

## 7. 비기능 요구사항

### NFR-01. 성능

| 요구사항 | 목표값 |
|---------|--------|
| STT 처리 (30초 음성 기준) | 10초 이하 |
| 의도 분류 | 3초 이하 |
| RAG 벡터 검색 | 2초 이하 |
| 병원 검색 (Kakao API) | 3초 이하 |
| 전체 응답 (end-to-end) | 15초 이하 |

### NFR-02. 가용성

| 요구사항 | 내용 |
|---------|------|
| 서비스 운영 | 24시간 365일 |
| 컨테이너 장애 복구 | Docker Compose restart 정책 |
| Kakao API 장애 시 | 병원 정보 없이 의료 안내만 제공 (서비스 중단 없음) |
| LLM 품질 미달 시 | 파인튜닝 모델 → Groq LLM 자동 폴백 |

### NFR-03. 접근성 (시니어 특화)

| 요구사항 | 내용 |
|---------|------|
| 글자 크기 | TV 22px 이상 / 모바일 15px 이상 |
| 색상 대비 | 배경-텍스트 명도 대비 4.5:1 이상 |
| 답변 길이 | 3~4문장 이내 |
| 언어 수준 | 어려운 의학 용어 사용 금지 |
| 오류 메시지 | 영어 오류 코드 노출 금지, 한국어 안내 |

### NFR-04. 보안

| 요구사항 | 내용 |
|---------|------|
| API 키 관리 | `.env` 분리, Git 커밋 금지 |
| CORS | 허용된 도메인만 접근 허용 |
| 개인정보 | 사용자 음성·위치 서버 영구 저장 금지 |

### NFR-05. 유지보수성

| 요구사항 | 내용 |
|---------|------|
| 레이어 격리 | 각 레이어는 Port 인터페이스를 통해서만 통신 |
| 팀 모듈 독립 | A(STT) / B(의도) / C(RAG+병원) / D(답변) 함수 단위 분리 |
| 테스트 | pytest 단위 테스트 + 통합 검증 자동화 (`src/todo/manager.py`) |
| 배포 | `docker compose up --build` 단일 명령 배포 |

---

## 8. 시스템 제약사항

### 8.1 법적 제약 (의료법)

| 제약 | 내용 |
|------|------|
| 진단 금지 | 특정 질병 확정 진단 표현 금지 |
| 처방 금지 | 처방전, 투약 지시 금지 |
| 금지어 (10개) | 예후, 처방전, 투약, 병변, 진단, 확정, 완치, 확신, 치료, 부작용 |
| 고지 의무 | 모든 화면 하단에 "본 서비스는 의료 진단을 대체하지 않습니다" 표시 |

### 8.2 기술 제약

| 제약 | 내용 |
|------|------|
| 하드웨어 | GPU 없음 — CPU 전용 실행 |
| ChromaDB | 버전 1.5.5 고정 (로컬 DB 스키마 호환) |
| httpx | <0.28.0 고정 (proxies 파라미터 호환) |
| 세션 영속성 | 서버 재시작 시 대화 이력 초기화 (`ISessionRepositoryPort` 메모리 구현) |
| 파인튜닝 모델 | Ollama 로컬 서버 별도 실행 필요 |

---

## 9. Human-in-the-Loop (HITL) — 하네스 엔지니어링

> AI가 자율적으로 행동하되, **사람이 핵심 의사결정 지점에서 검토·승인·제어**하는 구조.  
> 하네스 엔지니어링(`.claude/`)을 통해 AI-사람 협업 파이프라인을 구현한다.

### 9.1 HITL 적용 원칙

```
AI 행동 시도
    ↓
훅(Hook) — 자동 차단 or 알림
    ↓
사람 검토 (승인 / 수정 / 거부)
    ↓
다음 단계 진행
```

**의존성 방향:** AI는 사람의 판단을 대체하지 않는다. 사람이 기준을 정하고, AI는 그 기준 안에서 행동한다.

### 9.2 HITL 체크포인트 목록

| 체크포인트 | 구현 위치 | AI 역할 | 사람 역할 |
|-----------|---------|--------|---------|
| **위험 명령어 차단** | `.claude/settings.json` PreToolUse 훅 | 명령 실행 시도 | 차단 알림 확인 후 허용/거부 결정 |
| **파일 편집 후 알림** | `.claude/settings.json` PostToolUse 훅 | 파일 수정 완료 | diff 검토 후 승인 또는 롤백 |
| **배포 전 통합 검증** | `/validate` 슬래시 명령어 | 검증 항목 자동 실행 | 7개 항목 결과 직접 확인 후 배포 승인 |
| **테스트 결과 검토** | `/test` 슬래시 명령어 | pytest 전체 스위트 실행 | 실패 항목 원인 분석 후 머지 여부 결정 |
| **응급 키워드 승인** | `EMERGENCY_KEYWORDS` (backend/main.py) | 키워드 매칭 실행 | 키워드 목록 검토·추가·삭제 최종 확정 |
| **금지어 목록 확정** | `FORBIDDEN_WORDS` (backend/main.py) | 답변 생성 후 자동 필터 | 의료법 준수 여부 판단, 10개 항목 직접 승인 |
| **품질 임계값 설정** | 한국어 비율 40% 기준 (backend/main.py) | 비율 측정 후 폴백 판단 | 실험 결과 검토 후 임계값 수동 결정 |
| **파인튜닝 데이터 검수** | `finetune/llama_finetune.ipynb` | LoRA 학습 실행 | 학습 데이터 품질 검토 및 학습 결과 평가 |

### 9.3 하네스 구성 파일

| 파일 | HITL 역할 |
|------|---------|
| `.claude/settings.json` | 훅 기반 자동 차단·알림 — AI 행동의 가드레일 |
| `.claude/commands/validate.md` | 배포 전 사람이 직접 실행하는 통합 검증 게이트 |
| `.claude/commands/test.md` | 사람이 트리거하는 TDD 실행 및 결과 검토 게이트 |
| `.claude/commands/deploy.md` | 사람이 최종 승인 후 실행하는 배포 자동화 |

### 9.4 AI 자율 영역 vs 사람 개입 영역

| 영역 | AI 자율 처리 | 사람 개입 필수 |
|------|------------|-------------|
| **음성 처리** | STT 변환, 무음 제거, 텍스트 보정 | — |
| **의도 분류** | 키워드 매칭, LLM 분류 | — |
| **응급 감지** | 점수 계산, 등급 판정 | 키워드·점수 기준 초기 설정 |
| **답변 생성** | LLM 호출, 품질 검증 | 금지어 목록, 품질 임계값 결정 |
| **코드 수정** | 파일 편집, 리팩토링 제안 | 편집 결과 검토, 위험 명령 허용 여부 |
| **배포** | 컨테이너 빌드, 헬스 체크 실행 | 배포 최종 승인 (`/validate` → `/deploy`) |
| **모델 학습** | LoRA 파인튜닝 실행 | 학습 데이터 큐레이션, 결과 평가 |
