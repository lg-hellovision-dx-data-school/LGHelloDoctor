# 실데이터 들어오면 데이터내용 재수정 예정!

def search_hospital_dummy(keyword: str) -> list:
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
                "distance": "1.0km",
                "phone": "031-555-6666",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    if keyword == "약국":
        return [
            {
                "name": "강남메디약국",
                "distance": "0.2km",
                "phone": "031-777-8888",
                "open": True,
                "address": "서울시 강남구 ..."
            },
            {
                "name": "행복약국",
                "distance": "0.4km",
                "phone": "031-888-9999",
                "open": True,
                "address": "서울시 강남구 ..."
            }
        ]

    return []