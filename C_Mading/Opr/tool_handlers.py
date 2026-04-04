from Opr.rag_service import run_rag
from Opr.hospital_search import search_hospital
from Opr.otc_knowledge import find_otc_from_payload, build_otc_response_text


def build_empty_response(payload, severity_result):
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


def build_emergency_response(payload, severity_result):
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


def handle_medication_info(payload, severity, severity_result, has_medication_info):
    print("DEBUG medication_1:", payload.entities.medication_1)
    print("DEBUG medication_2:", payload.entities.medication_2)
    print("DEBUG input_text:", payload.input_text)

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

    otc_match = find_otc_from_payload(payload)
    print("DEBUG otc_match:", otc_match)

    if otc_match:
        _, item = otc_match
        otc_text = build_otc_response_text(item)

        return {
            "session_id": payload.session_id,
            "rag_context": otc_text,
            "hospital_results": [],
            "severity": severity,
            "severity_detail": severity_result,
            "tool_trace": ["otc_knowledge"],
            "tool_result": {
                "source": "otc_knowledge",
                "query": "medication_info_otc"
            }
        }

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


def handle_symptom_and_hospital(payload, severity, severity_result, has_symptom_info):
    if has_symptom_info(payload):
        rag_context = run_rag(payload)
        hospital_results = search_hospital(payload, severity=severity)

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


def handle_hospital_search_only(payload, severity, severity_result):
    hospital_results = search_hospital(payload, severity=severity)

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


def handle_symptom_only(payload, severity, severity_result, has_symptom_info):
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


def build_unknown_intent_response(payload, severity, severity_result):
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


def build_final_fallback_response(payload, severity, severity_result):
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