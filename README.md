# LG HelloDoctor — C팀 RAG 파이프라인

> **역할**: B팀(STT·NLU)에서 넘어온 의도/개체 정보를 받아 → RAG 검색 + 병원 추천 + 응급 판단 → 결과 반환

---

## RAG 고도화 과정 및 정확도

> `b_output_1000.json` (B팀 1,000개 샘플) 기반 측정  
> V1은 전체 문서 스캔 특성상 100개, V2~V6는 200개 샘플 기준  
> ChromaDB 문서 수: **56개 → 112개** 확장 후 최종 측정

| 단계 | 기술 | 핵심 변화 | DB 56개 | DB 112개 |
|------|------|-----------|---------|----------|
| V1 | 단순 키워드 검색 | 기준선 | 35.1% | 35.1% |
| V2 | ChromaDB 벡터 검색 | 의미 기반 검색 도입 | 42.2% | 50.0% (+7.8%p) |
| V3 | Query Rewriting + 벡터 | 쿼리 의도 확장 | 42.2% | 51.3% (+9.1%p) |
| V4 | Hybrid (벡터 + 키워드) | 두 방식 병합 | 50.0% | **57.1% (+7.1%p)** |
| V5 | Hybrid + Reranking | 코사인 유사도 재정렬 | 42.2% | 51.3% (+9.1%p) |
| V6 | GraphRAG (Neo4j 지식 그래프) | 질환-진료과 관계 탐색 | 42.2% | 50.0% (+7.8%p) |

---

## 고도화 순서 및 방법

### STEP 1 — RAG 검색 알고리즘 고도화 (V1 → V6)

#### V1 — 단순 키워드 검색 (기준선: 35.1%)
사용자 입력을 단어로 분리해 DB 전체 문서를 순회하며 포함 단어 수를 카운팅.  
의미적 유사도 없이 정확히 일치하는 단어만 찾기 때문에 정확도 한계 명확.
```
"무릎이 아파요" → ['무릎', '이', '아파요'] → 단어 포함 여부 카운팅
```

#### V2 — ChromaDB 벡터 검색 (+7.8%p → 50.0%)
`jhgan/ko-sroberta-multitask` 한국어 임베딩 모델로 질문을 벡터화해  
ChromaDB에서 코사인 유사도 기반으로 의미적으로 가까운 문서 검색.  
단어가 달라도 의미가 비슷하면 찾아낼 수 있어 정확도 향상.
```
"무릎이 아파요" → 벡터 임베딩 → ChromaDB cosine similarity → Top-3 문서 반환
```

#### V3 — Query Rewriting + 벡터 검색 (+1.3%p → 51.3%)
구어체 질문을 의학 전문 용어로 확장한 뒤 벡터 검색.  
DB 문서는 의학 용어 중심이라 구어체와의 의미 거리가 있는데,  
Rewriting으로 그 간격을 줄여 검색 품질 개선.
```
"무릎이 아파요"   → "무릎관절염 정형외과 관절 통증 진료" → 벡터 검색
"허리가 뻐근해요" → "허리디스크 정형외과 척추 통증 진료" → 벡터 검색
```

#### V4 — Hybrid 검색 (+5.8%p → 57.1%) ★ 최고 성능
벡터 검색 결과와 키워드 검색 결과를 병합해 두 방식의 장점을 모두 활용.  
벡터 검색이 놓친 정확 매칭 문서를 키워드 검색이 보완하는 구조.
```
벡터 검색 (Top-5) + 키워드 검색 (Top-3) → 중복 제거 → 병합 결과 반환
```

#### V5 — Hybrid + Reranking (51.3%)
V4 결과에 코사인 유사도 재정렬(Reranking) 추가.  
병합된 문서들을 원본 질문 벡터와 다시 비교해 관련도 높은 순으로 재배열.
```
V4 결과 → 원본 쿼리와 코사인 유사도 재계산 → Top-3 재정렬
```

#### V6 — GraphRAG / Neo4j 지식 그래프 (50.0%)
Neo4j AuraDB에 구성한 의료 지식 그래프를 활용해  
쿼리를 실제 의료 관계 기반으로 3단계 탐색 후 Hybrid + Reranking 검색.
```
"무릎이 아파요"
  ① 증상 → 질환 → 진료과:  무릎 → 무릎관절염 → 정형외과
  ② 질환 → 합병증:          무릎관절염 → 골절
  ③ 동반 질환:               무릎관절염 → 류마티스관절염
  → 확장 쿼리로 Hybrid + Reranking
```

---

### STEP 2 — Neo4j 지식 그래프 구축 및 확장

#### 초기 구축
증상-질환-진료과 관계를 Neo4j AuraDB에 구성.
```
(증상: 무릎 통증) -[SUGGESTS]→ (질환: 무릎관절염) -[TREATED_BY]→ (진료과: 정형외과)
(증상: 흉통)     -[SUGGESTS]→ (질환: 심근경색)   -[TREATED_BY]→ (진료과: 심장내과)
```

#### 진료과 확장 (13개 → 26개)
서울아산병원 53개 진료과 기준으로 증상-진료과 매핑 확대.  
`hospital_rules.py`의 증상 매핑도 46개 → 130개+로 동시 업데이트.

#### 합병증/동반 질환 관계 추가
질환 간 관계를 추가해 연관 질환 안내 기능 강화.

| 관계 타입 | 예시 | 수 |
|----------|------|-----|
| `SUGGESTS` | 증상 → 질환 | 102개 |
| `TREATED_BY` | 질환 → 진료과 | 81개 |
| `COMPLICATION_OF` | 고혈압→뇌졸중, 당뇨→신부전 | 73개 |
| `RELATED_TO` | 고혈압↔당뇨병, 천식↔알레르기비염 | 50개 |

**최종 그래프 규모: 217 노드 / 306 관계**

---

### STEP 3 — ChromaDB 문서 확장 (56개 → 112개)

국가건강정보포털 `cntnts_sn` ID 스캔으로 새 문서 발굴 후 크롤링.

| 단계 | 문서 수 | 추가 내용 |
|------|---------|----------|
| 초기 구축 | 21개 | 기본 질환 15개 + 복약/응급 안내 6개 |
| 1차 확장 | 35개 | 수면장애, 갑상선, 협심증 등 추가 |
| 2차 확장 | 49개 | 자궁경부암, 골다공증, 번아웃 등 추가 |
| 3차 확장 | 56개 | 대상포진, 담석증, 통풍 등 추가 |
| **4차 확장** | **112개** | 간경변증, 백내장, 이상지질혈증, 무릎 관절 손상 등 56개 추가 |

새로 추가된 주요 진료과별 문서:

| 진료과 | 추가 문서 |
|--------|----------|
| 감염내과 | 결핵, B형간염, 수두·대상포진, 패혈증, 코로나19 |
| 산부인과 | 무월경, 폐경기, 임신당뇨병, 월경전증후군 |
| 정형외과 | 무릎 관절 손상, 연골 손상, 인대 손상, 반월상 연골판 |
| 안과 | 백내장, 녹내장 |
| 피부과 | 원형탈모, 백반증 |
| 내분비내과 | 이상지질혈증, 당뇨병성 족부병증, 갑상선 결절 |
| 소화기내과 | 간경변증, 대사이상 지방간, 위십이지장 궤양 |

**DB 112개 확장 후 전 버전 7~9%p 향상 확인**

---

## 담당 작업 요약

### 1. RAG 파이프라인 구축 (`C_rag.ipynb`)

국가건강정보포털에서 질환 정보를 크롤링해 ChromaDB 벡터 DB를 구성하고, 사용자 질문에 맞는 문서를 검색하는 RAG 파이프라인을 구현했다.

| 단계 | 내용 |
|------|------|
| 크롤링 | 국가건강정보포털 112개 질환 정보 수집 |
| 임베딩 | `jhgan/ko-sroberta-multitask` 한국어 임베딩 모델 사용 |
| 벡터 DB | ChromaDB (cosine similarity, PersistentClient) |
| 검색 | Query Rewriting + Vector Search + Reranking |
| 병원 검색 | Kakao Local API (위치 기반 근처 병원) + HIRA 공공 API (진료과별 병원) |
| 응급 판단 | 심각도 점수 기반 3단계 분류 (low / medium / high) |

#### 크롤링 URL 변경 이력
- **구버전** (404): `GET gnrlzHealthInfoMain.do?cntnts_sn=XXXX`
- **현재** (정상): `POST gnrlzHealthInfoView.do` + `cntnts_sn` 파라미터

---

### 2. FastAPI 서비스 (`C_Mading/Opr/`)

B팀 출력을 입력으로 받아 RAG + 병원 검색 + 응급 판단을 실행하고 결과를 반환하는 REST API.

```
POST /pipeline/tools
GET  /health
```

**입력 (B팀 → C팀)**
```json
{
  "session_id": "abc123",
  "input_text": "무릎이 너무 아파요",
  "intent": ["symptom_inquiry"],
  "entities": {
    "symptom": "무릎 통증",
    "body_part": "무릎",
    "location": null,
    "emergency": false,
    "medication_1": null,
    "medication_2": null
  }
}
```

**출력 (C팀 → 다음 단계)**
```json
{
  "rag_context": "무릎관절염은 정형외과에서 진료합니다...",
  "hospital_results": [...],
  "severity": "low",
  "otc_info": null
}
```

**모듈 구성**

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 앱 진입점 |
| `router.py` | API 엔드포인트 정의 |
| `tool_router.py` | intent에 따라 RAG / 병원검색 / 응급판단 분기 |
| `rag_service.py` | ChromaDB 벡터 검색 |
| `hospital_search.py` | 증상→진료과 매핑 + Kakao/HIRA API 호출 |
| `severity.py` | 키워드 패턴 기반 응급도 판단 |
| `schemas.py` | Pydantic 입출력 모델 정의 |
| `otc_knowledge.py` | 일반의약품 안내 |

---

### 3. 평가 파이프라인 (`eval/`)

B팀 1,000개 샘플로 RAG V1~V6 정확도를 자동 측정하는 평가 모듈.

| 파일 | 역할 |
|------|------|
| `eval/setup.py` | ChromaDB, 임베딩 모델 공통 설정 |
| `eval/rag_stages.py` | RAG V1~V6 검색 함수 |
| `eval/router_stages.py` | Router V1~V4 함수 및 평가 데이터 |
| `eval/run.py` | 전체 평가 실행 메인 |

```bash
python -m eval.run
```

---

## 디렉토리 구조

```
LGHelloDoctor/
├── C_rag.ipynb          # RAG DB 구축 노트북 (크롤링 → ChromaDB)
├── RAG/
│   └── db/              # ChromaDB 저장소 (112개 문서)
├── C_Mading/
│   ├── Opr/             # FastAPI 서비스 소스
│   └── Std/
│       └── test_dummy_cases.py
├── eval/                # RAG 정확도 평가 모듈
│   ├── setup.py
│   ├── rag_stages.py
│   ├── router_stages.py
│   └── run.py
├── data/
│   └── b_output_1000.json  # B팀 평가 데이터셋
└── .env                 # API 키 (KAKAO_API_KEY, DATA_API_KEY, NEO4J_*)
```

---

## 환경 설정

```bash
pip install chromadb sentence-transformers requests beautifulsoup4 python-dotenv fastapi uvicorn neo4j
```

**.env 파일**
```
KAKAO_API_KEY=your_kakao_key
DATA_API_KEY=your_hira_key
NEO4J_URI=neo4j+ssc://xxxxxxxx.databases.neo4j.io
NEO4J_USER=your_neo4j_user
NEO4J_PASSWORD=your_neo4j_password
```

**서버 실행**
```bash
cd C_Mading
uvicorn Opr.main:app --reload
```

**RAG DB 구축**  
`C_rag.ipynb` 셀을 순서대로 실행 (Cell 1 → 마지막)

---

## 사용 외부 API

| API | 용도 |
|-----|------|
| [국가건강정보포털](https://health.kdca.go.kr) | 질환 정보 크롤링 |
| Kakao Local API | 위치 기반 근처 병원 검색 |
| HIRA 공공데이터 API | 진료과별 병원 목록 |
| Neo4j AuraDB | 의료 지식 그래프 (GraphRAG) |
