"""공통 설정: ChromaDB, 임베딩 모델, 유틸리티"""
import sys, io, os
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트로 이동
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH       = os.path.join(ROOT, 'RAG', 'db')
chroma_client = chromadb.PersistentClient(path=DB_PATH)
CHROMA_COLLECTION_NAME = 'medical_knowledge_v2'
collection = chroma_client.get_collection(CHROMA_COLLECTION_NAME)
embed_model   = SentenceTransformer('jhgan/ko-sroberta-multitask')


FILLER_WORDS = [
    "헬로비", "저기요", "있잖아요", "그런데", "혹시",
    "요즘", "방금", "지금", "계속", "아이고",
]

FORBIDDEN_IN_REWRITE = [
    "정형외과", "심장내과", "내과", "이비인후과", "피부과", "치과", "안과",
    "무릎관절염", "심근경색", "고혈압", "당뇨병",
    "진료", "병원",
]

NORMALIZE_PATTERNS = [
    ("귀에서 삐 소리가", "이명 귀 삐소리"),
    ("귀에서 삐 소리", "이명 귀 삐소리"),
    ("귀에서 삐이", "이명 귀 삐소리"),
    ("귀에 삐 소리", "이명 귀 삐소리"),
    ("귀에 삐이", "이명 귀 삐소리"),
    ("삐 소리가", "이명 삐소리"),
    ("삐이", "이명 삐소리"),
    ("이명이", "이명"),
    ("귀가 먹먹", "귀 먹먹함 이명"),
    ("귀가 울려", "이명 귀 울림"),
    ("목소리가 쉬", "목소리 쉼"),
    ("목이 쉰", "목소리 쉼"),
    ("목에 뭔가 걸린", "목 이물감"),
    ("속이 쓰려", "속쓰림"),
    ("신물이 올라와", "신물 역류감"),
    # 역류/속쓰림 보강
    ("속이 쓰리고 신물이 올라와", "속쓰림 신물 역류감 역류성식도염"),
    ("신물이 올라오고 속이 쓰려", "속쓰림 신물 역류감 역류성식도염"),
    ("속쓰리고 신물이 올라와", "속쓰림 신물 역류감 역류성식도염"),
    ("속이 쓰려", "속쓰림 위산 역류감"),
    ("신물이 올라와", "신물 역류감 위산 역류"),
    ("가슴이 쓰려", "가슴 쓰림 속쓰림 역류감"),
    ("목이 타는 듯", "목 쓰림 역류감"),
    ("목까지 올라와", "역류감 위산 역류"),

# 잇몸/치과 보강
    ("잇몸에서 피가 나", "잇몸 출혈 치과 치은염 치주염"),
    ("잇몸에서 피나요", "잇몸 출혈 치과 치은염 치주염"),
    ("잇몸에서 피", "잇몸 출혈 치과 치은염 치주염"),
    ("잇몸이 붓", "잇몸 부종 치과 치은염"),
    ("잇몸이 아파", "잇몸 통증 치과 치은염"),
    ("잇몸이 시려", "잇몸 시림 치과"),
    ("양치하면 피", "잇몸 출혈 치과 치은염 치주염"),
    ("피가 나요 잇몸", "잇몸 출혈 치과 치은염 치주염"),
    ("이가 시려", "치아 시림"),
    ("잇몸에서 피", "잇몸 출혈"),
    ("가슴이 아파", "가슴 통증 흉통"),
    ("가슴이 답답", "가슴 답답함 흉부 불편감"),
    ("가슴이 조여", "가슴 조임 흉부 불편감"),
    ("가슴이 묵직", "가슴 묵직함 흉부 불편감"),
    ("가슴이 쥐어짜", "가슴 통증 흉통"),
    ("숨이 안 쉬어", "호흡곤란 숨참"),
    ("숨이 잘 안 쉬어", "호흡곤란 숨참"),
    ("숨쉬기 답답", "호흡곤란 흉부 불편감"),
    ("숨이 막혀", "호흡곤란"),
    ("숨이 차", "호흡곤란 숨참"),
    ("숨쉬기 힘들", "호흡곤란"),
    ("무릎이 아파", "무릎 통증"),
    ("허리가 아파", "허리 통증"),
    ("어깨가 아파", "어깨 통증"),
    ("손목이 저리", "손목 저림"),
    ("손목이 아파", "손목 통증"),
    ("발목이 삐끗", "발목 염좌"),
    ("발목이 부었", "발목 부종"),
    ("두드러기가 났", "두드러기 피부 발진"),
    ("피부가 가려", "피부 가려움"),
    ("코피가", "코피"),
    ("눈이 빨개", "눈 충혈"),
    ("눈이 침침", "시야 흐림"),
    ("배가 살살 아파", "복통"),
    ("배가 아파", "복통"),
]

# 긴 패턴 우선
NORMALIZE_PATTERNS = sorted(NORMALIZE_PATTERNS, key=lambda x: len(x[0]), reverse=True)


def _remove_fillers(text: str) -> str:
    for word in FILLER_WORDS:
        text = text.replace(word, " ")
    return text


def _normalize_symptom_phrases(text: str) -> str:
    for src, dst in NORMALIZE_PATTERNS:
        if src in text:
            text = text.replace(src, dst)
    return text


def _cleanup_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def normalize_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""

    q = _remove_fillers(q)
    q = _normalize_symptom_phrases(q)

    # 질환/진료과 정답 주입 방지
    for bad in FORBIDDEN_IN_REWRITE:
        q = q.replace(bad, " ")

    return _cleanup_spaces(q)


def build_search_views(query: str) -> dict:
    raw = _cleanup_spaces(query)
    normalized = normalize_query(raw)

    # 벡터 검색은 원문을 우선 사용
    vector_query = raw or normalized

    # 키워드 검색은 약한 normalize 결과를 사용
    keyword_query = normalized or raw

    return {
        "raw": raw,
        "normalized": normalized,
        "vector_query": vector_query,
        "keyword_query": keyword_query,
    }


def query_rewrite(q: str) -> str:
    """
    이전 호환용.
    과한 확장 대신 약한 normalize만 유지한다.
    """
    normalized = normalize_query(q)
    return normalized or q