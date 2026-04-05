# Opr/rag_eval_config.py

B_SAMPLE_1000 = 1000

# 아래 rag_v1_keyword_only ~ rag_v6_graphrag 는
# 추후 각 버전 함수 구현 후 import 연결
# from Opr.rag_versions import ...

rag_b_meta = [
    ('V1', '단순 키워드 검색',             '기준선',               'rag_v1_keyword_only',B_SAMPLE_1000),
    ('V2', 'ChromaDB 벡터 검색',           '의미 기반 검색 도입',  'rag_v2_vector',       B_SAMPLE_1000),
    ('V3', 'Query Rewriting + 벡터',       '쿼리 의도 확장',       'rag_v3_rewrite',      B_SAMPLE_1000),
    ('V4', 'Hybrid (벡터 + 키워드)',       '두 방식 병합',         'rag_v4_hybrid',       B_SAMPLE_1000),
    ('V5', 'Hybrid + Reranking',           '코사인 유사도 재정렬', 'rag_v5_rerank',       B_SAMPLE_1000),
    ('V6', 'GraphRAG (Neo4j 지식 그래프)', '질환-진료과 관계 탐색', 'rag_v6_graphrag',    B_SAMPLE_1000),
]