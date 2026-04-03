from Opr.schemas import CInputPayload


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
    "불면": "정신건강의학과"
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
    "정신": "정신건강의학과"
}


# TODO:
# 이 파일은 현재 더미 병원 검색 결과를 반환하는 임시 구현입니다.
# 실제 배포 시 Kakao Local API 또는 병원 검색 API로 교체 예정입니다.
# 교체 대상:
# - location 기반 좌표 변환
# - keyword/category 기반 병원 검색
# - 응답 결과를 HospitalResult 형식으로 매핑


def get_department_keyword(
    symptom: str = None,
    body_part: str = None,
    intents=None,
    severity: str = "low"
) -> str:
    if intents is None:
        intents = []

    if isinstance(intents, str):
        intents = [intents]

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


def build_search_params(payload: CInputPayload, severity: str = "low") -> dict:
    entities = payload.entities
    symptom = entities.symptom
    body_part = entities.body_part
    location = entities.location
    intents = payload.intent or []

    keyword = get_department_keyword(
        symptom=symptom,
        body_part=body_part,
        intents=intents,
        severity=severity
    )

    category = "pharmacy" if keyword == "약국" else "hospital"
    radius = 1500 if keyword == "약국" else 3000

    return {
        "keyword": keyword,
        "location": location,
        "lat": None,
        "lng": None,
        "category": category,
        "radius": radius
    }


def search_hospital(payload: CInputPayload, severity: str = "low") -> list:
    params = build_search_params(payload, severity=severity)
    keyword = params["keyword"]

    # TODO:
    # 실제 구현 시 location 값이 있으면 좌표 기반 검색 사용
    # location이 없으면 기본 위치 / 사용자 현재 위치 fallback 가능

    if keyword == "응급실":
        return [
            {
                "name": "강남응급의료센터",
                "distance": "1.1km",
                "phone": "119",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "정형외과":
        return [
            {
                "name": "서울정형외과",
                "distance": "0.3km",
                "phone": "031-123-4567",
                "open": True,
                "address": "서울시 강남구 ..."
            },
            {
                "name": "연세관절클리닉",
                "distance": "0.8km",
                "phone": "031-234-5678",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "내과":
        return [
            {
                "name": "강남내과",
                "distance": "0.5km",
                "phone": "031-111-2222",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "이비인후과":
        return [
            {
                "name": "강남이비인후과",
                "distance": "0.7km",
                "phone": "031-222-3333",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "안과":
        return [
            {
                "name": "밝은안과",
                "distance": "0.9km",
                "phone": "031-333-4444",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "피부과":
        return [
            {
                "name": "맑은피부과",
                "distance": "0.6km",
                "phone": "031-444-5555",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "정신건강의학과":
        return [
            {
                "name": "마음정신건강의학과",
                "distance": "1.2km",
                "phone": "031-555-6666",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "약국":
        return [
            {
                "name": "우리약국",
                "distance": "0.2km",
                "phone": "031-345-6789",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    return [
        {
            "name": "가까운 병원",
            "distance": "1.0km",
            "phone": "031-000-0000",
            "open": True,
            "address": "서울시 ..."
        }
    ]