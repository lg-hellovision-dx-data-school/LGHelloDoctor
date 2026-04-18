---
applyTo: "RAG/**,backend/main.py"
---

# RAG 지침 (C팀 — 검색 증강 생성)

## 개요
ChromaDB 기반 의료 지식 벡터DB를 활용하여 사용자 증상과 관련된 의료 정보를 검색하고,
Kakao Map API로 주변 병원을 찾아 LLM 답변 생성에 활용한다.

## 데이터베이스 구조

### ChromaDB
```
RAG/db/
├── chroma.sqlite3              # 메타데이터 및 인덱스
└── {uuid}/                     # 벡터 데이터 세그먼트 (여러 개)
```
- 컬렉션명: `medical_knowledge`
- 거리 측정: cosine similarity (`hnsw:space: cosine`)
- 문서 수: 132개 (의료 지식 청크)
- ChromaDB 버전: `1.5.5` (로컬 DB 생성 버전과 반드시 일치)

### 임베딩 모델
```python
SentenceTransformer("jhgan/ko-sroberta-multitask")
```
- 한국어 특화 문장 임베딩
- HuggingFace에서 자동 다운로드

## RAG 파이프라인

### 1. 쿼리 재작성 (Query Rewriting)
```python
QUERY_REWRITE_MAP = {
    "무릎": "무릎통증 정형외과 관련 증상 치료 방법",
    "허리": "허리디스크 정형외과 척추 관련 증상 치료",
    ...
}
```
사용자 쿼리의 핵심 키워드를 의료 전문 표현으로 확장하여 검색 품질 향상.

### 2. 벡터 검색
```python
vec_res = collection.query(query_embeddings=q_emb, n_results=3)
# cosine distance ≤ 0.45인 문서만 사용 (유사도 ≥ 0.55)
filtered_docs = [doc for doc, dist in zip(...) if dist <= 0.45]
```

### 3. 결과 처리
- 관련 문서 없으면: `"관련된 전문적인 의학 정보를 찾지 못했습니다."` 반환
- 검색된 문서는 병원 정보와 합쳐 LLM 컨텍스트로 전달

## 병원 검색 (Kakao Map API)

### 증상→진료과 매핑
```python
SYMPTOM_DEPT_MAP = {
    "무릎": ("정형외과", "05"),
    "허리": ("정형외과", "05"),
    "눈":   ("안과", "12"),
    "귀":   ("이비인후과", "13"),
    "피부": ("피부과", "14"),
    "머리": ("신경과", "02"),
    "배":   ("소화기내과", "01"),
    ...
}
```

### Kakao API 호출
- 반경: 3km
- 카테고리: `HP8` (병원)
- 결과: 최대 5개 → 전화번호 있는 곳만 → 거리순 정렬 → 상위 3개
- 응답 필드: name, address, phone, distance, navi_url

## 응급 판단 (Emergency Check)

```python
EMERGENCY_SCORES = {
    "숨이 안 쉬어": 100,
    "의식이 없":    100,
    "피를 토":       90,
    "가슴이 너무 아파": 90,
    "쓰러":          85,
    ...
}
# 복수 키워드 매칭 시 1.2배 가중
# 70점 이상 → HIGH (즉시 119)
# 40점 이상 → MEDIUM (응급실)
# 미만     → LOW (일반 진료)
```

## 의도별 도구 분기 (Tool Router)

| 의도 | RAG | 병원검색 | 응급판단 |
|------|-----|----------|----------|
| `symptom_inquiry` | ✅ | ✅ | ✅ |
| `medication_info` | ✅ | ❌ | ✅ |
| `hospital_search` | ❌ | ✅ | ✅ |
| `emergency` | ❌ | ❌ | ✅ |

## ChromaDB 연결 코드
```python
import chromadb

chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_or_create_collection(
    "medical_knowledge",
    metadata={"hnsw:space": "cosine"},
)
```

## ChromaDB 버전 주의사항
- 로컬 DB는 `chromadb==1.5.5`로 생성됨
- Docker 환경도 동일 버전 사용 (`requirements.txt`)
- 버전 불일치 시 `KeyError: '_type'` 또는 `no such column: topic` 오류 발생

## DB 경로 설정
```python
DB_PATH = os.environ.get('DB_PATH', '/app/RAG/db')
```
- Docker: `docker-compose.yml`에서 `./RAG/db:/app/RAG/db` 볼륨 마운트
- 로컬 개발: `RAG/db/` 직접 참조

## RAG 데이터 업데이트 방법
새 의료 지식을 추가하려면:
```python
collection.add(
    documents=["새로운 의료 지식 텍스트"],
    embeddings=embed_model.encode(["새로운 의료 지식 텍스트"]).tolist(),
    ids=["unique-id-001"]
)
```
추가 후 `RAG/db/` 디렉토리를 백업해둘 것.
