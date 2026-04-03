from Opr.schemas import CInputPayload


# TODO:
# 이 파일은 현재 더미 병원 검색 결과를 반환하는 임시 구현입니다.
# 실제 배포 시 Kakao Local API 또는 병원 검색 API로 교체 예정입니다.
# 교체 대상:
# - location 기반 좌표 변환
# - keyword/category 기반 병원 검색
# - 응답 결과를 HospitalResult 형식으로 매핑


def search_hospital(payload: CInputPayload) -> list:
    intents = payload.intent or []
    entities = payload.entities

    symptom = entities.symptom or ""
    body_part = entities.body_part or ""
    med1 = entities.medication_1 or ""
    med2 = entities.medication_2 or ""

    # TODO:
    # 실제 구현 시 location 값이 있으면 좌표 기반 검색 사용
    # location이 없으면 기본 위치 / 사용자 현재 위치 fallback 가능

    if "hospital_search" in intents:
        if "무릎" in symptom or "무릎" in body_part:
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

        if "가슴" in symptom or "가슴" in body_part:
            return [
                {
                    "name": "강남응급의료센터",
                    "distance": "1.1km",
                    "phone": "119",
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

    if "medication_info" in intents:
        if med1 or med2:
            return [
                {
                    "name": "우리약국",
                    "distance": "0.2km",
                    "phone": "031-345-6789",
                    "open": True,
                    "address": "서울시 강남구 ..."
                }
            ]

    return []