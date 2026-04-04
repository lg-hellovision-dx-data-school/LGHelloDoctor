from Opr.otc_data import OTC_KNOWLEDGE


def find_otc_item_by_name(name: str):
    if not name:
        return None

    normalized = name.strip().lower()

    for key, item in OTC_KNOWLEDGE.items():
        aliases = [alias.lower() for alias in item.get("aliases", [])]
        if normalized == key.lower() or normalized in aliases:
            return key, item

    for key, item in OTC_KNOWLEDGE.items():
        aliases = [alias.lower() for alias in item.get("aliases", [])]
        if normalized in key.lower() or any(normalized in alias for alias in aliases):
            return key, item

    return None


def extract_otc_candidates_from_payload(payload) -> list[str]:
    entities = payload.entities
    candidates = []

    if entities.medication_1:
        candidates.append(entities.medication_1)

    if entities.medication_2:
        candidates.append(entities.medication_2)

    if payload.input_text:
        candidates.append(payload.input_text)

    return [c.strip() for c in candidates if c and c.strip()]


def find_otc_from_payload(payload):
    candidates = extract_otc_candidates_from_payload(payload)

    for candidate in candidates:
        result = find_otc_item_by_name(candidate)
        if result:
            return result

    return None