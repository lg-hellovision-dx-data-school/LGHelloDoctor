"""공통 설정: ChromaDB, 임베딩 모델, 유틸리티"""
import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트로 이동
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

import chromadb
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm

DB_PATH       = os.path.join(ROOT, 'RAG', 'db')
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection    = chroma_client.get_collection('medical_knowledge')
embed_model   = SentenceTransformer('jhgan/ko-sroberta-multitask')

QUERY_REWRITE_MAP = {
    '무릎': '무릎관절염 정형외과 관절 통증 진료',
    '허리': '허리디스크 정형외과 척추 통증 진료',
    '가슴': '심근경색 심장내과 흉통 진료',
    '혈압': '고혈압 내과 혈압약 복용',
    '항생제': '항생제 복용 방법 주의사항',
    '당뇨': '당뇨병 내과 당뇨약 복용',
}

def query_rewrite(q):
    for kw, rewritten in QUERY_REWRITE_MAP.items():
        if kw in q:
            return rewritten
    return q

# ── STEP 3: 문서 청킹 ─────────────────────────────────────────────────────────
def _chunk_text(text, max_chars=200):
    """한국어 문장 단위로 텍스트 청킹 (최대 max_chars 자)"""
    # 한국어 문장 종결 패턴으로 분리
    sentences = re.split(r'(?<=[다요임음됩니니])\s+', text)
    chunks, current = [], ''
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) + 1 <= max_chars:
            current += (' ' if current else '') + sent
        else:
            if current:
                chunks.append(current)
            # 단일 문장이 max_chars 초과하면 강제 분할
            if len(sent) > max_chars:
                for i in range(0, len(sent), max_chars):
                    part = sent[i:i + max_chars]
                    if len(part) >= 20:
                        chunks.append(part)
                current = ''
            else:
                current = sent
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c) >= 20]

def _build_chunked_collection():
    """기존 컬렉션 문서를 청킹해 새 컬렉션 생성 (이미 존재하면 재사용)"""
    CHUNK_COL = 'medical_knowledge_chunks'
    try:
        col = chroma_client.get_collection(CHUNK_COL)
        if col.count() > 0:
            print(f'청킹 DB 로드: {col.count()}개 청크')
            return col
    except Exception:
        pass

    col = chroma_client.get_or_create_collection(
        CHUNK_COL,
        metadata={'hnsw:space': 'cosine'}
    )

    all_data = collection.get(include=['documents', 'metadatas'])
    chunk_ids, chunk_docs, chunk_metas = [], [], []

    for i, (doc, meta) in enumerate(zip(all_data['documents'], all_data['metadatas'] or [{}]*len(all_data['documents']))):
        chunks = _chunk_text(doc)
        for j, chunk in enumerate(chunks):
            chunk_ids.append(f'c{i}_{j}')
            chunk_docs.append(chunk)
            chunk_metas.append({**(meta or {}), 'chunk_idx': j, 'source_idx': i})

    # 배치 임베딩 (50개씩 나눠서 처리)
    BATCH = 50
    all_embs = []
    for start in range(0, len(chunk_docs), BATCH):
        batch = chunk_docs[start:start + BATCH]
        all_embs.extend(embed_model.encode(batch).tolist())

    col.add(ids=chunk_ids, documents=chunk_docs, metadatas=chunk_metas, embeddings=all_embs)
    print(f'청킹 DB 생성 완료: {col.count()}개 청크 (원본 {len(all_data["documents"])}개 문서)')
    return col

collection_chunked = _build_chunked_collection()
