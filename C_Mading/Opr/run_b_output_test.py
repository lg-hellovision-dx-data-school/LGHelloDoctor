from pprint import pprint

from Opr.schemas import CInputPayload, InputEntities
from Opr.tool_router import run_tools
from Opr.test_data_loader import load_json, validate_b_output_items
from Opr.result_saver import save_json, save_json_with_timestamp


DEPARTMENT_WORDS = [
    "내과", "정형외과", "이비인후과", "안과", "피부과",
    "치과", "산부인과", "정신건강의학과", "한의원", "약국",
    "심장내과", "호흡기내과", "신경과", "외과", "비뇨의학과",
]


def normalize_null(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"null", "none", ""}:
        return None
    return value


def looks_like_location_text(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False

    keywords = [
        "서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산",
        "세종", "제주", "강남", "서초", "송파", "근처", "병원", "약국",
        "보건소", "대학병원", "의원",
    ]
    return any(k in value for k in keywords)


def extract_department_hint(text: str) -> str | None:
    if not text:
        return None

    for dept in DEPARTMENT_WORDS:
        if dept in text:
            return dept
    return None


def normalize_intent(raw_intent, query: str, entities: dict, true_intent: str | None = None) -> list[str]:
    """
    B output은 intent가 흔들릴 수 있어서 query/true_intent/엔티티를 함께 보고 보정
    """
    intents = []

    if isinstance(raw_intent, list):
        intents = raw_intent
    elif isinstance(raw_intent, str):
        intents = [raw_intent]
    else:
        intents = []

    query = query or ""
    symptom = normalize_null((entities or {}).get("symptom"))
    location = normalize_null((entities or {}).get("location"))

    # true_intent가 있으면 비교용으로 참고해서 보정
    if true_intent == "emergency":
        return ["emergency"]

    if true_intent == "medication_info":
        return ["medication_info"]

    if true_intent == "hospital_search":
        # 증상도 있으면 복합 intent로
        if symptom:
            return ["symptom_inquiry", "hospital_search"]
        return ["hospital_search"]

    # query 기반 보정
    hospital_keywords = ["어디 있어", "근처", "찾고 있어", "병원", "약국", "보건소", "대학병원", "의원", "한의원"]
    medication_keywords = ["약", "복용", "먹어도", "언제 먹", "같이 먹", "보관", "식전", "식후", "졸려", "부작용"]
    emergency_keywords = ["숨을 못", "쓰러졌", "마비", "캄캄", "화상", "저혈당", "의식", "피를", "가슴이 너무"]

    if any(k in query for k in emergency_keywords):
        return ["emergency"]

    if any(k in query for k in medication_keywords):
        return ["medication_info"]

    if any(k in query for k in hospital_keywords):
        if symptom:
            return ["symptom_inquiry", "hospital_search"]
        return ["hospital_search"]

    # 기본값
    if not intents:
        return ["symptom_inquiry"]

    return intents


def normalize_entities(raw_entities: dict, query: str) -> dict:
    raw_entities = raw_entities or {}

    symptom = normalize_null(raw_entities.get("symptom"))
    body_part = normalize_null(raw_entities.get("body_part"))
    location = normalize_null(raw_entities.get("location"))

    # location이 사실 문장형 잡음이면 제거
    if isinstance(location, str) and not looks_like_location_text(location):
        location = None

    # body_part에 진료과명이 들어온 경우는 실제 body_part로 쓰기 애매하니 제거
    dept_hint_from_body = extract_department_hint(body_part) if isinstance(body_part, str) else None
    if dept_hint_from_body:
        body_part = None

    # query나 symptom에서 진료과 힌트 추출
    dept_hint = extract_department_hint(query) or extract_department_hint(symptom or "")

    # 약 관련 쿼리는 medication_1, medication_2를 추정할 수 없으면 일단 비워둠
    medication_1 = normalize_null(raw_entities.get("medication_1"))
    medication_2 = normalize_null(raw_entities.get("medication_2"))

    return {
        "symptom": symptom,
        "body_part": body_part,
        "location": location or "서울 강남구",
        "medication_1": medication_1,
        "medication_2": medication_2,
        "department_hint": dept_hint,
    }


def b_item_to_c_payload(item: dict, idx: int) -> CInputPayload:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    normalized_entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=normalized_entities,
        true_intent=true_intent,
    )

    emergency_flag = "emergency" in intents

    return CInputPayload(
        session_id=f"b-output-{idx:04d}",
        input_text=query,
        intent=intents,
        entities=InputEntities(
            symptom=normalized_entities["symptom"],
            body_part=normalized_entities["body_part"],
            location=normalized_entities["location"],
            emergency=emergency_flag,
            medication_1=normalized_entities["medication_1"],
            medication_2=normalized_entities["medication_2"],
        ),
    )


def summarize_result(item: dict, result: dict) -> dict:
    rag_text = result.get("rag_context") or ""
    return {
        "session_id": result.get("session_id"),
        "input_query": item.get("query"),
        "raw_intent": item.get("intent"),
        "true_intent": item.get("true_intent"),
        "confidence": item.get("confidence"),
        "severity": result.get("severity"),
        "tool_trace": result.get("tool_trace"),
        "tool_source": result.get("tool_result", {}).get("source"),
        "rag_preview": rag_text[:80],
        "rag_full": rag_text,
        "hospital_count": len(result.get("hospital_results") or []),
    }


def run_b_output_test(
    input_filepath: str = "b_output_1000.json",
    save_prefix: str = "b_output_test_result",
    limit: int | None = None,
    verbose: bool = True,
):
    items = load_json(input_filepath)
    validate_b_output_items(items)

    if limit is not None:
        items = items[:limit]

    all_results = []

    for idx, item in enumerate(items, start=1):
        payload = b_item_to_c_payload(item, idx)
        result = run_tools(payload)
        summary = summarize_result(item, result)
        all_results.append(summary)

        if verbose:
            print(f"\n=== 테스트 {idx} ===")
            pprint(summary)

        # 중간 저장: 50개마다
        if idx % 50 == 0:
            save_json(all_results, f"{save_prefix}_partial.json")
            print(f"\n중간 저장 완료: {idx}건 -> {save_prefix}_partial.json")

    saved_path = save_json_with_timestamp(all_results, prefix=save_prefix)

    if verbose:
        print(f"\n총 테스트 수: {len(all_results)}")
        print(f"결과 저장 완료: {saved_path}")

    return all_results


if __name__ == "__main__":
    run_b_output_test()