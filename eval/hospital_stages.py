"""③ 병원 검색 — 증상/부위 → 진료과 매핑 정확도 평가"""

# 이미지 기준 증상→진료과 매핑 (복수 진료과는 첫 번째 우선)
SYMPTOM_TO_DEPT = {
    # 기침·열·감기 — 내과(전신) / 이비인후과(코·목)
    "기침": "내과", "열": "내과", "감기": "내과",
    "콧물": "이비인후과", "코막힘": "이비인후과", "인후통": "이비인후과",

    # 소화기 — 내과
    "속쓰림": "내과", "체함": "내과", "복통": "내과",
    "소화불량": "내과", "구토": "내과", "위염": "내과",

    # 설사·혈변·치질 — 내과 / 외과
    "설사": "내과", "혈변": "외과", "치질": "외과",

    # 두통·어지럼증 — 신경과 / 내과
    "두통": "신경과", "어지럼증": "신경과", "편두통": "신경과",

    # 허리·목 통증 — 정형외과
    "허리 통증": "정형외과", "목 통증": "정형외과",
    "허리·목 통증": "정형외과", "무릎 통증": "정형외과",
    "어깨 통증": "정형외과", "관절 통증": "정형외과",
    "골절": "정형외과", "사고": "응급실", "찢김": "응급실",
    "교통사고 후 통증": "정형외과",

    # 손저림·다리 당김 — 신경과 / 정형외과
    "손저림": "신경과", "손발 저림": "신경과", "다리 당김": "신경과",
    "마비": "신경과",

    # 피부 — 피부과
    "여드름": "피부과", "피부염": "피부과", "피부 발진": "피부과",
    "두드러기": "피부과", "습진": "피부과", "아토피": "피부과",

    # 눈 — 안과
    "눈 충혈": "안과", "시야 흐림": "안과", "눈 통증": "안과",
    "시력 저하": "안과",

    # 귀 — 이비인후과
    "귀 먹먹함": "이비인후과", "이통": "이비인후과", "이명": "이비인후과",
    "귀 통증": "이비인후과", "중이염": "이비인후과",

    # 치과
    "잇몸통증": "치과", "충치": "치과", "이 통증": "치과",

    # 산부인과
    "생리불순": "산부인과", "생리 불순": "산부인과", "생리통": "산부인과",
    "질염": "산부인과", "임신": "산부인과",

    # 비뇨의학과
    "소변 시 통증": "비뇨의학과", "잔뇨감": "비뇨의학과",
    "빈뇨": "비뇨의학과", "혈뇨": "비뇨의학과",

    # 가슴 두근거림·압박 — 내과 / 응급실
    "가슴 두근거림": "내과", "심장 두근거림": "내과",
    "가슴 압박": "내과", "흉통": "응급실", "가슴 통증": "내과",

    # 호흡곤란·기침 지속 — 내과
    "호흡곤란": "내과", "기침 지속": "내과", "숨가쁨": "내과",
    "천식": "내과", "폐렴": "내과",

    # 갑상선·당뇨·체중변화 — 내과
    "갑상선": "내과", "당뇨": "내과", "당뇨병": "내과",
    "체중변화": "내과", "고지혈증": "내과", "혈압": "내과", "고혈압": "내과",

    # 소아청소년과
    "아이 열": "소아청소년과", "소아 발열": "소아청소년과",
    "아이 감기": "소아청소년과", "피부트러블": "소아청소년과",
}

BODY_TO_DEPT = {
    "무릎": "정형외과", "허리": "정형외과", "어깨": "정형외과",
    "발목": "정형외과", "손목": "정형외과", "척추": "정형외과", "목": "정형외과",
    "머리": "신경과", "뇌": "신경과",
    "가슴": "내과", "심장": "내과",
    "폐": "내과", "기관지": "내과",
    "배": "내과", "위": "내과", "장": "내과",
    "코": "이비인후과", "귀": "이비인후과", "편도": "이비인후과",
    "눈": "안과",
    "피부": "피부과",
    "이": "치과", "잇몸": "치과",
    "신장": "비뇨의학과", "방광": "비뇨의학과",
    "자궁": "산부인과", "난소": "산부인과",
}


def get_dept_from_symptom(symptom: str = "", body_part: str = "", query: str = "") -> str:
    """증상·부위·쿼리에서 진료과 추론 (부분 매칭 포함)"""
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
    return "내과"


# ── 평가 샘플 (이미지 18개 행 기반) ──────────────────────────────────────────
HOSPITAL_SAMPLES = [
    {"symptom": "기침",             "body_part": None,    "query": "기침이 계속 나요",                    "true_dept": "내과"},
    {"symptom": "열",               "body_part": None,    "query": "열이 나고 몸살 기운이 있어요",         "true_dept": "내과"},
    {"symptom": "속쓰림",           "body_part": "배",    "query": "속이 쓰리고 더부룩해요",              "true_dept": "내과"},
    {"symptom": "복통",             "body_part": "배",    "query": "배가 심하게 아파요",                  "true_dept": "내과"},
    {"symptom": "설사",             "body_part": None,    "query": "설사가 멈추질 않아요",                "true_dept": "내과"},
    {"symptom": "혈변",             "body_part": None,    "query": "변에 피가 섞여 나와요",               "true_dept": "외과"},
    {"symptom": "두통",             "body_part": "머리",  "query": "머리가 너무 아파요",                  "true_dept": "신경과"},
    {"symptom": "어지럼증",         "body_part": None,    "query": "갑자기 어지럽고 울렁거려요",          "true_dept": "신경과"},
    {"symptom": "허리 통증",        "body_part": "허리",  "query": "허리가 뻐근하고 아파요",              "true_dept": "정형외과"},
    {"symptom": "손저림",           "body_part": None,    "query": "손이 자꾸 저려요",                    "true_dept": "신경과"},
    {"symptom": "여드름",           "body_part": "피부",  "query": "얼굴에 여드름이 너무 많아요",         "true_dept": "피부과"},
    {"symptom": "눈 충혈",          "body_part": "눈",    "query": "눈이 빨개지고 시야가 흐려요",         "true_dept": "안과"},
    {"symptom": "이명",             "body_part": "귀",    "query": "귀에서 소리가 나요",                  "true_dept": "이비인후과"},
    {"symptom": "잇몸통증",         "body_part": "잇몸",  "query": "잇몸이 붓고 아파요",                  "true_dept": "치과"},
    {"symptom": "생리불순",         "body_part": "자궁",  "query": "생리가 불규칙해요",                   "true_dept": "산부인과"},
    {"symptom": "소변 시 통증",     "body_part": None,    "query": "소변 볼 때 아프고 잔뇨감이 있어요",   "true_dept": "비뇨의학과"},
    {"symptom": "가슴 두근거림",    "body_part": "가슴",  "query": "가슴이 두근거리고 답답해요",          "true_dept": "내과"},
    {"symptom": "호흡곤란",         "body_part": None,    "query": "숨이 차고 호흡이 힘들어요",           "true_dept": "내과"},
    {"symptom": "당뇨",             "body_part": None,    "query": "혈당이 높고 당뇨가 걱정돼요",         "true_dept": "내과"},
    {"symptom": "갑상선",           "body_part": None,    "query": "갑상선 검사를 받고 싶어요",           "true_dept": "내과"},
    {"symptom": "아이 열",          "body_part": None,    "query": "아이가 열이 나고 감기 기운이 있어요", "true_dept": "소아청소년과"},
    {"symptom": "골절",             "body_part": "무릎",  "query": "넘어져서 무릎을 다쳤어요",            "true_dept": "정형외과"},
    {"symptom": "교통사고 후 통증", "body_part": "허리",  "query": "교통사고 후 허리가 아파요",           "true_dept": "정형외과"},
]


def eval_hospital_mapping():
    """증상→진료과 매핑 정확도 평가"""
    hits = 0
    results = []
    for s in HOSPITAL_SAMPLES:
        pred = get_dept_from_symptom(
            symptom=s.get("symptom") or "",
            body_part=s.get("body_part") or "",
            query=s.get("query") or "",
        )
        correct = (pred == s["true_dept"])
        if correct:
            hits += 1
        results.append({
            "query":     s["query"],
            "true_dept": s["true_dept"],
            "pred_dept": pred,
            "correct":   correct,
        })
    return hits, len(HOSPITAL_SAMPLES), results
