from pprint import pprint

from Opr.schemas import CInputPayload, InputEntities
from Opr.tool_router import run_tools
from Opr.test_data_loader import load_json, validate_b_output_items
from Opr.result_saver import save_json, save_json_with_timestamp
import re


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

def infer_department_from_symptom(query: str, symptom: str | None = None, body_part: str | None = None) -> str | None:
    text_parts = [query or "", symptom or "", body_part or ""]
    text = " ".join(text_parts)

    dept_symptom_map = [
        ("이비인후과", ["귀", "삐 소리", "이명", "코피", "목소리", "인후통", "목에 뭔가 걸린", "콧물", "코막힘", "후각", "미각", "목이 아파서 잘 못 먹", "목이 아파서 잘 못 자"]),
        ("정형외과", ["무릎", "허리", "어깨", "손목", "발목", "관절", "디스크", "삐끗", "팔을 못 들", "못 걷", "뼈", "근육", "인대", "척추", "골절", "염좌", "좌골신경통", "오십견", "골다공증", "관절염"]),
        ("피부과", ["두드러기", "피부", "가렵", "빨개", "발진", "염증", "화농", "뾰루지", "여드름", "습진", "건조", "각질", "탈모", "지루성", "아토피", "알레르기", "접촉성", "두피", "사마귀", "티눈", "무좀", "버짐", "옴", "한포진"]),
        ("치과", ["치아", "이가", "잇몸", "사랑니", "턱", "입이 잘 안 벌어", "치통", "입 냄새", "충치", "치석", "치주염", "치근염", "치수염", "치은염", "치조농루", "치조낭종", "치아 파절", "치아 골절", "치아 균열"]),
        ("안과", ["눈", "시야", "캄캄", "충혈", "눈물", "눈이 아파서 잘 못 자", "눈이 아파서 잘 못 먹", "안구건조", "눈부심", "눈꺼풀", "눈 밑이 검어"]),
        ("산부인과", ["생리", "질", "자궁", "임신", "하혈", "유산", "피임", "월경", "갱년기", "유방", "생리통", "생리불순", "분만", "산후", "부인과", "여성호르몬"]),
        ("정신건강의학과", ["불안", "우울", "불면", "공황", "스트레스", "자살", "사회생활", "대인관계", "화병", "분노", "집중력", "기억력", "자해", "환청", "망상"]),
        ("내과", ["위", "속쓰림", "신물", "복통", "설사", "혈압", "갑상선", "당뇨", "열", "몸살", "기침", "가슴 답답", "소화", "배가 아파", "체중", "콜레스테롤", "간 기능", "심장", "호흡기", "신장", "감염"]),
    ]

    for dept, keywords in dept_symptom_map:
        if any(k in text for k in keywords):
            return dept

    return None


def normalize_intent(raw_intent, query: str, entities: dict, true_intent: str | None = None) -> list[str]:
    query = _clean_multiturn_query(query) or query
    """
    B output은 intent가 흔들릴 수 있어서 query/true_intent/엔티티를 함께 보고 보정
    병원검색 오인식을 줄이기 위해 '진료과명 + 검색표현'을 강하게 hospital_search로 보정
    """
    intents = []

    if isinstance(raw_intent, list):
        intents = raw_intent
    elif isinstance(raw_intent, str):
        intents = [raw_intent]
    else:
        intents = []

    query = query or ""
    query_no_space = query.replace(" ", "")
    symptom = normalize_null((entities or {}).get("symptom"))

    # true_intent는 평가용 기준으로 가장 우선
    if true_intent == "emergency":
        return ["emergency"]

    if true_intent == "medication_info":
        return ["medication_info"]

    if true_intent == "hospital_search":
        return ["hospital_search"]

    strong_emergency_keywords = [
        "숨을 못", "숨이 안", "호흡이 안",
        "쓰러졌", "의식이 없", "의식 없어",
        "가슴에 돌", "가슴을 쥐어 짜", "가슴이 찢"
        "마비", "한쪽이 마비", "식은땀이 비 오듯",
        "피를 토", "대변이 검은", "대변이 까만", "대변이 까매",
        "가슴이 너무", "심장이 안뛰", "심장이 뛰질",
        "약을 너무 많이", "약을 과다 복용", "입이 돌아",
        "눈앞이 안 보여", "눈앞이 두개로",
        "혀이 꼬여", "말이 어눌",
    ]

    weak_emergency_keywords = [
        "화상", "저혈당", "의식", "살이 벌어져", "어지럽고 구토",
        "피가 나", "캄캄", "열이 펄펄 끓어", "상처가 붓고 고름"
    ]

    emergency_boost_keywords = [
        "갑자기", "심하게", "너무", "계속", "방금",
        "엄청", "전혀", "못", "안", "심한",
    ]

    medication_keywords = [
        "약", "복용", "먹어도", "언제 먹", "같이 먹", "보관",
        "식전", "식후", "졸려", "부작용", "하루에 몇 번",
    ]

    hospital_keywords = [
        "근처", "어디", "어디예요", "어디 있", "있나요",
        "알려주세요", "알려줘", "찾고 있어요", "찾아주세요",
        "병원", "약국", "보건소", "대학병원", "의원", "한의원",
        "오늘 진료", "야간 진료", "어디 가야", "어디로 가야",
        "진료하는", "잘 보는",
    ]

    dept_hint_in_query = extract_department_hint(query)
    dept_hint_in_symptom = extract_department_hint(symptom or "")

    # 1) 강응급 최우선
    if any(k in query for k in strong_emergency_keywords):
        return ["emergency"]

    # 1-1) 약응급 후보는 보조 신호가 있을 때만 emergency
    weak_hit = any(k in query for k in weak_emergency_keywords)
    boost_count = sum(1 for k in emergency_boost_keywords if k in query)

    if weak_hit and boost_count >= 2:
        return ["emergency"]

    # 2) 약 관련
    if any(k in query for k in medication_keywords):
        return ["medication_info"]

    # 3) 진료과명 + 검색표현 => hospital_search 강제
    # 예: "산부인과 근처에 있나요", "치과 어디 가야 해요", "호흡기내과 병원 알려주세요"
    if dept_hint_in_query and any(k in query for k in hospital_keywords):
        return ["hospital_search"]

    # 띄어쓰기 흔들림 대응
    if dept_hint_in_query and (
        "근처" in query_no_space or
        "병원" in query_no_space or
        "알려" in query_no_space or
        "찾고있어" in query_no_space or
        "어디가야" in query_no_space or
        "잘보는" in query_no_space
    ):
        return ["hospital_search"]

    # 4) 일반 병원검색 표현
    if any(k in query for k in hospital_keywords):
        return ["hospital_search"]

    # 5) 기본값
    return ["symptom_inquiry"]

DEPT_KEYWORDS = [
    "정형외과", "내과", "이비인후과", "피부과", "치과", "안과",
    "산부인과", "정신건강의학과", "응급실", "심장내과",
    "소화기내과", "호흡기내과", "신경과", "비뇨의학과",
]


def _clean_multiturn_query(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    # [1턴], [2턴] 같은 라벨 제거
    text = re.sub(r"\[\d+턴\]\s*", "", text)

    # [AI] 라인 제거
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    user_lines = [line for line in lines if not line.startswith("[AI]")]
    merged = " ".join(user_lines)

    # 줄 분리가 안 된 [AI] 토막도 제거
    merged = re.sub(r"\[AI\][^\[]*", " ", merged)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


def _extract_dept_hint(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None

    for dept in DEPT_KEYWORDS:
        if dept in value:
            return dept
    return None


def _clean_entity_text(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None

    value = _clean_multiturn_query(value)
    value = value[:80].strip()

    if value in {"", "None", "null"}:
        return None
    return value

def normalize_entities(raw_entities: dict, query: str) -> dict:
    raw_entities = raw_entities or {}

    cleaned_query = _clean_multiturn_query(query)

    symptom = _clean_entity_text(raw_entities.get("symptom"))
    body_part = _clean_entity_text(raw_entities.get("body_part"))
    location = _clean_entity_text(raw_entities.get("location"))

    department_hint = None

    # body_part / location 자리에 진료과가 잘못 들어온 경우 보정
    dept_from_body = _extract_dept_hint(body_part)
    dept_from_loc = _extract_dept_hint(location)

    department_hint = dept_from_body or dept_from_loc

    if dept_from_body:
        body_part = None
    if dept_from_loc:
        location = None

    # symptom에 멀티턴 조각이 그대로 들어간 경우 query 기준으로 보정
    if symptom and ("[1턴]" in symptom or "[AI]" in symptom or "[2턴]" in symptom):
        symptom = None

    if not symptom and cleaned_query:
        symptom = cleaned_query[:80]

    return {
        "symptom": symptom,
        "body_part": body_part,
        "location": location,
        "department_hint": department_hint,
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
    input_filepath: str = "b_output_700.json",
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