"""Router V1 ~ V4 함수 및 평가 데이터"""

EMERGENCY_SCORES_V1 = {
    '숨이 안 쉬어': 100, '의식이 없': 100, '심장이 멎': 100,
    '피를 토': 90,       '가슴이 너무 아프': 90, '한쪽이 마비': 90,
    '말이 어눌': 85,     '입이 돌아': 85,        '갑자기 안 보여': 80,
    '쓰러': 80,          '식은땀': 30,            '가슴이 아파': 40,
    '어지러': 20,        '두통': 15,
}
EMERGENCY_SCORES_V2 = {**EMERGENCY_SCORES_V1, '갑자기 말이': 85, '말을 못': 85}

SYMPTOM_DEPT_MAP = {
    '무릎': '정형외과', '허리': '정형외과', '어깨': '정형외과',
    '눈':   '안과',     '귀':   '이비인후과', '코': '이비인후과',
    '피부': '피부과',   '머리': '신경과',     '가슴': '심장내과',
    '배':   '소화기내과', '혈압': '내과',     '기침': '내과', '내과': '내과',
}

ROUTE_SAMPLES = [
    {"query": "무릎이 아파요. 많이 힘들어요",
     "intent": "symptom_inquiry",
     "entities": {"symptom": "무릎 통증", "body_part": "무릎"},
     "confidence": 0.91, "true_intent": "symptom_inquiry", "true_dept": "정형외과",
     "turn1_text": "무릎이 아파요", "turn2_text": "많이 힘들고 걷기 어려워요", "severity": None},
    {"query": "가슴이 아프고 숨이 안 쉬어져요",
     "intent": "emergency",
     "entities": {"symptom": "흉통 호흡곤란", "body_part": "가슴"},
     "confidence": 0.97, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "가슴이 아프고 숨이 안 쉬어져요", "turn2_text": None, "severity": "HIGH"},
    {"query": "혈압약이랑 감기약 같이 먹어도 되나요",
     "intent": "medication_info",
     "entities": {"symptom": None, "body_part": None},
     "confidence": 0.88, "true_intent": "medication_info", "true_dept": None,
     "turn1_text": "혈압약이랑 감기약 같이 먹어도 되나요", "turn2_text": None, "severity": None},
    {"query": "가까운 내과 알려주세요",
     "intent": "hospital_search",
     "entities": {"symptom": None, "body_part": None},
     "confidence": 0.95, "true_intent": "hospital_search", "true_dept": None,
     "turn1_text": "가까운 내과 알려주세요", "turn2_text": None, "severity": None},
    {"query": "허리가 아파요. 조금 뻐근한 정도예요",
     "intent": "symptom_inquiry",
     "entities": {"symptom": "허리 통증", "body_part": "허리"},
     "confidence": 0.85, "true_intent": "symptom_inquiry", "true_dept": "정형외과",
     "turn1_text": "허리가 아파요", "turn2_text": "조금 뻐근한 정도예요", "severity": "가벼움"},
    {"query": "갑자기 말이 안 나와요",
     "intent": "symptom_inquiry",
     "entities": {"symptom": None, "body_part": None},
     "confidence": 0.72, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "갑자기 말이 안 나와요", "turn2_text": None, "severity": None},
]


def _emerg(text, scores):
    total, matched = 0, []
    for kw, score in scores.items():
        if kw in text:
            total += score; matched.append(kw)
    if len(matched) >= 2:
        total = min(total * 1.2, 100)
    return 'HIGH' if total >= 70 else 'LOW'

def _dept(body_part='', symptom='', query=''):
    for kw, name in SYMPTOM_DEPT_MAP.items():
        if kw in (body_part or '') or kw in (symptom or '') or kw in query:
            return name
    return None


# ── Router V1: intent만 사용 ───────────────────────────────────────────────────
def router_v1(s):
    q = s['query']
    if s['intent'] == 'emergency' or _emerg(q, EMERGENCY_SCORES_V1) == 'HIGH':
        return {'ri': 'emergency', 'dept': None}
    dept = _dept(query=q) if s['intent'] in ('symptom_inquiry', 'hospital_search') else None
    return {'ri': s['intent'], 'dept': dept}

# ── Router V2: emergency 키워드 보강 ─────────────────────────────────────────
def router_v2(s):
    q = s['query']
    if s['intent'] == 'emergency' or _emerg(q, EMERGENCY_SCORES_V2) == 'HIGH':
        return {'ri': 'emergency', 'dept': None}
    dept = _dept(query=q) if s['intent'] in ('symptom_inquiry', 'hospital_search') else None
    return {'ri': s['intent'], 'dept': dept}

# ── Router V3: B팀 severity 우선 ─────────────────────────────────────────────
def router_v3(s):
    if s.get('severity') == 'HIGH' or s['intent'] == 'emergency':
        return {'ri': 'emergency', 'dept': None}
    if _emerg(s['query'], EMERGENCY_SCORES_V2) == 'HIGH':
        return {'ri': 'emergency', 'dept': None}
    dept = _dept(query=s['query']) if s['intent'] in ('symptom_inquiry', 'hospital_search') else None
    return {'ri': s['intent'], 'dept': dept}

# ── Router V4: 멀티턴 + entities + true_dept (최종) ──────────────────────────
def router_v4(s):
    if s.get('severity') == 'HIGH' or s['intent'] == 'emergency':
        return {'ri': 'emergency', 'dept': None}

    t1 = s.get('turn1_text') or ''
    t2 = s.get('turn2_text') or ''
    q  = (t1 + ' ' + t2).strip() if t2 else (s.get('query') or t1)

    if _emerg(q, EMERGENCY_SCORES_V2) == 'HIGH':
        return {'ri': 'emergency', 'dept': None}

    dept = None
    if s['intent'] in ('symptom_inquiry', 'hospital_search'):
        e = s.get('entities', {}) or {}
        dept = _dept(
            body_part=e.get('body_part', ''),
            symptom=e.get('symptom', ''),
            query=q,
        )

    return {'ri': s['intent'], 'dept': dept}


def eval_route(fn):
    ik = dk = dt = 0
    for s in ROUTE_SAMPLES:
        r = fn(s)
        if r['ri'] == s['true_intent']:
            ik += 1
        if s.get('true_dept'):
            dt += 1
            if r['dept'] == s['true_dept']:
                dk += 1
    return ik, len(ROUTE_SAMPLES), dk, dt
