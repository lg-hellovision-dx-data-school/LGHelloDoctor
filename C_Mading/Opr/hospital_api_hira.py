# Opr/hospital_api_hira.py
import requests
import xml.etree.ElementTree as ET

from Opr.config import (
    HIRA_API_KEY,
    HIRA_PHARMACY_ENDPOINT,
    HIRA_HOSPITAL_ENDPOINT,
)


def _request_hira_xml(endpoint: str, params: dict) -> str:
    query = {
        "serviceKey": HIRA_API_KEY,
        "pageNo": 1,
        "numOfRows": 10,
        **params,
    }

    resp = requests.get(endpoint, params=query, timeout=8)
    resp.raise_for_status()
    return resp.text


def _safe_text(node, tag_names, default=""):
    for tag in tag_names:
        found = node.find(tag)
        if found is not None and found.text:
            return found.text.strip()
    return default


def _parse_hira_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)

    items = []
    for item in root.findall(".//item"):
        name = _safe_text(item, ["yadmNm", "dutyName", "name"])
        address = _safe_text(item, ["addr", "address"])
        phone = _safe_text(item, ["telno", "phone"])
        x_pos = _safe_text(item, ["XPos", "xPos", "x"])
        y_pos = _safe_text(item, ["YPos", "yPos", "y"])
        cl_cd_nm = _safe_text(item, ["clCdNm", "clCdNmList", "deptNm"])

        items.append({
            "name": name,
            "distance": None,
            "phone": phone or None,
            "open": None,
            "address": address or None,
            "category_name": cl_cd_nm or None,
            "place_url": None,
            "x": x_pos or None,
            "y": y_pos or None,
            "source": "hira",
        })

    return items


def search_hira_pharmacy(
    keyword: str = "",
    x_pos: float | None = None,
    y_pos: float | None = None,
    radius: int = 3000,
    sido_cd: str | None = None,
    sggu_cd: str | None = None,
) -> list[dict]:
    params = {}

    if keyword:
        params["yadmNm"] = keyword
    if x_pos is not None:
        params["xPos"] = x_pos
    if y_pos is not None:
        params["yPos"] = y_pos
    if radius:
        params["radius"] = radius
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sggu_cd:
        params["sgguCd"] = sggu_cd

    xml_text = _request_hira_xml(HIRA_PHARMACY_ENDPOINT, params)
    return _parse_hira_items(xml_text)


def search_hira_hospital(
    keyword: str = "",
    x_pos: float | None = None,
    y_pos: float | None = None,
    radius: int = 3000,
    sido_cd: str | None = None,
    sggu_cd: str | None = None,
) -> list[dict]:
    params = {}

    # 병원정보서비스도 보통 동일한 이름 파라미터 계열을 쓰는 경우가 많아
    # 실제 Swagger의 요청변수명을 확인했다면 여기만 맞춰주면 됨
    if keyword:
        params["yadmNm"] = keyword
    if x_pos is not None:
        params["xPos"] = x_pos
    if y_pos is not None:
        params["yPos"] = y_pos
    if radius:
        params["radius"] = radius
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sggu_cd:
        params["sgguCd"] = sggu_cd

    xml_text = _request_hira_xml(HIRA_HOSPITAL_ENDPOINT, params)
    return _parse_hira_items(xml_text)


def enrich_with_hira(results: list[dict], keyword: str, target: str = "hospital") -> list[dict]:
    """
    Kakao 결과를 HIRA 결과와 병원명 기준으로 느슨하게 보강.
    target: hospital | pharmacy
    """
    if not results:
        return []

    hira_results = []
    try:
        if target == "pharmacy":
            hira_results = search_hira_pharmacy(keyword=keyword)
        else:
            hira_results = search_hira_hospital(keyword=keyword)
    except Exception:
        return results

    # 병원명 느슨한 매칭
    hira_by_name = {}
    for h in hira_results:
        if h.get("name"):
            hira_by_name[h["name"]] = h

    enriched = []
    for item in results:
        enriched_item = dict(item)
        hira_item = hira_by_name.get(item.get("name", ""))

        if hira_item:
            enriched_item["phone"] = hira_item.get("phone") or enriched_item.get("phone")
            enriched_item["address"] = hira_item.get("address") or enriched_item.get("address")
            enriched_item["category_name"] = hira_item.get("category_name") or enriched_item.get("category_name")
            enriched_item["source"] = "kakao+hira"
        else:
            enriched_item["source"] = "kakao"

        enriched.append(enriched_item)

    return enriched