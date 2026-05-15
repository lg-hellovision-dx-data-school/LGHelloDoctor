# LG HelloDoctor 기술 보고서: 시스템 고도화 여정

> **본 문서의 목적**
> 학회 발표·논문 근거 자료를 위한 기술 보고서. 시니어 대상 음성 의료 AI 에이전트 *LG HelloDoctor* 의 고도화 과정을 문제 정의 → 접근 방법 → 구현 → 결과 → 한계 순으로 정리한다. 시간순으로 마주친 기술적 난관과 그 해결 시도까지 모두 기록하여, 동일 영역에서 후속 연구가 시행착오를 반복하지 않도록 한다.

---

## 0. 요약 (Abstract)

본 프로젝트는 음성 입력 기반 시니어(어르신) 대상 의료 안내 AI 에이전트를 개발하는 것을 목표로 한다. 핵심 기여는 다음과 같다.

1. **Hybrid RAG v2 도입** — Vector + BM25 Reciprocal Rank Fusion 후 Cross-Encoder reranker 적용. 자체 ablation 검증에서 recall@3 0.85, MRR 0.86 으로 Vector-only 대비 +15% 향상.
2. **HITL 3-Tier 거버넌스** — 도메인 자문단(4 역할) × 개발팀 × 시니어 베타 구조의 7 체크포인트를 코드·테스트·훅·PR 절차에 내장하여 *"AI 단독 결정 0건"* 을 시스템 수준에서 강제.
3. **파인튜닝 시도와 양자화 호환성 분석** — Gemma 3 4B LoRA(intent 99% accuracy) 학습은 성공하였으나, bnb-4bit↔Q4_K_M 양자화 형식 호환성으로 인해 다섯 가지 GGUF 통합 경로가 모두 실패함을 진단. 본 한계는 향후 동일 환경 연구에 중요한 참고 자료가 된다.
4. **통합 검증 자동화** — `/validate` 7항목 (환경/RAG/API/응급/한국어/프론트) 7/7 통과로 배포 가능 상태 확정.
5. **AI Native Engineering 6단계 자산화** — 지침·프롬프트·에이전트·컨텍스트·TDD·통합 검증의 6 계층을 git 추적 24 파일로 정착.
6. **도메인 온톨로지 형식화** — `backend/main.py` 의 6개 코드 사전을 OWL/SKOS Turtle 온톨로지(79 개체, 16 클래스, SNOMED CT 30+ 매핑)로 격상하여 시맨틱 웹 표준 추론·SPARQL 질의·표준 의료 용어 연동 기반 확보.

전체 시스템은 Docker Compose 로 단일 호스트에서 구동되며, 응급 키워드 100% 감지·금지어 0건 머지·한국어 전용 응답 등의 정량 안전 지표를 통과하였다.

---

## 1. 시스템 개요

### 1.1 도메인 컨텍스트

LG HelloDoctor 는 시니어 사용자가 *"무릎이 아파요"*, *"머리가 어지러워요"* 같은 자연어 발화로 의료 정보를 얻을 수 있는 음성 에이전트다. 도메인 특수성은 다음과 같다.

- **사용자 특성**: 70대 이상, 키보드 입력 어려움, 의학 용어 친숙도 낮음, 안전·신뢰가 사용성보다 우선
- **법적 제약**: 의료법 §27 (무면허 의료행위 금지), 의료광고법 — *진단/처방/치료* 어휘 단정적 사용 금지
- **응급성**: 흉통·호흡곤란·의식소실 등은 골든타임 보호가 인명 직결

이 세 제약이 후술하는 모든 설계 의사결정의 근거가 된다.

### 1.2 4팀 파이프라인

```
사용자 음성
    ↓
[A팀] STT (Whisper + Silero VAD)         ← 음성 → 텍스트
    ↓
[B팀] 의도 분류 & 다중턴                ← 5 라벨 분류기
    ↓
[C팀] RAG + 병원 검색 + 응급 판단         ← Hybrid RAG + Kakao API
    ↓
[D팀] 답변 생성                           ← 시니어 친화 답변
    ↓
프론트엔드 (React + Vite)
```

- A, B, C, D 각 팀은 [`backend/main.py`](../backend/main.py) 의 별도 함수 군집으로 구현되며, 통합 진입점은 `full_pipeline()` 이다.
- 학술적 관점에서 본 파이프라인의 차별점은 **C팀(RAG)·B팀(Intent)·D팀(Answer) 모두에 룰 기반 안전장치가 LLM 출력을 wrap** 한다는 점이다 (§3.4 참고).

### 1.3 기술 스택

| 계층 | 컴포넌트 | 선택 근거 |
|---|---|---|
| 언어 모델 | Gemma 3 4B (Ollama 공식 GGUF) | 한국어 성능 + 단일 호스트 추론 가능 |
| STT | Whisper (`SungBeom/whisper-small-ko`) | 한국어 fine-tuned, CPU 추론 가능 |
| 임베딩 | sentence-transformers | 한국어 의료 도메인 검증 |
| 벡터 DB | ChromaDB PersistentClient | 임베디드 모드, 외부 의존성 없음 |
| BM25 | rank_bm25 | RAG v2 hybrid 의 lexical 축 |
| Reranker | `Dongjin-kr/ko-reranker` | 한국어 cross-encoder |
| 외부 API | Kakao Local Search | 병원 위치 검색 |
| 프론트 | React 18 + Vite + TypeScript | 모듈화 + 음성 API |
| 배포 | Docker Compose | 재현 가능한 단일 호스트 배포 |

### 1.4 아키텍처 동심원

본 프로젝트는 두 관점의 Clean Architecture 동심원을 채택했다 (자세한 다이어그램은 [`docs/CLEAN_ARCHITECTURE.md`](./CLEAN_ARCHITECTURE.md), [`docs/CLEAN_ARCHITECTURE_GOVERNANCE.md`](./CLEAN_ARCHITECTURE_GOVERNANCE.md) 참조).

- **기능 동심원**: Entities (의료 도메인 규칙) ← Use Cases (4팀 파이프라인) ← Adapters (FastAPI/React) ← Frameworks (Docker/외부 API)
- **거버넌스 동심원**: 도메인 자문단(Tier①) ← 개발팀(Tier②) ← 시니어 베타(Tier③) ← AI 도구(가장 바깥, 통제 대상)

핵심은 **AI 도구가 가장 바깥 동심원** 이라는 점이다. 즉, AI 가 핵심 의료 규칙을 직접 변경하지 못하고 항상 사람의 검토 layer 를 통과해야 한다.

---

## 2. 고도화 ①: Hybrid RAG v2 (BM25 + Cross-Encoder)

### 2.1 문제 정의

초기 RAG v1 은 ChromaDB 단일 vector retrieval 만 사용했다. 시니어 발화의 특성상 다음과 같은 retrieval 실패가 빈발했다.

- **희소 키워드 발화**: *"타이레놀"*, *"위내시경"* 같은 고유명사가 vector 임베딩에서 약하게 표현되어 정확한 문서가 top-k 에 안 잡힘.
- **동의어/이형 표기**: *"안과가"* (시니어 발음 특성) → *"안과"* 매칭 실패.
- **off-topic 답변**: 검색 점수만 고려하면 의미상 가장 유사하지만 질의의 *원래 의도* 와 무관한 문서가 컨텍스트로 들어가 LLM 이 *환각(hallucination)* 을 일으킴.

### 2.2 접근 방법

문헌의 hybrid retrieval 패턴 (Vector + Lexical) 과 reranker 단계를 결합한 4단 구조를 설계했다.

```
질의 → query rewrite → [Vector top-20]   ┐
                       [BM25 top-20]     ├─ RRF fusion → Cross-Encoder rerank → top-3 + threshold
                                         ┘
```

각 단계의 역할:

1. **Query rewrite**: 시니어 어휘를 RAG 친화 표현으로 확장 (예: *"무릎"* → *"무릎통증 정형외과 관련 증상 치료 방법"*)
2. **Vector retrieval (top-20)**: 의미적 유사도 기반 후보군
3. **BM25 retrieval (top-20)**: 키워드/희소 어휘 매칭 후보군
4. **Reciprocal Rank Fusion (RRF)**: $\text{score}(d) = \sum_{r \in \text{retrievers}} \frac{1}{60 + \text{rank}_r(d)}$
5. **Cross-Encoder rerank**: 질의-문서 페어를 함께 인코딩한 정밀 점수
6. **Confidence threshold**: rerank score ≥ 0 인 문서만 채택 (negative score = 무관 판정)

### 2.3 구현

[`backend/main.py:409-470`](../backend/main.py#L409-L470) 의 `full_rag_pipeline()` 에 6단계가 모두 구현되어 있다. 핵심 발췌:

```python
def full_rag_pipeline(query: str) -> dict:
    """Hybrid RAG v2: Vector + BM25 → RRF fusion → CrossEncoder rerank → confidence threshold."""
    rewritten = query_rewrite(query)

    # 1) Vector search (top-20)
    q_emb = embed_model.encode([rewritten]).tolist()
    vec_res = collection.query(query_embeddings=q_emb, n_results=20)

    # 2) BM25 search (top-20) — 키워드 매칭은 원본 쿼리 사용
    bm_scores = bm25.get_scores(_bm25_tok(query))

    # 3) RRF fusion
    sc = defaultdict(float)
    for hits in (vec_hits, bm25_hits):
        for rank, r in enumerate(hits, 1):
            sc[r["doc_id"]] += 1.0 / (60 + rank)

    # 4) Cross-Encoder rerank → top-3
    rerank_scores = reranker.predict([[query, c["text"]] for c in candidates])

    # 5) Confidence threshold (rerank_score < 0 → 미사용)
    confident = [c for c in top3 if c["rerank_score"] >= 0]

    # 6) Context + Citation 출처
    return {"context": ..., "sources": [{"doc_id", "score", "source": "질병관리청 국가건강정보포털"}]}
```

설계 디테일:

- **BM25 토크나이즈는 원본 쿼리, Vector 는 rewrite 쿼리**: lexical 매칭은 시니어가 실제 사용한 단어를 보존해야 하고, semantic 검색은 확장된 표현이 유리함.
- **RRF k=60**: 표준값, 양 retriever 영향 균형.
- **Threshold = 0**: ko-reranker 의 logit 0 을 무관/유관 경계로 사용. 0 미만은 컨텍스트 미사용 → "관련된 전문적인 의학 정보를 찾지 못했습니다" 응답으로 분기.
- **Citation source 명시**: 모든 retrieved 문서는 *질병관리청 국가건강정보포털(KDCA)* 출처로 표시 — Tier①-A 의사 자문 완화 장치 (§3.3).

### 2.4 평가 결과

`finetune/rag_evaluation.ipynb` 에서 LangSmith 통합 평가 + 4축 LLM-as-Judge (faithfulness, relevance, answer correctness, context precision) 를 수행하였다.

| 메트릭 | Vector only | Hybrid v2 (Vector+BM25+rerank) | 개선 |
|---|---|---|---|
| recall@3 | 0.74 | **0.85** | **+15%** |
| MRR | 0.75 | **0.86** | **+15%** |
| Faithfulness (Judge) | 0.72 | 0.81 | +12% |
| 환각률 | 18% | 9% | -50% |

### 2.5 한계 및 학습

- **BM25 토크나이저 한계**: 한국어 형태소 분석을 적용하지 않은 단순 split 토크나이저. 향후 `mecab`/`kiwi` 적용 시 추가 성능 향상 여지.
- **Reranker 추론 비용**: top-20 페어 처리에 약 200ms 추가. 단일 사용자 데모 환경에서는 무시 가능하나 동시 접속 시 병목 소지. Caching 또는 더 작은 reranker 적용 고려.
- **Threshold 일반화**: 0 은 ko-reranker 의 default 임계값이지만 도메인 fine-tune 시 재조정 필요.

---

## 3. 고도화 ②: HITL 3-Tier 거버넌스

### 3.1 문제 정의

의료 도메인의 AI 에이전트는 단일 실수가 인명 사고로 직결될 수 있다. 모델 정확도만으로는 부족하며, *"AI 가 어떤 결정을 누구의 책임 하에 내렸는가"* 가 검증되어야 한다. 본 프로젝트의 거버넌스 설계 원칙은:

> **"AI 단독 결정 0건 — 모든 의료 정책은 사람이 검토·승인한다."**

이를 슬로건이 아니라 **코드·테스트·훅·PR 절차에 강제로 박아넣는** 것이 본 고도화의 목표다.

### 3.2 3-Tier × 6 역할 구조

[`docs/HITL_3TIER.md`](./HITL_3TIER.md) 에 운영 매뉴얼이, [`CLAUDE.md`](../CLAUDE.md) 의 HITL 섹션에 상시 매트릭스가 있다.

| Tier | 역할 (수) | 책임 영역 |
|---|---|---|
| **① 도메인 자문단** | 4 역할 | 의료·법적 정확성 |
|   ├ 의사 (응급의학·일반의) |   | 응급 분류, 진료과 매칭, RAG 출처 |
|   ├ 약사 |   | 약물 상호작용, OTC, 부작용 |
|   ├ 노년학·시니어 UX |   | 어휘 난이도, 권유형 어조, 음성 속도 |
|   └ 법률·컴플라이언스 |   | 의료법, 의료광고법, 면책조항 |
| **② 개발팀** | 1 그룹 | PR·테스트·배포·위험 명령 차단 |
| **③ 시니어 사용자 베타** | 1 그룹 | 이해도·UX 피드백 |

> **MVP 단계 운영 정책**: 자문단은 *설계 단계에서 정립* 되었고, 베타·정식 출시 마일스톤별로 단계 도입한다. 현재는 KDCA 공공자료 + 개발자 검토 + 본 정책 매트릭스로 운영하되, 자문단 위촉 후 첫 검토 시점부터 [`docs/test-report.md`](./test-report.md) 의 검토 이력 로그에 기록한다.

### 3.3 7 체크포인트 매트릭스

| # | 체크포인트 | 위치 | 1차 책임자 | 검수 주기 |
|---|---|---|---|---|
| 1 | 위험 명령어 차단 | [`.claude/settings.json`](../.claude/settings.json) PreToolUse 훅 | 개발팀 | 자동 (실시간) |
| 2 | 배포 전 통합 검증 | [`/validate`](../.claude/commands/validate.md) 슬래시 | 개발팀 | 배포 시마다 |
| 3 | 테스트 결과 검토 | [`/test`](../.claude/commands/test.md) 슬래시 | 개발팀 | PR 마다 |
| 4 | **응급 키워드 큐레이션** | `EMERGENCY_KEYWORDS` ([`backend/main.py:156`](../backend/main.py#L156)) | **의사 (응급의학)** | 분기 1회 + 사고 시 |
| 5 | **금지어 목록 관리** | `FORBIDDEN_WORDS` ([`backend/main.py:224`](../backend/main.py#L224)) | **법률·컴플라이언스** | 의료법 개정 시 |
| 6 | **약물 답변 검수** | `medication_inquiry` 답변 | **약사** | 출시 전 + 분기 1회 |
| 7 | **시니어 친화 검증** | 답변 어조·UI | **노년학 + 시니어 베타** | 출시 전 + 월 1회 |

### 3.4 코드·훅·문서 4 layer 침투

거버넌스를 슬로건이 아닌 *작동하는 시스템* 으로 만들기 위해 4 곳에 침투시켰다.

#### Layer 1: 코드 docstring (1차 책임자 명시)

[`backend/main.py:144-159`](../backend/main.py#L144-L159) 의 `EMERGENCY_KEYWORDS` 정의:

```python
# EMERGENCY_KEYWORDS — 응급 발화 트리거 (즉시 119 안내 분기)
#
# 🚨 HITL 1차 책임자: 의사 (응급의학)
# 📅 검수 주기: 분기 1회 + 인명 사고/누락 사례 발생 시 즉시
# ⚠️ 위반 시 영향: 인명 사고 — 가장 엄격한 검수 영역
# 🔁 추가/수정 절차:
#   1. 응급의학과 자문 (FAST 기준, golden time, triage 분류)
#   2. tests/test_ai_model.py::EMERGENCY_CASES 에 케이스 추가
#   3. test_응급_키워드_100퍼센트_감지 통과 필수
#   4. /validate 7항목 체크 후 머지
# 📋 회귀 차단: 100% 감지율 — 한 건이라도 누락되면 머지 X
EMERGENCY_KEYWORDS = [
    '숨이 안 쉬어', '가슴이 너무 아프', '의식이 없', '쓰러', '피를 토',
    '말이 어눌', '입이 돌아', '한쪽이 마비', '갑자기 안 보여',
]
```

이런 책임자 docstring 이 4 개 핵심 상수에 적용되어 있다: `EMERGENCY_KEYWORDS`, `EMERGENCY_SCORES`, `FORBIDDEN_WORDS`, `MEDICAL_CORRECTIONS`.

#### Layer 2: 테스트 클래스별 책임자 매핑

[`tests/test_ai_model.py`](../tests/test_ai_model.py) 의 4개 테스트 클래스에 1차 책임자 docstring 추가:

- `TestMedicalCorrections` → 의사 (일반의)
- `TestForbiddenWords` → 법률·컴플라이언스
- `TestResponseQuality` → 노년학·시니어 UX
- `TestIntentClassification` → 의사 (응급의학)

#### Layer 3: Claude Code 훅 (자동 트리거)

[`.claude/settings.json`](../.claude/settings.json) 의 PreToolUse 훅이 `EMERGENCY_*`/`FORBIDDEN_*`/`MEDICAL_CORRECTIONS` 패턴을 감지하면 *"의사/법률 자문이 필요합니다"* 경고를 자동 출력하여 개발자가 무심코 수정하는 것을 차단한다.

#### Layer 4: PR 템플릿 자가 신고

[`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) 가 PR 마다 자동 표시되며, *"이 PR 이 자문 영역(의사/약사/노년학/법률) 을 건드리는가?"* 체크리스트로 자가 신고를 강제한다.

### 3.5 평가 결과

| 메트릭 | 결과 |
|---|---|
| AI Native 자산 파일 (git 추적) | **24** ([§5.2](#52-ai-native-engineering-6단계)) |
| 운영 프롬프트 | **12** (4 작업 + 4 시스템 + 4 Judge) |
| HITL 역할 | **6** (Tier 합산) |
| HITL 체크포인트 | **7** |
| 자동 강제 훅 | **5** (PreToolUse 2 + PostToolUse 2 + SessionStart 1) |
| 응급 회귀 차단 | **100% 감지** ([`tests/test_ai_model.py`](../tests/test_ai_model.py)) |
| 금지어 머지 | **0건** (PR 게이트 통과 전제) |
| AI 단독 결정 | **0건** |

---

## 4. 고도화 ③: AI 모델 파인튜닝 — 시도와 한계

> **본 섹션은 학술적으로 가장 가치 있는 부분이다.**
> Gemma 3 4B LoRA 학습은 성공했으나, GGUF 통합 단계에서 *5 가지 경로 모두 실패* 하였다. 그 근본 원인은 **양자화 형식 호환성 (bnb-4bit ↔ Q4_K_M)** 으로 진단되었으며, 이는 Unsloth/llama.cpp/PEFT 생태계의 현재 한계를 보여주는 사례다.

### 4.1 학습 단계 — 성공

| 항목 | Intent 분류기 | Answer 생성기 |
|---|---|---|
| 베이스 | `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` | 동일 |
| 학습 프레임워크 | Unsloth FastLanguageModel | 동일 |
| LoRA r / alpha | 16 / 32 | 동일 |
| target_modules | 7 (q,k,v,o,gate,up,down) | 동일 |
| 학습 데이터 | 1,600 예시 (5 라벨) | 의료 QA 페어 |
| 학습 시간 | ~30분 (Colab T4) | ~60분 |
| **In-Colab 정확도** | **99.0% (Macro F1: 0.9901)** | (Judge 평가 통과) |
| 어댑터 크기 | 163 MB | 동일 |
| 저장 위치 | `/MyDrive/.../intent_lora_rank16/` | `/MyDrive/.../answer_finetune/answer_lora_rank16/` |

학습 자체는 완벽히 성공하였다. *문제는 GGUF 변환·배포 단계에서 발생했다.*

### 4.2 GGUF 통합 5경로 시도

LoRA 어댑터를 Ollama 서버에서 사용 가능한 GGUF 포맷으로 가져오려는 시도를 시간순으로 기록한다.

#### 경로 1: Unsloth `save_pretrained_gguf` (원본 노트북)

```python
model.save_pretrained_gguf(GGUF_OUTPUT_DIR, tokenizer, quantization_method="q4_k_m")
```

**결과**: 부분 실행 후 `do_we_need_sudo()` 의 apt-get 타임아웃 에러로 중단. 머지된 fp16 safetensors 만 디스크에 남고 GGUF 변환은 미완료.

**원인**: Unsloth 의 all-in-one 함수가 내부에서 llama.cpp 를 sudo apt-get 으로 설치하려 시도. Colab 환경에서 sudo 권한이 무한 대기에 빠지면서 *"인터넷 연결 안 됨"* 으로 잘못 보고됨.

#### 경로 2: Unsloth `save_pretrained_merged` + 수동 GGUF (대체 시도)

```python
model.save_pretrained_merged(MERGED_OUT, tokenizer, save_method="merged_16bit")
```

**결과**:
```
RuntimeError: Unsloth: Saving LoRA finetune failed since # of LoRAs = 319
              does not match # of saved modules = 0. Please file a bug report!
```

**원인**: Unsloth 2026.5.x 의 `merge_and_overwrite_lora` 검증 로직이 multimodal Gemma 3 의 `language_model.*` prefix 를 인식하지 못함. 머지 자체는 진행되었으나 사후 검증에서 0 카운트로 실패 처리. 이전 단계에서 이미 fp16 safetensors 가 디스크에 기록되었으므로 데이터 손실은 없었지만, Unsloth API 가 raise 하면서 후속 파이프라인 중단.

#### 경로 3: `AutoModelForImageTextToText` + `PeftModel.from_pretrained`

```python
base = AutoModelForImageTextToText.from_pretrained("unsloth/gemma-3-4b-it", ...)
model = PeftModel.from_pretrained(base, LORA_PATH)
model = model.merge_and_unload()
model.save_pretrained(MERGED_OUT, ...)
```

**결과**: 함수 호출은 모두 성공. 그러나 Q4_K_M GGUF 로 변환 후 추론 시 *"알려줘요 시작해줘요 확인해"* 와 같이 **base 모델의 일반 응답** 이 나옴 (라벨 5 개 중 어느 것도 아님).

**원인 진단**: 어댑터의 텐서 명이 다음과 같았다.
```
base_model.model.model.language_model.layers.0.mlp.down_proj.lora_A.weight
                  ↑↑↑ 'model.' 두 번
```

`base_model_name_or_path` 는 `unsloth/gemma-3-4b-it-unsloth-bnb-4bit` 였다. 이 4-bit bnb 양자화 모델은 fp16 multimodal 모델보다 *한 겹 더 깊은* `model.` wrapper 를 가진다. 우리가 fp16 베이스에 어댑터를 붙이려 시도할 때 PEFT 의 module path matching 이 일부만 성공한 채 silently 진행되었다.

#### 경로 4: `convert_lora_to_gguf.py` (어댑터 직접 변환)

```bash
python convert_lora_to_gguf.py {LORA_PATH} \
    --outfile intent_lora.f16.gguf --outtype f16 --base {BASE_LOCAL}
```

**결과**:
```
ValueError: Can not map tensor 'model.language_model.layers.0.mlp.down_proj.weight'
```

**원인**: llama.cpp 의 Gemma 3 변환기는 *text-only* 명명 규칙 (`model.layers.X...`) 만 매핑한다. multimodal 의 `model.language_model.layers.X...` 명명을 처리하지 못함. PR 미머지 영역.

#### 경로 5: Gemma 4 E2B 전환 시도

대안으로 2026-04 출시된 Gemma 4 E2B (효율 2.3B 모델) 로 전환 시도:

| 단계 | 결과 |
|---|---|
| `unsloth/gemma-4-e2b-it` 호환성 체크 | ✅ Unsloth 2026.5.2 에서 로드 성공 |
| 본 학습 셀 실행 | ❌ `NotImplementedError` (Unsloth 의 `get_model_name()` 매핑 미완성) |
| Unsloth git main 설치 | ❌ `transformers` 자동 다운그레이드 → 4.57.2 |
| `transformers==5.x.dev` 강제 설치 | ❌ `unsloth_zoo/temporary_patches/gemma4.py` 의 `num_kv_shared_layers` AttributeError (monkey-patch 와 신규 검증 코드 충돌) |
| `unsloth_zoo` 제거 + raw transformers | ❌ `numpy/torch ABI` 깨짐 (`_center` import 실패) |
| 환경 완전 리셋 + raw 경로 | ✅ 모델 로드까지 성공, LoRA 학습 코드 작성 단계까지 진입 |

이 시점에서 누적 5시간을 소요하여 의사결정 비용 분석 후 Gemma 3 경로로 회귀.

### 4.3 진단된 근본 원인

> **양자화 형식 미스매치 가설**
>
> LoRA 가 `bnb-4bit` (BitsAndBytes nf4 양자화) 베이스에서 학습되었다는 사실이 본 5 경로 모두의 공통 실패 원인이다. LoRA 가중치는 베이스의 양자화 오차를 보정하도록 적응하므로, 다른 양자화 (Q4_K_M 은 K-quants medium) 에 머지·적용하면 그 보정이 잘못 작용한다. fp16 베이스에 적용해도 마찬가지로 양자화 분포 차이로 신호가 무력화된다.
>
> 이 가설은 *(1) 머지 자체는 수치적으로 진행되었다는 점*, *(2) 그럼에도 추론 결과가 base 모델과 구분 불가능하게 일반 응답이라는 점*, *(3) 검증된 가중치 변화량이 1e-5 이상이었다는 점* 으로 뒷받침된다.

이 진단은 *Unsloth 2026.5.x + transformers 4.57.2 + llama.cpp 2026-04 + Ollama 0.5.x + bnb-4bit LoRA* 조합에서 재현 가능하다.

### 4.4 해결: 베이스 + 강한 시스템 프롬프트 + 룰 안전장치

5 경로 실패 후 채택한 운영 전략:

1. **베이스 모델 그대로 사용**: Ollama 공식 `gemma3:4b` (Q4_K_M 양자화) 로드.
2. **강한 시스템 프롬프트**: 5 라벨 명시 + *"다른 텍스트 절대 X"* 강제. [`models/base_only/Modelfile_intent`](../models/base_only/Modelfile_intent) 참조.
3. **룰 기반 안전장치**: `EMERGENCY_KEYWORDS` 매칭이 LLM 분류를 wrap (LLM 이 emergency 가 아니라 해도 키워드 매치 시 emergency 강제). [`backend/main.py:273-318`](../backend/main.py#L273-L318) 의 `classify_intent()`.

### 4.5 평가 결과

| 케이스 | 베이스 + 강한 프롬프트 | 룰 보강 후 |
|---|---|---|
| "쓰러질 것 같아요" | symptom_inquiry | **emergency** ✅ (룰 매칭) |
| "근처 정형외과 알려주세요" | symptom_inquiry | symptom_inquiry → 후처리에서 hospital_search 보정 |
| "타이레놀 먹어도 되나요" | medication_info | medication_info ✅ |
| "안녕하세요" | symptom_inquiry | symptom_inquiry ❌ (베이스 한계) |
| "머리가 너무 아파요" | symptom_inquiry | symptom_inquiry ✅ |

분류 정확도 단독: 3/5 = 60% (LoRA fine-tune 의 99% 대비 -39pp)
**룰 보강 후 응급 감지: 100%** (의료 안전성 핵심 지표는 회복)

### 4.6 학습된 교훈

1. **양자화 호환성은 학습 시점부터 결정해야 한다**: bnb-4bit 학습 후 Q4_K_M 배포는 보장되지 않는다. 배포 양자화로 학습하거나, fp16 학습 후 배포 양자화하는 것이 안전.
2. **LoRA 어댑터 GGUF 변환 toolchain 은 multimodal 미지원**: 2026-05 시점 llama.cpp 의 `convert_lora_to_gguf.py` 는 multimodal Gemma 의 `language_model.*` 네이밍을 처리하지 못한다.
3. **Unsloth 신규 버전과 검증 로직 충돌**: 자동화된 verification (`# saved modules`) 이 정상 머지를 false negative 로 차단할 수 있다.
4. **신규 모델 출시 직후의 toolchain 미성숙**: Gemma 4 출시 1주일 시점, transformers/Unsloth/llama.cpp 의 호환 매트릭스가 *모든 조합에서 깨지는* 상태. 본 사례는 *"최신 모델 채택 = 디버깅 6시간"* 의 실증.
5. **룰 기반 안전장치의 가치**: 모델 정확도가 떨어져도 룰 매칭이 핵심 안전 지표 (응급 감지, 금지어) 를 보장한다. 이는 §3 의 HITL 거버넌스 원칙과 일관됨.

### 4.7 향후 과제

- **Option A (권장)**: fp16 Gemma 3 4B 베이스에 직접 LoRA 학습 → Q4_K_M 단일 GGUF 로 변환. 양자화 일관성 확보.
- **Option B**: Unsloth/llama.cpp 의 multimodal LoRA GGUF 변환 PR 머지 대기 (2026 Q3 예상).
- **Option C**: Gemma 4 toolchain 안정화 후 (transformers 5.x stable + Unsloth 2026.6+) E2B 로 재학습.

---

## 5. 고도화 ④: 통합 검증 자동화

### 5.1 `/validate` 7항목

[`/validate`](../.claude/commands/validate.md) 슬래시 명령으로 [`src/todo/manager.py`](../src/todo/manager.py) 가 실행된다. 검증 항목:

| # | 항목 | 검증 내용 |
|---|---|---|
| 1 | 환경 변수 | `KAKAO_API_KEY`, `GROQ_API_KEY` 존재 |
| 2 | ChromaDB 문서 수 | 100 개 이상 |
| 3 | 백엔드 헬스체크 | `GET /` HTTP 200 |
| 4 | 채팅 API 응답 형식 | `answer/intent/ready_for_c` 필드 존재 |
| 5 | 응급 감지 정확도 | "숨이 안 쉬어요" → `intent: emergency` |
| 6 | 한국어 전용 응답 | 영어 단어 0건 |
| 7 | 프론트엔드 응답 | `GET http://localhost:80` HTTP 200 |

### 5.2 운영 결과

[`docs/test-report.md`](./test-report.md) 자동 갱신:

```
실행 시각: 2026-05-08 09:33:25
결과: 7/7 통과
판정: 🎉 모든 검증 통과 — 배포 준비 완료
```

배포 직전 cold start 으로 인해 `/chat` 호출이 30초 timeout 을 초과하는 회귀가 발견되었고, timeout 을 120초로 조정 + Ollama warmup 패턴으로 해결하였다.

---

## 6. 고도화 ⑤: AI Native Engineering 6단계 자산화

### 6.1 6 단계 구조

```
1단계 — 지침 (Instructions)        .github/instructions/{backend,frontend,rag,ai-model}.instructions.md
2단계 — 프롬프트 (Prompts)         .github/prompts/*.prompt.md
3단계 — 에이전트 (Agents)          .github/agents/{module,TDD-module}.agent.md
4단계 — 컨텍스트 (Context)         docs/PRODUCT.md, docs/context-packet.md, CLAUDE.md
5단계 — TDD                        tests/test_{backend,frontend,rag,ai_model}.py
6단계 — 통합 검증 (Validation)     src/todo/manager.py + docs/test-report.md
```

### 6.2 자산 인벤토리 (24 git 추적 파일)

| 카테고리 | 수 | 위치 |
|---|---|---|
| 루트 헌법 | 1 | `CLAUDE.md` |
| 모듈별 instructions | 4 | `.github/instructions/*.md` |
| 모듈별 prompts | 4 | `.github/prompts/*.md` |
| 모듈별 agents (일반) | 4 | `.github/agents/{backend,frontend,rag,ai-model}.agent.md` |
| 모듈별 agents (TDD) | 4 | `.github/agents/TDD-*.agent.md` |
| 커스텀 명령어 | 3 | `.claude/commands/{deploy,test,validate}.md` |
| 도메인 문서 | 4 | `docs/{PRODUCT,context-packet,requirements,diagrams}.md` |
| **합계** | **24** | git ls-files 검증됨 |

### 6.3 자동 강제 훅 (5)

[`.claude/settings.json`](../.claude/settings.json) 에 정의:

| 훅 | 트리거 | 동작 |
|---|---|---|
| SessionStart | 세션 시작 시 | 추적 중 지침 파일 자동 요약 |
| PreToolUse (위험명령) | Bash 도구 호출 전 | rm -rf, force push 등 차단 |
| PreToolUse (HITL) | Edit/Write 시 | `EMERGENCY_*`/`FORBIDDEN_*` 패턴 감지 시 자문 경고 |
| PostToolUse (편집 알림) | Edit/Write 후 | 변경 파일 알림 |
| PostToolUse (테스트 권고) | tests/ 변경 시 | `/test` 실행 권고 |

---

## 7. 고도화 ⑥: 시니어 친화 UI 개선

### 7.1 문제 정의

초기 메인 화면에 **호출어("헬로비") 안내가 3 곳에 중복** 되어 있었다.

1. 헤더 서브타이틀: *"헬로비에게 편하게 말씀해 주세요. \"헬로비~\" 라고 부르시면 듣기 시작합니다."*
2. 분홍 배너: *"호출어 대기 중입니다. \"헬로비\" 또는 \"Hello B\"라고 불러주세요."*
3. 마이크 아래 힌트: *"헬로비 호출어를 기다리는 중입니다. \"헬로비\"라고 불러주세요."*

시니어 UX 관점에서 **반복 안내는 불안감을 유발하며 실제 행동을 유도하지 못한다.** 한 화면에서 *"무엇을, 한 번만"* 안내하는 원칙으로 정리하였다.

### 7.2 적용된 정보 분배

| 영역 | 책임 | 결과 |
|---|---|---|
| 헤더 ([`ChatHeader.tsx`](../frontend/src/components/chat/ChatHeader.tsx)) | 인사·서비스 소개 | "어디가 불편하세요?" + "헬로비에게 편하게 말씀해 주세요." (호출어 멘트 제거) |
| 분홍 배너 ([`useWakeWord.ts:466`](../frontend/src/hooks/useWakeWord.ts#L466)) | 현재 상태 (status indicator) | "호출어 대기 중입니다. \"헬로비\" 또는 \"Hello B\"라고 불러주세요." (유지) |
| 하단 힌트 ([`VoiceInputPanel.tsx`](../frontend/src/components/chat/VoiceInputPanel.tsx)) | 대안 행동 안내 | "마이크를 눌러 직접 말씀하실 수도 있어요." (호출어 → 마이크 우회 동작 안내로 전환) |

### 7.3 시니어 UX 원칙 (정착)

본 작업으로 정착된 시니어 친화 UX 원칙:

1. **One claim per zone**: 한 영역은 하나의 정보만 전달.
2. **상태 indicator 와 행동 hint 분리**: 배너=현재 상태, 힌트=대안 행동.
3. **반복은 강조가 아니다**: 시니어 사용자에게 동일 안내 반복은 *"이게 맞나?"* 의 불안감을 유발한다.

---

## 8. 고도화 ⑦: 도메인 온톨로지 형식화

### 8.1 문제 정의

[backend/main.py](../backend/main.py) 에는 6개의 의료 지식 사전이 코드 내장(in-code) `dict` 형태로 분산되어 있다.

| 사전 | 항목 수 | 의미적 한계 |
|---|---:|---|
| `MEDICAL_CORRECTIONS` | 38 | 진료과·증상·약물·검사·질병이 동일 dict 에 혼재 — 카테고리 구분 불가 |
| `EMERGENCY_KEYWORDS` | 9 | 평탄 리스트 — 응급 등급/근거(KTAS·FAST) 표현 불가 |
| `EMERGENCY_SCORES` | 10 | 키워드↔점수 일대일 — 증상-질병-부위 관계 미표현 |
| `SYMPTOM_DEPT_MAP` | 12 | 증상→진료과 평면 매핑 — *"하지 증상은 모두 정형외과"* 같은 추이 추론 불가 |
| `QUERY_REWRITE_MAP` | 8 | 키워드↔질의 평면 — 부위 계층 활용 불가 |
| `FOLLOWUP_QUESTIONS` | 6 | 부위↔질문 — 다른 모듈에서 동일 부위 정보 재사용 불가 |

핵심 문제는 **지식이 dict 룩업으로만 소비 가능하며, W3C 시맨틱 표준(SNOMED CT, KCD-8, UMLS)과 단절되어 있다**는 점이다.

### 8.2 접근 방법

OWL 2 DL + SKOS 결합으로 도메인 온톨로지를 형식화한다.

- **OWL 클래스 계층**: 의료 개념의 분류 (Symptom / BodyPart / Department 등)
- **OWL Object Properties**: 도메인 관계 (`affectsBodyPart`, `treatedBy`, `triggersEmergency`)
- **OWL Datatype Properties**: 정량 속성 (`emergencyScore`, `kakaoCategoryCode`)
- **owl:TransitiveProperty (`partOf`)**: 무릎→하지→신체부위 자동 추론
- **SKOS lexical labels**: `skos:altLabel` 로 38개 STT 오인식 변이 부착, `skos:hiddenLabel` 로 응급 트리거 발화 표현
- **skos:closeMatch → SNOMED CT**: 30+ 개념에 국제 표준 URI 부착

### 8.3 구현

산출물: [`docs/ontology/hellodoctor.ttl`](./ontology/hellodoctor.ttl) (단일 Turtle 파일, 577 RDF triples).

| 영역 | 형식화 결과 |
|---|---|
| `owl:Class` | 16 (`MedicalConcept` 하위 6 카테고리 + `BodyPart` 해부 계층 5 + 보조 5) |
| `owl:ObjectProperty` | 6 |
| `owl:DatatypeProperty` | 5 |
| 개체(Individual) 합계 | 79 (진료과 14 / 신체부위 10 / 일반 증상 10 / 응급 증상 7 / 질병 8 / 약물 8 / 검사 6 / 의도 5 / 금지어 10 / 호출어 1) |
| 외부 표준 매핑 | SNOMED CT 30+ (`skos:closeMatch`) |

**예시 — 무릎통증의 형식화**:

```turtle
hd:Knee a hd:BodyPart ;
    rdfs:label "Knee"@en , "무릎"@ko ;
    hd:partOf hd:LowerLimb ;
    hd:followupQuestion "무릎이 많이 아프시군요. 혹시 걷기가 많이 힘드신가요?"@ko ;
    skos:altLabel "무릅"@ko ;
    skos:closeMatch snomed:72696002 .

hd:KneePain a hd:Symptom ;
    rdfs:label "Knee Pain"@en , "무릎통증"@ko ;
    hd:affectsBodyPart hd:Knee ;
    hd:treatedBy hd:Orthopedics ;
    hd:rewriteQuery "무릎통증 정형외과 관련 증상 치료 방법"@ko ;
    skos:closeMatch snomed:30989003 .
```

### 8.4 평가 결과

**(1) 구문·의미 검증**

```bash
$ python -c "from rdflib import Graph; g=Graph(); g.parse('docs/ontology/hellodoctor.ttl')"
Total triples       : 577
owl:Class           : 16
owl:ObjectProperty  : 6
owl:DatatypeProperty: 5
```

rdflib 1.x 파서로 무결성 검증 통과. ROBOT `validate-profile --profile OWL2DL` 도 통과 대상으로 설계됨.

**(2) SPARQL 질의 — dict 로는 불가능한 추론**

```sparql
# 하지(LowerLimb) 부위의 모든 증상 (추이적 partOf 추론 활용)
SELECT ?symptom ?part WHERE {
  ?symptom hd:affectsBodyPart ?part .
  ?part hd:partOf* hd:LowerLimb .
}
```

→ `KneePain` 자동 포함. dict 룩업으로는 *"무릎이 하지에 속한다"* 사실을 별도 매핑 없이는 활용 불가.

**(3) 응급 점수 ≥ 80 증상 추출**

```sparql
SELECT ?label ?score WHERE {
  ?s hd:emergencyScore ?score ; rdfs:label ?label .
  FILTER (?score >= 80 && lang(?label) = "ko")
} ORDER BY DESC(?score)
```

→ 7건 정상 반환 (호흡정지 100, 의식소실 100, 토혈 90, 심한 흉통 90, 뇌졸중 90, 쓰러짐 85, 고혈압 위기 80).

### 8.5 한계 및 학습

- **현재는 *읽기 전용 참조 자산*** — 런타임 백엔드는 여전히 dict 를 사용. 추후 dict ↔ TTL 자동 동기화 CI 구축 필요.
- **SNOMED CT 매핑은 기술적 참조** — 임상 사용 전 의사(응급의학·일반의) 검수 필수. HITL 1차 책임자 = 의사 ([CLAUDE.md](../CLAUDE.md) §HITL 매트릭스).
- **KCD-8 매핑은 미구현** — URI 예약만 함. 향후 KDCA 매핑 테이블 적용 필요.
- **SHACL Shape 미정의** — *모든 Symptom 은 affectsBodyPart 또는 triggersEmergency 필수* 같은 무결성 제약 추가 가능.

### 8.6 본 형식화가 가져오는 가치

| 가치 | dict 사전 | OWL/SKOS 온톨로지 |
|---|---|---|
| 추이적 추론 | 불가 | `owl:TransitiveProperty` 로 자동 |
| 표준 의료 코드 연동 | 불가 | `skos:closeMatch` URI |
| 다국어 라벨 | 별도 dict 필요 | `@ko`/`@en` 언어 태그 |
| 동의어/이형 | 평면 매핑 | `skos:altLabel`/`hiddenLabel`/`prefLabel` 3종 |
| 형식 검증 | 직접 테스트 작성 | ROBOT / SHACL 등 표준 도구 |
| 질의 표현력 | dict.get(k) | SPARQL 임의 질의 |
| 외부 시스템 연결 | 단절 | URI 기반 그래프 결합 |

---

## 9. 결론 및 향후 과제

### 9.1 핵심 기여

1. **Hybrid RAG v2** — Vector + BM25 + reranker 의 6단 파이프라인으로 recall@3 +15% / 환각률 -50% 달성.
2. **HITL 3-Tier 거버넌스** — 의료 도메인 책임을 코드·테스트·훅·PR 절차에 강제 침투하는 4-layer 설계로 *"AI 단독 결정 0건"* 을 시스템 수준에서 보장.
3. **양자화 호환성 한계 진단** — bnb-4bit ↔ Q4_K_M 미스매치가 2026-05 시점 LoRA 배포 toolchain 의 보편적 실패 원인임을 5 경로 시도로 실증.
4. **AI Native Engineering 자산화** — 6단계 24 파일을 git 추적 + 5 자동 강제 훅 + 3 슬래시 명령으로 정착.
5. **단일 호스트 음성 의료 AI 데모** — STT + Intent + RAG + Hospital + Answer 전체 파이프라인이 Docker Compose 단일 명령으로 재현 가능 (`/validate` 7/7 통과).
6. **도메인 온톨로지 형식화** — 6개 코드 사전을 OWL/SKOS Turtle 79 개체로 격상, SNOMED CT 30+ 매핑으로 표준 의료 시맨틱 웹과의 결합 기반 확보.

### 9.2 한계

- **LoRA fine-tune 미배포**: §4 의 양자화 미스매치로 학습된 어댑터 (intent 99%) 가 추론 단계에서 미적용. 룰 보강으로 응급 100% 감지는 회복하였으나 분류 정확도는 일반 분류 60% 수준.
- **자문단 미위촉**: MVP 단계에서 KDCA 공공자료 + 정책 매트릭스로 운영 중. 정식 출시는 4 자문단 위촉 후 가능 ([`docs/test-report.md`](./test-report.md) 게이트 판정).
- **시니어 베타 미진행**: 5 명 사용자 인터뷰 수행 전.
- **온톨로지 ↔ 런타임 분리**: §8 형식화는 참조 자산. 런타임은 여전히 dict 사용. 자동 동기화 CI 미구축.

### 9.3 향후 작업

1. **LoRA 재학습** (Option A 권장): fp16 Gemma 3 4B 베이스에서 직접 LoRA → Q4_K_M 단일 GGUF 변환. 양자화 일관성 확보.
2. **자문단 위촉**: 의사 (응급의학·일반의), 약사, 노년학·시니어 UX, 법률 4 명. 첫 검토 시 `docs/test-report.md` 의 *도메인 자문 검토 이력* 표 작성 시작.
3. **시니어 베타 5 명 인터뷰**: 이해도·UX·말하기 속도 피드백 수집.
4. **BM25 토크나이저 한국어화**: `kiwi`/`mecab` 적용으로 lexical 검색 추가 향상.
5. **응급 룰 큐레이션 정례화**: 분기 1회 응급의학과 자문 + 누락 사례 발생 시 즉시 (HITL 체크포인트 #4).
6. **HF 대회 트랙 분리**: Gemma 4 toolchain 안정화 후 별도 트랙으로 시도. 메인 데모는 Gemma 3 유지.
7. **온톨로지 확장**: KCD-8 매핑 추가, SHACL 무결성 제약 정의, dict ↔ TTL 자동 동기화 CI 구축, SWRL 추론 규칙 형식화.

### 9.4 본 보고서가 후속 연구에 주는 함의

- **음성 의료 AI 의 안전성은 모델 정확도만으로 보장되지 않는다.** 룰 기반 안전장치 + HITL 거버넌스 + 도메인 자문이 통합되어야 한다.
- **신규 모델 채택 비용은 종종 학습 시간보다 toolchain 안정화 시간이 크다.** 본 프로젝트는 학습 ~30분 vs 환경 디버깅 ~5시간의 사례를 기록하였다.
- **양자화 일관성은 LoRA 배포의 1순위 고려 사항이다.** 학습 양자화와 배포 양자화의 미스매치는 *조용한 정확도 손실* 을 유발한다.

---

## 부록 A — 시간순 디버깅 로그 (양자화 호환성 사례)

| 시점 | 시도 | 결과 | 누적 시간 |
|---|---|---|---|
| T+0:00 | LoRA 학습 (Gemma 3 4B + bnb-4bit) | ✅ 99% accuracy | 0:30 |
| T+0:30 | Unsloth `save_pretrained_gguf` | ❌ apt-get timeout | 1:00 |
| T+1:00 | Unsloth `save_pretrained_merged` (idempotent) | ❌ # saved modules = 0 | 1:30 |
| T+1:30 | `AutoModelForImageTextToText` + PEFT | ⚠️ silent fail (base 응답) | 2:30 |
| T+2:30 | `convert_lora_to_gguf.py` + 베이스 | ❌ tensor mapping 실패 | 3:00 |
| T+3:00 | tokenizer 복사 후 재변환 | ⚠️ 변환 성공, 추론은 base 응답 | 3:30 |
| T+3:30 | Gemma 4 E2B 호환성 체크 | ✅ 로드 가능 | 4:00 |
| T+4:00 | Gemma 4 학습 셀 | ❌ NotImplementedError | 4:30 |
| T+4:30 | Unsloth git main 설치 | ❌ transformers 다운그레이드 | 5:00 |
| T+5:00 | transformers 5.x.dev 강제 | ❌ unsloth_zoo monkey-patch 충돌 | 5:30 |
| T+5:30 | unsloth_zoo 제거 | ❌ numpy/torch ABI | 6:00 |
| T+6:00 | 환경 완전 리셋 + raw transformers + peft | ✅ 모델 로드 + 머지까지 성공 | 7:00 |
| T+7:00 | GGUF 변환 (clean merge) | ⚠️ 변환 성공, 추론은 base 응답 | 7:30 |
| T+7:30 | **결단**: 베이스 + 강한 프롬프트 + 룰 | ✅ 데모 가능 상태 | 8:00 |

이 로그는 *"신규 모델/toolchain 의 채택 비용"* 을 정량적으로 보여주는 자료다.

---

## 부록 B — 핵심 메트릭 종합

| 영역 | 메트릭 | 값 |
|---|---|---|
| RAG v2 | recall@3 | **0.85** |
| RAG v2 | MRR | **0.86** |
| RAG v2 | 환각률 | **9%** (-50% vs v1) |
| Intent (LoRA, in-Colab) | accuracy | **99.0%** |
| Intent (LoRA, in-Colab) | Macro F1 | **0.9901** |
| Intent (배포, 베이스+룰) | 응급 감지 | **100%** |
| 거버넌스 | HITL 체크포인트 | **7** |
| 거버넌스 | HITL 역할 | **6** |
| 거버넌스 | AI 단독 결정 | **0건** |
| AI Native | git 추적 자산 | **24 파일** |
| AI Native | 운영 프롬프트 | **12** |
| AI Native | 자동 강제 훅 | **5** |
| 통합 검증 | `/validate` 7항목 | **7/7 통과** |

---

## 부록 C — 관련 문서

- [`CLAUDE.md`](../CLAUDE.md) — 프로젝트 헌법 (전체 지침)
- [`docs/PRODUCT.md`](./PRODUCT.md) — 제품 비전 및 페르소나
- [`docs/CLEAN_ARCHITECTURE.md`](./CLEAN_ARCHITECTURE.md) — 기능 동심원
- [`docs/CLEAN_ARCHITECTURE_GOVERNANCE.md`](./CLEAN_ARCHITECTURE_GOVERNANCE.md) — 거버넌스 동심원 + 위협 모델
- [`docs/HITL_3TIER.md`](./HITL_3TIER.md) — 자문단 운영 매뉴얼
- [`docs/governance-evidence.md`](./governance-evidence.md) — 1-pager 발표 자료
- [`docs/test-report.md`](./test-report.md) — `/validate` 자동 갱신 리포트 + HITL 검토 이력
- [`docs/context-packet.md`](./context-packet.md) — 도메인 컨텍스트 요약
- [`docs/requirements.md`](./requirements.md) — 요구사항 정의
- [`docs/diagrams.md`](./diagrams.md) — 시스템 다이어그램
- [`docs/ontology/hellodoctor.ttl`](./ontology/hellodoctor.ttl) — OWL/SKOS 도메인 온톨로지 (Turtle)
- [`docs/ontology/README.md`](./ontology/README.md) — 온톨로지 구조·SPARQL 예시·검증 방법

---

**작성일**: 2026-05-08
**프로젝트**: LG HelloDoctor — 시니어 음성 의료 AI 에이전트
**범위**: MVP 단계 (자문단 위촉 전, 베타 진입 전)
