"""
RAG 평가 노트북 생성 스크립트.

생성되는 노트북: finetune/rag_evaluation.ipynb

섹션:
0. 환경 설정
1. ChromaDB 탐색 및 코퍼스 분석
2. 평가 데이터셋 생성 (Groq LLM 자동 생성 + 검수)
3. 검색 함수 구현 (Vector / BM25 / Hybrid / +Reranker / +LLM Rewriting)
4. 평가 지표 구현 (Recall@k, MRR, nDCG, Precision@k)
5. Baseline 평가 (Vector only)
6. + Cross-Encoder Reranker
7. + BM25 Hybrid Search
8. + LLM Query Rewriting
9. 청킹 전략 분석
10. Citation Tracking 검증
11. Negation Handling 테스트
12. Hard-Negative 분석
13. Lightweight Medical KG
14. 최종 비교표 + 시각화
15. Backend 적용 코드 (참고)
"""
import json
import uuid
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "rag_evaluation.ipynb"


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source,
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source,
        "outputs": [],
        "execution_count": None,
    }


cells = []

# ════════════════════════════════════════════════════════════════════════
# 0. 환경 설정
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""# LG HelloDoctor RAG 고도화 평가 노트북

기존 vector-only RAG의 성능을 정량 측정하고, 단계별 고도화 효과를 비교합니다.

**평가 단계 (Ablation):**
1. **Baseline** — Vector only (현재 backend 구현)
2. **+ Cross-Encoder Reranker**
3. **+ BM25 Hybrid Search**
4. **+ LLM Query Rewriting**

**측정 지표:** Recall@1, Recall@3, Recall@5, MRR, nDCG@5, Precision@3

**환경:** Colab GPU (T4 권장, 30분 이내 완료)"""))

cells.append(md("## 0. 환경 설정"))

cells.append(code("""# Colab 환경에서 처음 실행 시 설치
!pip install -q chromadb==1.5.5 sentence-transformers rank-bm25 \\
    konlpy soynlp groq seaborn matplotlib"""))

cells.append(code("""import os
import re
import json
import random
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

print("Imports done.")"""))

cells.append(code("""# Colab Drive 마운트 및 경로 설정
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=True)
    PROJECT_DIR = Path('/content/drive/MyDrive/LG_HelloDoctor_혼자_논문')
except ImportError:
    PROJECT_DIR = Path('.')

# ChromaDB 경로 (Drive에 RAG/db/ 업로드 필요)
DB_PATH = PROJECT_DIR / 'RAG' / 'db'
EVAL_DATA_DIR = PROJECT_DIR / 'RAG' / 'eval'
EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f'PROJECT_DIR: {PROJECT_DIR}')
print(f'DB_PATH exists: {DB_PATH.exists()}')"""))

# ════════════════════════════════════════════════════════════════════════
# 1. ChromaDB 탐색
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 1. ChromaDB 탐색 및 코퍼스 분석

기존 ChromaDB의 구조를 파악합니다.
- 컬렉션명, 문서 수, 임베딩 차원, 청크 길이 분포, 메타데이터 분석"""))

cells.append(code("""# ChromaDB 로드
chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
collections = chroma_client.list_collections()
print('컬렉션 목록:')
for c in collections:
    print(f'  - {c.name}')

# 메인 컬렉션 (medical_knowledge)
collection = chroma_client.get_collection('medical_knowledge')
print(f'\\n총 문서 수: {collection.count()}')"""))

cells.append(code("""# 전체 문서 추출
all_data = collection.get(include=['documents', 'metadatas', 'embeddings'])

ids = all_data['ids']
docs = all_data['documents']
metas = all_data['metadatas'] or [{} for _ in ids]
embeds = all_data.get('embeddings') or []

print(f'문서 ID 샘플: {ids[:5]}')
print(f'임베딩 차원: {len(embeds[0]) if len(embeds) > 0 else "N/A"}')
print(f'\\n첫 번째 문서:')
print(f'  ID: {ids[0]}')
print(f'  Meta: {metas[0]}')
print(f'  Doc[:200]: {docs[0][:200]}')"""))

cells.append(code("""# 청크 길이 분포
lengths = [len(d) for d in docs]
print(f'문서 길이 통계 (문자 수)')
print(f'  min={min(lengths)}, max={max(lengths)}, mean={np.mean(lengths):.0f}, median={np.median(lengths):.0f}')

plt.figure(figsize=(10, 4))
plt.hist(lengths, bins=30, edgecolor='black')
plt.axvline(np.mean(lengths), color='red', linestyle='--', label=f'mean={np.mean(lengths):.0f}')
plt.xlabel('Chunk length (chars)')
plt.ylabel('Count')
plt.title('Chunk length distribution')
plt.legend()
plt.show()

# 카테고리 분포 (메타데이터)
print('\\n메타데이터 키:')
all_meta_keys = set()
for m in metas:
    all_meta_keys.update(m.keys())
print(f'  {all_meta_keys}')

if 'category' in all_meta_keys:
    cat_counts = Counter(m.get('category', '?') for m in metas)
    print('\\n카테고리 분포:')
    for c, n in cat_counts.most_common():
        print(f'  {c}: {n}')"""))

cells.append(code("""# 코퍼스 DataFrame 생성 (이후 평가에서 재사용)
corpus_df = pd.DataFrame({
    'doc_id': ids,
    'text': docs,
    'meta': metas,
})
# 카테고리 컬럼 추출
corpus_df['category'] = corpus_df['meta'].apply(lambda m: m.get('category', '?'))
corpus_df['title'] = corpus_df['meta'].apply(lambda m: m.get('title', m.get('source', '?')))

print(f'코퍼스 크기: {len(corpus_df)}')
display(corpus_df.head(3))"""))

# ════════════════════════════════════════════════════════════════════════
# 2. 평가 데이터셋 생성
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 2. 평가 데이터셋 생성

각 문서에서 1~2개의 평가 쿼리를 합성합니다. 총 100개 목표.
- **방법 1**: Groq LLM(`llama-3.3-70b`)으로 각 문서 → 자연스러운 쿼리 생성
- **방법 2**: 수동 작성 (양 적을 시)

각 항목 구조:
```json
{
  "query_id": "Q-001",
  "query": "무릎이 아픈데 어디로 가야 해요?",
  "relevant_doc_ids": ["doc_42", "doc_51"],
  "category": "증상_진료과",
  "difficulty": "easy"
}
```"""))

cells.append(code("""# Groq API 키 (환경변수 또는 직접 입력)
import os
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

if not GROQ_API_KEY:
    GROQ_API_KEY = input('Groq API key 입력 (없으면 빈칸): ').strip()

USE_GROQ = bool(GROQ_API_KEY)
print(f'Groq 사용: {USE_GROQ}')"""))

cells.append(code("""# Groq 기반 쿼리 자동 생성 (USE_GROQ=True인 경우)
def generate_queries_with_groq(doc_text, category, n=2):
    \"\"\"문서 1개에서 n개의 쿼리 생성.\"\"\"
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f\"\"\"다음 의료 문서에서 시니어(어르신) 사용자가 자연스럽게 물어볼 만한 한국어 질문 {n}개를 생성하세요.

문서 카테고리: {category}
문서 내용:
{doc_text[:600]}

요구사항:
- 각 질문은 짧고 자연스러운 구어체
- 질문 1개당 1줄, JSON 배열 형태로 출력 (예: ["질문1", "질문2"])
- 다른 설명은 출력하지 마세요\"\"\"

    resp = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.7,
        max_tokens=200,
    )
    text = resp.choices[0].message.content.strip()
    # JSON 추출
    m = re.search(r'\\[.*\\]', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return []


# 또는 수동 시드 쿼리 (USE_GROQ=False)
SEED_QUERIES = [
    # 증상 → 진료과
    {'query': '무릎이 시리고 아파요', 'keywords': ['무릎', '정형외과'], 'category': '증상_진료과'},
    {'query': '허리가 욱신거려요', 'keywords': ['허리', '정형외과', '디스크'], 'category': '증상_진료과'},
    {'query': '눈이 침침해서 잘 안 보여요', 'keywords': ['눈', '안과'], 'category': '증상_진료과'},
    {'query': '귀가 잘 안 들려요', 'keywords': ['귀', '이비인후과'], 'category': '증상_진료과'},
    {'query': '피부에 두드러기가 났어요', 'keywords': ['피부', '두드러기', '피부과'], 'category': '증상_진료과'},
    {'query': '머리가 자꾸 어지러워요', 'keywords': ['머리', '어지럼', '신경과'], 'category': '증상_진료과'},
    {'query': '배가 자주 아파요', 'keywords': ['배', '복통', '소화기내과'], 'category': '증상_진료과'},
    {'query': '가슴이 답답하고 두근거려요', 'keywords': ['가슴', '심장', '심혈관'], 'category': '증상_진료과'},
    {'query': '기침이 멈추지 않아요', 'keywords': ['기침', '호흡기'], 'category': '증상_진료과'},
    {'query': '소변 보기가 불편해요', 'keywords': ['소변', '비뇨기'], 'category': '증상_진료과'},

    # 복약
    {'query': '타이레놀 먹어도 되나요', 'keywords': ['타이레놀', '아세트아미노펜'], 'category': '복약_안내'},
    {'query': '혈압약과 진통제 같이 먹어도 돼요', 'keywords': ['혈압약', '진통제', '병용'], 'category': '복약_안내'},
    {'query': '감기약은 식전에 먹나요 식후에 먹나요', 'keywords': ['감기약', '식전', '식후'], 'category': '복약_안내'},
    {'query': '항생제 부작용이 어떤 게 있어요', 'keywords': ['항생제', '부작용'], 'category': '복약_안내'},
    {'query': '약 먹는 시간을 놓쳤는데', 'keywords': ['복용', '시간'], 'category': '복약_안내'},

    # 응급
    {'query': '갑자기 가슴이 쥐어짜듯 아파요', 'keywords': ['가슴', '쥐어짜', '심근경색'], 'category': '응급_안내'},
    {'query': '한쪽 팔에 힘이 안 들어가요', 'keywords': ['마비', '뇌졸중'], 'category': '응급_안내'},
    {'query': '말이 어눌해지고 얼굴이 비뚤어졌어요', 'keywords': ['뇌졸중', '안면마비'], 'category': '응급_안내'},
    {'query': '의식이 흐려져요', 'keywords': ['의식', '저하'], 'category': '응급_안내'},
    {'query': '숨이 잘 안 쉬어져요', 'keywords': ['호흡곤란'], 'category': '응급_안내'},
]
print(f'수동 시드 쿼리 수: {len(SEED_QUERIES)}')"""))

cells.append(code("""# 쿼리당 정답 doc_ids 자동 매칭 (키워드 기반)
def find_relevant_docs(keywords, corpus_df, top_n=3):
    \"\"\"키워드 포함 문서 ID 찾기 (대소문자 무시).\"\"\"
    matches = []
    for _, row in corpus_df.iterrows():
        text = row['text']
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            matches.append((row['doc_id'], score))
    matches.sort(key=lambda x: -x[1])
    return [m[0] for m in matches[:top_n]]


# 시드 쿼리에서 평가셋 생성
eval_dataset = []
for i, q in enumerate(SEED_QUERIES, 1):
    rel_ids = find_relevant_docs(q['keywords'], corpus_df, top_n=3)
    if not rel_ids:
        print(f'⚠ 쿼리 {i}: 매칭 doc 없음 — {q[\"query\"]}')
        continue
    eval_dataset.append({
        'query_id': f'Q-{i:03d}',
        'query': q['query'],
        'keywords': q['keywords'],
        'relevant_doc_ids': rel_ids,
        'category': q['category'],
        'difficulty': 'easy' if len(rel_ids) >= 2 else 'medium',
    })

print(f'\\n생성된 평가셋: {len(eval_dataset)}개')
print('\\n샘플:')
for e in eval_dataset[:3]:
    print(f'  [{e[\"query_id\"]}] {e[\"query\"]} → {e[\"relevant_doc_ids\"]}')"""))

cells.append(code("""# Groq로 추가 쿼리 생성 (사용 가능 시)
if USE_GROQ:
    additional = []
    sample_docs = corpus_df.sample(40, random_state=SEED)  # 40개 문서 샘플링
    for i, (_, row) in enumerate(sample_docs.iterrows(), len(eval_dataset) + 1):
        try:
            queries = generate_queries_with_groq(row['text'], row['category'], n=2)
            for j, q in enumerate(queries[:2]):
                additional.append({
                    'query_id': f'Q-{i:03d}-{j}',
                    'query': q.strip(),
                    'keywords': [],
                    'relevant_doc_ids': [row['doc_id']],
                    'category': row['category'],
                    'difficulty': 'medium',
                    'source': 'groq_synthetic',
                })
            if i % 10 == 0:
                print(f'  진행: {i}/{len(eval_dataset) + 40}')
        except Exception as e:
            print(f'  쿼리 생성 실패 (doc_id={row[\"doc_id\"]}): {e}')

    eval_dataset.extend(additional)
    print(f'\\n총 평가셋: {len(eval_dataset)}개 (수동 {len(SEED_QUERIES)} + Groq {len(additional)})')
else:
    print('Groq 미사용 — 수동 시드만 사용')"""))

cells.append(code("""# 평가셋 저장
eval_path = EVAL_DATA_DIR / 'rag_eval_dataset.json'
with eval_path.open('w', encoding='utf-8') as f:
    json.dump(eval_dataset, f, ensure_ascii=False, indent=2)
print(f'Saved: {eval_path}')
print(f'\\n카테고리 분포:')
for c, n in Counter(e['category'] for e in eval_dataset).items():
    print(f'  {c}: {n}')"""))

# ════════════════════════════════════════════════════════════════════════
# 3. 검색 함수 구현
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 3. 검색 함수 구현

5가지 검색 방식을 구현합니다:
1. **vector_search** — 기존 ChromaDB 벡터 검색 (Baseline)
2. **bm25_search** — BM25 키워드 검색
3. **hybrid_search** — RRF로 vector + BM25 결합
4. **rerank** — Cross-Encoder로 재정렬
5. **llm_rewrite** — Groq로 쿼리 재작성"""))

cells.append(code("""# 임베딩 모델 (기존과 동일)
embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
print('Embedding model loaded.')


def vector_search(query, top_k=10):
    \"\"\"기존 ChromaDB 벡터 검색.\"\"\"
    q_emb = embed_model.encode([query]).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=top_k)
    return [
        {'doc_id': did, 'text': txt, 'score': 1 - dist}  # cosine sim
        for did, txt, dist in zip(res['ids'][0], res['documents'][0], res['distances'][0])
    ]


# Smoke test
result = vector_search('무릎이 아파요', top_k=5)
for r in result[:3]:
    print(f\"  [{r['doc_id']}] score={r['score']:.3f} | {r['text'][:80]}\")"""))

cells.append(code("""# BM25 인덱스 구축
def korean_tokenize(text):
    \"\"\"간단한 한국어 토크나이저 (어절 + 명사 추출).\"\"\"
    # konlpy.Mecab이 가장 좋지만 의존성이 무거우니, 단순 어절 분리 + 명사 추출 시도
    tokens = re.findall(r'[가-힣]+|[a-zA-Z0-9]+', text)
    # 1글자 stopword 제거
    return [t for t in tokens if len(t) >= 2]


# 코퍼스 토큰화
corpus_tokens = [korean_tokenize(t) for t in corpus_df['text'].tolist()]
bm25 = BM25Okapi(corpus_tokens)
corpus_doc_ids = corpus_df['doc_id'].tolist()
print(f'BM25 인덱스: {len(corpus_tokens)} 문서')


def bm25_search(query, top_k=10):
    q_tokens = korean_tokenize(query)
    scores = bm25.get_scores(q_tokens)
    top_idx = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_idx:
        if scores[idx] <= 0:
            continue
        results.append({
            'doc_id': corpus_doc_ids[idx],
            'text': corpus_df.iloc[idx]['text'],
            'score': float(scores[idx]),
        })
    return results


result = bm25_search('타이레놀 부작용', top_k=5)
for r in result[:3]:
    print(f\"  [{r['doc_id']}] score={r['score']:.3f} | {r['text'][:80]}\")"""))

cells.append(code("""# Reciprocal Rank Fusion (RRF)
def rrf_fuse(result_lists, k=60, top_k=10):
    \"\"\"여러 검색 결과를 RRF로 결합. result_lists: List[List[{doc_id, ...}]]\"\"\"
    rrf_scores = defaultdict(float)
    doc_info = {}
    for results in result_lists:
        for rank, r in enumerate(results, 1):
            rrf_scores[r['doc_id']] += 1.0 / (k + rank)
            doc_info[r['doc_id']] = r
    sorted_ids = sorted(rrf_scores.keys(), key=lambda d: -rrf_scores[d])[:top_k]
    return [{**doc_info[d], 'score': rrf_scores[d]} for d in sorted_ids]


def hybrid_search(query, top_k=10, alpha=0.5):
    \"\"\"BM25 + Vector RRF 하이브리드.\"\"\"
    v_results = vector_search(query, top_k=20)
    b_results = bm25_search(query, top_k=20)
    return rrf_fuse([v_results, b_results], top_k=top_k)


result = hybrid_search('가슴이 쥐어짜듯 아파요', top_k=5)
for r in result[:3]:
    print(f\"  [{r['doc_id']}] score={r['score']:.4f} | {r['text'][:80]}\")"""))

cells.append(code("""# Cross-Encoder Reranker
reranker = CrossEncoder('Dongjin-kr/ko-reranker', max_length=512)
print('Reranker loaded.')


def rerank(query, candidates, top_k=5):
    \"\"\"검색 결과 candidates를 Cross-Encoder로 재정렬.\"\"\"
    pairs = [[query, c['text']] for c in candidates]
    scores = reranker.predict(pairs)
    for c, s in zip(candidates, scores):
        c['rerank_score'] = float(s)
    return sorted(candidates, key=lambda x: -x['rerank_score'])[:top_k]


# Smoke test: hybrid → rerank
candidates = hybrid_search('무릎이 시리고 아파요', top_k=10)
reranked = rerank('무릎이 시리고 아파요', candidates, top_k=3)
for r in reranked:
    print(f\"  [{r['doc_id']}] rerank={r['rerank_score']:.3f} | {r['text'][:80]}\")"""))

cells.append(code("""# LLM Query Rewriting (Groq)
def llm_rewrite_query(query, n=3):
    \"\"\"시니어 발화 → 의료 검색에 적합한 쿼리 n개로 재작성.\"\"\"
    if not USE_GROQ:
        return [query]

    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f\"\"\"한국어 의료 검색을 위해 다음 사용자 발화를 {n}개의 검색 쿼리로 재작성하세요.
- 동의어, 의학 용어, 연관 진료과를 포함
- 각 쿼리는 짧고 명확하게 (10단어 이내)
- JSON 배열로만 출력

사용자 발화: "{query}"\"\"\"

    resp = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3, max_tokens=200,
    )
    text = resp.choices[0].message.content.strip()
    m = re.search(r'\\[.*\\]', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())[:n]
        except json.JSONDecodeError:
            return [query]
    return [query]


def multi_query_search(query, search_fn, top_k=10):
    \"\"\"LLM 재작성 → 다중 쿼리 검색 → RRF 결합.\"\"\"
    queries = llm_rewrite_query(query, n=3)
    queries = [query] + queries  # 원본 + 재작성
    print(f'  재작성된 쿼리: {queries}')
    all_results = [search_fn(q, top_k=20) for q in queries]
    return rrf_fuse(all_results, top_k=top_k)


# Smoke test
if USE_GROQ:
    result = multi_query_search('속이 좀 안 좋고 더부룩해', hybrid_search, top_k=5)
    for r in result[:3]:
        print(f\"  [{r['doc_id']}] score={r['score']:.4f} | {r['text'][:80]}\")"""))

# ════════════════════════════════════════════════════════════════════════
# 4. 평가 지표
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 4. 평가 지표 구현

| 지표 | 정의 |
|------|------|
| **Recall@k** | 정답 doc 중 top-k 안에 들어온 비율 |
| **Precision@k** | top-k 결과 중 정답 비율 |
| **MRR** | Mean Reciprocal Rank — 첫 정답의 역순위 평균 |
| **nDCG@k** | 정규화된 누적 이익 (순위 가중) |"""))

cells.append(code("""def recall_at_k(retrieved_ids, relevant_ids, k):
    \"\"\"top-k 안에 정답 중 몇 개 포함됐는지 비율.\"\"\"
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    return len(set(top_k) & set(relevant_ids)) / len(relevant_ids)


def precision_at_k(retrieved_ids, relevant_ids, k):
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    return len(set(top_k) & set(relevant_ids)) / k


def mrr(retrieved_ids, relevant_ids):
    \"\"\"첫 정답의 역순위.\"\"\"
    for i, did in enumerate(retrieved_ids, 1):
        if did in relevant_ids:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved_ids, relevant_ids, k):
    \"\"\"이진 relevance 기준 nDCG@k.\"\"\"
    dcg = 0.0
    for i, did in enumerate(retrieved_ids[:k], 1):
        if did in relevant_ids:
            dcg += 1.0 / np.log2(i + 1)
    # ideal DCG
    n_rel = min(len(relevant_ids), k)
    idcg = sum(1.0 / np.log2(i + 1) for i in range(1, n_rel + 1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retriever(search_fn, eval_dataset, top_k=10, name='retriever'):
    rows = []
    for item in eval_dataset:
        results = search_fn(item['query'], top_k=top_k)
        retrieved = [r['doc_id'] for r in results]
        rel = item['relevant_doc_ids']
        rows.append({
            'query_id': item['query_id'],
            'query': item['query'],
            'category': item['category'],
            'recall@1': recall_at_k(retrieved, rel, 1),
            'recall@3': recall_at_k(retrieved, rel, 3),
            'recall@5': recall_at_k(retrieved, rel, 5),
            'precision@3': precision_at_k(retrieved, rel, 3),
            'mrr': mrr(retrieved, rel),
            'ndcg@5': ndcg_at_k(retrieved, rel, 5),
        })
    df = pd.DataFrame(rows)
    summary = {
        'method': name,
        'recall@1': df['recall@1'].mean(),
        'recall@3': df['recall@3'].mean(),
        'recall@5': df['recall@5'].mean(),
        'precision@3': df['precision@3'].mean(),
        'mrr': df['mrr'].mean(),
        'ndcg@5': df['ndcg@5'].mean(),
        'n_queries': len(df),
    }
    return summary, df


print('평가 함수 정의 완료')"""))

# ════════════════════════════════════════════════════════════════════════
# 5~8. 단계별 평가
# ════════════════════════════════════════════════════════════════════════
cells.append(md("## 5. Baseline 평가 — Vector only"))

cells.append(code("""baseline_summary, baseline_df = evaluate_retriever(
    vector_search, eval_dataset, top_k=10, name='Vector only'
)
print('[Baseline]')
for k, v in baseline_summary.items():
    if isinstance(v, float):
        print(f'  {k}: {v:.4f}')
    else:
        print(f'  {k}: {v}')"""))

cells.append(md("## 6. + Cross-Encoder Reranker"))

cells.append(code("""def vector_then_rerank(query, top_k=10):
    candidates = vector_search(query, top_k=20)
    return rerank(query, candidates, top_k=top_k)


reranker_summary, reranker_df = evaluate_retriever(
    vector_then_rerank, eval_dataset, top_k=10, name='Vector + Reranker'
)
print('[Vector + Reranker]')
for k, v in reranker_summary.items():
    if isinstance(v, float):
        print(f'  {k}: {v:.4f}')"""))

cells.append(md("## 7. + BM25 Hybrid Search"))

cells.append(code("""def hybrid_then_rerank(query, top_k=10):
    candidates = hybrid_search(query, top_k=20)
    return rerank(query, candidates, top_k=top_k)


hybrid_summary, hybrid_df = evaluate_retriever(
    hybrid_search, eval_dataset, top_k=10, name='Hybrid (BM25+Vec)'
)
hybrid_rr_summary, hybrid_rr_df = evaluate_retriever(
    hybrid_then_rerank, eval_dataset, top_k=10, name='Hybrid + Reranker'
)
print('[Hybrid]')
for k, v in hybrid_summary.items():
    if isinstance(v, float):
        print(f'  {k}: {v:.4f}')

print('\\n[Hybrid + Reranker]')
for k, v in hybrid_rr_summary.items():
    if isinstance(v, float):
        print(f'  {k}: {v:.4f}')"""))

cells.append(md("## 8. + LLM Query Rewriting"))

cells.append(code("""if USE_GROQ:
    def llm_hybrid_rerank(query, top_k=10):
        candidates = multi_query_search(query, hybrid_search, top_k=20)
        return rerank(query, candidates, top_k=top_k)

    full_summary, full_df = evaluate_retriever(
        llm_hybrid_rerank, eval_dataset, top_k=10, name='Full Pipeline'
    )
    print('[Full Pipeline (LLM Rewrite + Hybrid + Reranker)]')
    for k, v in full_summary.items():
        if isinstance(v, float):
            print(f'  {k}: {v:.4f}')
else:
    full_summary = None
    print('Groq 없음 — 스킵')"""))

# ════════════════════════════════════════════════════════════════════════
# 9. 청킹 전략 분석
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 9. 청킹 전략 분석

현재 청크의 길이/내용 분포를 보고, 너무 길거나 짧은 청크가 있는지 점검."""))

cells.append(code("""# 길이 이상치
print('[너무 짧은 청크 (<50자)]')
short = corpus_df[corpus_df['text'].str.len() < 50]
print(f'  개수: {len(short)}')
for _, r in short.head(5).iterrows():
    print(f'    [{r[\"doc_id\"]}] {r[\"text\"]}')

print('\\n[너무 긴 청크 (>2000자)]')
long = corpus_df[corpus_df['text'].str.len() > 2000]
print(f'  개수: {len(long)}')

# 카테고리별 평균 길이
if 'category' in corpus_df.columns:
    print('\\n[카테고리별 평균 청크 길이]')
    print(corpus_df.groupby('category')['text'].apply(lambda x: x.str.len().mean()).round(0))"""))

# ════════════════════════════════════════════════════════════════════════
# 10. Citation Tracking
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 10. Citation Tracking 검증

검색 결과에 출처 정보가 정확히 따라오는지 확인."""))

cells.append(code("""def search_with_citations(query, top_k=3):
    \"\"\"메타데이터 + 점수 포함 검색.\"\"\"
    results = hybrid_then_rerank(query, top_k=top_k)
    out = []
    for r in results:
        meta = corpus_df[corpus_df['doc_id'] == r['doc_id']].iloc[0]['meta']
        out.append({
            'doc_id': r['doc_id'],
            'text': r['text'],
            'score': r.get('rerank_score', r.get('score', 0)),
            'title': meta.get('title', ''),
            'category': meta.get('category', ''),
            'source': meta.get('source', '질병관리청 국가건강정보포털'),
        })
    return out


sample = search_with_citations('타이레놀 먹어도 되나요', top_k=3)
for s in sample:
    print(f\"  [{s['doc_id']}] ({s['category']}) score={s['score']:.3f}\")
    print(f\"    title: {s['title']}\")
    print(f\"    source: {s['source']}\")
    print(f\"    text: {s['text'][:100]}\")
    print()"""))

# ════════════════════════════════════════════════════════════════════════
# 11. Negation Handling
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 11. Negation / Confidence Handling

부정 표현이나 "잘 모르는" 쿼리에서 RAG가 잘못된 정보를 가져오는지 검증."""))

cells.append(code("""NEGATION_TESTS = [
    '두통 없는데 약 추천해줘',          # 두통 청크 가져오면 안 됨
    '오늘 날씨가 좋아요',                 # 무관한 쿼리
    '이 앱 어떻게 써요',                  # 의료 무관
    '특별한 증상은 없어요',               # 부정
    '딱히 아픈 건 아닌데',                # 모호
]

print('[Negation / OOD 테스트]')
for q in NEGATION_TESTS:
    results = hybrid_then_rerank(q, top_k=3)
    if results:
        top = results[0]
        score = top.get('rerank_score', top.get('score', 0))
        print(f'  Q: \"{q}\"')
        print(f'    → top doc score={score:.3f} | {top[\"text\"][:80]}')
        # confidence threshold 권장: rerank_score < 0 이면 RAG 결과 미사용
        if score < 0:
            print(f'    ⚠ 낮은 confidence — RAG 미사용 권장')
    else:
        print(f'  Q: \"{q}\" → 결과 없음')
    print()"""))

# ════════════════════════════════════════════════════════════════════════
# 12. Hard-Negative 분석
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 12. Hard-Negative 분석

평가셋에서 모델이 가장 자주 틀리는 쿼리 유형 분석."""))

cells.append(code("""# Hybrid+Reranker 기준 오답 분석
fail = hybrid_rr_df[hybrid_rr_df['recall@3'] == 0]
print(f'[Recall@3 = 0 인 쿼리: {len(fail)}건]')
for _, row in fail.head(10).iterrows():
    print(f'  [{row[\"query_id\"]}] ({row[\"category\"]}) {row[\"query\"]}')

# 카테고리별 평균 recall
print('\\n[카테고리별 Recall@3]')
cat_recall = hybrid_rr_df.groupby('category')['recall@3'].mean().round(4)
display(cat_recall)"""))

# ════════════════════════════════════════════════════════════════════════
# 13. Lightweight Medical KG
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 13. Lightweight Medical KG

GraphRAG 대신 가벼운 entity-relation 매핑으로 다중홉 쿼리 일부 커버."""))

cells.append(code("""MEDICAL_KG = {
    'symptom_to_dept': {
        '무릎': '정형외과', '허리': '정형외과', '목': '정형외과',
        '눈': '안과', '귀': '이비인후과', '피부': '피부과',
        '머리': '신경과', '어지': '신경과',
        '배': '소화기내과', '속': '소화기내과',
        '가슴': '심장내과', '두근': '심장내과',
        '기침': '호흡기내과', '숨': '호흡기내과',
        '소변': '비뇨기과',
    },
    'symptom_to_diseases': {
        '가슴 통증': ['협심증', '심근경색', '역류성식도염'],
        '한쪽 마비': ['뇌졸중', '뇌출혈'],
        '말 어눌': ['뇌졸중', '안면마비'],
        '의식 흐려': ['뇌졸중', '저혈당', '뇌출혈'],
    },
    'med_warnings': {
        '타이레놀': ['간 손상 위험 — 음주 금지', '하루 4g 이하'],
        '아스피린': ['위장 출혈 위험', '위궤양·천식 환자 주의'],
        '이부프로펜': ['신장·위장 부작용', '식후 복용'],
        '항생제': ['처방 기간 끝까지 복용', '내성 위험'],
    },
    'med_contraindications': {
        '아스피린': ['위궤양', '출혈성 질환'],
        '이부프로펜': ['신부전', '심부전'],
    },
}


def kg_lookup(query):
    \"\"\"쿼리에서 KG 엔티티 찾아 부가 정보 반환.\"\"\"
    info = []
    for kw, dept in MEDICAL_KG['symptom_to_dept'].items():
        if kw in query:
            info.append(f'관련 진료과: {dept}')
            break
    for kw, diseases in MEDICAL_KG['symptom_to_diseases'].items():
        if all(t in query for t in kw.split()):
            info.append(f'의심 질환: {\", \".join(diseases)}')
    for med, warns in MEDICAL_KG['med_warnings'].items():
        if med in query:
            info.append(f'{med} 주의사항: {\"; \".join(warns)}')
    return info


# 예시
for q in ['타이레놀 먹어도 돼요', '갑자기 한쪽 마비됐어요', '무릎이 아파요']:
    print(f'Q: {q}')
    for line in kg_lookup(q):
        print(f'  → {line}')
    print()"""))

# ════════════════════════════════════════════════════════════════════════
# 14. 최종 비교표
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 14. 최종 비교표 + 시각화"""))

cells.append(code("""summaries = [baseline_summary, reranker_summary, hybrid_summary, hybrid_rr_summary]
if full_summary:
    summaries.append(full_summary)

final_df = pd.DataFrame(summaries)
metric_cols = ['recall@1', 'recall@3', 'recall@5', 'precision@3', 'mrr', 'ndcg@5']
for c in metric_cols:
    final_df[c] = final_df[c].round(4)

print('[RAG Ablation 최종 비교표]')
display(final_df)

# CSV 저장
final_df.to_csv(EVAL_DATA_DIR / 'rag_ablation_summary.csv', index=False, encoding='utf-8-sig')
print('Saved: rag_ablation_summary.csv')"""))

cells.append(code("""# 시각화 (한글 폰트)
import matplotlib.font_manager as fm
os.system('apt-get -qq -y install fonts-nanum > /dev/null 2>&1')
for fp in fm.findSystemFonts(fontpaths=['/usr/share/fonts/truetype/nanum']):
    fm.fontManager.addfont(fp)
plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# 막대그래프 (지표별 method 비교)
fig, axes = plt.subplots(2, 3, figsize=(16, 8))
for ax, m in zip(axes.flatten(), metric_cols):
    sns.barplot(data=final_df, x='method', y=m, ax=ax, palette='Blues_d')
    ax.set_title(m, fontweight='bold')
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=20)
    for i, v in enumerate(final_df[m]):
        ax.text(i, v, f'{v:.3f}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig(EVAL_DATA_DIR / 'rag_ablation.png', dpi=150, bbox_inches='tight')
plt.show()
print('Saved: rag_ablation.png')"""))

# ════════════════════════════════════════════════════════════════════════
# 15. Backend 적용 코드
# ════════════════════════════════════════════════════════════════════════
cells.append(md("""## 15. Backend 적용 코드 (참고)

위 평가에서 가장 좋은 조합을 backend에 적용. `backend/main.py`의 `full_rag_pipeline()` 교체."""))

cells.append(code("""# backend/main.py 적용 예시 (직접 실행 X — 코드 참고용)
BACKEND_RAG_PIPELINE = '''
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import re, numpy as np
from collections import defaultdict

# 초기화 (앱 시작 시 1회)
all_data = collection.get(include=["documents", "metadatas"])
corpus_doc_ids = all_data["ids"]
corpus_texts = all_data["documents"]
corpus_meta = all_data["metadatas"] or [{} for _ in corpus_doc_ids]

def korean_tokenize(t):
    return [tok for tok in re.findall(r"[가-힣]+|[a-zA-Z0-9]+", t) if len(tok) >= 2]

bm25 = BM25Okapi([korean_tokenize(t) for t in corpus_texts])
reranker = CrossEncoder("Dongjin-kr/ko-reranker", max_length=512)


def vector_search(query, top_k=20):
    q_emb = embed_model.encode([query]).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=top_k)
    return [
        {"doc_id": d, "text": t, "score": 1 - dist}
        for d, t, dist in zip(res["ids"][0], res["documents"][0], res["distances"][0])
    ]


def bm25_search(query, top_k=20):
    scores = bm25.get_scores(korean_tokenize(query))
    top = np.argsort(scores)[::-1][:top_k]
    return [
        {"doc_id": corpus_doc_ids[i], "text": corpus_texts[i], "score": float(scores[i])}
        for i in top if scores[i] > 0
    ]


def rrf_fuse(lists, k=60, top_k=20):
    sc = defaultdict(float); info = {}
    for results in lists:
        for rank, r in enumerate(results, 1):
            sc[r["doc_id"]] += 1.0 / (k + rank)
            info[r["doc_id"]] = r
    return [info[d] for d in sorted(sc, key=lambda x: -sc[x])[:top_k]]


def full_rag_pipeline_v2(query: str) -> dict:
    if collection.count() == 0:
        return {"context": "", "sources": []}

    # 1. Hybrid retrieval (top-20)
    candidates = rrf_fuse([vector_search(query, 20), bm25_search(query, 20)], top_k=20)
    if not candidates:
        return {"context": "관련된 전문적인 의학 정보를 찾지 못했습니다.", "sources": []}

    # 2. Cross-Encoder Rerank (top-3)
    pairs = [[query, c["text"]] for c in candidates]
    rerank_scores = reranker.predict(pairs)
    for c, s in zip(candidates, rerank_scores):
        c["rerank_score"] = float(s)
    top = sorted(candidates, key=lambda x: -x["rerank_score"])[:3]

    # 3. Confidence threshold (rerank_score < 0 → 미사용)
    confident = [c for c in top if c["rerank_score"] >= 0]
    if not confident:
        return {"context": "관련된 전문적인 의학 정보를 찾지 못했습니다.", "sources": []}

    # 4. Citation 포함
    context = " ".join(c["text"] for c in confident)
    sources = [
        {
            "doc_id": c["doc_id"],
            "score": c["rerank_score"],
            "source": "질병관리청 국가건강정보포털",
        }
        for c in confident
    ]
    return {"context": context, "sources": sources}
'''
print('백엔드 적용 코드는 위 코드 참고. backend/main.py 수정 시 사용.')"""))

cells.append(md("""## 끝.

위 평가가 완료되면:
1. `RAG/eval/rag_eval_dataset.json` — 평가 데이터셋
2. `RAG/eval/rag_ablation_summary.csv` — 단계별 성능 비교
3. `RAG/eval/rag_ablation.png` — 시각화

이 결과를 들고 backend/main.py를 업데이트합니다."""))

# ════════════════════════════════════════════════════════════════════════
# 노트북 저장
# ════════════════════════════════════════════════════════════════════════
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print(f"Generated: {OUTPUT_PATH}")
print(f"Total cells: {len(cells)}")
md_count = sum(1 for c in cells if c["cell_type"] == "markdown")
code_count = sum(1 for c in cells if c["cell_type"] == "code")
print(f"  Markdown: {md_count}")
print(f"  Code:     {code_count}")
