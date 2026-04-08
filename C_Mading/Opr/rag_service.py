# Opr/rag_service.py

from Opr.schemas import CInputPayload
from Opr.symptom_info_map import SYMPTOM_INFO_MAP


def _normalize_text(text: str) -> str:
    return (text or "").strip()


def _find_symptom_info(symptom: str = "", body_part: str = ""):
    symptom = _normalize_text(symptom)
    body_part = _normalize_text(body_part)

    # 1) symptom exact / partial match
    if symptom:
        for key, info in SYMPTOM_INFO_MAP.items():
            if key == symptom or key in symptom or symptom in key:
                return key, info

    # 2) body_part fallback
    if body_part:
        body_map = {
            "무릎": "무릎 통증",
            "허리": "허리 통증",
            "어깨": "어깨 통증",
            "목": "인후통",
            "눈": "눈 통증",
            "배": "복통",
            "가슴": "가슴 통증",
        }
        mapped = body_map.get(body_part)
        if mapped and mapped in SYMPTOM_INFO_MAP:
            return mapped, SYMPTOM_INFO_MAP[mapped]

    return None, None


def _build_symptom_rag_text(symptom_key: str, info: dict) -> str:
    department = info.get("department", "관련 진료과")
    disease_candidates = info.get("disease_candidates", [])
    summary = info.get("summary", "")
    caution = info.get("caution", "")

    disease_part = ""
    if disease_candidates:
        disease_part = f" 흔한 관련 가능성으로는 {', '.join(disease_candidates)} 등이 있습니다."

    caution_part = ""
    if caution:
        caution_part = f" {caution}"

    return f"{summary} 우선적으로는 {department} 진료를 고려할 수 있습니다.{disease_part}{caution_part}"


def _handle_medication_rag(payload: CInputPayload) -> str:
    entities = payload.entities
    med1 = entities.medication_1 or ""
    med2 = entities.medication_2 or ""

    if med1 and med2:
        return f"{med1}과 {med2}은 함께 복용 시 주의가 필요할 수 있습니다. 정확한 복용 가능 여부는 약사 또는 의료진 상담이 권장됩니다."

    if med1:
        return f"{med1} 관련 복용 정보가 필요합니다. 제품명과 성분을 함께 확인하면 더 정확한 안내가 가능합니다."

    return "복용 중인 약 정보가 불충분합니다. 약 이름을 다시 확인해 주세요."


def _handle_symptom_rag(payload: CInputPayload) -> str:
    entities = payload.entities
    symptom = entities.symptom or ""
    body_part = entities.body_part or ""

    symptom_key, info = _find_symptom_info(symptom=symptom, body_part=body_part)
    if info:
        return _build_symptom_rag_text(symptom_key, info)

    if symptom:
        return f"{symptom} 관련 진료 정보가 필요합니다. 증상이 지속되거나 심해지면 진료를 고려해 주세요."

    if body_part:
        return f"{body_part} 부위 증상 관련 진료 정보가 필요합니다. 통증이 심해지면 진료를 고려해 주세요."

    return "증상 관련 정보를 찾았습니다."


def run_rag(payload: CInputPayload) -> str:
    intents = payload.intent or []
    if isinstance(intents, str):
        intents = [intents]

    if "medication_info" in intents:
        return _handle_medication_rag(payload)

    if "symptom_inquiry" in intents:
        return _handle_symptom_rag(payload)

    return "관련 정보를 찾지 못했습니다."
