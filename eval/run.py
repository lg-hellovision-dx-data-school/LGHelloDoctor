"""평가 메인 실행기 — RAG V1~V11 / Router V1~V4"""
import json, random, re
from eval.setup import collection
from eval.hospital_stages import SYMPTOM_TO_DEPT, BODY_TO_DEPT
from eval.rag_stages import (
    rag_v1_keyword_only, rag_v2_vector, rag_v3_rewrite,
    rag_v4_hybrid, rag_v5_rerank, rag_v6_graphrag, rag_v7_chunked,
    rag_v8_top5, rag_v9_bm25, rag_v10_synonym, rag_v11_decompose,
    rag_v12_graph_hybrid_rerank,
)
from eval.router_stages import (
    router_v1, router_v2, router_v3, router_v4,
    eval_route,
)
from eval.hospital_stages import eval_hospital_mapping
from eval.otc_stages import eval_otc_recognition, eval_otc_interaction

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
    ('RAG-V5  Hybrid + Reranking',         rag_v5_rerank),
    ('RAG-V7  청킹 + Hybrid + Reranking',  rag_v7_chunked),
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

def _is_valid_kw(kw):
    """유효한 한국어 키워드인지 확인 (영어, 특수문자, 너무 짧은 키워드 제외)"""
    if not kw or len(kw) < 2:
        return False
    if re.search(r'[a-zA-Z]', kw):   # 영어 포함 키워드 제외
        return False
    if re.search(r'[,.\[\]()]', kw):  # 구두점 포함 제외
        return False
    return True

def _extract_user_turns(query):
    """멀티턴 형식 '[N턴] ...\n[AI] ...' 에서 모든 사용자 발화를 합쳐서 반환
    RAG 검색에 전체 맥락이 필요하므로 모든 턴을 합침
    """
    if '[1턴]' not in query:
        return query
    turns = re.findall(r'\[\d+턴\]\s*(.+?)(?=\n\[|\Z)', query, re.DOTALL)
    if turns:
        return ' '.join(t.strip() for t in turns)
    return query

def _clean_entity(value):
    """entities 필드에서 멀티턴 마커([1턴], [AI]) 제거 후 순수 텍스트 반환"""
    if not value:
        return value
    if '[1턴]' in value:
        # '[1턴] 팔이 저려요\n[AI] 갑자기' → '팔이 저려요'
        m = re.match(r'\[1턴\]\s*(.+?)(?:\n|$)', value)
        if m:
            return m.group(1).strip()
    return value

_JOSA = re.compile(r'(이|가|을|를|은|는|으로|로|에서|에게|이에요|예요)$')

def _strip_josa(word):
    """체언 뒤 조사만 제거: 팔이→팔, 배가→배 / 어지러워요는 그대로 유지"""
    return _JOSA.sub('', word)

def _infer_dept(symptom, body_part):
    """SYMPTOM_TO_DEPT / BODY_TO_DEPT로 진료과 추론
    BODY_TO_DEPT는 단어 단위 정확 매칭만 사용 (짧은 키 오탐 방지)
    """
    for text in [symptom or '', body_part or '']:
        if not text:
            continue
        # 증상 사전: 부분 포함 매칭 허용
        if text in SYMPTOM_TO_DEPT:
            return SYMPTOM_TO_DEPT[text]
        for key, dept in SYMPTOM_TO_DEPT.items():
            if key in text or text in key:
                return dept
        # 신체부위 사전: 단어 단위 정확 매칭만 (짧은 키 오탐 방지)
        words = re.split(r'\s+', text)
        for w in words:
            w_clean = _JOSA.sub('', w)
            if w_clean in BODY_TO_DEPT:
                return BODY_TO_DEPT[w_clean]
    return None

def _build_expected_kws(sample):
    kws = []
    e = sample.get('entities') or {}
    symptom   = _clean_entity(e.get('symptom'))
    body_part = _clean_entity(e.get('body_part'))

    # true_dept 없는 멀티턴은 SYMPTOM_TO_DEPT/BODY_TO_DEPT로 진료과 추론
    dept = sample.get('true_dept') or _infer_dept(symptom, body_part)
    if dept:
        kws.append(dept)

    if symptom:
        kws.append(_strip_josa(symptom.split()[0]))
    if body_part:
        kws.append(_strip_josa(body_part.split()[0]))

    # 중복 제거 + 노이즈 키워드 필터링
    return list(dict.fromkeys(kw for kw in kws if _is_valid_kw(kw)))

def eval_rag_on_b_data(fn, samples, require_hit=1):
    hits = total = 0
    for s in samples:
        kws = _build_expected_kws(s)
        if not kws:
            continue
        # 멀티턴 형식이면 모든 사용자 발화를 합쳐서 사용
        query = _extract_user_turns(s.get('query', ''))
        if len(query) < 5 or query.count(' ') == 0:
            continue
        total += 1
        combined = ' '.join(fn(query))
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
    ('V7', '청킹 + Hybrid + Reranking',   '문서 단락 분할 검색', rag_v7_chunked,      B_SAMPLE_200),
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
# 3-2. 성능 향상 실험 — V8~V11 (V4 Hybrid 기준 개선)
# ══════════════════════════════════════════════════════════════════════════════
v4_base_hits, v4_base_total = eval_rag_on_b_data(rag_v4_hybrid, B_SAMPLE_200)
v4_base_acc = v4_base_hits / v4_base_total * 100 if v4_base_total else 0

improve_meta = [
    ('V4',  'Hybrid (기준선)',              '—',                         rag_v4_hybrid,      B_SAMPLE_200),
    ('V8',  'Top-K 5 확장',                'Top-3 → Top-5',             rag_v8_top5,        B_SAMPLE_200),
    ('V9',  'BM25 + Vector',               '단순 카운팅 → TF-IDF 가중치', rag_v9_bm25,        B_SAMPLE_200),
    ('V10', '동의어 확장 + BM25',           '의학 동의어 쿼리 확장',        rag_v10_synonym,    B_SAMPLE_200),
    ('V11', '쿼리 분해 + 동의어 + BM25',   '복합 질문 분리 검색',          rag_v11_decompose,        B_SAMPLE_200),
    ('V12', 'GraphRAG + Hybrid + Rerank', 'V5 + V6 결합 최종버전',       rag_v12_graph_hybrid_rerank, B_SAMPLE_200),
]

print('\n' + '='*78)
print('  RAG 성능 향상 실험 — V4 기준 개선 비교 (b_output_700.json, 200샘플)')
print('='*78)
print(f'  {"단계":<5} {"기술":<28} {"핵심 변화":<24} {"적중률":>10} {"V4 대비":>8}')
print('-'*78)

for stage, tech, change, fn, samples in improve_meta:
    hits, total = eval_rag_on_b_data(fn, samples)
    acc = hits / total * 100 if total else 0
    diff = acc - v4_base_acc
    diff_str = f'{diff:+.1f}%p' if stage != 'V4' else '기준'
    print(f'  {stage:<5} {tech:<30} {change:<24} {hits}/{total} = {acc:>5.1f}%  {diff_str:>8}')

print('='*78)

# ══════════════════════════════════════════════════════════════════════════════
# 4. 병원 검색 — 증상→진료과 매핑 정확도
# ══════════════════════════════════════════════════════════════════════════════
hits, total, h_results = eval_hospital_mapping()
acc = hits / total * 100

print('\n' + '='*65)
print('  병원 검색 — 증상→진료과 매핑 정확도')
print('='*65)
print(f'{"쿼리":<30} {"정답":>10} {"예측":>10} {"결과":>6}')
print('-'*65)
for r in h_results:
    mark = 'O' if r['correct'] else 'X'
    print(f'  {r["query"]:<28} {r["true_dept"]:>10} {r["pred_dept"]:>10} {mark:>6}')
print('-'*65)
print(f'  최종 정확도: {hits}/{total} = {acc:.1f}%')
print('='*65)

# ══════════════════════════════════════════════════════════════════════════════
# 5. 복약 안내 — OTC 약 이름 인식 정확도
# ══════════════════════════════════════════════════════════════════════════════
hits, total, o_results = eval_otc_recognition()
acc = hits / total * 100

print('\n' + '='*65)
print('  복약 안내 — OTC 약 이름 인식 정확도')
print('='*65)
print(f'{"쿼리":<38} {"정답":>12} {"결과":>6}')
print('-'*65)
for r in o_results:
    mark = 'O' if r['correct'] else 'X'
    true_str = '+'.join(r['true_keys'])
    pred_str = '+'.join(r['pred_keys']) if r['pred_keys'] else '없음'
    print(f'  {r["query"]:<36} {true_str:>20} → {pred_str:<20} {mark:>4}')
print('-'*65)
print(f'  최종 정확도: {hits}/{total} = {acc:.1f}%')
print('='*65)

# ══════════════════════════════════════════════════════════════════════════════
# 6. 복약 안내 — LLM 약물 상호작용 판단 정확도 (Ollama EXAONE 3.5)
# ══════════════════════════════════════════════════════════════════════════════
hits, total, i_results = eval_otc_interaction()
acc = hits / total * 100

print('\n' + '='*65)
print('  복약 안내 — LLM 약물 상호작용 판단 정확도 (EXAONE 3.5)')
print('='*65)
print(f'{"쿼리":<38} {"정답":>8} {"결과":>6}')
print('-'*65)
for r in i_results:
    mark = 'O' if r['correct'] else 'X'
    true_str = '안전' if r['true_safe'] else '주의'
    print(f'  {r["query"]:<36} {true_str:>8} {mark:>6}')
    print(f'    └ LLM: {r["llm_resp"]}')
print('-'*65)
print(f'  최종 정확도: {hits}/{total} = {acc:.1f}%')
print('='*65)