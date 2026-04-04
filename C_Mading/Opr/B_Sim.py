from copy import deepcopy
from pprint import pprint

from Opr.schemas import CInputPayload, InputEntities
from Opr.tool_router import run_tools


BASE_CASES = [
    # 시나리오 A - 증상 문의
    {
        "intent": "symptom_inquiry",
        "entities": {"symptom": "무릎 통증", "body_part": "무릎"},
        "query": "무릎이 아파요. 많이 힘들어요",
        "confidence": 0.91,
    },
    # 시나리오 B - 응급
    {
        "intent": "emergency",
        "entities": {"symptom": "흉통 호흡곤란", "body_part": "가슴"},
        "query": "가슴이 아프고 숨이 안 쉬어져요",
        "confidence": 0.97,
    },
    # 시나리오 C - 복약
    {
        "intent": "medication_info",
        "entities": {"medication_1": "혈압약", "medication_2": "감기약"},
        "query": "혈압약이랑 감기약 같이 먹어도 되나요",
        "confidence": 0.88,
    },
    # 시나리오 D - 병원 검색
    {
        "intent": "hospital_search",
        "entities": {"location": None, "symptom": "무릎 통증", "body_part": "무릎"},
        "query": "가까운 정형외과 알려주세요",
        "confidence": 0.95,
    },
]

# 다양하게 돌리기 위한 변형 후보
SYMPTOM_VARIANTS = [
    ("무릎 통증", "무릎", "무릎이 너무 아파요"),
    ("허리 통증", "허리", "허리가 너무 아파요"),
    ("어깨 통증", "어깨", "어깨가 결리고 아파요"),
    ("기침", None, "기침이 계속 나요"),
    ("몸살", None, "몸살이 심하고 열이 좀 있어요"),
    ("두통", None, "머리가 계속 아파요"),
    ("복통", "배", "배가 너무 아파요"),
    ("소화불량", "배", "속이 더부룩하고 소화가 안 돼요"),
    ("설사", "배", "설사가 계속 나와요"),
    ("인후통", "목", "목이 너무 아파요"),
]

EMERGENCY_VARIANTS = [
    ("흉통 호흡곤란", "가슴", "가슴이 아프고 숨이 안 쉬어져요"),
    ("의식 저하", None, "의식이 없어요"),
    ("출혈", None, "피가 너무 많이 나요"),
    ("경련", None, "몸을 떨면서 쓰러졌어요"),
    ("신경학적 이상", None, "말이 어눌하고 한쪽 팔이 안 움직여요"),
]

MEDICATION_VARIANTS = [
    ("tylenol", None, "타이레놀 효과가 뭐야"),
    ("tylenol", None, "타이레놀 몇 번 먹어"),
    ("혈압약", "감기약", "혈압약이랑 감기약 같이 먹어도 되나요"),
    ("당뇨약", "소화제", "당뇨약이랑 소화제 같이 먹어도 될까요"),
    ("이부프로펜", None, "이부프로펜은 어떻게 먹어요"),
    ("감기약", None, "감기약 복용법 알려주세요"),
]

HOSPITAL_SEARCH_VARIANTS = [
    ("무릎 통증", "무릎", "가까운 정형외과 알려주세요"),
    ("기침", None, "근처 내과 찾아주세요"),
    ("인후통", "목", "이비인후과 어디로 가면 될까요"),
    ("눈 통증", "눈", "가까운 안과 알려주세요"),
    ("두드러기", "피부", "피부과 알려주세요"),
]


def make_b_mock_cases(target_count: int = 100):
    cases = []

    # 1) symptom_inquiry
    for idx, (symptom, body_part, query) in enumerate(SYMPTOM_VARIANTS):
        cases.append({
            "intent": "symptom_inquiry",
            "entities": {"symptom": symptom, "body_part": body_part},
            "query": query,
            "confidence": round(0.80 + (idx % 10) * 0.01, 2),
        })

    # 2) emergency
    for idx, (symptom, body_part, query) in enumerate(EMERGENCY_VARIANTS):
        cases.append({
            "intent": "emergency",
            "entities": {"symptom": symptom, "body_part": body_part},
            "query": query,
            "confidence": round(0.93 + (idx % 5) * 0.01, 2),
        })

    # 3) medication_info
    for idx, (med1, med2, query) in enumerate(MEDICATION_VARIANTS):
        cases.append({
            "intent": "medication_info",
            "entities": {"medication_1": med1, "medication_2": med2},
            "query": query,
            "confidence": round(0.84 + (idx % 6) * 0.01, 2),
        })

    # 4) hospital_search
    for idx, (symptom, body_part, query) in enumerate(HOSPITAL_SEARCH_VARIANTS):
        cases.append({
            "intent": "hospital_search",
            "entities": {"location": None, "symptom": symptom, "body_part": body_part},
            "query": query,
            "confidence": round(0.88 + (idx % 5) * 0.01, 2),
        })

    # 5) symptom + hospital_search 복합 의도
    for idx, (symptom, body_part, query) in enumerate(SYMPTOM_VARIANTS):
        cases.append({
            "intent": ["symptom_inquiry", "hospital_search"],
            "entities": {"symptom": symptom, "body_part": body_part, "location": "서울 강남구"},
            "query": f"{query} 어디 가야 하나요?",
            "confidence": round(0.85 + (idx % 10) * 0.01, 2),
        })

    # target_count 맞춰서 반복 확장
    expanded = []
    serial = 1
    while len(expanded) < target_count:
        for base in cases:
            if len(expanded) >= target_count:
                break
            item = deepcopy(base)
            item["case_id"] = f"mock-{serial:03d}"
            expanded.append(item)
            serial += 1

    return expanded[:target_count]


def b_output_to_c_payload(input_from_b: dict) -> CInputPayload:
    entities = input_from_b.get("entities", {}) or {}

    return CInputPayload(
        session_id=input_from_b.get("case_id", "mock-session"),
        input_text=input_from_b.get("query", ""),
        intent=input_from_b.get("intent", []),
        entities=InputEntities(
            symptom=entities.get("symptom"),
            body_part=entities.get("body_part"),
            location=entities.get("location", "서울 강남구"),
            emergency=True if input_from_b.get("intent") == "emergency" else False,
            medication_1=entities.get("medication_1"),
            medication_2=entities.get("medication_2"),
        ),
    )


def summarize_result(result: dict) -> dict:
    return {
        "session_id": result.get("session_id"),
        "severity": result.get("severity"),
        "tool_trace": result.get("tool_trace"),
        "tool_source": result.get("tool_result", {}).get("source"),
        "rag_preview": (result.get("rag_context") or "")[:60],
        "hospital_count": len(result.get("hospital_results") or []),
    }


if __name__ == "__main__":
    test_cases = make_b_mock_cases(100)

    all_results = []

    for i, input_from_b in enumerate(test_cases, start=1):
        print(f"\n=== 테스트 {i}: {input_from_b['intent']} / {input_from_b['case_id']} ===")
        payload = b_output_to_c_payload(input_from_b)
        result = run_tools(payload)
        summary = summarize_result(result)
        all_results.append(summary)
        pprint(summary)

    print("\n총 테스트 수:", len(all_results))

import json

with open("b_sim_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)