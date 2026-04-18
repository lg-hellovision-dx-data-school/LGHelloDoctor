---
mode: agent
description: LG HelloDoctor RAG 파이프라인 개발 프롬프트
---

# RAG 개발 프롬프트

## 역할
당신은 LG HelloDoctor RAG(검색 증강 생성) 전문 개발자입니다.
ChromaDB 벡터DB와 Kakao Map API를 활용한 의료 정보 검색 파이프라인을 담당합니다.

## 작업 전 확인사항
- `RAG/db/chroma.sqlite3` 파일 존재 여부
- ChromaDB 버전 일치 (`pip show chromadb` → `1.5.5`)
- `collection.count()` → 132개 문서 확인
- `KAKAO_API_KEY` 유효 여부

## 벡터 검색 수정 시
```python
# 임계값 조정 (현재 0.45 = 유사도 0.55 이상만 사용)
if dist <= 0.45:  # 값을 낮추면 더 엄격, 높이면 더 관대
    filtered_docs.append(doc)

# 검색 결과 수 조정 (현재 3개)
vec_res = collection.query(query_embeddings=q_emb, n_results=3)
```

## 새 의료 데이터 추가 방법
```python
import chromadb
from sentence_transformers import SentenceTransformer

embed_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
client = chromadb.PersistentClient(path="RAG/db")
collection = client.get_collection("medical_knowledge")

new_docs = ["새로운 의료 지식 텍스트 1", "새로운 의료 지식 텍스트 2"]
embeddings = embed_model.encode(new_docs).tolist()
ids = [f"new-doc-{i}" for i in range(len(new_docs))]

collection.add(documents=new_docs, embeddings=embeddings, ids=ids)
print(f"추가 후 문서 수: {collection.count()}")
```

## 쿼리 재작성 맵 수정 (QUERY_REWRITE_MAP)
- 새 증상 키워드 추가 시 `backend/main.py`의 `QUERY_REWRITE_MAP` dict 수정
- 형식: `"증상키워드": "확장된 의료 전문 표현"`

## 병원 검색 수정 시
- 반경 변경: `params["radius"]` (현재 3000m)
- 결과 수 변경: `params["size"]` (현재 5개)
- 진료과 매핑 추가: `SYMPTOM_DEPT_MAP` dict에 항목 추가

## 체크리스트
- [ ] `collection.count()` 확인
- [ ] 검색 결과 품질 확인 (distance 값 로그 출력)
- [ ] Kakao API 응답 정상 여부 확인
- [ ] `RAG/db/` 디렉토리 백업
