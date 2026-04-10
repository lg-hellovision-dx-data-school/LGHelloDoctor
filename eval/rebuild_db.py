"""
medical_knowledge DB에서 개요-XXX 헤더만 제거하여
medical_knowledge_v2 컬렉션으로 저장하는 스크립트

실행: python -m eval.rebuild_db
"""
import os, re
import chromadb
from sentence_transformers import SentenceTransformer

# ── 설정 ──────────────────────────────────────────────────────────────────────
ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH  = os.path.join(ROOT, 'eval', 'RAG', 'db')
SRC_NAME = 'medical_knowledge'
DST_NAME = 'medical_knowledge_v2'

chroma      = chromadb.PersistentClient(path=DB_PATH)
embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# ── 원본 문서 불러오기 ─────────────────────────────────────────────────────────
src_col = chroma.get_collection(SRC_NAME)
raw     = src_col.get(include=['documents', 'metadatas'])
docs    = raw['documents']
metas   = raw['metadatas']
print(f'원본 문서 수: {len(docs)}개')

# ── 헤더 제거 함수 ─────────────────────────────────────────────────────────────
HEADER_PATTERN = re.compile(r'개요-[\w\s&및]+?\s')

def remove_headers(text: str) -> str:
    return HEADER_PATTERN.sub(' ', text).strip()

# ── 목표 컬렉션 초기화 ────────────────────────────────────────────────────────
try:
    chroma.delete_collection(DST_NAME)
    print(f'기존 {DST_NAME} 삭제')
except:
    pass
dst_col = chroma.create_collection(DST_NAME)

# ── 헤더 제거 후 저장 ─────────────────────────────────────────────────────────
cleaned_docs = []
for i, (doc, meta) in enumerate(zip(docs, metas)):
    cleaned = remove_headers(doc)
    cleaned_docs.append(cleaned)
    print(f'[{i+1}/{len(docs)}] 헤더 제거 완료')

print('임베딩 생성 중...')
embeddings = embed_model.encode(cleaned_docs).tolist()

dst_col.add(
    documents=cleaned_docs,
    embeddings=embeddings,
    metadatas=metas,
    ids=[str(i) for i in range(len(cleaned_docs))]
)

print(f'\n완료! {DST_NAME}에 총 {len(cleaned_docs)}개 문서 저장됨')
print(f'setup.py의 CHROMA_COLLECTION_NAME을 "{DST_NAME}"으로 바꾸면 적용됩니다.')
