from Opr.schemas import CInputPayload
from Opr.severity import assess_severity
from Opr.tool_handlers import (
    build_empty_response,
    build_emergency_response,
    handle_medication_info,
    handle_symptom_and_hospital,
    handle_hospital_search_only,
    handle_symptom_only,
    build_unknown_intent_response,
    build_final_fallback_response,
)

print("LOADED tool_router:", __file__)


# TODO:
# tool_router는 실제 배포 시에도 유지되는 오케스트레이션 레이어입니다.
# 내부 분기별 처리 로직은 tool_handlers로 분리하여 유지보수성을 높였습니다.


def normalize_intents(intents):
    if intents is None:
        return []
    if isinstance(intents, str):
        return [intents]
    if isinstance(intents, list):
        return intents
    return []


def has_symptom_info(payload: CInputPayload) -> bool:
    entities = payload.entities
    return bool(entities.symptom or entities.body_part)


def has_medication_info(payload: CInputPayload) -> bool:
    entities = payload.entities
    return bool(entities.medication_1 and entities.medication_2)


def run_tools(payload: CInputPayload) -> dict:
    intents = normalize_intents(payload.intent)
    input_text = payload.input_text or ""

    severity_result = assess_severity(payload)
    severity = severity_result["severity"]

    # 0) 완전 fallback
    if not input_text and not intents:
        return build_empty_response(payload, severity_result)

    # 1) 응급 최우선
    if "emergency" in intents or severity == "high":
        return build_emergency_response(payload, severity_result)

    # 2) 약 정보 문의
    if "medication_info" in intents:
        return handle_medication_info(
            payload=payload,
            severity=severity,
            severity_result=severity_result,
            has_medication_info=has_medication_info,
        )

    # 3) 증상 문의 + 병원 검색
    if "symptom_inquiry" in intents and "hospital_search" in intents:
        return handle_symptom_and_hospital(
            payload=payload,
            severity=severity,
            severity_result=severity_result,
            has_symptom_info=has_symptom_info,
        )

    # 4) 병원 검색만 있는 경우
    if "hospital_search" in intents:
        return handle_hospital_search_only(
            payload=payload,
            severity=severity,
            severity_result=severity_result,
        )

    # 5) 증상 문의만 있는 경우
    if "symptom_inquiry" in intents:
        return handle_symptom_only(
            payload=payload,
            severity=severity,
            severity_result=severity_result,
            has_symptom_info=has_symptom_info,
        )

    # 6) intent는 있는데 애매한 경우
    if intents:
        return build_unknown_intent_response(payload, severity, severity_result)

    # 7) 최종 fallback
    return build_final_fallback_response(payload, severity, severity_result)