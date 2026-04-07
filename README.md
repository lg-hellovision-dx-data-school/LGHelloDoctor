# LG HelloDoctor — C팀 RAG 파이프라인

> **역할**: B팀(STT·NLU)에서 넘어온 의도/개체 정보를 받아 → RAG 검색 + 병원 추천 + 응급 판단 → 결과 반환

---

## 담당 작업 요약

### 1. RAG 파이프라인 구축 (`C_rag.ipynb`)

국가건강정보포털에서 질환 정보를 크롤링해 ChromaDB 벡터 DB를 구성하고, 사용자 질문에 맞는 문서를 검색하는 RAG 파이프라인을 구현했다.

| 단계 | 내용 |
|------|------|
| 크롤링 | 국가건강정보포털 15개 질환 정보 수집 (무릎관절염, 고혈압, 당뇨병 등) |
| 보완 문서 | 크롤링 실패 대비 수기 문서 16건 (증상-진료과, 복약 안내, 응급 안내) |
| 임베딩 | `jhgan/ko-sroberta-multitask` 한국어 임베딩 모델 사용 |
| 벡터 DB | ChromaDB (cosine similarity, PersistentClient) |
| 검색 | Query Rewriting + Vector Search + Reranking |
| 병원 검색 | Kakao Local API (위치 기반 근처 병원) + HIRA 공공 API (진료과별 병원) |
| 응급 판단 | 심각도 점수 기반 3단계 분류 (low / medium / high) |

#### 크롤링 URL 변경 이력
- **구버전** (404): `GET gnrlzHealthInfoMain.do?cntnts_sn=XXXX`
- **현재** (정상): `POST gnrlzHealthInfoView.do` + `cntnts_sn` 파라미터
- 2026년 4월 기준 국가건강정보포털 URL 구조 변경에 따라 새 ID로 업데이트

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
| `rag_service.py` | ChromaDB 벡터 검색 (현재 더미 → 실제 연동 예정) |
| `hospital_search.py` | 증상→진료과 매핑 + Kakao/HIRA API 호출 |
| `severity.py` | 키워드 패턴 기반 응급도 판단 |
| `schemas.py` | Pydantic 입출력 모델 정의 |
| `otc_knowledge.py` | 일반의약품 안내 |

---

## 디렉토리 구조

```
LGHelloDoctor/
├── C_rag.ipynb                    # RAG 파이프라인 구축 노트북 (크롤링 → ChromaDB)
├── RAG/
│   └── db/                        # ChromaDB 저장소
├── C_Mading/
│   ├── Opr/                       # C파트 핵심 서비스 로직
│   │   ├── main.py                # FastAPI 앱 진입점
│   │   ├── router.py              # API 엔드포인트 정의
│   │   ├── rag_versions.py        # V1~V6 버전별 예측 로직
│   │   ├── rag_service.py         # 증상/복약 안내 응답 생성
│   │   ├── chroma_client.py       # ChromaDB 컬렉션 및 임베딩 설정
│   │   ├── chroma_loader.py       # 내부 seed 문서 적재
│   │   ├── crawl_official_docs.py # 공공 의료정보 크롤링 및 벡터DB 추가
│   │   ├── run_rag_eval.py        # 평가 실행
│   │   ├── rag_eval_config.py     # 평가 버전 설정
│   │   ├── severity.py            # 응급도 판단
│   │   ├── schemas.py             # 입출력 스키마 정의
│   │   ├── hospital_*             # 병원 검색 및 외부 API 관련 모듈
│   │   ├── otc_*                  # 일반의약품 안내 관련 모듈
│   │   └── tool_*                 # 도구 라우팅 및 핸들러 모듈
│   └── Std/                       # 테스트 및 보조 스크립트
│        └──test_dummy_cases.py    # 테스트 더미데이터
└── .env                           # 환경 변수 및 API 키
```

---

## 환경 설정

```bash
pip install chromadb sentence-transformers requests beautifulsoup4 python-dotenv fastapi uvicorn
```

**.env 파일**
```
KAKAO_API_KEY=your_kakao_key
DATA_API_KEY=your_hira_key
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
