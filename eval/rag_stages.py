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

