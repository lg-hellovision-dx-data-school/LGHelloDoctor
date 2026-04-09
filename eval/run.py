"""평가 메인 실행기 — RAG V1~V6 / Router V1~V4"""
import json, random
from eval.setup import collection, embed_model
from eval.rag_stages import (
    rag_v1_keyword_only, rag_v2_vector, rag_v3_rewrite,
    rag_v4_hybrid, rag_v5_rerank, rag_v6_graphrag,
)
from eval.router_stages import (
    router_v1, router_v2, router_v3, router_v4,
    ROUTE_SAMPLES, eval_route,
)

print(f'DB 문서 수: {collection.count()}개')

# ══════════════════════════════════════════════════════════════════════════════
# 1. RAG 검색 품질 (소규모 샘플 5개)
# ══════════════════════════════════════════════════════════════════════════════
RAG_SAMPLES = [
    {'query': '무릎이 너무 아파요',           'expected_kws': ['무릎', '정형외과']},
    {'query': '혈압약 같이 먹어도 되나요',    'expected_kws': ['혈압', '복용']},
    {'query': '가슴이 아프고 숨이 안 쉬어요', 'expected_kws': ['심근경색', '심장']},
    {'query': '허리가 너무 뻐근해요',         'expected_kws': ['허리', '정형외과']},
    {'query': '항생제 언제까지 먹어야 하나요', 'expected_kws': ['항생제', '복용']},
]

def eval_rag_hit(docs, expected_kws):
    combined = ' '.join(docs)
    return sum(1 for kw in expected_kws if kw in combined) >= len(expected_kws)

rag_versions = [
    ('RAG-V1  단순 키워드 검색',           rag_v1_keyword_only),
    ('RAG-V2  ChromaDB 벡터 검색',         rag_v2_vector),
    ('RAG-V3  Query Rewriting + 벡터',     rag_v3_rewrite),
    ('RAG-V4  Hybrid (벡터 + 키워드)',     rag_v4_hybrid),
    ('RAG-V5  Hybrid + Reranking (최종)',   rag_v5_rerank),
]

print('\n' + '='*60)
print('  RAG 검색 품질 (Top-3 기대 키워드 적중률)')
print('='*60)
print(f'{"버전":<38} {"적중":<8} {"정확도":>8}')
print('-'*60)

rag_results = []
for label, fn in rag_versions:
    hits = sum(1 for s in RAG_SAMPLES if eval_rag_hit(fn(s['query']), s['expected_kws']))
    acc  = hits / len(RAG_SAMPLES) * 100
    rag_results.append((label, hits, acc))
    print(f'{label:<38} {hits}/{len(RAG_SAMPLES)}      {acc:>6.1f}%')

print('='*60)
print('[향상 요약]')
for i in range(1, len(rag_results)):
    d = rag_results[i][2] - rag_results[i-1][2]
    if d != 0:
        print(f'  {rag_results[i-1][0].split()[0]} → {rag_results[i][0].split()[0]}:  {d:+.1f}%p')

# ══════════════════════════════════════════════════════════════════════════════
# 2. 라우팅 정확도
# ══════════════════════════════════════════════════════════════════════════════
route_versions = [
    ('Router-V1  intent만 사용',                   router_v1),
    ('Router-V2  emergency 키워드 보강',            router_v2),
    ('Router-V3  B팀 severity 우선',               router_v3),
    ('Router-V4  멀티턴+entities+true_dept (최종)', router_v4),
]

print('\n' + '='*65)
print('  라우팅 정확도')
print('='*65)
print(f'{"버전":<44} {"Intent 정확도":>14} {"진료과 정확도":>12}')
print('-'*65)

route_results = []
for label, fn in route_versions:
    ik, n, dk, dt = eval_route(fn)
    ia = ik/n*100; da = dk/dt*100 if dt else 0
    route_results.append((label, ia, da))
    print(f'{label:<44} {ik}/{n} = {ia:>5.1f}%    {dk}/{dt} = {da:>5.1f}%')

print('='*65)
print('[향상 요약]')
for i in range(1, len(route_results)):
    di = route_results[i][1] - route_results[i-1][1]
    dd = route_results[i][2] - route_results[i-1][2]
    if di != 0 or dd != 0:
        print(f'  {route_results[i-1][0].split()[0]} → {route_results[i][0].split()[0]}:  Intent {di:+.1f}%p  |  진료과 {dd:+.1f}%p')

# ══════════════════════════════════════════════════════════════════════════════
# 3. b_output_1000.json 기반 RAG 고도화 단계별 정확도
# ══════════════════════════════════════════════════════════════════════════════
with open('data/b_output_700.json', encoding='utf-8') as f:
    B_DATA = json.load(f)

def _build_expected_kws(sample):
    kws = []
    e = sample.get('entities') or {}
    if sample.get('true_dept'):
        kws.append(sample['true_dept'])
    if e.get('symptom'):
        kws.append(e['symptom'].split()[0])
    if e.get('body_part'):
        kws.append(e['body_part'].split()[0])
    return kws

def eval_rag_on_b_data(fn, samples, require_hit=1):
    hits = total = 0
    for s in samples:
        kws = _build_expected_kws(s)
        if not kws:
            continue
        total += 1
        combined = ' '.join(fn(s['query']))
        if sum(1 for kw in kws if kw in combined) >= require_hit:
            hits += 1
    return hits, total

random.seed(42)
B_SAMPLE_100 = random.sample(B_DATA, 100)
B_SAMPLE_200 = random.sample(B_DATA, 200)

rag_b_meta = [
    ('V1', '단순 키워드 검색',             '기준선',              rag_v1_keyword_only, B_SAMPLE_100),
    ('V2', 'ChromaDB 벡터 검색',           '의미 기반 검색 도입', rag_v2_vector,       B_SAMPLE_200),
    ('V3', 'Query Rewriting + 벡터',       '쿼리 의도 확장',      rag_v3_rewrite,      B_SAMPLE_200),
    ('V4', 'Hybrid (벡터 + 키워드)',       '두 방식 병합',        rag_v4_hybrid,       B_SAMPLE_200),
    ('V5', 'Hybrid + Reranking',           '코사인 유사도 재정렬', rag_v5_rerank,       B_SAMPLE_200),
    ('V6', 'GraphRAG (Neo4j 지식 그래프)', '질환-진료과 관계 탐색', rag_v6_graphrag,   B_SAMPLE_200),
]

print('\n' + '='*72)
print('  RAG 고도화 단계별 정확도 — b_output_700.json 기반')
print('='*72)
print('  ※ V1은 전체 문서 스캔 특성상 100개 샘플로 측정, V2~V6는 200개 샘플 기준')
print('-'*72)
print(f'  {"단계":<6} {"기술":<28} {"핵심 변화":<22} {"적중률":>10}')
print('-'*72)

rag_b_results = []
for stage, tech, change, fn, samples in rag_b_meta:
    hits, total = eval_rag_on_b_data(fn, samples)
    acc = hits / total * 100 if total else 0
    rag_b_results.append((stage, acc))
    print(f'  {stage:<6} {tech:<30} {change:<22} {hits}/{total} = {acc:>5.1f}%')

print('='*72)
print('[향상 요약]')
for i in range(1, len(rag_b_results)):
    d = rag_b_results[i][1] - rag_b_results[i-1][1]
    if d != 0:
        print(f'  {rag_b_results[i-1][0]} → {rag_b_results[i][0]}:  {d:+.1f}%p')

        # ══════════════════════════════════════════════════════════════════════════════
# 4. 운영 관점 간이 sanity check
# ══════════════════════════════════════════════════════════════════════════════
SANITY_SAMPLES = [
    "가슴이 답답해요",
    "무릎이 왜 이러지",
    "귀에서 삐 소리가 나요",
    "속이 쓰리고 신물이 올라와요",
    "잇몸에서 피가 나요",
]

print('\n' + '='*72)
print('  운영 관점 Sanity Check (딴소리 여부 확인용)')
print('='*72)

for q in SANITY_SAMPLES:
    print(f'\n[QUERY] {q}')
    for label, fn in rag_versions:
        try:
            docs = fn(q)
            preview = docs[0][:120] if docs else '(no result)'
            print(f'  - {label}: {preview}')
        except Exception as e:
            print(f'  - {label}: ERROR -> {e}')