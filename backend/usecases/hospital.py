"""Use Case — FindNearbyHospital (증상 → 진료과 → 인근 병원).

domain 규칙(`lookup_department`)만 직접 의존하고, 지도 검색(MapGateway)과
Graph DB(OntologyGateway)는 주입(DI)받는다. → Kakao 를 Naver 로 바꿔도 이 파일은 불변.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from domain.rules import lookup_department


def find_nearby_hospital(
    symptom_text: str,
    lat: float = 37.5012,
    lng: float = 127.0396,
    *,
    map_search: Callable[[str, float, float], List[dict]],
    ontology: Optional[object] = None,
) -> dict:
    """진료과는 domain 규칙으로 우선 매핑, 미매칭 시 ontology(Graph DB)로 폴백.

    map_search·ontology 는 포트(추상)로 주입 — 안쪽(usecase)은 Kakao/rdflib 라는 구현을 모른다.
    """
    dept = lookup_department(symptom_text)
    if dept is not None:
        dept_name = dept[0]
    else:
        onto = ontology.symptom_to_department(symptom_text) if ontology is not None else None
        dept_name = onto[0] if onto else "내과"
    hospitals = sorted(
        [h for h in map_search(dept_name, lat, lng) if h.get("phone")],
        key=lambda x: x["distance"],
    )
    return {"department": dept_name, "nearby": hospitals[:3]}
