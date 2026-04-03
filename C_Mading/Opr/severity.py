from Opr.schemas import CInputPayload


# ---------------------------
# Severity 판단용 패턴 사전
# ---------------------------
HIGH_PATTERNS = {
    "dyspnea": [
        "숨이 안 쉬어",
        "숨이 안쉬어",
        "숨이 차",
        "숨 쉬기 힘들",
        "숨이 막혀",
        "숨을 못 쉬"
    ],
    "unconscious": [
        "의식이 없어",
        "정신을 잃",
        "쓰러졌",
        "반응이 없어",
        "깨워도 안 일어나"
    ],
    "bleeding": [
        "피가 많이 나",
        "피가 멈추지 않",
        "피를 계속 흘",
        "출혈이 멈추지 않"
    ],
    "neurologic": [
        "말이 어눌",
        "말을 못 하",
        "한쪽 팔이 안 움직",
        "한쪽 다리가 안 움직",
        "마비",
        "얼굴이 돌아갔"
    ],
    "seizure": [
        "경련",
        "발작",
        "몸을 떨면서 쓰러졌"
    ]
}

MEDIUM_PATTERNS = {
    "chest_pain": [
        "가슴이 너무 아파",
        "가슴이 아파",
        "가슴 통증",
        "가슴이 답답",
        "가슴이 쥐어짜",
        "가슴이 찢어질"
    ],
    "severe_pain": [
        "너무 아파",
        "계속 아파",
        "심하게 아파",
        "참기 힘들",
        "갑자기 아파졌"
    ],
    "fever": [
        "열이 너무",
        "열이 계속",
        "열이 안 내려",
        "몸이 너무 떨"
    ],
    "vomit_diarrhea": [
        "계속 토",
        "설사를 너무",
        "물도 못 마시",
        "배가 너무 아파"
    ],
    "dizziness": [
        "너무 어지러",
        "서있기 힘들",
        "기운이 하나도 없",
        "쓰러질 것 같"
    ],
    "allergy_swelling": [
        "입술이 부었",
        "얼굴이 붓",
        "두드러기"
    ]
}

LOW_PATTERNS = {
    "general_symptom": [
        "무릎이 아파",
        "허리가 아파",
        "기침이 나",
        "목이 아파",
        "열이 조금 나",
        "두통이 있어"
    ]
}

# ---------------------------
# Intent 힌트용 패턴 사전
# 지금은 severity 계산에 직접 쓰지 않음
# 추후 intent 보정/실데이터 분석용으로 활용 가능
# ---------------------------
INTENT_HINT_PATTERNS = {
    "medication_info": [
        "같이 먹어도",
        "약 부작용",
        "언제 먹",
        "복용해도",
        "약 먹는 법"
    ],
    "hospital_search": [
        "어디 병원",
        "정형외과 어디",
        "약국 어디",
        "가까운 병원",
        "근처 약국"
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