"""공통 설정: ChromaDB, 임베딩 모델, 유틸리티"""
import sys, io, os
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
