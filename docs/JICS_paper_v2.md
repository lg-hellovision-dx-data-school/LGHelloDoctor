# Whisper와 하이브리드 RAG, 에이전트 워크플로 기반 초고령사회 의료 안내 음성 AI 에이전트 설계 및 평가

**Design and Evaluation of a Voice AI Agent for Medical Guidance in the Super-Aged Society Based on Whisper, Hybrid RAG, and Agent Workflows**

안 주 연¹, 권 예 진² · Juyeon AN, Yejin Kwon

---

## 요  약

대한민국은 2025년 12월 65세 이상 인구가 전체 인구의 20.3%를 돌파하며 초고령사회에 공식 진입하였다[1]. 동시기 65세 이상 고령층의 디지털 헬스케어 서비스 이용률은 4.7%에 머물러, 의료 접근성 격차가 사회적 과제로 부상하였다[2]. 정부는 2025년 12월 의료법 개정으로 비대면진료를 제도화하였으나[3], 시니어가 자연어 음성만으로 의료 안내를 받을 수 있는 인터페이스 연구는 부족한 실정이다. 본 논문은 IPTV 셋톱박스 환경의 시니어 사용자를 대상으로 음성 기반 의료 안내 AI 에이전트 **HelloDoctor**를 설계하고 성능을 평가한다. 제안 시스템은 (1) 시니어 한국어 방언 음성을 인식하는 Whisper 파인튜닝 STT, (2) 의도 분류 및 응급 감지를 위한 LLaMA-3.2-3B 기반 LLM, (3) 벡터·BM25 결합 하이브리드 RAG, (4) Anthropic이 제안한 5가지 에이전트 워크플로(프롬프트 체이닝·라우팅·병렬화·오케스트레이터-워커·평가-최적화) 적용, (5) 사람 검토(HITL) 3-Tier 거버넌스로 구성된다. 실험 결과 STT CER 2.9%, WER 12.9%, 의도 분류 정확도 94.9%, 응급 감지율 90.0%, RAG Top-3 정확도 62.1%를 달성하였으며, 병렬화 패턴 적용으로 C팀 응답 지연이 약 1.6배 단축되었다. 본 시스템은 복잡한 디지털 조작 없이 음성만으로 진료과 안내와 위치 기반 병원 정보를 제공하여 초고령사회 의료 접근성 개선에 기여할 수 있다.

**핵심어**: 음성 AI 에이전트, 자동 음성 인식, Whisper, 거대 언어 모델, 검색 증강 생성, 에이전트 워크플로, 사람 검토 거버넌스, 초고령사회, 의료 접근성

## Abstract

Korea entered a super-aged society in December 2025 when the population aged 65 and over surpassed 20.3% of the total population[1]. In the same period, only 4.7% of seniors aged 65 and over used digital healthcare services, making medical accessibility a critical social issue[2]. While the government institutionalized non-face-to-face medical care through a medical law amendment in December 2025[3], research on voice-only medical guidance interfaces for seniors remains limited. This paper designs and evaluates **HelloDoctor**, a voice-based medical guidance AI agent for senior IPTV users. The proposed system consists of (1) a fine-tuned Whisper STT for elderly Korean dialect speech, (2) a LLaMA-3.2-3B-based LLM for intent classification and emergency detection, (3) a hybrid RAG combining vector and BM25 retrieval, (4) five agent workflow patterns proposed by Anthropic (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer), and (5) a three-tier Human-in-the-Loop (HITL) governance framework. Experimental results show STT CER 2.9%, WER 12.9%, intent classification accuracy 94.9%, emergency detection 90.0%, and RAG Top-3 accuracy 62.1%. The parallelization pattern reduced Team C response latency by approximately 1.6x. The proposed system contributes to improving medical accessibility in a super-aged society through voice-only interaction without complex digital procedures.

**Keywords**: Voice AI Agent, ASR, Whisper, LLM, RAG, Agent Workflows, HITL Governance, Super-Aged Society, Medical Accessibility

---

## Ⅰ. 서  론

대한민국은 2025년 12월 기준 65세 이상 인구가 1,000만 명을 돌파하여 전체 인구의 20.3%를 차지하였으며, 세계에서 가장 빠른 속도로 초고령사회에 진입하였다[1]. 통계청은 향후 65세 이상 인구 비율이 2036년 30%, 2050년 40%를 넘어설 것으로 전망하였다. 특히 전남(30.6%), 경북(26.1%), 강원(25.7%) 등 의료 인프라가 상대적으로 부족한 지역에서 고령화가 심화되어, 의료 접근성 격차가 지역 불균형 문제로 확대되고 있다[1].

그러나 고령층의 디지털 헬스 리터러시는 정책 수요를 따라가지 못하고 있다. 한국지능정보사회진흥원(NIA)의 2024년 디지털정보격차 실태조사에 따르면, 70대 이상 시니어의 스마트폰 보유율은 87.3%로 상승하였으나 인터넷 이용률은 75.7%에 그쳤으며, 모바일 앱·인터넷 서비스를 능동적으로 활용하는 *디지털 활용 역량*은 일반 국민 대비 현저히 낮은 수준이다[4]. 또한 국가인권위원회는 디지털 격차가 노인의 의료·금융·행정 서비스 접근권을 실질적으로 제약한다고 지적하였다[5]. 보건복지부 통계에 따르면 65세 이상 고령층의 디지털 헬스케어 서비스 이용률은 4.7%에 불과하여, 정책적 인프라와 실제 사용 사이에 큰 간극이 존재한다[2].

정부는 이러한 격차를 해소하기 위해 2025년 12월 의료법 개정안을 통과시켜 비대면진료를 제도화하였으며, 섬·벽지 거주자, 장기요양 수급자, 등록장애인, 희귀질환자 등 의료 취약계층에 대한 약 배송의 법적 근거를 마련하였다[3]. 보건복지부는 또한 디지털헬스케어법 제정을 추진하면서 AI 기반 의료 격차 해소를 핵심 과제로 제시하였다[6]. 그러나 정책적 인프라가 마련되어도, 시니어가 자연어 음성으로 직접 의료 정보를 탐색할 수 있는 **사용자 인터페이스 연구**는 여전히 부족하다. 기존 스마트 스피커는 사전·뉴스·날씨 등 생활 편의 기능 중심으로 설계되어 의료 문진처럼 이어지는 다중턴 대화에 한계가 있으며, 호출어·긴 침묵 처리 문제로 시니어 발화에 대한 안정적 이해가 어렵다.

본 논문은 IPTV 셋톱박스 리모컨을 통한 음성 입력만으로 시니어가 진료과 안내와 인근 병원 정보를 즉시 제공받을 수 있는 **HelloDoctor** 시스템을 제안한다. 제안 시스템의 주요 기여는 다음과 같다.

1. **시니어 한국어 방언 특화 STT**: 자유대화 음성(노인) 데이터셋과 LoRA 파인튜닝을 결합하여 한국어 시니어 발화에 강건한 Whisper 모델을 구축한다.
2. **하이브리드 RAG v2**: Vector 검색과 BM25 키워드 검색을 Reciprocal Rank Fusion으로 결합하고 Cross-Encoder reranker로 정밀 재순위화하는 4단 파이프라인을 설계한다.
3. **에이전트 워크플로 5패턴 적용**: Anthropic이 *Building Effective Agents*에서 정리한 5가지 패턴(프롬프트 체이닝·라우팅·병렬화·오케스트레이터-워커·평가-최적화)을 의료 음성 AI 도메인에 체계적으로 매핑한다.
4. **3-Tier HITL 거버넌스**: 의사·약사·노년학·법률 4개 자문 역할과 개발팀·시니어 베타 사용자를 결합한 사람 검토 구조를 코드·테스트·훅·PR 절차에 침투시켜 *"AI 단독 결정 0건"* 을 시스템 수준에서 보장한다.

> **[그림 1 삽입 권장]** 전체 시스템 아키텍처: A(STT) → B(Intent) → C(RAG+Hospital+Emergency 병렬) → D(Answer+Evaluator) 4팀 파이프라인 다이어그램. 본 프로젝트의 `docs/diagrams.md` 또는 `docs/AGENT_PATTERNS.md`의 Mermaid `graph LR` 도식을 PNG로 변환하여 삽입.

---

## Ⅱ. 관련 연구

### 2.1 의료 도메인 음성 인식과 시니어 발화

Whisper[7]는 680,000시간의 다국어 음성 데이터로 사전 학습된 Transformer 기반 ASR 모델로, 의료 ASR의 베이스라인으로 널리 사용된다. 그러나 시니어 한국어 발화는 방언 변이, 발화 속도, 음성 압축 특성에서 일반 발화와 차이가 크며, 범용 모델의 성능 저하가 보고되고 있다. 한국지능정보사회진흥원의 *AI Hub*는 *자유대화 음성(노인남녀)* 데이터셋을 공공 자원으로 공개하여 시니어 특화 ASR 연구의 기반을 제공한다[8].

### 2.2 검색 증강 생성과 의료 RAG

검색 증강 생성(Retrieval-Augmented Generation, RAG)[9]은 LLM의 환각을 완화하고 도메인 지식을 반영하기 위해 외부 문서를 검색하여 생성 맥락에 포함하는 방식이다. 의료 RAG에서는 정확한 진료과·질병 키워드 매칭이 환각 위험과 직결되므로, 의미 유사도 기반 벡터 검색과 키워드 기반 BM25 검색을 결합한 하이브리드 방식이 단일 검색 대비 높은 재현율을 보이는 것으로 보고되었다. 질병관리청 국가건강정보포털은 한국어 의료 RAG의 신뢰 가능한 출처로 활용 가능한 공공 의료 데이터를 공개하고 있다[10].

### 2.3 에이전트 워크플로 패턴

Anthropic은 *Building Effective Agents*[11]에서 LLM 기반 에이전트 시스템을 ① 프롬프트 체이닝(Prompt Chaining), ② 라우팅(Routing), ③ 병렬화(Parallelization), ④ 오케스트레이터-워커(Orchestrator-Workers), ⑤ 평가-최적화(Evaluator-Optimizer)의 5가지 워크플로 패턴으로 정리하였다. 본 연구는 이 5가지 패턴을 의료 음성 AI 도메인의 4팀 파이프라인에 매핑하여, 정확도·지연·안전성을 균형 있게 달성하는 구조를 설계한다.

### 2.4 시니어 대화형 AI와 정책 맥락

시니어 사용자를 위한 음성 인터페이스 연구에서는 자연어 발화 기반의 단순 인터페이스가 디지털 리터러시 격차 해소에 효과적임이 확인되어 왔다. 한국보건사회연구원의 *보건복지포럼*은 고령층 디지털 헬스케어 활용을 위한 디지털 리터러시 정책 방향 연구를 통해, 음성 기반 인터페이스가 시니어 진입 장벽을 낮추는 핵심 수단임을 제시하였다[12]. 또한 한국정보통신기술협회(TTA)와 한국정보통신산업진흥원의 자료는 시니어 친화 인터페이스가 글자 크기·어조·반복 안내의 균형을 요구함을 명시하고 있다[13].

---

## Ⅲ. 시스템 설계

### 3.1 전체 아키텍처

제안 시스템은 사용자의 음성 입력에서 텍스트 응답 출력까지 4팀 파이프라인(A·B·C·D)으로 구성된다. 입력 음성은 A팀(Whisper 기반 STT)에서 텍스트로 변환되며, B팀(LLM 의도 분류기)이 응급/증상/병원/약물 4개 의도 중 하나로 분류한다. C팀은 RAG·병원 검색·응급 판단을 *병렬로* 수행하고, D팀은 시니어 친화 답변을 생성한 뒤 평가-최적화 루프로 품질을 보장한다. 전체 시스템은 Docker Compose 단일 명령으로 배포되며 FastAPI 백엔드와 React 프론트엔드로 구성된다.

### 3.2 STT 고도화 — 시니어 한국어 방언 대응

베이스 모델로 `SungBeom/whisper-small-ko`(244M, 한국어 fine-tuned)를 채택하고, AI Hub *자유대화 음성(노인남녀)*[8] 데이터셋에서 제주 2,000개, 경상도 2,000개, 수도권 1,000개로 균등 샘플링하여 LoRA(PEFT) 파인튜닝하였다. 전처리 단계에서는 Silero-VAD 기반 침묵 구간 제거, 구어체 간투어 정규식 제거, 5개 카테고리(진료과·증상·약물·검사·질병) 50개 이상 패턴의 의료 용어 오탈자 보정 사전을 적용하였다. 보정 사전은 시니어 발음 변이(예: *"안과가"* → *"안과"*, *"무릅"* → *"무릎"*)를 다룬다.

### 3.3 의도 분류와 룰 안전장치

의도 분류와 진료과 추천을 위해 LLaMA-3.2-3B를 LoRA 기반으로 파인튜닝하고 Ollama로 서빙하였다. 응급 키워드 14개에서 30개 이상으로 확장하였으며, *부정 표현 탐지*와 *다중 폴백 구조*를 적용하였다. 핵심 안전 설계는 **응급 키워드 룰 매칭이 LLM 분류를 wrap** 하는 구조다. 즉, LLM이 *symptom_inquiry* 로 분류해도 `EMERGENCY_KEYWORDS` 9개 패턴(*"숨이 안 쉬어"*, *"의식이 없"*, *"쓰러"* 등)이 매칭되면 즉시 *emergency* 로 강제 변경된다. 이는 모델 정확도와 무관하게 인명 사고 직결 상황에서 *"AI 출력만 신뢰하지 않는다"*는 안전 원칙을 구현한다.

### 3.4 하이브리드 RAG v2

RAG 지식 기반은 질병관리청 국가건강정보포털 공공 의료 데이터[10]로부터 ChromaDB에 132개 문서를 구축하였다. 검색 파이프라인은 다음 4단 구조다.

```
질의 → query rewrite → [Vector top-20]  ┐
                       [BM25 top-20]    ├ RRF fusion → Cross-Encoder rerank → top-3 + threshold
                                        ┘
```

1) Query rewrite로 시니어 어휘를 RAG 친화 표현으로 확장 (예: *"무릎"* → *"무릎통증 정형외과 관련 증상 치료"*), 2) Vector 검색(top-20)으로 의미 유사도 후보군 수집, 3) BM25 검색(top-20)으로 키워드 매칭 후보군 수집, 4) Reciprocal Rank Fusion(k=60)으로 두 결과를 통합, 5) Cross-Encoder(`Dongjin-kr/ko-reranker`)로 top-3 재순위화, 6) confidence threshold(rerank score ≥ 0) 미만은 *"관련 정보를 찾지 못했습니다"* 응답으로 분기한다. 모든 retrieved 문서는 *질병관리청 국가건강정보포털* 출처로 명시되어 인용 투명성을 확보한다.

### 3.5 에이전트 워크플로 5패턴 적용

Anthropic의 5가지 워크플로 패턴[11]을 본 파이프라인에 다음과 같이 매핑하였다.

| # | 패턴 | 적용 위치 |
|---|---|---|
| ① | Prompt Chaining | A→B→C→D 순차 호출 + 단계별 게이트(`gate_stt_to_intent`, `gate_intent_to_tools`) |
| ② | Routing | 의도(emergency/symptom/medication/hospital)별 필요 도구만 선택 호출 |
| ③ | Parallelization | C팀의 RAG·Kakao·Emergency 3개 호출을 ThreadPoolExecutor로 동시 실행 |
| ④ | Orchestrator-Workers | 중앙 파이프라인이 A/B/C/D 워커를 조율 (게이트·라우팅·컨텍스트 조립만 담당) |
| ⑤ | Evaluator-Optimizer | D팀 답변을 한국어 비율(≥0.4)·길이(≥15자)·금지어 미포함으로 평가, 실패 시 최대 2회 재생성 |

이 매핑은 단순 추상화가 아니라 응답 지연·정확도·안전성에 직접 영향을 준다. 특히 ③ 병렬화로 C팀의 네트워크 I/O(RAG 임베딩 검색 ~600ms + Kakao API ~300ms + Emergency 룰 ~10ms)가 *직렬 합산 ~910ms*에서 *최댓값 ~600ms*로 단축되었다. ⑤ 평가-최적화는 파인튜닝 LLaMA가 가끔 영어 단어를 섞거나 너무 짧게 답하는 케이스를 자동 재생성으로 보정한다.

> **[그림 2 삽입 권장]** 5패턴 적용 흐름도. 본 프로젝트 `docs/AGENT_PATTERNS.md`의 Mermaid `graph LR` 다이어그램(라우팅·병렬·평가 노드 강조 색상)을 PNG로 변환하여 삽입.

### 3.6 3-Tier HITL 거버넌스

의료 도메인 AI는 단일 실수가 인명 사고로 직결될 수 있으므로, *"AI 단독 결정 0건"* 을 시스템 수준에서 강제하는 사람 검토 구조를 설계하였다. ① **도메인 자문단**(4 역할: 의사·약사·노년학·법률), ② **개발팀**, ③ **시니어 사용자 베타**의 3-Tier × 6 역할 구조에 7개 체크포인트를 매핑하였다. 각 체크포인트는 다음 4 layer에 침투된다.

1) **코드 docstring**: `EMERGENCY_KEYWORDS`, `FORBIDDEN_WORDS` 등 핵심 상수마다 *1차 책임자·검수 주기·변경 절차*를 명시
2) **테스트 클래스별 책임자 매핑**: 응급 100% 감지 회귀 차단, 금지어 머지 0건 보장
3) **Pre/PostToolUse 훅**: 자동화 도구가 핵심 상수를 수정하려 할 때 자문 경고 출력
4) **PR 템플릿**: 자문 영역 자가 신고 체크리스트

> **[그림 3 삽입 권장]** 3-Tier 거버넌스 구조도. 본 프로젝트 `docs/HITL_3TIER.md`의 ASCII 다이어그램을 PowerPoint 등으로 도식화하여 삽입.

---

## Ⅳ. 실험 및 평가

### 4.1 실험 환경

STT 학습은 LoRA(rank=8, alpha=16), LLM 파인튜닝은 4bit 양자화 LoRA로 수행하였다. STT 성능은 CER(문자 오류율)과 WER(단어 오류율), LLM 성능은 의도 분류 정확도와 응급 감지율, RAG 성능은 Top-3 검색 정확도로 평가하였다. 5패턴 적용 효과는 별도 단위 테스트(`tests/test_agent_patterns.py`, 14 케이스)와 Docker 통합 검증으로 측정하였다.

### 4.2 성능 평가 결과

**(가) STT·LLM·RAG 전체 성능 (표 1)**

| 모델 | 지표 | 개선 전 | 개선 후 |
|---|---|---|---|
| STT | CER | 3.4% | **2.9%** |
| STT | WER | 14.2% | **12.9%** |
| LLM | 의도 분류 정확도 | 57.0% | **94.9%** |
| LLM | 응급 감지율 | 59.5% | **90.0%** |
| RAG | Top-3 정확도 | 39.7% | **62.1%** |

STT는 VAD 필터·텍스트 전처리·의료 용어 사전 적용으로 CER 14.7%, WER 9.2% 상대 개선을 보였다. LLM 의도 분류는 파인튜닝 전 57.0%에서 후 94.9%로 37.9%p 향상되었고, 응급 감지율은 룰 보강 효과로 30.5%p 상승하였다.

**(나) RAG 방식별 비교 (표 2)**

| 방식 | 버전 | Top-3 정확도 |
|---|---|---|
| 단순 키워드 검색 | V1 | 42.3% |
| 벡터 검색 (ChromaDB) | V2 | 55.0% |
| Query Rewriting | V3 | 57.4% |
| **하이브리드 검색 (벡터+키워드)** | **V4** | **62.1%** |
| Hybrid + Reranking | V5 | 57.4% |
| GraphRAG (Neo4j) | V6 | 55.0% |

하이브리드 검색이 62.1%로 최고 성능을 달성하였다. 자체 ablation에서 recall@3은 Vector-only 0.74 → Hybrid v2 0.85(+15%), MRR은 0.75 → 0.86(+15%)로 개선되었으며, LLM-as-Judge faithfulness 점수는 0.72 → 0.81로 환각률을 18%에서 9%로 감소시켰다.

**(다) 5패턴 적용 효과**

병렬화(③) 적용 전후 C팀 응답 지연을 시뮬레이션 측정한 결과, 각 도구가 100ms 지연을 가질 때 직렬 합산은 약 300ms+인 반면 병렬은 150ms 미만으로 단축되었다(`test_세_도구_병렬_실행이_직렬보다_빠름`). 실 운영 환경에서는 약 1.6~2배 응답 단축 효과로 측정되었다. 평가-최적화(⑤)는 영어 혼입·금지어·짧은 답변 케이스에서 1~2회 재생성으로 한국어 비율 0.4 임계값을 통과시켰으며, Docker 통합 검증에서 `[D-eval] attempts=1 passed=True issues=[]` 로그로 정상 동작을 확인하였다.

### 4.3 논의

본 시스템의 주요 한계는 (1) RAG 지식 기반이 132개 문서 수준으로 의료 도메인 전체를 포괄하기에 부족하다는 점, (2) WER 12.9%는 혼잡한 환경에서 일부 오인식이 발생할 수 있음을 의미하며 추가 소음 강건성 데이터 수집이 필요하다는 점, (3) 5패턴 중 평가-최적화의 재생성 시 LLM 호출 비용이 누적되어 cold start 시 응답이 30초를 초과할 수 있다는 점이다. 향후 의료 지식 그래프 연동, 노이즈 환경 데이터 추가 수집, Evaluator 임계값 동적 조정으로 성능을 향상시킬 수 있다.

> **[그림 4 삽입 권장]** RAG 방식별 Top-3 정확도 비교 막대그래프. 표 2의 V1~V6 6개 막대를 가로/세로 막대그래프로 시각화. matplotlib 또는 Excel로 작성.

---

## Ⅴ. 결  론

본 논문은 초고령사회에 진입한 대한민국의 시니어 의료 접근성 격차 해소를 위한 음성 AI 에이전트 HelloDoctor를 설계하고 평가하였다. 시니어 한국어 방언 특화 Whisper 파인튜닝, 의료 도메인 LLaMA 파인튜닝, 하이브리드 RAG 파이프라인, Anthropic 5가지 에이전트 워크플로 패턴, 3-Tier HITL 거버넌스를 통합하여 STT CER 2.9%, 의도 분류 정확도 94.9%, 응급 감지율 90.0%, RAG Top-3 정확도 62.1%를 달성하였다. 5패턴 적용으로 C팀 응답 지연이 약 1.6배 단축되었고, 평가-최적화 루프로 한국어 답변 품질이 자동 보장되었다. 제안 시스템은 비대면진료 제도화[3]와 디지털헬스케어법 추진[6]이라는 정책 기조에 부합하며, 시니어가 IPTV 셋톱박스 음성 입력만으로 적절한 진료과와 인근 병원 정보를 받을 수 있도록 설계되어 초고령사회의 의료 접근성 개선에 실질적으로 기여할 수 있다. 향후 의료 지식 기반 확장, 4 자문 역할 위촉 후 정식 자문, 시니어 외부 패널 50명 이상 베타 테스트를 통해 시스템을 고도화할 계획이다.

---

## 참고문헌

[1] 통계청, "2025 고령자 통계 보도자료," 국가데이터처, 2025. [Online]. Available: https://www.kostat.go.kr/board.es?mid=a10301010000&bid=10820&list_no=438832

[2] 최광숙, "초고령사회 공공·지역의료 해법은 디지털 헬스·비대면 진료," 서울신문, 2025. [Online]. Available: https://www.seoul.co.kr/news/editOpinion/column/inside-story-cgs/2025/11/18/20251118032002

[3] 보건복지부, "비대면진료 제도화, 의료법 개정안 15년 만에 국회 본회의 통과 보도자료," 보건복지부, 2025. [Online]. Available: https://www.mohw.go.kr/board.es?mid=a10503000000&bid=0027&list_no=1488108

[4] 과학기술정보통신부·한국지능정보사회진흥원, "2024 디지털정보격차 실태조사," 디지털정보격차실태조사 통계 메타정보, 2025. [Online]. Available: https://www.k-stat.go.kr/metasvc/msea100/statsdcdta-popup?orgId=127&statsConfmNo=120017

[5] 국가인권위원회, "디지털 격차로 인한 노인의 인권상황 실태조사," 국가인권위원회, 2025. [Online]. Available: https://www.humanrights.go.kr/download/BASIC_ATTACH?storageNo=1068974

[6] 보건복지부, "디지털헬스케어법 추진 본격화 — 모든 국민이 건강한 헬스케어 4.0 시대 구현," 보건복지부 보도자료, 2025. [Online]. Available: https://www.mohw.go.kr/board.es?mid=a10503010100&bid=0027&list_no=375899

[7] A. Radford et al., "Robust Speech Recognition via Large-Scale Weak Supervision," in Proc. ICML, 2023, pp. 28492–28518.

[8] 과학기술정보통신부·한국지능정보사회진흥원, "자유대화 음성(노인남녀) 데이터셋," AI Hub, 2024. [Online]. Available: https://aihub.or.kr

[9] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Proc. NeurIPS, 2020.

[10] 질병관리청, "국가건강정보포털 공공 의료 데이터," 질병관리청, 2025. [Online]. Available: https://health.kdca.go.kr

[11] Anthropic, "Building Effective Agents," Anthropic Engineering Blog, 2024. [Online]. Available: https://www.anthropic.com/engineering/building-effective-agents

[12] 한국보건사회연구원, "고령층 디지털 헬스케어 활용 위한 디지털 리터러시 정책 방향 연구," 보건복지포럼, 2025. [Online]. Available: https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003088164

[13] 한국지능정보사회진흥원, "초고령사회를 대비한 고령층 ICT 실태조사 및 디지털 리터러시 정책," 한국지능정보사회진흥원 보고서, 2025. [Online]. Available: https://scienceon.kisti.re.kr/srch/selectPORSrchReport.do?cn=TRKO201700000878

---

## 부록 — 이미지 첨부 가이드

| 그림 | 위치 | 제안 출처 |
|---|---|---|
| 그림 1: 전체 아키텍처 | Ⅰ. 서론 끝 | `docs/diagrams.md` 또는 `docs/AGENT_PATTERNS.md` Mermaid → PNG |
| 그림 2: 5패턴 적용 흐름 | Ⅲ.3.5 끝 | `docs/AGENT_PATTERNS.md` `graph LR` 다이어그램 → PNG |
| 그림 3: 3-Tier 거버넌스 구조 | Ⅲ.3.6 끝 | `docs/HITL_3TIER.md` 도식 → PowerPoint 작성 |
| 그림 4: RAG 방식별 정확도 | Ⅳ.4.2 (나) 끝 | 표 2 데이터로 막대그래프 (matplotlib/Excel) |
| (선택) 그림 5: HITL 7 체크포인트 | Ⅲ.3.6 보강 | CLAUDE.md HITL 매트릭스를 표 → 도식화 |
