# Opr/hospital_api_kakao.py
import requests
from Opr.config import KAKAO_REST_API_KEY, KAKAO_LOCAL_BASE_URL, DEFAULT_LOCATION


def _headers():
    return {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }


def geocode_location(location: str) -> tuple[float | None, float | None]:
    location = location or DEFAULT_LOCATION

    url = f"{KAKAO_LOCAL_BASE_URL}/search/address.json"
    resp = requests.get(
        url,
        headers=_headers(),
        params={"query": location},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    docs = data.get("documents", [])
    if not docs:
        return None, None

    first = docs[0]
    lng = float(first["x"])
    lat = float(first["y"])
    return lat, lng


def search_places_by_keyword(keyword: str, location: str, radius: int = 3000, size: int = 5) -> list[dict]:
    lat, lng = geocode_location(location)
    if lat is None or lng is None:
        return []

    url = f"{KAKAO_LOCAL_BASE_URL}/search/keyword.json"
    resp = requests.get(
        url,
        headers=_headers(),
        params={
            "query": keyword,
            "x": lng,
            "y": lat,
            "radius": radius,
            "size": size,
            "sort": "distance",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("documents", []):
        results.append({
            "name": item.get("place_name"),
            "distance": f"{item.get('distance')}m" if item.get("distance") else None,
            "phone": item.get("phone"),
            "open": None,
            "address": item.get("road_address_name") or item.get("address_name"),
            "category_name": item.get("category_name"),
            "place_url": item.get("place_url"),
            "source": "kakao",
        })
    return results