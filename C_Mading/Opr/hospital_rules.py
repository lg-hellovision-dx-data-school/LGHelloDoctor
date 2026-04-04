from typing import Optional


# ---------------------------
# 증상 / 부위 -> 진료과 매핑표
# ---------------------------
SYMPTOM_TO_DEPARTMENT = {
    "무릎 통증": "정형외과",
    "허리 통증": "정형외과",
    "관절 통증": "정형외과",
    "근육통": "정형외과",
    "발목 통증": "정형외과",
    "손목 통증": "정형외과",

    "기침": "내과",
    "가래": "내과",
    "열": "내과",
    "몸살": "내과",
    "감기": "내과",
    "두통": "내과",
    "복통": "내과",
    "소화불량": "내과",
    "설사": "내과",
    "구토": "내과",

    "목 통증": "이비인후과",
    "인후통": "이비인후과",
    "콧물": "이비인후과",
    "코막힘": "이비인후과",
    "귀 통증": "이비인후과",

    "눈 통증": "안과",
    "시야 이상": "안과",

    "피부 발진": "피부과",
    "두드러기": "피부과",
    "가려움": "피부과",

    "가슴 통증": "내과",
    "흉통": "내과",
    "호흡곤란": "내과",

    "우울감": "정신건강의학과",
    "불안": "정신건강의학과",
    "불면": "정신건강의학과",
}

BODY_PART_TO_DEPARTMENT = {
    "무릎": "정형외과",
    "허리": "정형외과",
    "어깨": "정형외과",
    "손목": "정형외과",
    "발목": "정형외과",
    "관절": "정형외과",

    "목": "이비인후과",
    "코": "이비인후과",
    "귀": "이비인후과",

    "눈": "안과",

    "피부": "피부과",

    "가슴": "내과",
    "배": "내과",
    "위": "내과",
    "장": "내과",
    "폐": "내과",

    "마음": "정신건강의학과",
    "정신": "정신건강의학과",
}


def normalize_intents(intents) -> list[str]:
    if intents is None:
        return []
    if isinstance(intents, str):
        return [intents]
    if isinstance(intents, list):
        return intents
    return []


def get_department_keyword(
    symptom: Optional[str] = None,
    body_part: Optional[str] = None,
    intents=None,
    severity: str = "low"
) -> str:
    intents = normalize_intents(intents)

    # 1) 응급이면 응급실 우선
    if severity == "high":
        return "응급실"

    # 2) 약 정보 문의면 약국
    if "medication_info" in intents:
        return "약국"

    # 3) symptom 매핑
    if symptom:
        for key, dept in SYMPTOM_TO_DEPARTMENT.items():
            if key in symptom or symptom in key:
                return dept

    # 4) body_part 매핑
    if body_part:
        for key, dept in BODY_PART_TO_DEPARTMENT.items():
            if key in body_part or body_part in key:
                return dept

    # 5) fallback
    return "내과"