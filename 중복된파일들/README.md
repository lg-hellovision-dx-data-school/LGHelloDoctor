# LGHelloDoctor — A팀: STT · 음성 파이프라인

> LG HelloVision AI 스피커 기반 노인 대상 의료 음성 AI 에이전트  
> **A팀 담당 범위**: 음성 입력 → VAD → Whisper STT → 텍스트 전처리 → B팀으로 전달

---

## 팀 구성 및 역할

| 팀 | 담당 |
|----|------|
| **A팀 (이 레포)** | STT · 음성 파이프라인 (음성 입력 ~ 텍스트 전처리) |
| B팀 | 의료 LLM · 파인튜닝 (Ollama, LoRA, 의도 분류) |
| C팀 | RAG · 도구 연동 (ChromaDB, 병원 검색, 응급 처리) |
| D팀 | API 서버 · 응답 포맷터 · TTS (FastAPI, PostgreSQL) |

---

## A팀 파이프라인 흐름

```
대기 상태 → Wake word 감지 ("헬로비")
        ↓
① 음성 입력 — 마이크 녹음 or 파일 로드
        ↓
② VAD 필터 — 침묵 구간 제거 (silero-vad, threshold=0.4)
        ↓
③ Whisper STT — 음성 → 텍스트 (Groq whisper-large-v3)
        ↓
④ 텍스트 전처리 — 간투어 제거 + 의료 용어 오탈자 보정(50개) + 정규화
        ↓
   B팀 의도 분류기로 전달
```

---

## 완료 현황

| 항목 | 파일 | 상태 |
|------|------|------|
| 음성 입력 (마이크 / 파일 로드) | `src/audio_input.py` | ✅ |
| VAD 필터 (침묵 제거) | `src/vad_filter.py` | ✅ |
| Whisper STT (Groq API + 로컬 자동 전환) | `src/stt_module.py` | ✅ |
| 텍스트 전처리 모듈 | `src/preprocessor.py` | ✅ |
| 의료 용어 오탈자 보정 사전 (50개) | `src/preprocessor.py` | ✅ |
| 파이프라인 통합 진입점 | `src/pipeline.py` | ✅ |
| Wake word 감지 ("헬로비") | `src/wake_word.py` | ✅ 구조 완성 |
| STT 정확도 평가 지표 (WER / CER) | `src/evaluate_stt.py` | ✅ |
| AI Hub 데이터 가공 프레임워크 | `src/data_prep.py` | ✅ 구조 완성 |
| 자유대화 음성(노인남녀) 데이터 가공 실행 | `data/processed/` | ✅ 완료 (훈련 80,243개 / 검증 11,202개) |
| Whisper LoRA 파인튜닝 프레임워크 | `src/finetune_whisper.py` | ✅ 구조 완성 |
| 단위 테스트 (20개 통과) | `tests/test_pipeline.py` | ✅ |

### 남은 작업

| 항목 | 조건 |
|------|------|
| ~~AI Hub 데이터 다운로드 및 가공 실행~~ | ✅ 완료 |
| Whisper 노인 한국어 파인튜닝 실행 | GPU 환경 + 가공 데이터 준비 후 `finetune_whisper.py` 실행 |
| Wake word 실기 테스트 | 마이크 연결 환경에서 `wake_word.py` 동작 확인 |
| 평가용 JSONL 레이블 작성 | 샘플 파일(case1~4.mp3) 정답 텍스트 작성 → WER/CER 실측 |
| B팀과 출력 스키마 확정 | confidence 임계값 등 인터페이스 협의 |

---

## 폴더 구조

```
LGHelloDoctor/
├── src/
│   ├── audio_input.py        # 마이크 녹음 or 파일 로드
│   ├── vad_filter.py         # 침묵 제거 (silero-vad)
│   ├── stt_module.py         # Whisper STT (Groq API / 로컬 파인튜닝 모델 자동 전환)
│   ├── preprocessor.py       # 간투어 제거 + 의료 용어 오탈자 보정(50개) + 정규화
│   ├── pipeline.py           # 전체 파이프라인 진입점
│   ├── wake_word.py          # "헬로비" Wake word 감지 모듈
│   ├── evaluate_stt.py       # WER / CER 정확도 평가
│   ├── data_prep.py          # AI Hub 데이터셋 가공 프레임워크
│   └── finetune_whisper.py   # Whisper LoRA 파인튜닝 프레임워크
├── tests/
│   ├── test_pipeline.py      # 단위 테스트 (20개)
│   └── samples/
│       ├── case1.mp3         # 시나리오 A — 증상 문의
│       ├── case2.mp3         # 시나리오 B — 응급 상황
│       ├── case3.mp3         # 시나리오 C — 약 정보 문의
│       └── case4.mp3         # 기타 발화
├── models/
│   └── whisper-ko-elderly/   # 파인튜닝 완료 시 여기 배치 (자동 전환)
├── data/
│   ├── raw/                  # AI Hub 원본 데이터 (로컬에만 보관)
│   └── processed/            # data_prep.py 실행 후 생성
├── .env
└── requirements.txt
```

---

## 환경 설정

`.env` 파일 생성:

```
GROQ_API_KEY=your_groq_api_key
```

패키지 설치:

```bash
pip install -r requirements.txt
```

---

## 실행 방법

### 1. 파일로 파이프라인 테스트

```bash
cd src
python -X utf8 pipeline.py --file ../tests/samples/case1.mp3
```

### 2. 마이크로 실시간 녹음 (7초)

```bash
cd src
python -X utf8 pipeline.py --record --duration 7
```

### 3. Wake word 모드 (마이크 필요)

```bash
cd src
python -X utf8 pipeline.py --wake_word
```

### 4. 단위 테스트 (네트워크 불필요)

```bash
pytest tests/test_pipeline.py -v -k "not TestSTT and not TestPipeline"
```

### 5. STT 정확도 평가

```bash
# tests/eval_data.jsonl 형식: {"reference": "정답", "hypothesis": "STT결과"}
python src/evaluate_stt.py --input tests/eval_data.jsonl
```

---

## B팀으로 전달하는 출력 형식

```python
{
    "text":       "무릎 통증. 진료 병원 문의",          # 전처리된 텍스트
    "raw_text":   "무릎이 너무 아파요. 어디 가야 하나요?",  # STT 원본
    "confidence": 0.94,
    "language":   "ko"
}
```

---

## 파인튜닝 모델 자동 전환

`models/whisper-ko-elderly/` 폴더가 존재하면 자동으로 로컬 모델로 전환됩니다.  
없으면 Groq Whisper API를 사용합니다.

```
models/whisper-ko-elderly/ 있음 → 로컬 파인튜닝 모델 사용
models/whisper-ko-elderly/ 없음 → Groq whisper-large-v3 API 사용  ← 현재
```

파인튜닝 실행 (GPU + 데이터 준비 후):

```bash
python src/data_prep.py --raw_dir ./data/raw --output_dir ./data/processed
python src/finetune_whisper.py --data_dir ./data/processed --output_dir ./models/whisper-ko-elderly
```

AI Hub 원본 폴더를 바로 쓰는 경우 (현재 워크스페이스 구조 기준):

```bash
python src/data_prep.py --raw_dir "./자유대화 음성(노인남녀)" --output_dir ./data/processed
```

대용량 데이터 사전 점검(스모크 테스트):

```bash
python src/data_prep.py --raw_dir "./자유대화 음성(노인남녀)" --output_dir ./data/processed_smoke --train_limit 200 --val_limit 50
```

---

## 트러블슈팅

**torchaudio 2.9+ 오류 (`torchcodec` 없음)**

```
RuntimeError: torchaudio version requires torchcodec for audio I/O
```

→ `vad_filter.py`에서 `read_audio` 대신 `librosa`로 오디오 로드하도록 수정 완료

**silero-vad 신뢰 확인 오류**

```
EOFError: EOF when reading a line
```

→ `torch.hub.load(trust_repo=True)` 추가로 해결 완료

**Windows 한글 인코딩 오류**

```bash
python -X utf8 your_script.py
```

---

## 전체 서비스 시나리오

### 시나리오 A — 증상 문의 + 병원 검색

> "무릎이 너무 아파요. 어디 가야 하나요?"

| 단계 | 담당 | 처리 내용 |
|------|------|-----------|
| ① 음성 입력 | **A팀** | Wake word("헬로비") 감지 후 녹음 |
| ② VAD | **A팀** | 침묵 구간 제거 |
| ③ STT | **A팀** | "무릎이 너무 아파요. 어디 가야 하나요?" |
| ④ 전처리 | **A팀** | 간투어 제거, 오탈자 보정 |
| ⑤ 의도 분류 | B팀 | `symptom_inquiry` + `hospital_search` |
| ⑥ 도구 실행 | C팀 | RAG 검색 + 카카오 병원 검색 병렬 실행 |
| ⑦ LLM 추론 | B팀 | Ollama llama3 + LoRA |
| ⑧ 포맷터 + TTS | D팀 | 3문장 이하, 존댓말, 속도 0.85x |

### 시나리오 B — 응급 상황

> "가슴이 너무 아프고 숨이 안 쉬어져요"

의도 분류에서 `emergency` 감지 즉시 RAG·LLM 건너뛰고 119 안내 출력 (~0.5초)

### 시나리오 C — 약 정보 문의

> "혈압약이랑 감기약 같이 먹어도 되나요?"

`medication_info` 감지 → 병원 검색 없이 RAG만 단독 실행

| 구분 | 시나리오 A | 시나리오 B | 시나리오 C |
|------|-----------|-----------|-----------|
| 감지 의도 | symptom + hospital | emergency | medication_info |
| RAG 실행 | ✅ | ❌ | ✅ |
| 병원 검색 | ✅ | ❌ | ✅ (약국) |
| LLM 추론 | ✅ | ❌ | ✅ |
| 응답 시간 | ~2–3초 | ~0.5초 | ~2초 |
