from Opr.schemas import CInputPayload
from Opr.hospital_rules import get_department_keyword
from Opr.hospital_dummy_backend import search_hospital_dummy
from Opr.hospital_api_kakao import search_places_by_keyword
from Opr.hospital_api_hybrid import search_hospital_hybrid
from Opr.config import HOSPITAL_SEARCH_BACKEND, HOSPITAL_SEARCH_SIZE


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

    target = "pharmacy" if keyword == "약국" else "hospital"
    radius = 1500 if target == "pharmacy" else 3000

    return {
        "keyword": keyword,
        "location": location,
        "lat": None,
        "lng": None,
        "target": target,
        "radius": radius
    }


def search_hospital(payload: CInputPayload, severity: str = "low") -> list:
    params = build_search_params(payload, severity=severity)
    keyword = params["keyword"]
    location = params["location"]
    radius = params["radius"]
    target = params["target"]

    if HOSPITAL_SEARCH_BACKEND == "dummy":
     return search_hospital_dummy(keyword)

    if HOSPITAL_SEARCH_BACKEND == "kakao":
     return search_places_by_keyword(
        keyword=keyword,
        location=location,
        radius=radius,
        size=HOSPITAL_SEARCH_SIZE,
    )

    if HOSPITAL_SEARCH_BACKEND == "hybrid":
        try:
            return search_hospital_hybrid(
                keyword=keyword,
                location=location,
                radius=radius,
                size=HOSPITAL_SEARCH_SIZE,
                target=target,
        )
        except Exception as e:
            print("DEBUG hospital hybrid fallback:", e)
            return search_hospital_dummy(keyword)

    return []