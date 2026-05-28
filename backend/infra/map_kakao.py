"""Infra — Kakao Local API 어댑터 (domain.ports.MapGateway 구현).

Clean Architecture 가장 바깥(Frameworks & Drivers). domain/usecases 에 의존하지 않으며
표준 `requests` 만 사용한다. Kakao → Naver 등으로 교체할 때 이 파일만 바꾸면 된다.
"""

from __future__ import annotations

import os
from typing import List

import requests

KAKAO_API_KEY = os.environ.get('KAKAO_API_KEY', '')


def search_kakao(dept_name: str, lat: float, lng: float) -> List[dict]:
    """반경 3km 병원(HP8) 키워드 검색. 실패 시 빈 리스트.

    반환: Hospital 호환 dict 리스트 (name·address·phone·distance·navi_url·lat·lng).
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "query": dept_name,
        "x": lng,
        "y": lat,
        "radius": 3000,
        "category_group_code": "HP8",
        "size": 5,
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        docs = res.json().get("documents", [])
        results = []
        for p in docs:
            navi_link = f"https://map.kakao.com/link/to/{p['place_name']},{p['y']},{p['x']}"
            results.append({
                "name": p["place_name"],
                "address": p.get("road_address_name", ""),
                "phone": p.get("phone", ""),
                "distance": int(p.get("distance", 999999)),
                "navi_url": navi_link,
                "lat": p["y"],
                "lng": p["x"],
            })
        return results
    except Exception:
        return []


class KakaoMapGateway:
    """domain.ports.MapGateway 구현체."""

    def nearby(self, category: str, lat: float, lng: float) -> List[dict]:
        return search_kakao(category, lat, lng)
