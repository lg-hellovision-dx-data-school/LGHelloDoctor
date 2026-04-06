# Opr/rag_versions.py

from Opr.run_b_output_test import normalize_intent, normalize_entities, infer_department_from_symptom
from Opr.chroma_client import get_medical_collection


def _preview_text(text: str, max_len: int = 180) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def _debug_print_chroma_hits(query: str, hits: list[dict], tag: str = "V2"):
    print("\n" + "=" * 100)
    print(f"[{tag}] query = {query}")

    if not hits:
        print("No chroma hits")
        print("=" * 100)
        return

    for i, hit in enumerate(hits, start=1):
        dist = hit.get("distance")
        sim = None
        if isinstance(dist, (int, float)):
            sim = 1 - dist  # cosine distance라고 가정한 직관용 참고값

        print("-" * 100)
        print(f"rank       : {i}")
        print(f"id         : {hit.get('id')}")
        print(f"department : {hit.get('department')}")
        print(f"distance   : {dist}")
        if sim is not None:
            print(f"sim~(1-d)  : {sim:.6f}")
        print(f"metadata   : {hit.get('metadata')}")
        print(f"preview    : {_preview_text(hit.get('document'))}")

    print("=" * 100)


def _build_chroma_hits(result: dict) -> list[dict]:
    ids = result.get("ids", [[]])[0] if result.get("ids") else []
    docs = result.get("documents", [[]])[0] if result.get("documents") else []
    metadatas = result.get("metadatas", [[]])[0] if result.get("metadatas") else []
    distances = result.get("distances", [[]])[0] if result.get("distances") else []

    hits = []
    max_len = max(len(docs), len(metadatas), len(distances), len(ids)) if any([docs, metadatas, distances, ids]) else 0

    for i in range(max_len):
        meta = metadatas[i] if i < len(metadatas) else {}
        hit = {
            "rank": i + 1,
            "id": ids[i] if i < len(ids) else None,
            "document": docs[i] if i < len(docs) else None,
            "distance": distances[i] if i < len(distances) else None,
            "metadata": meta,
            "department": meta.get("department") if isinstance(meta, dict) else None,
        }
        hits.append(hit)

    return hits


def _rewrite_query_for_chroma(query: str, entities: dict) -> str:
    """
    너무 과하지 않게 증상/부위 힌트를 붙여서 Chroma 검색용 쿼리를 보강
    """
    symptom = (entities.get("symptom") or "").strip()
    body_part = (entities.get("body_part") or "").strip()

    extra = []
    if symptom:
        extra.append(symptom)
    if body_part and body_part not in symptom:
        extra.append(body_part)

    if not extra:
        return query

    extra_text = " ".join(extra)
    return f"{query} {extra_text} 관련 진료과"


def search_chroma_department(query: str, n_results: int = 3, debug: bool = False) -> dict:
    collection = get_medical_collection()

    result = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    hits = _build_chroma_hits(result)

    if debug:
        _debug_print_chroma_hits(query, hits, tag="V2-Chroma")

    if not hits:
        return {
            "predicted_dept": None,
            "top_doc": None,
            "top_distance": None,
            "top_hits": [],
        }

    top_hit = hits[0]

    return {
        "predicted_dept": top_hit.get("department"),
        "top_doc": top_hit.get("document"),
        "top_distance": top_hit.get("distance"),
        "top_hits": hits,
    }

# ================================
# V3 / V4 helper functions
# ================================

DEPT_CANDIDATES = [
    "이비인후과",
    "정형외과",
    "피부과",
    "치과",
    "안과",
    "산부인과",
    "정신건강의학과",
    "내과",
]

DEPT_ALIAS_MAP = {
    "호흡기내과": "내과",
    "소화기내과": "내과",
    "심장내과": "내과",
    "신장내과": "내과",
    "내분비내과": "내과",
    "류마티스내과": "내과",
}


def _normalize_korean_medical_phrase(text: str) -> str:
    text = (text or "").strip()

    replacements = [
        ("이가 시려서 못 먹겠어요", "치아 시림 치통"),
        ("잇몸에서 피가 나요", "잇몸 출혈"),
        ("사랑니가 아파요", "사랑니 통증"),
        ("턱이 아프고 입이 잘 안 벌어져요", "턱 통증 입 벌리기 어려움"),
        ("귀에서 삐 소리가 나요", "이명 귀 삐 소리"),
        ("목소리가 쉬었어요", "목소리 쉼 인후통"),
        ("목에 뭔가 걸린 것 같아요", "목 이물감 인후통"),
        ("코피가 자꾸 나요", "코피 비출혈"),
        ("피부가 너무 가렵고 빨개요", "피부 가려움 발진"),
        ("두드러기가 났어요", "두드러기 피부 발진"),
        ("무릎이 왜 이러지", "무릎 통증"),
        ("무릎이 아파요", "무릎 통증"),
        ("허리 디스크인 것 같아요", "허리 디스크 통증"),
        ("어깨가 너무 아파서 팔을 못 들겠어요", "어깨 통증 팔 들기 어려움"),
        ("어깨가 올라가지를 않아요", "어깨 통증 팔 들기 어려움"),
        ("손목이 저리고 아파요", "손목 저림 통증"),
        ("발목이 삐끗했어요", "발목 염좌 삐끗"),
        ("발목이 부었어요", "발목 부종 통증"),
        ("위가 쓰리고 신물이 올라와요", "속쓰림 신물 위장"),
        ("갑상선이 이상한 것 같아요", "갑상선 이상"),
        ("혈압이 자꾸 높아요", "고혈압 혈압 상승"),
        ("열이 38도 이상 나요", "고열 발열"),
    ]

    for src, dst in replacements:
        if src in text:
            text = text.replace(src, dst)

    filler_words = [
        "헬로비", "저기요", "있잖아요", "그런데", "혹시", "지금", "방금",
        "요즘", "계속", "갑자기", "며칠 전부터", "아이고"
    ]
    for w in filler_words:
        text = text.replace(w, " ")

    return " ".join(text.split())


def _rewrite_query_for_v3(query: str, entities: dict) -> str:
    clean_query = _normalize_korean_medical_phrase(query)

    symptom = (entities.get("symptom") or "").strip()
    body_part = (entities.get("body_part") or "").strip()

    pieces = []
    if clean_query:
        pieces.append(clean_query)
    if symptom and symptom not in clean_query:
        pieces.append(symptom)
    if body_part and body_part not in clean_query:
        pieces.append(body_part)

    rewritten = " ".join(pieces).strip()
    return f"{rewritten or query} 관련 진료과"


def _normalize_dept_name(dept: str | None) -> str | None:
    if not dept:
        return None
    return DEPT_ALIAS_MAP.get(dept, dept)


def _rule_dept_from_entities(query: str, entities: dict) -> str | None:
    return infer_department_from_symptom(
        query=query,
        symptom=entities.get("symptom"),
        body_part=entities.get("body_part"),
    )


def _get_chroma_result_with_rewrite(query: str, entities: dict, debug: bool = False) -> dict:
    rewritten_query = _rewrite_query_for_v3(query, entities)
    chroma_result = search_chroma_department(
        query=rewritten_query,
        n_results=3,
        debug=debug,
    )
    chroma_result["rewritten_query"] = rewritten_query
    chroma_result["predicted_dept"] = _normalize_dept_name(chroma_result.get("predicted_dept"))
    return chroma_result


def _score_rule_dept(rule_dept: str | None, entities: dict) -> float:
    if not rule_dept:
        return 0.0

    score = 0.55

    symptom = (entities.get("symptom") or "").strip()
    body_part = (entities.get("body_part") or "").strip()
    department_hint = (entities.get("department_hint") or "").strip()

    if symptom:
        score += 0.20
    if body_part:
        score += 0.15
    if department_hint:
        score += 0.10

    return min(score, 0.95)


def _score_chroma_result(chroma_result: dict) -> float:
    dept = _normalize_dept_name(chroma_result.get("predicted_dept"))
    dist = chroma_result.get("top_distance")
    hits = chroma_result.get("top_hits", [])

    if not dept or dist is None:
        return 0.0

    # distance가 작을수록 가산
    if dist <= 0.08:
        score = 0.92
    elif dist <= 0.12:
        score = 0.84
    elif dist <= 0.18:
        score = 0.74
    elif dist <= 0.25:
        score = 0.62
    elif dist <= 0.35:
        score = 0.50
    else:
        score = 0.35

    # top1과 top2 부서가 같으면 약간 신뢰 가산
    if len(hits) >= 2:
        top1 = _normalize_dept_name(hits[0].get("department"))
        top2 = _normalize_dept_name(hits[1].get("department"))
        if top1 and top1 == top2:
            score += 0.05

    return min(score, 0.97)


def _choose_hybrid_dept(dept_hint: str | None, rule_dept: str | None, chroma_result: dict, entities: dict) -> tuple[str | None, dict]:
    dept_hint = _normalize_dept_name(dept_hint)
    rule_dept = _normalize_dept_name(rule_dept)

    chroma_dept = _normalize_dept_name(chroma_result.get("predicted_dept"))
    rule_score = _score_rule_dept(rule_dept, entities)
    chroma_score = _score_chroma_result(chroma_result)

    debug_info = {
        "dept_hint": dept_hint,
        "rule_dept": rule_dept,
        "rule_score": rule_score,
        "chroma_dept": chroma_dept,
        "chroma_score": chroma_score,
    }

    if dept_hint:
        return dept_hint, debug_info

    if not rule_dept and not chroma_dept:
        return None, debug_info

    if rule_dept and not chroma_dept:
        return rule_dept, debug_info
    if chroma_dept and not rule_dept:
        return chroma_dept, debug_info

    if rule_dept == chroma_dept:
        return rule_dept, debug_info

    if chroma_score >= 0.84 and chroma_score >= rule_score + 0.20:
        return chroma_dept, debug_info

    return rule_dept, debug_info

def _base_predict(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    if predicted_intent in {"emergency", "medication_info"}:
        predicted_dept = None
    else:
        predicted_dept = (
            entities.get("department_hint")
            or infer_department_from_symptom(
                query=query,
                symptom=entities.get("symptom"),
                body_part=entities.get("body_part"),
            )
        )

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
    }

def _tokenize_koreanish(text: str) -> list[str]:
    text = _normalize_korean_medical_phrase(text)
    tokens = [tok.strip() for tok in text.replace(",", " ").split() if tok.strip()]
    return tokens


def _compute_overlap_score(query: str, doc: str, entities: dict) -> float:
    query_tokens = set(_tokenize_koreanish(query))
    doc_tokens = set(_tokenize_koreanish(doc or ""))

    symptom = (entities.get("symptom") or "").strip()
    body_part = (entities.get("body_part") or "").strip()

    score = 0.0

    if not query_tokens or not doc_tokens:
        return score

    overlap = query_tokens & doc_tokens
    if overlap:
        score += min(0.30, 0.06 * len(overlap))

    if symptom and symptom in (doc or ""):
        score += 0.20

    if body_part and body_part in (doc or ""):
        score += 0.15

    return min(score, 0.45)


def _distance_to_score(dist: float | None) -> float:
    if dist is None:
        return 0.0

    if dist <= 0.08:
        return 0.95
    elif dist <= 0.12:
        return 0.85
    elif dist <= 0.18:
        return 0.75
    elif dist <= 0.25:
        return 0.62
    elif dist <= 0.35:
        return 0.48
    else:
        return 0.30


def _rerank_chroma_hits(query: str, entities: dict, rule_dept: str | None, hits: list[dict]) -> list[dict]:
    rule_dept = _normalize_dept_name(rule_dept)

    rescored = []

    for hit in hits:
        dept = _normalize_dept_name(hit.get("department"))
        doc = hit.get("document") or ""
        dist = hit.get("distance")

        if not dept:
            continue

        distance_score = _distance_to_score(dist)
        overlap_score = _compute_overlap_score(query, doc, entities)

        rule_bonus = 0.0
        if rule_dept and dept == rule_dept:
            rule_bonus = 0.18

        final_score = distance_score + overlap_score + rule_bonus

        rescored_hit = dict(hit)
        rescored_hit["distance_score"] = distance_score
        rescored_hit["overlap_score"] = overlap_score
        rescored_hit["rule_bonus"] = rule_bonus
        rescored_hit["rerank_score"] = round(final_score, 6)

        rescored.append(rescored_hit)

    rescored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return rescored


def _debug_print_reranked_hits(query: str, hits: list[dict], tag: str = "V5-Rerank"):
    print("\n" + "=" * 100)
    print(f"[{tag}] query = {query}")

    if not hits:
        print("No reranked hits")
        print("=" * 100)
        return

    for i, hit in enumerate(hits, start=1):
        print("-" * 100)
        print(f"rank          : {i}")
        print(f"department    : {hit.get('department')}")
        print(f"distance      : {hit.get('distance')}")
        print(f"distance_score: {hit.get('distance_score')}")
        print(f"overlap_score : {hit.get('overlap_score')}")
        print(f"rule_bonus    : {hit.get('rule_bonus')}")
        print(f"rerank_score  : {hit.get('rerank_score')}")
        print(f"preview       : {_preview_text(hit.get('document'))}")

    print("=" * 100)

    # ================================
# V6 GraphRAG-lite helpers
# ================================

GRAPH_SYMPTOM_TO_DEPT = {
    "이명": ["이비인후과"],
    "귀 삐 소리": ["이비인후과"],
    "코피": ["이비인후과"],
    "목소리 쉼": ["이비인후과"],
    "인후통": ["이비인후과"],
    "목 이물감": ["이비인후과"],
    "콧물": ["이비인후과"],
    "코막힘": ["이비인후과"],

    "무릎 통증": ["정형외과"],
    "허리 통증": ["정형외과"],
    "허리 디스크": ["정형외과"],
    "어깨 통증": ["정형외과"],
    "손목 통증": ["정형외과"],
    "손목 저림": ["정형외과"],
    "발목 통증": ["정형외과"],
    "발목 염좌": ["정형외과"],
    "관절 통증": ["정형외과"],
    "못 걷": ["정형외과"],
    "팔 들기 어려움": ["정형외과"],

    "두드러기": ["피부과"],
    "피부 가려움": ["피부과"],
    "발진": ["피부과"],
    "피부 빨개짐": ["피부과"],
    "습진": ["피부과"],
    "여드름": ["피부과"],

    "치통": ["치과"],
    "치아 시림": ["치과"],
    "잇몸 출혈": ["치과"],
    "사랑니 통증": ["치과"],
    "턱 통증": ["치과"],
    "입 벌리기 어려움": ["치과"],

    "눈 통증": ["안과"],
    "시야 이상": ["안과"],
    "눈앞 캄캄": ["안과"],
    "충혈": ["안과"],
    "눈물": ["안과"],
    "안구건조": ["안과"],

    "생리통": ["산부인과"],
    "생리불순": ["산부인과"],
    "하혈": ["산부인과"],
    "임신": ["산부인과"],
    "질 출혈": ["산부인과"],

    "불안": ["정신건강의학과"],
    "우울": ["정신건강의학과"],
    "불면": ["정신건강의학과"],
    "공황": ["정신건강의학과"],
    "환청": ["정신건강의학과"],
    "망상": ["정신건강의학과"],

    "속쓰림": ["내과"],
    "신물": ["내과"],
    "복통": ["내과"],
    "설사": ["내과"],
    "고열": ["내과"],
    "발열": ["내과"],
    "기침": ["내과"],
    "혈압 상승": ["내과"],
    "갑상선 이상": ["내과"],
    "당뇨": ["내과"],
    "가슴 답답": ["내과"],
}

GRAPH_BODY_TO_DEPT = {
    "귀": ["이비인후과"],
    "코": ["이비인후과"],
    "목": ["이비인후과"],
    "무릎": ["정형외과"],
    "허리": ["정형외과"],
    "어깨": ["정형외과"],
    "손목": ["정형외과"],
    "발목": ["정형외과"],
    "관절": ["정형외과"],
    "피부": ["피부과"],
    "치아": ["치과"],
    "이가": ["치과"],
    "잇몸": ["치과"],
    "턱": ["치과"],
    "눈": ["안과"],
    "생리": ["산부인과"],
    "질": ["산부인과"],
    "자궁": ["산부인과"],
    "배": ["내과"],
    "위": ["내과"],
    "가슴": ["내과"],
}

GRAPH_ALIAS_MAP = {
    "귀에서 삐 소리가 나요": ["이명", "귀 삐 소리"],
    "목소리가 쉬었어요": ["목소리 쉼", "인후통"],
    "목에 뭔가 걸린 것 같아요": ["목 이물감", "인후통"],
    "이가 시려서 못 먹겠어요": ["치아 시림", "치통"],
    "잇몸에서 피가 나요": ["잇몸 출혈"],
    "턱이 아프고 입이 잘 안 벌어져요": ["턱 통증", "입 벌리기 어려움"],
    "무릎이 왜 이러지": ["무릎 통증"],
    "무릎이 아파요": ["무릎 통증"],
    "허리 디스크인 것 같아요": ["허리 디스크", "허리 통증"],
    "어깨가 너무 아파서 팔을 못 들겠어요": ["어깨 통증", "팔 들기 어려움"],
    "어깨가 올라가지를 않아요": ["어깨 통증", "팔 들기 어려움"],
    "손목이 저리고 아파요": ["손목 저림", "손목 통증"],
    "발목이 삐끗했어요": ["발목 염좌", "발목 통증"],
    "발목이 부었어요": ["발목 통증"],
    "위가 쓰리고 신물이 올라와요": ["속쓰림", "신물"],
    "갑상선이 이상한 것 같아요": ["갑상선 이상"],
    "열이 38도 이상 나요": ["고열", "발열"],
    "피부가 너무 가렵고 빨개요": ["피부 가려움", "발진", "피부 빨개짐"],
    "두드러기가 났어요": ["두드러기", "발진"],
}


def _extract_graph_concepts(query: str, entities: dict) -> list[str]:
    clean_query = _normalize_korean_medical_phrase(query)
    concepts = []

    # alias match
    for pattern, mapped_concepts in GRAPH_ALIAS_MAP.items():
        if pattern in query:
            concepts.extend(mapped_concepts)

    # symptom/body_part from entities
    symptom = (entities.get("symptom") or "").strip()
    body_part = (entities.get("body_part") or "").strip()

    if symptom:
        concepts.append(symptom)
    if body_part:
        concepts.append(body_part)

    # direct concept string match
    for concept in GRAPH_SYMPTOM_TO_DEPT.keys():
        if concept in clean_query or concept in query:
            concepts.append(concept)

    for body in GRAPH_BODY_TO_DEPT.keys():
        if body in clean_query or body in query:
            concepts.append(body)

    # dedupe
    out = []
    seen = set()
    for c in concepts:
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    return out


def _graph_vote_departments(concepts: list[str]) -> dict[str, float]:
    scores = {}

    for concept in concepts:
        if concept in GRAPH_SYMPTOM_TO_DEPT:
            for dept in GRAPH_SYMPTOM_TO_DEPT[concept]:
                scores[dept] = scores.get(dept, 0.0) + 1.0

        if concept in GRAPH_BODY_TO_DEPT:
            for dept in GRAPH_BODY_TO_DEPT[concept]:
                scores[dept] = scores.get(dept, 0.0) + 0.6

    return scores


def _graph_best_dept(query: str, entities: dict) -> dict:
    concepts = _extract_graph_concepts(query, entities)
    dept_scores = _graph_vote_departments(concepts)

    if not dept_scores:
        return {
            "graph_dept": None,
            "graph_score": 0.0,
            "graph_concepts": concepts,
            "graph_candidates": [],
        }

    ranked = sorted(dept_scores.items(), key=lambda x: x[1], reverse=True)
    graph_dept, graph_score = ranked[0]

    return {
        "graph_dept": graph_dept,
        "graph_score": graph_score,
        "graph_concepts": concepts,
        "graph_candidates": ranked,
    }


def _choose_v6_dept(
    dept_hint: str | None,
    rule_dept: str | None,
    chroma_result: dict,
    graph_result: dict,
    entities: dict,
) -> tuple[str | None, dict]:
    dept_hint = _normalize_dept_name(dept_hint)
    rule_dept = _normalize_dept_name(rule_dept)
    chroma_dept = _normalize_dept_name(chroma_result.get("predicted_dept"))
    graph_dept = _normalize_dept_name(graph_result.get("graph_dept"))

    rule_score = _score_rule_dept(rule_dept, entities)
    chroma_score = _score_chroma_result(chroma_result)

    graph_score = graph_result.get("graph_score", 0.0)
    # graph 점수를 0~1 대충 정규화
    if graph_score >= 2.0:
        graph_score_norm = 0.90
    elif graph_score >= 1.5:
        graph_score_norm = 0.80
    elif graph_score >= 1.0:
        graph_score_norm = 0.68
    elif graph_score >= 0.6:
        graph_score_norm = 0.52
    else:
        graph_score_norm = 0.0

    debug_info = {
        "dept_hint": dept_hint,
        "rule_dept": rule_dept,
        "rule_score": rule_score,
        "chroma_dept": chroma_dept,
        "chroma_score": chroma_score,
        "graph_dept": graph_dept,
        "graph_score": graph_score_norm,
        "graph_concepts": graph_result.get("graph_concepts", []),
        "graph_candidates": graph_result.get("graph_candidates", []),
    }

    if dept_hint:
        return dept_hint, debug_info

    candidates = {}

    def add_score(dept: str | None, score: float):
        dept = _normalize_dept_name(dept)
        if not dept:
            return
        candidates[dept] = candidates.get(dept, 0.0) + score

    add_score(rule_dept, rule_score)
    add_score(chroma_dept, chroma_score)
    add_score(graph_dept, graph_score_norm)

    if not candidates:
        return None, debug_info

    ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    top_dept, top_score = ranked[0]
    debug_info["final_candidates"] = ranked
    debug_info["final_top_score"] = top_score

    # 보수적 장치:
    # rule_dept 있으면 graph/chroma가 동시에 같은 방향일 때만 뒤집기
    if rule_dept and top_dept != rule_dept:
        support = 0
        if chroma_dept == top_dept:
            support += 1
        if graph_dept == top_dept:
            support += 1

        if support >= 2 and top_score >= rule_score + 0.20:
            return top_dept, debug_info

        return rule_dept, debug_info

    return top_dept, debug_info

def rag_v1_keyword_only(item: dict) -> dict:
    return _base_predict(item)


def rag_v2_vector(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    chroma_result = {
        "predicted_dept": None,
        "top_doc": None,
        "top_distance": None,
        "top_hits": [],
    }

    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        dept_hint = entities.get("department_hint")

        rule_dept = infer_department_from_symptom(
            query=query,
            symptom=entities.get("symptom"),
            body_part=entities.get("body_part"),
        )

        chroma_dept = None

        # V1이 못 잡을 때만 V2 개입
        if not dept_hint and not rule_dept:
            rewritten_query = _rewrite_query_for_chroma(query, entities)
            chroma_result = search_chroma_department(
                query=rewritten_query,
                n_results=3,
                debug=False,
            )
            chroma_dept = chroma_result.get("predicted_dept")

        predicted_dept = dept_hint or rule_dept or chroma_dept

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
        "top_doc": chroma_result.get("top_doc"),
        "top_distance": chroma_result.get("top_distance"),
        "top_hits": chroma_result.get("top_hits", []),
    }


def rag_v3_rewrite(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    chroma_result = {
        "predicted_dept": None,
        "top_doc": None,
        "top_distance": None,
        "top_hits": [],
        "rewritten_query": None,
    }

    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        dept_hint = entities.get("department_hint")
        rule_dept = _rule_dept_from_entities(query, entities)

        chroma_dept = None
        if not dept_hint and not rule_dept:
            chroma_result = _get_chroma_result_with_rewrite(
                query=query,
                entities=entities,
                debug=False,
            )
            chroma_dept = chroma_result.get("predicted_dept")

        predicted_dept = (
            _normalize_dept_name(dept_hint)
            or _normalize_dept_name(rule_dept)
            or _normalize_dept_name(chroma_dept)
        )

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
        "rewritten_query": chroma_result.get("rewritten_query"),
        "top_doc": chroma_result.get("top_doc"),
        "top_distance": chroma_result.get("top_distance"),
        "top_hits": chroma_result.get("top_hits", []),
    }


def rag_v4_hybrid(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    chroma_result = {
        "predicted_dept": None,
        "top_doc": None,
        "top_distance": None,
        "top_hits": [],
        "rewritten_query": None,
    }
    hybrid_debug = {
        "dept_hint": None,
        "rule_dept": None,
        "rule_score": 0.0,
        "chroma_dept": None,
        "chroma_score": 0.0,
    }

    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        dept_hint = entities.get("department_hint")
        rule_dept = _rule_dept_from_entities(query, entities)

        # V4는 하이브리드니까 symptom inquiry면 chroma도 같이 본다
        if not dept_hint:
            chroma_result = _get_chroma_result_with_rewrite(
                query=query,
                entities=entities,
                debug=False,
            )

        predicted_dept, hybrid_debug = _choose_hybrid_dept(
            dept_hint=dept_hint,
            rule_dept=rule_dept,
            chroma_result=chroma_result,
            entities=entities,
)

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
        "rewritten_query": chroma_result.get("rewritten_query"),
        "top_doc": chroma_result.get("top_doc"),
        "top_distance": chroma_result.get("top_distance"),
        "top_hits": chroma_result.get("top_hits", []),
        "hybrid_debug": hybrid_debug,
    }


def rag_v5_rerank(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    chroma_result = {
        "predicted_dept": None,
        "top_doc": None,
        "top_distance": None,
        "top_hits": [],
        "rewritten_query": None,
    }

    reranked_hits = []
    rerank_debug = {
        "dept_hint": None,
        "rule_dept": None,
        "top_rerank_dept": None,
        "top_rerank_score": 0.0,
    }

    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        dept_hint = entities.get("department_hint")
        rule_dept = _rule_dept_from_entities(query, entities)

        rerank_debug["dept_hint"] = _normalize_dept_name(dept_hint)
        rerank_debug["rule_dept"] = _normalize_dept_name(rule_dept)

        if dept_hint:
            predicted_dept = _normalize_dept_name(dept_hint)
        else:
            chroma_result = _get_chroma_result_with_rewrite(
                query=query,
                entities=entities,
                debug=False,
            )

            reranked_hits = _rerank_chroma_hits(
                query=query,
                entities=entities,
                rule_dept=rule_dept,
                hits=chroma_result.get("top_hits", []),
            )

            top_rerank_dept = reranked_hits[0].get("department") if reranked_hits else None
            top_rerank_score = reranked_hits[0].get("rerank_score", 0.0) if reranked_hits else 0.0

            rerank_debug["top_rerank_dept"] = top_rerank_dept
            rerank_debug["top_rerank_score"] = top_rerank_score

            # 보수적 선택:
            # rule_dept 있으면 기본적으로 유지
            # 단, rerank 점수가 충분히 높고 rule이 없거나 매우 약할 때만 rerank 선택
            if rule_dept and top_rerank_dept:
                if top_rerank_dept == _normalize_dept_name(rule_dept):
                    predicted_dept = _normalize_dept_name(rule_dept)
                elif top_rerank_score >= 1.05:
                    predicted_dept = top_rerank_dept
                else:
                    predicted_dept = _normalize_dept_name(rule_dept)
            else:
                predicted_dept = _normalize_dept_name(rule_dept) or top_rerank_dept

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
        "rewritten_query": chroma_result.get("rewritten_query"),
        "top_doc": chroma_result.get("top_doc"),
        "top_distance": chroma_result.get("top_distance"),
        "top_hits": chroma_result.get("top_hits", []),
        "reranked_hits": reranked_hits,
        "rerank_debug": rerank_debug,
    }


def rag_v6_graphrag(item: dict) -> dict:
    query = item.get("query", "")
    raw_entities = item.get("entities", {}) or {}
    true_intent = item.get("true_intent")

    entities = normalize_entities(raw_entities, query)
    intents = normalize_intent(
        raw_intent=item.get("intent"),
        query=query,
        entities=entities,
        true_intent=true_intent,
    )

    predicted_intent = intents[0] if intents else "unknown"

    chroma_result = {
        "predicted_dept": None,
        "top_doc": None,
        "top_distance": None,
        "top_hits": [],
        "rewritten_query": None,
    }
    graph_result = {
        "graph_dept": None,
        "graph_score": 0.0,
        "graph_concepts": [],
        "graph_candidates": [],
    }
    graph_debug = {}

    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        dept_hint = entities.get("department_hint")
        rule_dept = _rule_dept_from_entities(query, entities)

        if not dept_hint:
            chroma_result = _get_chroma_result_with_rewrite(
                query=query,
                entities=entities,
                debug=False,
            )

        graph_result = _graph_best_dept(query, entities)

        predicted_dept, graph_debug = _choose_v6_dept(
            dept_hint=dept_hint,
            rule_dept=rule_dept,
            chroma_result=chroma_result,
            graph_result=graph_result,
            entities=entities,
        )

    return {
        "predicted_intent": predicted_intent,
        "predicted_dept": predicted_dept,
        "rewritten_query": chroma_result.get("rewritten_query"),
        "top_doc": chroma_result.get("top_doc"),
        "top_distance": chroma_result.get("top_distance"),
        "top_hits": chroma_result.get("top_hits", []),
        "graph_result": graph_result,
        "graph_debug": graph_debug,
    }