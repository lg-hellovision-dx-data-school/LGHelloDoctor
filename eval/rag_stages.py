"""RAG V1 ~ V11 검색 함수"""
import os
from numpy import dot
from numpy.linalg import norm
from eval.setup import collection, collection_chunked, embed_model, query_rewrite

# ── V1: 단순 키워드 검색 ───────────────────────────────────────────────────────
def rag_v1_keyword_only(query):
    docs_data = collection.get(include=['documents', 'metadatas'])
    keywords  = query.split()
    scored = []
    for text in docs_data['documents']:
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, text))
    scored.sort(reverse=True)
    return [t for _, t in scored[:3]]

# ── V2: ChromaDB 벡터 검색 ────────────────────────────────────────────────────
def rag_v2_vector(query):
    emb = embed_model.encode([query]).tolist()
    res = collection.query(query_embeddings=emb, n_results=3)
    return res['documents'][0]

# ── V3: Query Rewriting + 벡터 검색 ──────────────────────────────────────────
def rag_v3_rewrite(query):
    rewritten = query_rewrite(query)
    emb = embed_model.encode([rewritten]).tolist()
    res = collection.query(query_embeddings=emb, n_results=3)
    return res['documents'][0]

# ── V4: Hybrid (벡터 + 키워드 병합) ──────────────────────────────────────────
def rag_v4_hybrid(query):
    rewritten = query_rewrite(query)
    emb = embed_model.encode([rewritten]).tolist()
    vec_res  = collection.query(query_embeddings=emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    docs_data = collection.get(include=['documents'])
    keywords  = query.split()
    kw_docs   = [
        text for text in docs_data['documents']
        if sum(1 for kw in keywords if kw in text) > 0
    ][:3]

    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d); combined.append(d)
    return combined[:5]

# ── V5: Hybrid + Reranking (코사인 유사도 재정렬) ────────────────────────────
def rag_v5_rerank(query):
    docs = rag_v4_hybrid(query)
    if not docs:
        return []
    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(docs)
    scores = [
        (dot(q_emb[0], d_emb) / (norm(q_emb[0]) * norm(d_emb) + 1e-9), docs[i])
        for i, d_emb in enumerate(d_embs)
    ]
    scores.sort(reverse=True)
    return [d for _, d in scores[:3]]

# ── V7: 문서 청킹 + Hybrid + Reranking ───────────────────────────────────────
def rag_v7_chunked(query):
    """V7: 청킹된 컬렉션에서 Hybrid 검색 + Reranking"""
    from eval.setup import query_rewrite
    rewritten = query_rewrite(query)

    # 벡터 검색 (청킹 컬렉션)
    emb = embed_model.encode([rewritten]).tolist()
    vec_res  = collection_chunked.query(query_embeddings=emb, n_results=7)
    vec_docs = vec_res['documents'][0]

    # 키워드 검색 (청킹 컬렉션)
    keywords  = query.split()
    all_chunks = collection_chunked.get(include=['documents'])
    kw_docs = [
        text for text in all_chunks['documents']
        if sum(1 for kw in keywords if kw in text) > 0
    ][:5]

    # 병합 후 Reranking
    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d); combined.append(d)

    if not combined:
        return []
    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scores = [
        (dot(q_emb[0], d_emb) / (norm(q_emb[0]) * norm(d_emb) + 1e-9), combined[i])
        for i, d_emb in enumerate(d_embs)
    ]
    scores.sort(reverse=True)
    return [d for _, d in scores[:3]]

# ── V6: GraphRAG (Neo4j 지식 그래프) ─────────────────────────────────────────
from neo4j import GraphDatabase as _Neo4jDriver
from dotenv import load_dotenv
load_dotenv()

_neo4j_driver = _Neo4jDriver.driver(
    os.getenv('NEO4J_URI', '').replace('neo4j+s://', 'neo4j+ssc://'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def neo4j_query_expand(query):
    """쿼리 키워드 → Neo4j 그래프 탐색 → 질환/진료과/합병증/동반질환 반환"""
    keywords = [w for w in query.split() if len(w) >= 2]
    if not keywords:
        return []
    extra_terms = []
    with _neo4j_driver.session() as session:
        # 1) 증상 → 질환 → 진료과
        result = session.run("""
            MATCH (s:Symptom)-[:SUGGESTS]->(d:Disease)-[:TREATED_BY]->(dept:Department)
            WHERE any(kw IN $keywords WHERE s.name CONTAINS kw)
            RETURN DISTINCT d.name AS disease, dept.name AS department
            LIMIT 10
        """, keywords=keywords)
        for record in result:
            extra_terms.append(record['disease'])
            extra_terms.append(record['department'])

        # 2) 질환 → 합병증 → 진료과 (합병증 예방 안내 강화)
        result2 = session.run("""
            MATCH (d:Disease)-[:COMPLICATION_OF]->(c:Disease)-[:TREATED_BY]->(dept:Department)
            WHERE any(kw IN $keywords WHERE d.name CONTAINS kw)
            RETURN DISTINCT c.name AS complication, dept.name AS department
            LIMIT 5
        """, keywords=keywords)
        for record in result2:
            extra_terms.append(record['complication'])
            extra_terms.append(record['department'])

        # 3) 동반 질환 탐색
        result3 = session.run("""
            MATCH (d:Disease)-[:RELATED_TO]->(related:Disease)-[:TREATED_BY]->(dept:Department)
            WHERE any(kw IN $keywords WHERE d.name CONTAINS kw)
            RETURN DISTINCT related.name AS related_disease, dept.name AS department
            LIMIT 5
        """, keywords=keywords)
        for record in result3:
            extra_terms.append(record['related_disease'])
            extra_terms.append(record['department'])

    return list(dict.fromkeys(extra_terms))

def rag_v6_graphrag(query):
    """V6: 실제 Neo4j 지식 그래프 탐색 + Hybrid + Reranking"""
    graph_terms    = neo4j_query_expand(query)
    expanded_query = query + ' ' + ' '.join(graph_terms[:5]) if graph_terms else query

    emb      = embed_model.encode([expanded_query]).tolist()
    vec_res  = collection.query(query_embeddings=emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    all_keywords = query.split() + graph_terms[:3]
    docs_data    = collection.get(include=['documents'])
    kw_docs      = [
        text for text in docs_data['documents']
        if sum(1 for kw in all_keywords if kw in text) > 0
    ]

    seen, combined = set(), []
    for d in vec_docs + kw_docs[:3]:
        if d not in seen:
            seen.add(d); combined.append(d)

    if not combined:
        return []
    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scores = [
        (dot(q_emb[0], d_emb) / (norm(q_emb[0]) * norm(d_emb) + 1e-9), combined[i])
        for i, d_emb in enumerate(d_embs)
    ]
    scores.sort(reverse=True)
    return [d for _, d in scores[:3]]

# ── V8: Top-5 Hybrid (V4 기반, Top-K 3→5) ────────────────────────────────────
def rag_v8_top5(query):
    """V8: Hybrid 검색 Top-K 5로 확장"""
    emb      = embed_model.encode([query]).tolist()
    vec_res  = collection.query(query_embeddings=emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    keywords = query.split()
    all_docs = collection.get(include=['documents'])
    kw_docs  = [t for t in all_docs['documents']
                if sum(1 for kw in keywords if kw in t) > 0][:5]

    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d); combined.append(d)
    return combined[:5]


# ── V9: BM25 + Vector Hybrid ──────────────────────────────────────────────────
from rank_bm25 import BM25Okapi as _BM25
from numpy import dot as _dot
from numpy.linalg import norm as _norm

_all_docs_list = collection.get(include=['documents'])['documents']
_bm25 = _BM25([doc.split() for doc in _all_docs_list])

def rag_v9_bm25(query):
    """V9: BM25 키워드 검색 + 벡터 검색 Hybrid + Reranking"""
    tokens      = query.split()
    bm25_scores = _bm25.get_scores(tokens)
    top_idx     = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:5]
    bm25_docs   = [_all_docs_list[i] for i in top_idx if bm25_scores[i] > 0]

    emb      = embed_model.encode([query]).tolist()
    vec_docs = collection.query(query_embeddings=emb, n_results=5)['documents'][0]

    seen, combined = set(), []
    for d in vec_docs + bm25_docs:
        if d not in seen:
            seen.add(d); combined.append(d)
    if not combined:
        return []

    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scored = sorted(
        [(_dot(q_emb[0], e) / (_norm(q_emb[0]) * _norm(e) + 1e-9), combined[i])
         for i, e in enumerate(d_embs)],
        reverse=True
    )
    return [d for _, d in scored[:5]]


# ── V10: 의학 동의어 확장 + BM25 + Vector ────────────────────────────────────
_SYNONYMS = {
    "무릎": ["무릎", "슬관절", "슬부"],
    "허리": ["허리", "요추", "요부", "척추"],
    "어깨": ["어깨", "견관절", "견부"],
    "두통": ["두통", "머리 통증", "두부"],
    "고혈압": ["고혈압", "혈압", "혈압 상승"],
    "당뇨": ["당뇨", "당뇨병", "혈당", "고혈당"],
    "천식": ["천식", "기관지 천식", "호흡곤란"],
    "위염": ["위염", "위장염", "위통", "소화불량"],
    "디스크": ["디스크", "추간판", "요추 디스크"],
    "편두통": ["편두통", "두통"],
    "갑상선": ["갑상선", "갑상선염"],
    "심장": ["심장", "협심증", "심근경색"],
    "신장": ["신장", "콩팥", "신부전"],
    "관절": ["관절", "관절염", "관절 통증"],
}

def _expand_query(query):
    extra = []
    for key, syns in _SYNONYMS.items():
        if key in query:
            extra.extend(syns)
    return (query + " " + " ".join(dict.fromkeys(extra))).strip() if extra else query

def rag_v10_synonym(query):
    """V10: 의학 동의어 확장 + BM25 + 벡터 Hybrid + Reranking"""
    expanded    = _expand_query(query)
    tokens      = expanded.split()
    bm25_scores = _bm25.get_scores(tokens)
    top_idx     = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:5]
    bm25_docs   = [_all_docs_list[i] for i in top_idx if bm25_scores[i] > 0]

    emb      = embed_model.encode([expanded]).tolist()
    vec_docs = collection.query(query_embeddings=emb, n_results=5)['documents'][0]

    seen, combined = set(), []
    for d in vec_docs + bm25_docs:
        if d not in seen:
            seen.add(d); combined.append(d)
    if not combined:
        return []

    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scored = sorted(
        [(_dot(q_emb[0], e) / (_norm(q_emb[0]) * _norm(e) + 1e-9), combined[i])
         for i, e in enumerate(d_embs)],
        reverse=True
    )
    return [d for _, d in scored[:5]]


# ── V11: 쿼리 분해 + V10 ──────────────────────────────────────────────────────
import re as _re

def _decompose(query):
    parts = _re.split(r'[,，]|이랑|랑\s|하고|이고|이며|과\s|와\s', query)
    parts = [p.strip() for p in parts if len(p.strip()) >= 3]
    return parts if len(parts) > 1 else [query]

def rag_v11_decompose(query):
    """V11: 쿼리 분해 + 동의어 확장 + BM25 + 벡터"""
    seen, combined = set(), []
    for sq in _decompose(query):
        for d in rag_v10_synonym(sq):
            if d not in seen:
                seen.add(d); combined.append(d)
    if not combined:
        return []

    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scored = sorted(
        [(_dot(q_emb[0], e) / (_norm(q_emb[0]) * _norm(e) + 1e-9), combined[i])
         for i, e in enumerate(d_embs)],
        reverse=True
    )
    return [d for _, d in scored[:5]]


# ── V12: GraphRAG + Hybrid + Reranking (V5 + V6 결합) ────────────────────────
def rag_v12_graph_hybrid_rerank(query):
    """V12: Neo4j 그래프 확장 → Hybrid(벡터+키워드) 검색 → Reranking
    V5(Hybrid+Reranking) + V6(GraphRAG) 를 하나로 결합한 최종 버전
    """
    # 1) Neo4j 그래프 탐색으로 쿼리 확장
    graph_terms    = neo4j_query_expand(query)
    expanded_query = (query + ' ' + ' '.join(graph_terms[:5])) if graph_terms else query

    # 2) 벡터 검색 (확장된 쿼리 사용, Top-5)
    emb      = embed_model.encode([expanded_query]).tolist()
    vec_docs = collection.query(query_embeddings=emb, n_results=5)['documents'][0]

    # 3) 키워드 검색 (원본 쿼리 + 그래프 확장 용어)
    all_keywords = query.split() + graph_terms[:3]
    all_docs     = collection.get(include=['documents'])['documents']
    kw_docs      = [
        text for text in all_docs
        if sum(1 for kw in all_keywords if kw in text) > 0
    ][:5]

    # 4) 병합 (중복 제거)
    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d); combined.append(d)

    if not combined:
        return []

    # 5) Reranking (원본 쿼리 기준 코사인 유사도 재정렬)
    q_emb  = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scores = sorted(
        [(dot(q_emb[0], e) / (norm(q_emb[0]) * norm(e) + 1e-9), combined[i])
         for i, e in enumerate(d_embs)],
        reverse=True
    )
    return [d for _, d in scores[:5]]
