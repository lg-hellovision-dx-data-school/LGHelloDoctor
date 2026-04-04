from Opr.schemas import CInputPayload
from Opr.hospital_rules import get_department_keyword
from Opr.hospital_dummy_backend import search_hospital_dummy


# TODO:
# 이 파일은 병원/약국 검색의 오케스트레이션 레이어입니다.
# 현재는 더미 백엔드(search_hospital_dummy)를 사용하지만,
# 실제 배포 시 Kakao Local API 또는 병원 검색 API 호출로 교체 예정입니다.
# 교체 대상:
# - location 기반 좌표 변환
# - keyword/category 기반 병원 검색
# - 응답 결과를 HospitalResult 형식으로 매핑


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

    return search_hospital_dummy(keyword)