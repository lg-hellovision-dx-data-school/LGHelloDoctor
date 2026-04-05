"""RAG V1 ~ V6 검색 함수"""
import os
from numpy import dot
from numpy.linalg import norm
from eval.setup import collection, embed_model, query_rewrite

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

# ── V6: GraphRAG (Neo4j 지식 그래프) ─────────────────────────────────────────
from neo4j import GraphDatabase as _Neo4jDriver
from dotenv import load_dotenv
load_dotenv()

_neo4j_driver = _Neo4jDriver.driver(
    os.getenv('NEO4J_URI', '').replace('neo4j+s://', 'neo4j+ssc://'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def neo4j_query_expand(query):
    """쿼리 키워드 → Neo4j 그래프 탐색 → 관련 질환/진료과 반환"""
    keywords = [w for w in query.split() if len(w) >= 2]
    if not keywords:
        return []
    extra_terms = []
    with _neo4j_driver.session() as session:
        result = session.run("""
            MATCH (s:Symptom)-[:SUGGESTS]->(d:Disease)-[:TREATED_BY]->(dept:Department)
            WHERE any(kw IN $keywords WHERE s.name CONTAINS kw)
            RETURN DISTINCT d.name AS disease, dept.name AS department
            LIMIT 10
        """, keywords=keywords)
        for record in result:
            extra_terms.append(record['disease'])
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