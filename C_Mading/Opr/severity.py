from Opr.schemas import CInputPayload


# ---------------------------
# Severity 판단용 패턴 사전
# ---------------------------
HIGH_PATTERNS = {
    "dyspnea": [
        "숨이 안 쉬어",
        "숨이 안쉬어",
        "숨을 못 쉬",
        "숨 쉬기 힘들",
        "숨이 막혀",
        "호흡곤란",
        "숨이 너무 차",
        "질식할 것 같",
        "숨넘어갈 것 같",
        "호흡이 안 돼"
    ],
    "unconscious": [
        "의식이 없어",
        "정신을 잃",
        "쓰러졌",
        "반응이 없어",
        "깨워도 안 일어나",
        "기절했",
        "혼절했",
        "눈을 못 떠",
        "의식 저하",
        "불러도 대답이 없"
    ],
    "bleeding": [
        "피가 많이 나",
        "피를 너무 많이 흘",
        "출혈이 멈추지 않",
        "피가 멈추지 않",
        "계속 피가 나",
        "피가 쏟아져",
        "지혈이 안 돼",
        "피가 철철 나"
    ],
    "neurologic": [
        "말이 어눌",
        "말을 못 하",
        "말이 안 나와",
        "한쪽 팔이 안 움직",
        "한쪽 다리가 안 움직",
        "한쪽이 마비",
        "얼굴이 돌아갔",
        "입이 돌아갔",
        "손발이 마비",
        "중풍 같"
    ],
    "seizure": [
        "경련",
        "발작",
        "몸을 떨",
        "몸을 떨면서 쓰러졌",
        "거품을 물",
        "눈이 뒤집",
        "경기를 해"
    ]
}

MEDIUM_PATTERNS = {
    "chest_pain": [
        "가슴이 아파",
        "가슴 통증",
        "가슴이 답답",
        "가슴이 쥐어짜",
        "가슴이 찌릿",
        "가슴이 조여오",
        "가슴이 묵직",
        "가슴이 눌리는 것 같"
    ],
    "severe_pain": [
        "너무 아파",
        "계속 아파",
        "심하게 아파",
        "참기 힘들",
        "갑자기 아파졌",
        "통증이 심해",
        "엄청 아파",
        "통증이 점점 심해"
    ],
    "fever": [
        "열이 너무",
        "열이 계속",
        "열이 안 내려",
        "고열",
        "오한이 심해",
        "몸이 너무 떨",
        "열 때문에 못 움직이"
    ],
    "vomit_diarrhea": [
        "계속 토",
        "설사를 너무",
        "물도 못 마시",
        "토가 안 멈춰",
        "구토가 계속",
        "설사가 멈추지 않",
        "탈수될 것 같"
    ],
    "dizziness": [
        "너무 어지러",
        "서있기 힘들",
        "기운이 하나도 없",
        "쓰러질 것 같",
        "현기증이 심해",
        "눈앞이 캄캄",
        "비틀거려"
    ],
    "allergy_swelling": [
        "입술이 부었",
        "얼굴이 붓",
        "두드러기",
        "목이 붓는 것 같",
        "혀가 부은 것 같",
        "온몸이 가려"
    ]
}

LOW_PATTERNS = {
    "general_symptom": [
        "무릎이 아파",
        "허리가 아파",
        "기침이 나",
        "목이 아파",
        "열이 조금 나",
        "두통이 있어",
        "콧물이 나",
        "몸살 같",
        "어깨가 아파",
        "손목이 아파",
        "발목이 아파",
        "배가 살살 아파",
        "소화가 안 돼",
        "가래가 나",
        "재채기가 나",
        "목이 칼칼",
        "속이 더부룩",
        "허리가 뻐근",
        "관절이 아파",
        "근육통이 있"
    ],
    "mild_pain": [
        "조금 아파",
        "살짝 아파",
        "뻐근해",
        "약간 불편",
        "좀 아픈 것 같",
        "약하게 아파",
        "살짝 쑤셔",
        "크게 아프진 않"
    ]
}

INTENT_HINT_PATTERNS = {
    "medication_info": [
        "같이 먹어도",
        "약 부작용",
        "언제 먹",
        "복용해도",
        "약 먹는 법",
        "식전 식후",
        "몇 시간 간격",
        "약이랑 술",
        "약이랑 커피",
        "약 두 개 같이"
    ],
    "hospital_search": [
        "어디 병원",
        "정형외과 어디",
        "약국 어디",
        "가까운 병원",
        "근처 약국",
        "어느 병원 가",
        "병원 찾아줘",
        "약국 찾아줘",
        "근처 내과",
        "응급실 어디"
    ],
    "general_help": [
        "어떻게 해야",
        "도와줘",
        "어쩌면 좋",
        "뭘 해야",
        "어디 문의",
        "방법 알려줘",
        "궁금해",
        "문의하고 싶"
    ]
}


def _match_patterns(text: str, pattern_dict: dict) -> list:
    matched = []

    for category, patterns in pattern_dict.items():
        for pattern in patterns:
            if pattern in text:
                matched.append(category)
                break

    return matched


def assess_severity(payload: CInputPayload) -> dict:
    intents = payload.intent or []
    if isinstance(intents, str):
        intents = [intents]

    text = payload.input_text or ""
    entities = payload.entities

    symptom_text = " ".join([
        entities.symptom or "",
        entities.body_part or ""
    ]).strip()

    merged_text = f"{text} {symptom_text}".strip()

    high_reasons = _match_patterns(merged_text, HIGH_PATTERNS)
    medium_reasons = _match_patterns(merged_text, MEDIUM_PATTERNS)
    low_reasons = _match_patterns(merged_text, LOW_PATTERNS)

    # 1) intent 기준 emergency 최우선
    if "emergency" in intents:
        return {
            "severity": "high",
            "emergency_flag": True,
            "reason": ["emergency_intent"],
            "action": "emergency_redirect"
        }

    # 2) entity emergency flag
    if entities.emergency is True:
        return {
            "severity": "high",
            "emergency_flag": True,
            "reason": ["entity_emergency_flag"],
            "action": "emergency_redirect"
        }

    # 3) 가슴 통증 + 호흡곤란 조합은 high
    if "chest_pain" in medium_reasons and "dyspnea" in high_reasons:
        return {
            "severity": "high",
            "emergency_flag": True,
            "reason": ["chest_pain", "dyspnea"],
            "action": "emergency_redirect"
        }

    # 4) high 카테고리 하나라도 있으면 high
    if high_reasons:
        return {
            "severity": "high",
            "emergency_flag": True,
            "reason": high_reasons,
            "action": "emergency_redirect"
        }

    # 5) medium 카테고리 있으면 medium
    if medium_reasons:
        return {
            "severity": "medium",
            "emergency_flag": False,
            "reason": medium_reasons,
            "action": "priority_hospital_search"
        }

    # 6) intent 기반 low reason 보강
    if "medication_info" in intents:
        return {
            "severity": "low",
            "emergency_flag": False,
            "reason": ["medication_intent"],
            "action": "normal_flow"
        }

    if "hospital_search" in intents and not low_reasons:
        return {
            "severity": "low",
            "emergency_flag": False,
            "reason": ["hospital_search_intent"],
            "action": "normal_flow"
        }

    # 7) low 카테고리 있으면 low
    if low_reasons:
        return {
            "severity": "low",
            "emergency_flag": False,
            "reason": low_reasons,
            "action": "normal_flow"
        }

    # 8) symptom intent만 있으면 low
    if "symptom_inquiry" in intents:
        return {
            "severity": "low",
            "emergency_flag": False,
            "reason": ["symptom_intent"],
            "action": "normal_flow"
        }

    # 9) 기본값
    return {
        "severity": "low",
        "emergency_flag": False,
        "reason": ["default_low"],
        "action": "normal_flow"
    }