"""
C팀 통합 파이프라인
RAG + 병원검색 + 응급판단 + Tool Router
eval/ 폴더 기반으로 재작성
"""
import os
import requests
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from numpy import dot
from numpy.linalg import norm

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────────────────────────
# Colab 환경이면 아래 경로로, 로컬이면 'RAG/db'
DB_PATH       = os.getenv('DB_PATH', '/content/drive/MyDrive/LG_HelloDoctor/RAG/db')
KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')  # .env 또는 환경변수에 설정

os.makedirs(DB_PATH, exist_ok=True)

embed_model   = SentenceTransformer('jhgan/ko-sroberta-multitask')
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection    = chroma_client.get_or_create_collection(
    'medical_knowledge', metadata={'hnsw:space': 'cosine'}
)

print(f'ChromaDB 문서 수: {collection.count()}개')


# ──────────────────────────────────────────────────────────────────────────────
# 1. RAG — V5: Hybrid (Vector + Keyword) + Reranking
#    eval/rag_stages.py의 rag_v5_rerank 기반
# ──────────────────────────────────────────────────────────────────────────────
QUERY_REWRITE_MAP = {
    '무릎': '무릎관절염 정형외과 관절 통증 진료',
    '허리': '허리디스크 정형외과 척추 통증 진료',
    '어깨': '오십견 정형외과 어깨 통증 진료',
    '머리': '편두통 신경과 두통 진료',
    '배':   '위염 소화불량 소화기내과 진료',
    '가슴': '심근경색 심장내과 흉통 진료',
    '혈압': '고혈압 내과 혈압약 복용',
    '항생제': '항생제 복용 방법 주의사항',
    '당뇨': '당뇨병 내과 당뇨약 복용',
}

def _query_rewrite(query: str) -> str:
    for kw, rewritten in QUERY_REWRITE_MAP.items():
        if kw in query:
            return rewritten
    return query

def full_rag_pipeline(query: str) -> str:
    """V5: Hybrid(Vector + Keyword) + Reranking
    1) 쿼리 리라이팅 → 벡터 검색 (Top-5)
    2) 원본 쿼리 → 키워드 검색 (Top-3)
    3) 병합 후 코사인 유사도로 Reranking → Top-3 반환
    """
    rewritten = _query_rewrite(query)

    # 벡터 검색
    q_emb    = embed_model.encode([rewritten]).tolist()
    vec_res  = collection.query(query_embeddings=q_emb, n_results=5)
    vec_docs = vec_res['documents'][0]

    # 키워드 검색
    keywords  = query.split()
    all_docs  = collection.get(include=['documents'])['documents']
    kw_docs   = [
        d for d in all_docs
        if sum(1 for kw in keywords if kw in d) > 0
    ][:3]

    # 병합 (중복 제거)
    seen, combined = set(), []
    for d in vec_docs + kw_docs:
        if d not in seen:
            seen.add(d); combined.append(d)

    if not combined:
        return ''

    # Reranking: 원본 쿼리 기준 코사인 유사도
    q_emb2 = embed_model.encode([query])
    d_embs = embed_model.encode(combined)
    scores = sorted(
        [(dot(q_emb2[0], e) / (norm(q_emb2[0]) * norm(e) + 1e-9), combined[i])
         for i, e in enumerate(d_embs)],
        reverse=True
    )
    return ' '.join(d for _, d in scores[:3])


# ──────────────────────────────────────────────────────────────────────────────
# 2. 병원 검색 — Kakao Local API
#    eval/hospital_stages.py의 SYMPTOM_TO_DEPT / BODY_TO_DEPT 기반
# ──────────────────────────────────────────────────────────────────────────────
SYMPTOM_TO_DEPT = {
    # 기침·열·감기
    '기침': '내과', '열': '내과', '감기': '내과',
    '콧물': '이비인후과', '코막힘': '이비인후과', '인후통': '이비인후과',
    # 소화기
    '속쓰림': '내과', '복통': '내과', '소화불량': '내과', '구토': '내과',
    '설사': '내과', '혈변': '외과', '치질': '외과',
    # 두통·어지럼증
    '두통': '신경과', '어지럼증': '신경과', '편두통': '신경과',
    # 근골격
    '허리 통증': '정형외과', '무릎 통증': '정형외과', '어깨 통증': '정형외과',
    '관절 통증': '정형외과', '골절': '정형외과',
    # 신경
    '손저림': '신경과', '손발 저림': '신경과', '마비': '신경과',
    # 피부
    '여드름': '피부과', '두드러기': '피부과', '습진': '피부과', '아토피': '피부과',
    # 눈·귀
    '눈 충혈': '안과', '시야 흐림': '안과', '시력 저하': '안과',
    '이명': '이비인후과', '중이염': '이비인후과', '귀 통증': '이비인후과',
    # 치과
    '잇몸통증': '치과', '충치': '치과',
    # 산부인과
    '생리불순': '산부인과', '생리통': '산부인과', '질염': '산부인과',
    # 비뇨의학과
    '소변 시 통증': '비뇨의학과', '잔뇨감': '비뇨의학과', '혈뇨': '비뇨의학과',
    # 내과 기타
    '가슴 두근거림': '내과', '흉통': '내과', '호흡곤란': '내과',
    '당뇨': '내과', '고혈압': '내과', '혈압': '내과', '갑상선': '내과',
    # 소아
    '아이 열': '소아청소년과', '소아 발열': '소아청소년과',
}

BODY_TO_DEPT = {
    '무릎': '정형외과', '허리': '정형외과', '어깨': '정형외과',
    '발목': '정형외과', '손목': '정형외과', '척추': '정형외과', '목': '정형외과',
    '머리': '신경과', '뇌': '신경과',
    '가슴': '내과', '심장': '내과', '폐': '내과', '기관지': '내과',
    '배': '내과', '위': '내과', '장': '내과',
    '코': '이비인후과', '귀': '이비인후과', '편도': '이비인후과',
    '눈': '안과', '피부': '피부과',
    '잇몸': '치과',
    '신장': '비뇨의학과', '방광': '비뇨의학과',
    '자궁': '산부인과', '난소': '산부인과',
}

def _get_dept(symptom: str = '', body_part: str = '', query: str = '') -> str:
    """증상·부위·쿼리에서 진료과 추론 (eval/hospital_stages.py 동일 로직)"""
    for text in [symptom, body_part, query]:
        if not text:
            continue
        if text in SYMPTOM_TO_DEPT:
            return SYMPTOM_TO_DEPT[text]
        if text in BODY_TO_DEPT:
            return BODY_TO_DEPT[text]
        for key, dept in SYMPTOM_TO_DEPT.items():
            if key in text or text in key:
                return dept
        for key, dept in BODY_TO_DEPT.items():
            if key in text:
                return dept
    return '내과'

def _search_kakao(dept_name: str, lat: float, lng: float) -> list:
    if not KAKAO_API_KEY:
        return []
    url     = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    headers = {'Authorization': f'KakaoAK {KAKAO_API_KEY}'}
    params  = {
        'query': dept_name, 'x': lng, 'y': lat,
        'radius': 3000, 'category_group_code': 'HP8', 'size': 5
    }
    try:
        res  = requests.get(url, headers=headers, params=params, timeout=5)
        docs = res.json().get('documents', [])
        results = []
        for p in docs:
            navi_url = f"https://map.kakao.com/link/to/{p['place_name']},{p['y']},{p['x']}"
            results.append({
                'name':     p['place_name'],
                'address':  p['road_address_name'],
                'phone':    p['phone'],
                'distance': int(p['distance']),
                'navi_url': navi_url,
                'lat':      p['y'],
                'lng':      p['x'],
            })
        return results
    except Exception:
        return []

def search_hospital(query: str, symptom: str = '', body_part: str = '',
                    lat: float = 37.5012, lng: float = 127.0396) -> dict:
    dept_name = _get_dept(symptom=symptom, body_part=body_part, query=query)
    hospitals = sorted(
        [h for h in _search_kakao(dept_name, lat, lng) if h['phone']],
        key=lambda x: x['distance']
    )
    return {'department': dept_name, 'nearby': hospitals[:3]}


# ──────────────────────────────────────────────────────────────────────────────
# 3. 응급 판단
#    eval/router_stages.py의 EMERGENCY_SCORES_V2 기반 (키워드 보강 버전)
# ──────────────────────────────────────────────────────────────────────────────
EMERGENCY_SCORES = {
    '숨이 안 쉬어': 100, '의식이 없': 100, '심장이 멎': 100,
    '피를 토': 90,        '가슴이 너무 아프': 90, '한쪽이 마비': 90,
    '말이 어눌': 85,      '입이 돌아': 85,         '갑자기 말이': 85,
    '말을 못': 85,        '갑자기 안 보여': 80,
    '쓰러': 80,           '혈압이 200': 80,
    '가슴이 아파': 40,    '식은땀': 30,
    '어지러': 20,         '두통': 15,
}

def emergency_check(text: str) -> dict:
    """응급 여부 판단 — eval/router_stages.py EMERGENCY_SCORES_V2 기반"""
    total, matched = 0, []
    for kw, score in EMERGENCY_SCORES.items():
        if kw in text:
            total += score; matched.append(kw)
    if len(matched) >= 2:
        total = min(total * 1.2, 100)

    if total >= 70:
        return {
            'is_emergency': True, 'severity': 'HIGH',
            'score': round(total), 'matched': matched,
            'action': '지금 바로 119에 전화해 주세요.',
        }
    elif total >= 40:
        return {
            'is_emergency': True, 'severity': 'MEDIUM',
            'score': round(total), 'matched': matched,
            'action': '응급실에 가보시는 게 좋을 것 같아요.',
        }
    return {
        'is_emergency': False, 'severity': 'LOW',
        'score': round(total), 'matched': matched,
        'action': None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tool Router — eval/router_stages.py router_v4 기반
#    멀티턴 + entities + severity 통합 판단
# ──────────────────────────────────────────────────────────────────────────────
def tool_router(output_from_B: dict, lat: float = 37.5012, lng: float = 127.0396) -> dict:
    """
    B팀 출력을 받아 RAG / 병원검색 / 응급 결과를 통합 반환

    output_from_B 예시:
    {
        'intent':     'symptom_inquiry',   # symptom_inquiry | medication_info | hospital_search | emergency
        'query':      '무릎이 너무 아파요',
        'entities':   {'symptom': '무릎 통증', 'body_part': '무릎'},
        'severity':   None,                # 'HIGH' | 'MEDIUM' | None
        'turn1_text': '무릎이 너무 아파요',
        'turn2_text': '많이 힘들어요',     # 멀티턴 2번째 발화 (없으면 None)
    }
    """
    intent    = output_from_B.get('intent', 'symptom_inquiry')
    entities  = output_from_B.get('entities') or {}
    symptom   = entities.get('symptom') or ''
    body_part = entities.get('body_part') or ''
    severity  = output_from_B.get('severity')

    # 멀티턴: turn1 + turn2 합쳐서 쿼리 구성
    t1 = output_from_B.get('turn1_text') or output_from_B.get('query') or ''
    t2 = output_from_B.get('turn2_text') or ''
    query = (t1 + ' ' + t2).strip() if t2 else t1

    result = {
        'intent': intent,
        'rag_context': None,
        'hospitals':   None,
        'emergency':   None,
    }

    # ── 1) 응급 판단 (severity HIGH이면 RAG/병원 없이 즉시 반환) ──────────────
    if severity == 'HIGH' or intent == 'emergency':
        emerg = emergency_check(query)
        emerg['is_emergency'] = True
        emerg['severity']     = 'HIGH'
        result['emergency']   = emerg
        return result

    emerg = emergency_check(query)
    if emerg['is_emergency']:
        result['emergency'] = emerg
        if emerg['severity'] == 'HIGH':
            return result

    # ── 2) intent별 분기 ──────────────────────────────────────────────────────
    if intent == 'symptom_inquiry':
        result['rag_context'] = full_rag_pipeline(query)
        result['hospitals']   = search_hospital(query, symptom, body_part, lat, lng)

    elif intent == 'medication_info':
        result['rag_context'] = full_rag_pipeline(query)

    elif intent == 'hospital_search':
        result['hospitals'] = search_hospital(query, symptom, body_part, lat, lng)

    return result


print('C팀 파이프라인 로드 완료!')
print('  - full_rag_pipeline(query)  : RAG V5 Hybrid+Reranking')
print('  - search_hospital(query)    : Kakao API 병원 검색')
print('  - emergency_check(text)     : 응급 판단 (V2 키워드 보강)')
print('  - tool_router(output_from_B): 통합 라우터')
