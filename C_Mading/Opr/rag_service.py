from Opr.schemas import CInputPayload


# TODO:
# 이 파일은 현재 더미 RAG 결과를 반환하는 임시 구현입니다.
# 실제 배포 시 아래 로직은 벡터DB(예: ChromaDB) + 검색 파이프라인으로 교체 예정입니다.
# 교체 대상:
# - symptom / medication 기반 query 생성
# - 문서 검색
# - rerank
# - 최종 rag_context 생성


def run_rag(payload: CInputPayload) -> str:
    intents = payload.intent or []
    entities = payload.entities

    symptom = entities.symptom or ""
    body_part = entities.body_part or ""
    med1 = entities.medication_1 or ""
    med2 = entities.medication_2 or ""

    # TODO:
    # 실제 구현 시 medication_info / symptom_inquiry 별 query template 분리 가능
    # ex) medication_info -> 약물 병용 질의
    # ex) symptom_inquiry -> 증상-진료과 매핑 질의

    if "medication_info" in intents:
        if med1 and med2:
            return f"{med1}과 {med2}은 함께 복용 시 주의가 필요할 수 있습니다."
        return "복용 중인 약 정보가 불충분합니다. 약 이름을 다시 확인해 주세요."

    if "symptom_inquiry" in intents:
        if "무릎" in symptom or "무릎" in body_part:
            return "무릎 통증은 정형외과 진료가 가능합니다."
        if "가슴" in symptom or "가슴" in body_part:
            return "가슴 통증은 응급 여부 확인이 중요합니다."
        if symptom:
            return f"{symptom} 관련 진료 정보가 필요합니다."
        return "증상 관련 정보를 찾았습니다."

    return "관련 정보를 찾지 못했습니다."