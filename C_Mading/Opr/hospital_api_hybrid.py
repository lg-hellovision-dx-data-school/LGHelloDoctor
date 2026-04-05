# Opr/hospital_api_hybrid.py
from Opr.hospital_api_kakao import search_places_by_keyword
from Opr.hospital_api_hira import enrich_with_hira


def search_hospital_hybrid(
    keyword: str,
    location: str,
    radius: int = 3000,
    size: int = 5,
    target: str = "hospital",
) -> list[dict]:
    kakao_results = search_places_by_keyword(
        keyword=keyword,
        location=location,
        radius=radius,
        size=size,
    )

    if not kakao_results:
        return []

    return enrich_with_hira(kakao_results, keyword=keyword, target=target)