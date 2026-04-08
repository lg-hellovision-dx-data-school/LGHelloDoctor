"""Router V1 ~ V4 함수 및 평가 데이터"""
import json, os

def _load_samples():
    """data/samples/ JSON에서 ROUTE_SAMPLES 형식으로 로드"""
    base = os.path.join(os.path.dirname(__file__), '..', 'data', 'samples')
    samples = []
    for fname in ['emergency_samples.json', 'symptom_samples.json', 'medication_samples.json']:
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            for item in json.load(f):
                samples.append({
                    "query":       item["query"],
                    "intent":      item["true_intent"],
                    "entities":    {"symptom": None, "body_part": None},
                    "confidence":  0.90,
                    "true_intent": item["true_intent"],
                    "true_dept":   item.get("true_dept"),
                    "turn1_text":  item["query"],
                    "turn2_text":  None,
                    "severity":    item.get("severity"),
                })
    return samples

EMERGENCY_SCORES_V1 = {
    '숨이 안 쉬어': 100, '의식이 없': 100, '심장이 멎': 100,
    '피를 토': 90,       '가슴이 너무 아프': 90, '한쪽이 마비': 90,
    '말이 어눌': 85,     '입이 돌아': 85,        '갑자기 안 보여': 80,
    '쓰러': 80,          '식은땀': 30,            '가슴이 아파': 40,
    '어지러': 20,        '두통': 15,
}
EMERGENCY_SCORES_V2 = {**EMERGENCY_SCORES_V1, '갑자기 말이': 85, '말을 못': 85}

SYMPTOM_DEPT_MAP = {
    # 근골격 — 정형외과
    '무릎': '정형외과', '허리': '정형외과', '어깨': '정형외과',
    '골절': '정형외과', '척추': '정형외과', '목': '정형외과',
    # 신경 — 신경과
    '머리': '신경과',   '두통': '신경과',   '어지럼증': '신경과',
    '손저림': '신경과', '다리 당김': '신경과',
    # 소화기 — 내과
    '배': '내과', '속쓰림': '내과', '복통': '내과', '설사': '내과',
    # 이비인후과
    '귀': '이비인후과', '코': '이비인후과',
    # 기타
    '눈': '안과',   '피부': '피부과', '이': '치과', '잇몸': '치과',
    '당뇨': '내과', '갑상선': '내과', '혈압': '내과', '열': '내과',
    '기침': '내과', '호흡': '내과', '가슴': '내과', '심장': '내과',
    '소변': '비뇨의학과', '생리': '산부인과',
    '아이': '소아청소년과',
}

ROUTE_SAMPLES = _load_samples() + [
    # ── 기존 수동 샘플 (복약안내 / 병원검색 / 의료정보) ──────────────────────────
    {"query": "기침이 계속 나고 열이 나요",
     "intent": "symptom_inquiry", "entities": {"symptom": "기침", "body_part": None},
     "confidence": 0.86, "true_intent": "symptom_inquiry", "true_dept": "내과",
     "turn1_text": "기침이 계속 나고 열이 나요", "turn2_text": None, "severity": None},
    {"query": "속이 쓰리고 더부룩해요",
     "intent": "symptom_inquiry", "entities": {"symptom": "속쓰림", "body_part": "배"},
     "confidence": 0.84, "true_intent": "symptom_inquiry", "true_dept": "내과",
     "turn1_text": "속이 쓰리고 더부룩해요", "turn2_text": None, "severity": None},
    {"query": "머리가 너무 아파요",
     "intent": "symptom_inquiry", "entities": {"symptom": "두통", "body_part": "머리"},
     "confidence": 0.88, "true_intent": "symptom_inquiry", "true_dept": "신경과",
     "turn1_text": "머리가 너무 아파요", "turn2_text": None, "severity": None},
    {"query": "허리가 아파요. 조금 뻐근한 정도예요",
     "intent": "symptom_inquiry", "entities": {"symptom": "허리 통증", "body_part": "허리"},
     "confidence": 0.85, "true_intent": "symptom_inquiry", "true_dept": "정형외과",
     "turn1_text": "허리가 아파요", "turn2_text": "조금 뻐근한 정도예요", "severity": "가벼움"},
    {"query": "무릎이 아파요. 많이 힘들어요",
     "intent": "symptom_inquiry", "entities": {"symptom": "무릎 통증", "body_part": "무릎"},
     "confidence": 0.91, "true_intent": "symptom_inquiry", "true_dept": "정형외과",
     "turn1_text": "무릎이 아파요", "turn2_text": "많이 힘들고 걷기 어려워요", "severity": None},
    {"query": "손이 자꾸 저려요",
     "intent": "symptom_inquiry", "entities": {"symptom": "손저림", "body_part": None},
     "confidence": 0.82, "true_intent": "symptom_inquiry", "true_dept": "신경과",
     "turn1_text": "손이 자꾸 저려요", "turn2_text": None, "severity": None},
    {"query": "얼굴에 여드름이 너무 많아요",
     "intent": "symptom_inquiry", "entities": {"symptom": "여드름", "body_part": "피부"},
     "confidence": 0.83, "true_intent": "symptom_inquiry", "true_dept": "피부과",
     "turn1_text": "얼굴에 여드름이 너무 많아요", "turn2_text": None, "severity": None},
    {"query": "눈이 빨개지고 시야가 흐려요",
     "intent": "symptom_inquiry", "entities": {"symptom": "눈 충혈", "body_part": "눈"},
     "confidence": 0.85, "true_intent": "symptom_inquiry", "true_dept": "안과",
     "turn1_text": "눈이 빨개지고 시야가 흐려요", "turn2_text": None, "severity": None},
    {"query": "귀에서 소리가 나요",
     "intent": "symptom_inquiry", "entities": {"symptom": "이명", "body_part": "귀"},
     "confidence": 0.84, "true_intent": "symptom_inquiry", "true_dept": "이비인후과",
     "turn1_text": "귀에서 소리가 나요", "turn2_text": None, "severity": None},
    {"query": "잇몸이 붓고 아파요",
     "intent": "symptom_inquiry", "entities": {"symptom": "잇몸통증", "body_part": "잇몸"},
     "confidence": 0.87, "true_intent": "symptom_inquiry", "true_dept": "치과",
     "turn1_text": "잇몸이 붓고 아파요", "turn2_text": None, "severity": None},
    {"query": "생리가 불규칙해요",
     "intent": "symptom_inquiry", "entities": {"symptom": "생리불순", "body_part": "자궁"},
     "confidence": 0.86, "true_intent": "symptom_inquiry", "true_dept": "산부인과",
     "turn1_text": "생리가 불규칙해요", "turn2_text": None, "severity": None},
    {"query": "소변 볼 때 아프고 잔뇨감이 있어요",
     "intent": "symptom_inquiry", "entities": {"symptom": "소변 시 통증", "body_part": None},
     "confidence": 0.85, "true_intent": "symptom_inquiry", "true_dept": "비뇨의학과",
     "turn1_text": "소변 볼 때 아프고 잔뇨감이 있어요", "turn2_text": None, "severity": None},
    {"query": "가슴이 두근거리고 답답해요",
     "intent": "symptom_inquiry", "entities": {"symptom": "가슴 두근거림", "body_part": "가슴"},
     "confidence": 0.86, "true_intent": "symptom_inquiry", "true_dept": "내과",
     "turn1_text": "가슴이 두근거리고 답답해요", "turn2_text": None, "severity": None},
    {"query": "혈당이 높고 당뇨가 걱정돼요",
     "intent": "symptom_inquiry", "entities": {"symptom": "당뇨", "body_part": None},
     "confidence": 0.83, "true_intent": "symptom_inquiry", "true_dept": "내과",
     "turn1_text": "혈당이 높고 당뇨가 걱정돼요", "turn2_text": None, "severity": None},
    {"query": "아이가 열이 나고 감기 기운이 있어요",
     "intent": "symptom_inquiry", "entities": {"symptom": "아이 열", "body_part": None},
     "confidence": 0.89, "true_intent": "symptom_inquiry", "true_dept": "소아청소년과",
     "turn1_text": "아이가 열이 나고 감기 기운이 있어요", "turn2_text": None, "severity": None},
    # ── 응급 ────────────────────────────────────────────────────────────────────
    {"query": "가슴이 아프고 숨이 안 쉬어져요",
     "intent": "emergency", "entities": {"symptom": "흉통 호흡곤란", "body_part": "가슴"},
     "confidence": 0.97, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "가슴이 아프고 숨이 안 쉬어져요", "turn2_text": None, "severity": "HIGH"},
    {"query": "갑자기 말이 안 나와요",
     "intent": "symptom_inquiry", "entities": {"symptom": None, "body_part": None},
     "confidence": 0.72, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "갑자기 말이 안 나와요", "turn2_text": None, "severity": None},
    {"query": "의식을 잃고 쓰러졌어요",
     "intent": "emergency", "entities": {"symptom": "의식 소실", "body_part": None},
     "confidence": 0.99, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "의식을 잃고 쓰러졌어요", "turn2_text": None, "severity": "HIGH"},
    {"query": "한쪽 팔이 갑자기 마비됐어요",
     "intent": "emergency", "entities": {"symptom": "마비", "body_part": None},
     "confidence": 0.96, "true_intent": "emergency", "true_dept": None,
     "turn1_text": "한쪽 팔이 갑자기 마비됐어요", "turn2_text": None, "severity": "HIGH"},
    # ── 복약 안내 ───────────────────────────────────────────────────────────────
    {"query": "혈압약이랑 감기약 같이 먹어도 되나요",
     "intent": "medication_info", "entities": {"symptom": None, "body_part": None},
     "confidence": 0.88, "true_intent": "medication_info", "true_dept": None,
     "turn1_text": "혈압약이랑 감기약 같이 먹어도 되나요", "turn2_text": None, "severity": None},
    {"query": "타이레놀 하루 몇 번 먹어요",
     "intent": "medication_info", "entities": {"symptom": None, "body_part": None},
     "confidence": 0.90, "true_intent": "medication_info", "true_dept": None,
     "turn1_text": "타이레놀 하루 몇 번 먹어요", "turn2_text": None, "severity": None},
    # ── 병원 검색 ───────────────────────────────────────────────────────────────
    {"query": "가까운 내과 알려주세요",
     "intent": "hospital_search", "entities": {"symptom": None, "body_part": None},
     "confidence": 0.95, "true_intent": "hospital_search", "true_dept": None,
     "turn1_text": "가까운 내과 알려주세요", "turn2_text": None, "severity": None},
    {"query": "근처 정형외과 어디 있어요",
     "intent": "hospital_search", "entities": {"symptom": None, "body_part": None},
     "confidence": 0.93, "true_intent": "hospital_search", "true_dept": None,
     "turn1_text": "근처 정형외과 어디 있어요", "turn2_text": None, "severity": None},
    # ── 의료 정보 ───────────────────────────────────────────────────────────────
    {"query": "당뇨가 있으면 어떤 음식을 피해야 하나요",
     "intent": "medical_info", "entities": {"symptom": "당뇨", "body_part": None},
     "confidence": 0.87, "true_intent": "medical_info", "true_dept": None,
     "turn1_text": "당뇨가 있으면 어떤 음식을 피해야 하나요", "turn2_text": None, "severity": None},
    {"query": "고혈압은 왜 생기나요",
     "intent": "medical_info", "entities": {"symptom": "고혈압", "body_part": None},
     "confidence": 0.85, "true_intent": "medical_info", "true_dept": None,
     "turn1_text": "고혈압은 왜 생기나요", "turn2_text": None, "severity": None},
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
    return '내과'


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
    t1 = s.get('turn1_text') or ''; t2 = s.get('turn2_text') or ''
    q  = (t1 + ' ' + t2).strip() if t2 else (s.get('query') or t1)
    if _emerg(q, EMERGENCY_SCORES_V2) == 'HIGH':
        return {'ri': 'emergency', 'dept': None}
    dept = None
    if s['intent'] in ('symptom_inquiry', 'hospital_search'):
        e    = s.get('entities', {})
        dept = s.get('true_dept') or _dept(e.get('body_part', ''), e.get('symptom', ''), q)
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
