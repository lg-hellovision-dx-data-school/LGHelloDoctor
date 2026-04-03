from Opr.schemas import CInputPayload
from Opr.severity import assess_severity
from Opr.rag_service import run_rag
from Opr.hospital_search import search_hospital


# TODO:
# tool_router는 실제 배포 시에도 유지되는 오케스트레이션 레이어입니다.
# 다만 내부에서 호출하는 run_rag / search_hospital / assess_severity는
# 더미 구현에서 실제 API/DB/모델 호출로 교체될 예정입니다.
#
# 연동 시 확인 포인트:
# - intent 형식 (string vs list)
# - entities 누락 여부
# - hospital_results 응답 구조
# - severity 값 체계 (low/medium/high)


def normalize_intents(intents):
    """
    intent가 None / 문자열 / 리스트 등으로 와도 최대한 리스트로 정리
    """
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

    # 1) severity 먼저 판단
    severity_result = assess_severity(payload)
    severity = severity_result["severity"]

    # ---------------------------
    # 0) 완전 fallback
    # ---------------------------
    if not input_text and not intents:
        return {
            "session_id": payload.session_id,
            "rag_context": None,
            "hospital_results": [],
            "severity": "low",
            "severity_detail": severity_result,
            "tool_trace": ["fallback"],
            "tool_result": {
                "source": "none",
                "query": "empty_input"
            }
        }

    # ---------------------------
    # 1) 응급 최우선
    # ---------------------------
    if "emergency" in intents or severity == "high":
        return {
            "session_id": payload.session_id,
            "rag_context": None,
            "hospital_results": [],
            "severity": "high",
            "severity_detail": severity_result,
            "tool_trace": ["emergency"],
            "tool_result": {
                "source": "severity_rule",
                "query": "emergency"
            }
        }

    # ---------------------------
    # 2) 약 정보 문의 -> RAG만
    # ---------------------------
    if "medication_info" in intents:
        if has_medication_info(payload):
            rag_context = run_rag(payload)
            return {
                "session_id": payload.session_id,
                "rag_context": rag_context,
                "hospital_results": [],
                "severity": severity,
                "severity_detail": severity_result,
                "tool_trace": ["rag"],
                "tool_result": {
                    "source": "rag_service",
                    "query": "medication_info"
                }
            }

        # 약 정보 부족
        return {
            "session_id": payload.session_id,
            "rag_context": "약 이름 정보가 부족합니다. 약 이름을 다시 확인해 주세요.",
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["medication_fallback"],
            "tool_result": {
                "source": "none",
                "query": "missing_medication_info"
            }
        }

    # ---------------------------
    # 3) 증상 문의 + 병원 검색 -> RAG + 병원검색
    # ---------------------------
    if "symptom_inquiry" in intents and "hospital_search" in intents:
        if has_symptom_info(payload):
            rag_context = run_rag(payload)
            hospital_results = search_hospital(payload)

            if hospital_results:
                return {
                    "session_id": payload.session_id,
                    "rag_context": rag_context,
                    "hospital_results": hospital_results,
                    "severity": severity,
                    "severity_detail": severity_result,
                    "tool_trace": ["rag", "hospital_search"],
                    "tool_result": {
                        "source": "rag_service+hospital_search",
                        "query": "symptom_inquiry+hospital_search"
                    }
                }

            return {
                "session_id": payload.session_id,
                "rag_context": rag_context,
                "hospital_results": [],
                "severity": severity,
                "severity_detail": severity_result,
                "tool_trace": ["rag", "hospital_search_fallback"],
                "tool_result": {
                    "source": "rag_service",
                    "query": "hospital_not_found"
                }
            }

        # 증상 정보 부족
        return {
            "session_id": payload.session_id,
            "rag_context": "증상 정보가 부족합니다. 아픈 부위를 다시 말씀해 주세요.",
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["symptom_fallback"],
            "tool_result": {
                "source": "none",
                "query": "missing_symptom_info"
            }
        }

    # ---------------------------
    # 4) 병원 검색만 있는 경우
    # ---------------------------
    if "hospital_search" in intents:
        hospital_results = search_hospital(payload)

        if hospital_results:
            return {
                "session_id": payload.session_id,
                "rag_context": None,
                "hospital_results": hospital_results,
                "severity": severity,
                "severity_detail": severity_result,
                "tool_trace": ["hospital_search"],
                "tool_result": {
                    "source": "hospital_search",
                    "query": "hospital_search"
                }
            }

        return {
            "session_id": payload.session_id,
            "rag_context": None,
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["hospital_search_fallback"],
            "tool_result": {
                "source": "none",
                "query": "hospital_not_found"
            }
        }

    # ---------------------------
    # 5) 증상 문의만 있는 경우 -> RAG만
    # ---------------------------
    if "symptom_inquiry" in intents:
        if has_symptom_info(payload):
            rag_context = run_rag(payload)
            return {
                "session_id": payload.session_id,
                "rag_context": rag_context,
                "hospital_results": [],
                "severity": severity,
                "severity_detail": severity_result,
                "tool_trace": ["rag"],
                "tool_result": {
                    "source": "rag_service",
                    "query": "symptom_inquiry"
                }
            }

        return {
            "session_id": payload.session_id,
            "rag_context": "증상 정보가 부족합니다. 아픈 부위를 다시 말씀해 주세요.",
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["symptom_fallback"],
            "tool_result": {
                "source": "none",
                "query": "missing_symptom_info"
            }
        }

    # ---------------------------
    # 6) intent는 있는데 애매한 경우
    # ---------------------------
    if intents:
        return {
            "session_id": payload.session_id,
            "rag_context": "요청을 정확히 이해하지 못했습니다. 증상이나 약 이름을 다시 말씀해 주세요.",
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["fallback"],
            "tool_result": {
                "source": "none",
                "query": "unknown_intent"
            }
        }

    # ---------------------------
    # 7) 최종 fallback
    # ---------------------------
    return {
        "session_id": payload.session_id,
        "rag_context": None,
        "hospital_results": [],
        "severity": severity,
        "severity_detail": severity_result,
        "tool_trace": ["fallback"],
        "tool_result": {
            "source": "none",
            "query": "fallback"
        }
    }