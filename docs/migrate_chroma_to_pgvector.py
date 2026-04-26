# ============================================================
# LG HelloDoctor — ChromaDB → pgvector 마이그레이션
# ============================================================
# 실행 전: docker compose -f docker-compose.pgvector.yml up -d
# pip install chromadb==1.5.5 sentence-transformers psycopg2-binary pgvector

import chromadb
import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# ── 설정 ──
CHROMA_PATH  = "../RAG/db"
EMBED_MODEL  = "snunlp/KR-SROBERTA-multitask"
PG_CONN = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "hellodoctor",
    "user":     "postgres",
    "password": "postgres",
}

# ============================================================
# 1. ChromaDB에서 데이터 읽기
# ============================================================
print("ChromaDB 로딩 중...")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_collection("medical_docs")

results  = collection.get(include=["documents", "metadatas", "embeddings"])
docs     = results["documents"]
metas    = results["metadatas"]
embeddings = results["embeddings"]

print(f"ChromaDB 문서 수: {len(docs)}개")

# 임베딩이 없는 경우 새로 생성
if embeddings is None or len(embeddings) == 0:
    print("임베딩 생성 중...")
    embed_model = SentenceTransformer(EMBED_MODEL)
    embeddings  = embed_model.encode(docs, show_progress_bar=True).tolist()

# ============================================================
# 2. PostgreSQL + pgvector 테이블 생성
# ============================================================
print("\nPostgreSQL 연결 중...")
conn = psycopg2.connect(**PG_CONN)
register_vector(conn)
cur = conn.cursor()

# pgvector 확장 활성화
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# 테이블 생성
VECTOR_DIM = len(embeddings[0])
cur.execute(f"""
    CREATE TABLE IF NOT EXISTS medical_docs (
        id          SERIAL PRIMARY KEY,
        content     TEXT        NOT NULL,
        category    VARCHAR(100),
        source      VARCHAR(200),
        embedding   VECTOR({VECTOR_DIM})
    );
""")

# 인덱스 생성 (IVFFlat — 빠른 근사 검색)
cur.execute("""
    CREATE INDEX IF NOT EXISTS medical_docs_embedding_idx
    ON medical_docs
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
""")

conn.commit()
print(f"테이블 생성 완료 (벡터 차원: {VECTOR_DIM})")

# ============================================================
# 3. 데이터 삽입
# ============================================================
print("\n데이터 삽입 중...")

# 기존 데이터 초기화
cur.execute("TRUNCATE TABLE medical_docs RESTART IDENTITY;")

insert_sql = """
    INSERT INTO medical_docs (content, category, source, embedding)
    VALUES (%s, %s, %s, %s)
"""

batch_size = 50
for i in range(0, len(docs), batch_size):
    batch_docs  = docs[i:i+batch_size]
    batch_metas = metas[i:i+batch_size] if metas else [{}] * len(batch_docs)
    batch_embs  = embeddings[i:i+batch_size]

    rows = []
    for doc, meta, emb in zip(batch_docs, batch_metas, batch_embs):
        meta     = meta or {}
        category = meta.get("category", "unknown")
        source   = meta.get("source", "")
        rows.append((doc, category, source, emb))

    cur.executemany(insert_sql, rows)
    conn.commit()
    print(f"  {min(i+batch_size, len(docs))}/{len(docs)}개 삽입 완료")

print(f"\n마이그레이션 완료: {len(docs)}개 문서")

# ============================================================
# 4. 검증
# ============================================================
cur.execute("SELECT COUNT(*) FROM medical_docs;")
count = cur.fetchone()[0]
print(f"pgvector 저장 문서 수: {count}개")

cur.execute("SELECT category, COUNT(*) FROM medical_docs GROUP BY category ORDER BY COUNT(*) DESC;")
rows = cur.fetchall()
print("\n카테고리 분포:")
for category, cnt in rows:
    print(f"  {category}: {cnt}개")

# 검색 테스트
print("\n[벡터 검색 테스트] '무릎이 아파요'")
embed_model = SentenceTransformer(EMBED_MODEL)
test_emb = embed_model.encode("무릎이 아파요").tolist()
cur.execute("""
    SELECT content, category,
           1 - (embedding <=> %s::vector) AS similarity
    FROM medical_docs
    ORDER BY embedding <=> %s::vector
    LIMIT 3;
""", (test_emb, test_emb))

for row in cur.fetchall():
    content, category, sim = row
    print(f"  [{category}] 유사도: {sim:.3f} | {content[:60]}...")

cur.close()
conn.close()
print("\n완료. pgAdmin: http://localhost:5050")
print("  이메일: admin@admin.com / 비밀번호: admin")
print("  서버 연결: host=postgres, port=5432, db=hellodoctor")
