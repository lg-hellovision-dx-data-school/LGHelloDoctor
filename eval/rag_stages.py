"""RAG V1 ~ V6 검색 함수"""
import os
from numpy import dot
from numpy.linalg import norm
from eval.setup import collection, embed_model, query_rewrite, build_search_views

# ── 공통 helper ──────────────────────────────────────────────────────────────
WEAK_KEYWORDS = {
    "가슴", "귀", "눈", "코", "배", "피부",
    "통증", "불편감", "증상", "숨참"
}

def _tokenize_simple(text):
    return [t.strip() for t in (text or "").replace(",", " ").split() if t.strip()]

def _keyword_doc_score(text: str, keywords: list[str]) -> float:
    if not text or not keywords:
        return 0.0

    score = 0.0
    matched = 0

    for kw in keywords:
        if len(kw) < 2:
            continue
        if kw in text:
            matched += 1
            score += 0.5 if kw in WEAK_KEYWORDS else 1.5

    if matched >= 2:
        score += 1.0

    if "치과" in keywords and "치과" in text:
        score += 0.8
    if "치은염" in keywords and "치은염" in text:
        score += 1.0
    if "치주염" in keywords and "치주염" in text:
        score += 1.0

    if "역류성식도염" in keywords and "역류성식도염" in text:
        score += 1.0
    if "위산" in keywords and "위산" in text:
        score += 0.6
    if "역류감" in keywords and "역류" in text:
        score += 0.8

    return score

def _overlap_count(text: str, terms: list[str]) -> int:
    return sum(1 for t in terms if len(t) >= 2 and t in text)


def _should_keep_doc_for_query(doc: str, keyword_query: str) -> bool:
    kq = keyword_query or ""

    # 속쓰림/신물/역류 계열은
    # '역류' 관련 단서가 없는 일반 소화불량 문서를 약하게 배제
    if any(term in kq for term in ["속쓰림", "신물", "역류감", "위산", "역류성식도염"]):
        if "소화불량" in doc and not any(t in doc for t in ["역류", "위산", "식도", "신물"]):
            return False

    return True

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

# ── V3: 약한 Rewrite + 벡터 검색 ─────────────────────────────────────────────
def rag_v3_rewrite(query):
    views = build_search_views(query)

    raw_q = views["raw"]
    norm_q = views["normalized"]

    if norm_q and norm_q != raw_q:
        merged_q = f"{raw_q} {norm_q}"
    else:
        merged_q = raw_q or norm_q

    emb = embed_model.encode([merged_q]).tolist()
    res = collection.query(query_embeddings=emb, n_results=3)
    return res['documents'][0]

# ── V4: Hybrid (원문 벡터 + 약한 normalize 키워드) ──────────────────────────
def rag_v4_hybrid(query):
    views = build_search_views(query)

    # 1) 벡터 검색은 원문 우선
    emb = embed_model.encode([views["vector_query"]]).tolist()
    vec_res = collection.query(query_embeddings=emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    # 2) 키워드 검색은 normalize 결과를 쓰되, 1토큰 포함만으로 통과시키지 않음
    docs_data = collection.get(include=['documents'])
    keywords = _tokenize_simple(views["keyword_query"])

    kw_scored = []
    for text in docs_data['documents']:
        if not _should_keep_doc_for_query(text, views["keyword_query"]):
            continue

        s = _keyword_doc_score(text, keywords)
        if s >= 2.0:
            kw_scored.append((s, text))

    kw_scored.sort(reverse=True)
    kw_docs = [text for _, text in kw_scored[:3]]

    # 3) 중복 제거 후 후보 결합
    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d)
            combined.append(d)

    return combined[:5]

# ── V5: Hybrid + 혼합 재정렬 ────────────────────────────────────────────────
def rag_v5_rerank(query):
    views = build_search_views(query)
    docs = rag_v4_hybrid(query)

    if not docs:
        return []

    raw_q = views["raw"]
    norm_q = views["normalized"] or raw_q

    raw_emb = embed_model.encode([raw_q])
    norm_emb = embed_model.encode([norm_q])
    d_embs = embed_model.encode(docs)

    raw_terms = _tokenize_simple(raw_q)
    norm_terms = _tokenize_simple(norm_q)

    scored = []
    for i, d_emb in enumerate(d_embs):
        doc = docs[i]

        raw_cos = dot(raw_emb[0], d_emb) / (norm(raw_emb[0]) * norm(d_emb) + 1e-9)
        norm_cos = dot(norm_emb[0], d_emb) / (norm(norm_emb[0]) * norm(d_emb) + 1e-9)

        raw_overlap = _overlap_count(doc, raw_terms)
        norm_overlap = _overlap_count(doc, norm_terms)

        final_score = (
            raw_cos * 0.55 +
            norm_cos * 0.20 +
            raw_overlap * 0.20 +
            norm_overlap * 0.35
        )
        scored.append((final_score, doc))

    scored.sort(reverse=True)
    return [d for _, d in scored[:3]]

# ── V6: GraphRAG (Neo4j 지식 그래프) ─────────────────────────────────────────
from neo4j import GraphDatabase as _Neo4jDriver
from dotenv import load_dotenv
load_dotenv()

_neo4j_driver = None
_neo4j_uri = os.getenv('NEO4J_URI', '').strip()
_neo4j_user = os.getenv('NEO4J_USER', '').strip()
_neo4j_password = os.getenv('NEO4J_PASSWORD', '').strip()

if _neo4j_uri:
    try:
        _neo4j_driver = _Neo4jDriver.driver(
            _neo4j_uri.replace('neo4j+s://', 'neo4j+ssc://'),
            auth=(_neo4j_user, _neo4j_password),
        )
        print(f"[Neo4j] enabled: {_neo4j_uri}")
    except Exception as e:
        print(f"[Neo4j] disabled (driver init failed): {e}")
        _neo4j_driver = None
else:
    print("[Neo4j] disabled: NEO4J_URI not set")

def neo4j_query_expand(query):
    """쿼리 키워드 → Neo4j 그래프 탐색 → 관련 질환/진료과 반환"""
    if _neo4j_driver is None:
        return []

    keywords = [w for w in query.split() if len(w) >= 2]
    if not keywords:
        return []

    extra_terms = []
    try:
        with _neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Symptom)-[:SUGGESTS]->(d:Disease)-[:TREATED_BY]->(dept:Department)
                WHERE any(kw IN $keywords WHERE s.name CONTAINS kw)
                RETURN DISTINCT d.name AS disease, dept.name AS department
                LIMIT 10
            """, keywords=keywords)

            for record in result:
                if record.get('disease'):
                    extra_terms.append(record['disease'])
                if record.get('department'):
                    extra_terms.append(record['department'])

    except Exception as e:
        print(f"[Neo4j] query skipped: {e}")
        return []

    return list(dict.fromkeys(extra_terms))

def _graph_overlap_bonus(doc: str, graph_terms: list[str]) -> float:
    if not doc or not graph_terms:
        return 0.0

    bonus = 0.0
    for term in graph_terms[:5]:
        if term and term in doc:
            bonus += 0.12

    return min(bonus, 0.36)

def rag_v6_graphrag(query):
    """
    V6: 그래프 용어를 쿼리에 직접 주입하지 않고,
    후보 문서 rerank 보조 신호로만 사용
    """
    graph_terms = neo4j_query_expand(query)

    emb = embed_model.encode([query]).tolist()
    vec_res = collection.query(query_embeddings=emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    keywords = _tokenize_simple(query)
    docs_data = collection.get(include=['documents'])
    kw_docs = [
        text for text in docs_data['documents']
        if sum(1 for kw in keywords if kw in text) > 0
    ][:3]

    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d)
            combined.append(d)

    if not combined:
        return []

    q_emb = embed_model.encode([query])
    d_embs = embed_model.encode(combined)

    scored = []
    for i, d_emb in enumerate(d_embs):
        cos_score = dot(q_emb[0], d_emb) / (norm(q_emb[0]) * norm(d_emb) + 1e-9)
        graph_bonus = _graph_overlap_bonus(combined[i], graph_terms)
        final_score = cos_score + graph_bonus
        scored.append((final_score, combined[i]))

    scored.sort(reverse=True)
    return [d for _, d in scored[:3]]