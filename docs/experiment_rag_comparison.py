# ============================================================
# LG HelloDoctor — RAG V1~V8 검색 정확도 비교 실험
# V1 키워드 / V2 벡터 / V3 QueryRewriting / V4 Hybrid
# V5 Rerank / V6 GraphRAG / V7 HyDE / V8 MultiQuery
# Google Colab A100 환경 기준
# ============================================================

# %%
# ============================================================
# [Cell 1] 패키지 설치
# ============================================================
# !pip install -q chromadb==1.5.5
# !pip install -q sentence-transformers
# !pip install -q rank_bm25
# !pip install -q langchain langchain-community langchain-chroma
# !pip install -q groq
# !pip install -q networkx  # GraphRAG용
# !pip install -q pandas scikit-learn

# %%
# ============================================================
# [Cell 2] 임포트
# ============================================================
import os
import json
import re
import random
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

# LangChain (V7 HyDE, V8 MultiQuery용)
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import MultiQueryRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.chat_models import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# %%
# ============================================================
# [Cell 3] 환경 설정
# ============================================================

# Google Drive 마운트 (ChromaDB 경로)
# from google.colab import drive
# drive.mount('/content/drive')

CHROMA_PATH = "./RAG/db"          # 실제 ChromaDB 경로로 교체
EMBED_MODEL  = "snunlp/KR-SROBERTA-multitask"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key")
TOP_K        = 3


# %%
# ============================================================
# [Cell 4] RAG 평가 데이터셋
# 쿼리 + 정답 키워드 (Top-3 안에 해당 키워드 포함 시 정답)
# ============================================================

RAG_EVAL_DATA = [
    # 증상 → 진료과 (정형외과)
    {"query": "아이고 무릎이 너무 쑤셔요",           "expected_keywords": ["무릎", "관절", "정형외과"]},
    {"query": "어제부터 허리가 많이 아파요",          "expected_keywords": ["허리", "척추", "정형외과"]},
    {"query": "어깨가 결리고 팔이 저려요",            "expected_keywords": ["어깨", "경추", "정형외과"]},
    {"query": "발목을 삐었어요",                      "expected_keywords": ["발목", "인대", "정형외과"]},
    {"query": "손목이 너무 아파요",                   "expected_keywords": ["손목", "관절", "정형외과"]},

    # 증상 → 내과
    {"query": "열이 나고 기침이 심해요",              "expected_keywords": ["발열", "기침", "내과"]},
    {"query": "소화가 안 되고 속이 쓰려요",           "expected_keywords": ["소화", "위", "내과"]},
    {"query": "며칠째 설사를 해요",                   "expected_keywords": ["설사", "장", "내과"]},
    {"query": "혈압이 높은 것 같아요",                "expected_keywords": ["혈압", "고혈압", "내과"]},
    {"query": "당뇨가 있는데 혈당이 올라갔어요",      "expected_keywords": ["당뇨", "혈당", "내과"]},

    # 증상 → 피부과
    {"query": "피부에 두드러기가 났어요",             "expected_keywords": ["두드러기", "피부", "피부과"]},
    {"query": "얼굴에 뾰루지가 심하게 났어요",        "expected_keywords": ["여드름", "피부", "피부과"]},
    {"query": "손이 너무 가려워요",                   "expected_keywords": ["가려움", "피부염", "피부과"]},

    # 증상 → 안과
    {"query": "눈이 충혈되고 가려워요",               "expected_keywords": ["결막염", "눈", "안과"]},
    {"query": "있잖아요 눈이 침침하고 잘 안 보여요",  "expected_keywords": ["시력", "눈", "안과"]},

    # 증상 → 이비인후과
    {"query": "귀에서 이상한 소리가 나요",            "expected_keywords": ["이명", "귀", "이비인후과"]},
    {"query": "목이 너무 아프고 삼키기 힘들어요",     "expected_keywords": ["인후염", "목", "이비인후과"]},
    {"query": "코가 막히고 콧물이 계속 나요",         "expected_keywords": ["비염", "코", "이비인후과"]},

    # 응급
    {"query": "갑자기 숨이 안 쉬어져요",              "expected_keywords": ["호흡곤란", "응급", "119"]},
    {"query": "아이고 쓰러졌어요",                    "expected_keywords": ["응급", "의식", "119"]},
    {"query": "어머 말이 어눌해졌어요",               "expected_keywords": ["뇌졸중", "응급", "119"]},

    # 복약
    {"query": "타이레놀 어떻게 먹는 건가요",          "expected_keywords": ["타이레놀", "해열", "복용"]},
    {"query": "혈압약 언제 먹어야 해요",              "expected_keywords": ["혈압약", "복용", "아침"]},
    {"query": "항생제 다 먹어야 해요",                "expected_keywords": ["항생제", "복용", "완료"]},
    {"query": "두 가지 약 같이 먹어도 돼요",          "expected_keywords": ["병용", "약물", "복용"]},
]

print(f"RAG 평가셋: {len(RAG_EVAL_DATA)}개")


# %%
# ============================================================
# [Cell 5] 공통 유틸리티
# ============================================================

def check_top_k(retrieved_docs: List[str], expected_keywords: List[str], k: int = 3) -> bool:
    """Top-K 문서 안에 정답 키워드가 하나라도 포함되면 정답"""
    retrieved_text = " ".join(retrieved_docs[:k]).lower()
    return any(kw.lower() in retrieved_text for kw in expected_keywords)

def evaluate_retriever(retriever_fn, eval_data: List[Dict], label: str) -> float:
    """retriever_fn(query) → List[str] 형태의 함수를 받아 정확도 측정"""
    correct = 0
    for item in eval_data:
        try:
            docs = retriever_fn(item["query"])
            if check_top_k(docs, item["expected_keywords"]):
                correct += 1
        except Exception as e:
            print(f"  오류 [{label}]: {e}")
    accuracy = correct / len(eval_data) * 100
    print(f"[{label}] Top-3 정확도: {accuracy:.1f}%  ({correct}/{len(eval_data)})")
    return accuracy


# %%
# ============================================================
# [Cell 6] 임베딩 모델 & ChromaDB 로드
# ============================================================

print("임베딩 모델 로딩 중...")
embed_model = SentenceTransformer(EMBED_MODEL)

print("ChromaDB 로딩 중...")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection("medical_docs")

# 전체 문서 로드 (BM25, GraphRAG용)
all_results = collection.get(include=["documents", "metadatas"])
all_docs    = all_results["documents"]
all_meta    = all_results["metadatas"]

print(f"ChromaDB 문서 수: {len(all_docs)}개")


# %%
# ============================================================
# [Cell 7] V1 — 키워드 검색 (BM25)
# ============================================================

tokenized_docs = [doc.split() for doc in all_docs]
bm25 = BM25Okapi(tokenized_docs)

def v1_keyword(query: str) -> List[str]:
    tokenized_query = query.split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:TOP_K]
    return [all_docs[i] for i in top_indices]

acc_v1 = evaluate_retriever(v1_keyword, RAG_EVAL_DATA, "V1 키워드(BM25)")


# %%
# ============================================================
# [Cell 8] V2 — 벡터 검색 (ChromaDB)
# ============================================================

def v2_vector(query: str) -> List[str]:
    query_emb = embed_model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=TOP_K,
        include=["documents"],
    )
    return results["documents"][0]

acc_v2 = evaluate_retriever(v2_vector, RAG_EVAL_DATA, "V2 벡터(ChromaDB)")


# %%
# ============================================================
# [Cell 9] V3 — Query Rewriting + 벡터 검색
# ============================================================

from groq import Groq
groq_client = Groq(api_key=GROQ_API_KEY)

QUERY_REWRITE_MAP = {
    "무릎": "무릎통증 정형외과 관련 증상 치료 방법",
    "허리": "허리통증 요통 척추 정형외과 증상",
    "어깨": "어깨통증 오십견 회전근개 정형외과",
    "소화": "소화불량 위염 소화기내과 증상",
    "혈압": "고혈압 혈압약 내과 관리",
    "당뇨": "당뇨병 혈당 내과 관리 합병증",
    "피부": "피부염 두드러기 피부과 증상",
    "눈": "안과 눈 질환 시력 결막염",
    "귀": "이비인후과 귀 이명 청력",
    "기침": "기관지염 폐 호흡기 내과",
    "응급": "응급 처치 119 즉각 대처",
    "타이레놀": "타이레놀 아세트아미노펜 해열진통제 복용법",
    "혈압약": "항고혈압제 복용법 주의사항",
}

def rewrite_query(query: str) -> str:
    for keyword, rewritten in QUERY_REWRITE_MAP.items():
        if keyword in query:
            return rewritten
    # 맵에 없으면 LLM으로 재작성
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"다음 의료 질문을 벡터 검색에 적합한 형태로 재작성하세요. 핵심 의학 키워드를 포함해서 한 문장으로만 답하세요.\n질문: {query}\n재작성:"
        }],
        temperature=0,
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()

def v3_query_rewriting(query: str) -> List[str]:
    rewritten = rewrite_query(query)
    query_emb = embed_model.encode(rewritten).tolist()
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=TOP_K,
        include=["documents"],
    )
    return results["documents"][0]

acc_v3 = evaluate_retriever(v3_query_rewriting, RAG_EVAL_DATA, "V3 Query Rewriting")


# %%
# ============================================================
# [Cell 10] V4 — Hybrid Search (BM25 + 벡터, RRF 결합)
# ============================================================

def reciprocal_rank_fusion(rankings: List[List[int]], k: int = 60) -> List[int]:
    """Reciprocal Rank Fusion으로 여러 랭킹 결합"""
    scores = {}
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking):
            scores[doc_idx] = scores.get(doc_idx, 0) + 1 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

def v4_hybrid(query: str) -> List[str]:
    # BM25 랭킹
    bm25_scores = bm25.get_scores(query.split())
    bm25_ranking = list(np.argsort(bm25_scores)[::-1][:20])

    # 벡터 랭킹
    query_emb = embed_model.encode(query).tolist()
    vector_results = collection.query(
        query_embeddings=[query_emb],
        n_results=20,
        include=["documents"],
    )
    vector_docs = vector_results["documents"][0]
    vector_ranking = [all_docs.index(doc) for doc in vector_docs if doc in all_docs]

    # RRF 결합
    fused = reciprocal_rank_fusion([bm25_ranking, vector_ranking])
    return [all_docs[i] for i in fused[:TOP_K]]

acc_v4 = evaluate_retriever(v4_hybrid, RAG_EVAL_DATA, "V4 Hybrid(BM25+Vector+RRF)")


# %%
# ============================================================
# [Cell 11] V5 — Rerank (CrossEncoder)
# ============================================================

cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def v5_rerank(query: str) -> List[str]:
    # 1단계: 벡터 검색으로 후보 20개
    query_emb = embed_model.encode(query).tolist()
    candidates = collection.query(
        query_embeddings=[query_emb],
        n_results=20,
        include=["documents"],
    )["documents"][0]

    # 2단계: CrossEncoder로 재순위화
    pairs = [[query, doc] for doc in candidates]
    scores = cross_encoder.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:TOP_K]]

acc_v5 = evaluate_retriever(v5_rerank, RAG_EVAL_DATA, "V5 Rerank(CrossEncoder)")


# %%
# ============================================================
# [Cell 12] V6 — GraphRAG (개념 노드 기반 검색)
# ============================================================
import networkx as nx

def build_medical_graph(docs: List[str], meta: List[Dict]) -> nx.Graph:
    """의료 문서를 노드로, 공통 키워드를 엣지로 연결"""
    G = nx.Graph()
    medical_keywords = [
        "정형외과", "내과", "피부과", "안과", "이비인후과",
        "응급", "통증", "염증", "수술", "약물", "혈압", "당뇨",
    ]
    for i, (doc, meta_item) in enumerate(zip(docs, meta)):
        category = meta_item.get("category", "unknown") if meta_item else "unknown"
        G.add_node(i, text=doc, category=category)
    # 같은 카테고리 문서끼리 엣지 연결
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            cat_i = G.nodes[i].get("category", "")
            cat_j = G.nodes[j].get("category", "")
            if cat_i == cat_j and cat_i != "unknown":
                shared = sum(1 for kw in medical_keywords
                             if kw in docs[i] and kw in docs[j])
                if shared > 0:
                    G.add_edge(i, j, weight=shared)
    return G

print("의료 지식 그래프 구축 중...")
medical_graph = build_medical_graph(all_docs, all_meta)
print(f"그래프 노드: {medical_graph.number_of_nodes()}개, 엣지: {medical_graph.number_of_edges()}개")

def v6_graph_rag(query: str) -> List[str]:
    # 1단계: 벡터 검색으로 시드 노드 찾기
    query_emb = embed_model.encode(query).tolist()
    seed_results = collection.query(
        query_embeddings=[query_emb],
        n_results=3,
        include=["documents"],
    )["documents"][0]

    # 2단계: 시드 노드의 이웃 노드 탐색
    seed_indices = [all_docs.index(doc) for doc in seed_results if doc in all_docs]
    expanded = set(seed_indices)
    for idx in seed_indices:
        if idx in medical_graph:
            neighbors = list(medical_graph.neighbors(idx))
            # 엣지 가중치 기준 상위 이웃만 추가
            weighted = sorted(
                neighbors,
                key=lambda n: medical_graph[idx][n].get("weight", 0),
                reverse=True
            )
            expanded.update(weighted[:2])

    # 3단계: 확장된 후보에서 벡터 유사도로 최종 TOP_K 선택
    candidates = [all_docs[i] for i in expanded if i < len(all_docs)]
    if not candidates:
        return seed_results
    cand_embs = embed_model.encode(candidates)
    query_emb_np = embed_model.encode(query)
    sims = np.dot(cand_embs, query_emb_np) / (
        np.linalg.norm(cand_embs, axis=1) * np.linalg.norm(query_emb_np) + 1e-8
    )
    top_indices = np.argsort(sims)[::-1][:TOP_K]
    return [candidates[i] for i in top_indices]

acc_v6 = evaluate_retriever(v6_graph_rag, RAG_EVAL_DATA, "V6 GraphRAG")


# %%
# ============================================================
# [Cell 13] V7 — HyDE (LangChain)
# 사용자 쿼리 → LLM이 가상 답변 문서 생성 → 가상 문서로 검색
# ============================================================

# LangChain용 ChromaDB 래퍼
lc_embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
lc_vectorstore = Chroma(
    client=chroma_client,
    collection_name="medical_docs",
    embedding_function=lc_embeddings,
)

# HyDE용 프롬프트
HYDE_PROMPT = PromptTemplate(
    input_variables=["query"],
    template="""당신은 한국어 의료 정보 전문가입니다.
다음 환자의 질문에 대해 의료 문서처럼 상세한 답변을 작성하세요.
실제 문서처럼 증상, 원인, 진료과를 포함해 2~3문장으로 작성하세요.

질문: {query}
의료 문서:"""
)

from langchain_groq import ChatGroq as LangChainGroq
lc_llm = LangChainGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile",
    temperature=0,
)

hyde_chain = HYDE_PROMPT | lc_llm | StrOutputParser()

def v7_hyde(query: str) -> List[str]:
    # 1단계: LLM이 가상 답변 문서 생성
    hypothetical_doc = hyde_chain.invoke({"query": query})
    # 2단계: 가상 문서로 벡터 검색
    hypo_emb = embed_model.encode(hypothetical_doc).tolist()
    results = collection.query(
        query_embeddings=[hypo_emb],
        n_results=TOP_K,
        include=["documents"],
    )
    return results["documents"][0]

acc_v7 = evaluate_retriever(v7_hyde, RAG_EVAL_DATA, "V7 HyDE(LangChain)")


# %%
# ============================================================
# [Cell 14] V8 — Multi-Query Retrieval (LangChain)
# 하나의 쿼리 → LLM이 여러 관점의 쿼리 생성 → 각각 검색 → 합치기
# ============================================================

MULTI_QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""당신은 한국어 의료 검색 전문가입니다.
환자의 질문을 3가지 다른 관점의 검색 쿼리로 변환하세요.
각 쿼리는 다른 의학적 관점(증상/원인/진료과)을 포함해야 합니다.
각 줄에 하나씩, 번호 없이 출력하세요.

질문: {question}
검색 쿼리:"""
)

lc_retriever = lc_vectorstore.as_retriever(search_kwargs={"k": TOP_K})

multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=lc_retriever,
    llm=lc_llm,
    prompt=MULTI_QUERY_PROMPT,
)

def v8_multi_query(query: str) -> List[str]:
    docs = multi_query_retriever.invoke(query)
    # 중복 제거 후 TOP_K 반환
    seen = set()
    unique_docs = []
    for doc in docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc.page_content)
    return unique_docs[:TOP_K]

acc_v8 = evaluate_retriever(v8_multi_query, RAG_EVAL_DATA, "V8 Multi-Query(LangChain)")


# %%
# ============================================================
# [Cell 15] 최종 결과 비교 테이블
# ============================================================

results = {
    "버전": ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"],
    "방식": [
        "키워드 (BM25)",
        "벡터 (ChromaDB)",
        "Query Rewriting",
        "Hybrid (BM25+Vector+RRF)",
        "Rerank (CrossEncoder)",
        "GraphRAG",
        "HyDE (LangChain)",
        "Multi-Query (LangChain)",
    ],
    "Top-3 정확도(%)": [
        round(acc_v1, 1), round(acc_v2, 1), round(acc_v3, 1),
        round(acc_v4, 1), round(acc_v5, 1), round(acc_v6, 1),
        round(acc_v7, 1), round(acc_v8, 1),
    ],
}

df = pd.DataFrame(results)
best_idx = df["Top-3 정확도(%)"].idxmax()
df["비고"] = ""
df.loc[best_idx, "비고"] = "← 최고"

print("\n" + "="*65)
print("RAG V1~V8 검색 정확도 비교 결과")
print("="*65)
print(df.to_string(index=False))
print("="*65)

df.to_csv("rag_experiment_results.csv", index=False, encoding="utf-8-sig")
print("\n결과 저장 완료: rag_experiment_results.csv")
