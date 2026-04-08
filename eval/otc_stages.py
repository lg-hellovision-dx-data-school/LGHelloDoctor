"""④ 복약 안내 — OTC 약 이름 인식 및 정보 제공 정확도 평가"""

import requests
import json

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "exaone3.5:2.4b"

# C_Mading/Opr/otc_data.py의 OTC_KNOWLEDGE를 평가용으로 재정의
OTC_KNOWLEDGE = {
    "tylenol":      ["타이레놀", "아세트아미노펜", "acetaminophen", "paracetamol"],
    "ibuprofen":    ["이부프로펜", "덱시부프로펜", "부루펜", "애드빌"],
    "cold_medicine":["종합감기약", "감기약", "판콜", "콜대원", "테라플루"],
    "digestive":    ["소화제", "제산제", "속쓰림약", "겔포스", "개비스콘", "베아제", "훼스탈"],
    "antidiarrheal":["지사제", "설사약", "로페라마이드", "스멕타"],
}

OTC_INFO = {
    "tylenol": {
        "category": "해열진통제",
        "effect": "열과 두통, 몸살, 치통 같은 통증 완화",
        "caution": "다른 감기약과 성분 중복 주의, 음주 시 복용 주의",
    },
    "ibuprofen": {
        "category": "소염진통제",
        "effect": "두통, 근육통, 생리통 등 염증성 통증 완화",
        "caution": "위장 약한 경우·신장 질환자 주의, 식후 복용 권장",
    },
    "cold_medicine": {
        "category": "종합감기약",
        "effect": "콧물·기침·몸살 등 복합 감기 증상 완화",
        "caution": "졸음 유발 가능, 타이레놀과 성분 중복 주의",
    },
    "digestive": {
        "category": "소화제·제산제",
        "effect": "더부룩함·속쓰림·과식 후 불편감 완화",
        "caution": "다른 약과 복용 간격 필요",
    },
    "antidiarrheal": {
        "category": "지사제",
        "effect": "갑작스러운 설사·배탈 증상 완화",
        "caution": "탈수 방지를 위해 충분한 수분 섭취 필요",
    },
}


def find_otc(query: str):
    """쿼리에서 OTC 약 이름 인식 → 매칭된 모든 (key, info) 리스트 반환"""
    query_lower = query.lower()
    found = {}  # key 중복 방지
    for key, aliases in OTC_KNOWLEDGE.items():
        for alias in aliases:
            if alias.lower() in query_lower:
                found[key] = OTC_INFO[key]
                break
    return list(found.items())  # [(key, info), ...], 없으면 []


def build_otc_response(matches: list) -> str:
    """매칭된 약 목록으로 안내 텍스트 생성"""
    if not matches:
        return "약 이름을 찾지 못했습니다."
    lines = []
    for key, info in matches:
        lines.append(
            f"[{info['category']}] {OTC_KNOWLEDGE[key][0]}\n"
            f"  효능: {info['effect']}\n"
            f"  주의: {info['caution']}"
        )
    if len(matches) > 1:
        lines.append("※ 여러 약을 함께 복용할 경우 약사 또는 의료진 상담을 권장합니다.")
    return "\n\n".join(lines)


def llm_judge_interaction(drug_keys: list, query: str) -> str:
    """Ollama(EXAONE 3.5)로 약물 상호작용 판단"""
    drug_names = [OTC_KNOWLEDGE[k][0] for k in drug_keys]
    drug_infos = "\n".join(
        f"- {OTC_KNOWLEDGE[k][0]}: {OTC_INFO[k]['caution']}" for k in drug_keys
    )
    prompt = (
        f"다음 약들을 함께 복용해도 되는지 판단해주세요.\n"
        f"약물: {', '.join(drug_names)}\n"
        f"약물별 주의사항:\n{drug_infos}\n\n"
        f"질문: {query}\n\n"
        f"안전/주의/위험 여부를 2~3문장으로 간결하게 한국어로 답해주세요."
    )
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        return resp.json().get("response", "판단 결과를 가져올 수 없습니다.")
    except Exception as e:
        return f"(Ollama 연결 실패: {e})"


def build_otc_response_v2(matches: list, query: str) -> str:
    """복합 약은 Ollama LLM으로 상호작용 판단 + 면책 문구 추가"""
    if not matches:
        return "약 이름을 찾지 못했습니다."
    lines = []
    for key, info in matches:
        lines.append(
            f"[{info['category']}] {OTC_KNOWLEDGE[key][0]}\n"
            f"  효능: {info['effect']}\n"
            f"  주의: {info['caution']}"
        )
    if len(matches) > 1:
        drug_keys = [k for k, _ in matches]
        llm_result = llm_judge_interaction(drug_keys, query)
        lines.append(f"[AI 상호작용 판단]\n{llm_result}")
    lines.append("※ 정확한 복용은 약사/의사 상담을 권장합니다.")
    return "\n\n".join(lines)


# ── 평가 샘플 ──────────────────────────────────────────────────────────────────
# true_keys: 리스트로 표기 (복합 질문은 여러 약 모두 인식해야 정답)
OTC_SAMPLES = [
    {"query": "타이레놀 먹어도 되나요",               "true_keys": ["tylenol"]},
    {"query": "아세트아미노펜 부작용이 뭐예요",         "true_keys": ["tylenol"]},
    {"query": "부루펜이랑 타이레놀 같이 먹어도 돼요",   "true_keys": ["ibuprofen", "tylenol"]},  # 복합
    {"query": "이부프로펜 언제 먹어요",                "true_keys": ["ibuprofen"]},
    {"query": "종합감기약 졸려요",                     "true_keys": ["cold_medicine"]},
    {"query": "판콜 하루 몇 번 먹어요",                "true_keys": ["cold_medicine"]},
    {"query": "소화제 식전 식후 언제 먹나요",           "true_keys": ["digestive"]},
    {"query": "겔포스 효과 있나요",                    "true_keys": ["digestive"]},
    {"query": "설사가 심한데 지사제 먹어도 되나요",     "true_keys": ["antidiarrheal"]},
    {"query": "스멕타 어떻게 먹어요",                  "true_keys": ["antidiarrheal"]},
]


# ── 상호작용 평가 샘플 ──────────────────────────────────────────────────────────
INTERACTION_SAMPLES = [
    {
        "keys": ["ibuprofen", "tylenol"],
        "query": "부루펜이랑 타이레놀 같이 먹어도 돼요",
        "true_safe": True,   # 다른 계열 진통제 — 병용 가능
        "safe_kw":   ["가능", "됩니다", "괜찮", "안전", "병용"],
        "unsafe_kw": ["위험", "절대", "금지"],
    },
    {
        "keys": ["tylenol", "cold_medicine"],
        "query": "타이레놀이랑 종합감기약 같이 먹어도 되나요",
        "true_safe": False,  # 아세트아미노펜 성분 중복 위험
        "safe_kw":   ["가능", "안전"],
        "unsafe_kw": ["주의", "위험", "중복", "삼가", "초과"],
    },
    {
        "keys": ["ibuprofen", "antidiarrheal"],
        "query": "이부프로펜이랑 지사제 같이 먹어도 되나요",
        "true_safe": True,   # 병용 가능, 위장 부담 주의 정도
        "safe_kw":   ["가능", "됩니다", "괜찮", "안전"],
        "unsafe_kw": ["위험", "절대", "금지"],
    },
]


def eval_otc_interaction():
    """LLM 약물 상호작용 판단 정확도 평가 (Ollama 호출)"""
    hits = 0
    results = []
    for s in INTERACTION_SAMPLES:
        llm_resp = llm_judge_interaction(s["keys"], s["query"])
        has_safe   = any(kw in llm_resp for kw in s["safe_kw"])
        has_unsafe = any(kw in llm_resp for kw in s["unsafe_kw"])
        if s["true_safe"]:
            correct = has_safe and not has_unsafe
        else:
            correct = has_unsafe
        if correct:
            hits += 1
        results.append({
            "query":      s["query"],
            "true_safe":  s["true_safe"],
            "llm_resp":   llm_resp[:80] + "..." if len(llm_resp) > 80 else llm_resp,
            "correct":    correct,
        })
    return hits, len(INTERACTION_SAMPLES), results


def eval_otc_recognition():
    """OTC 약 이름 인식 정확도 평가 (복합 질문: 모든 약 인식 시 정답)"""
    hits = 0
    results = []
    for s in OTC_SAMPLES:
        matches = find_otc(s["query"])
        pred_keys = set(k for k, _ in matches)
        true_keys = set(s["true_keys"])
        correct = (pred_keys == true_keys)
        if correct:
            hits += 1
        results.append({
            "query":     s["query"],
            "true_keys": sorted(true_keys),
            "pred_keys": sorted(pred_keys),
            "correct":   correct,
        })
    return hits, len(OTC_SAMPLES), results
