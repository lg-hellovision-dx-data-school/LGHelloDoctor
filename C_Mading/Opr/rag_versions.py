# Opr/rag_versions.py

from Opr.run_b_output_test import normalize_intent, normalize_entities, infer_department_from_symptom
from Opr.chroma_client import get_medical_collection


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

def search_chroma_department(query: str, n_results: int = 3) -> dict:
    collection = get_medical_collection()

    result = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    docs = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    if not docs or not metadatas:
        return {
            "predicted_dept": None,
            "top_doc": None,
            "top_distance": None,
        }

    top_meta = metadatas[0] if metadatas else {}
    top_doc = docs[0] if docs else None
    top_distance = distances[0] if distances else None

    predicted_dept = top_meta.get("department") if top_meta else None

    return {
        "predicted_dept": predicted_dept,
        "top_doc": top_doc,
        "top_distance": top_distance,
    }


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

    # 1) symptom_inquiry가 아니면 dept는 비움
    if predicted_intent != "symptom_inquiry":
        predicted_dept = None
    else:
        # 2) query에 진료과명이 직접 있으면 그걸 우선
        dept_hint = entities.get("department_hint")

        # 3) 없으면 Chroma 검색
        chroma_dept = None
        if not dept_hint:
            chroma_result = search_chroma_department(query=query, n_results=3)
            chroma_dept = chroma_result.get("predicted_dept")

        # 4) 그래도 없으면 기존 symptom rule fallback
        predicted_dept = (
            dept_hint
            or chroma_dept
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


def rag_v3_rewrite(item: dict) -> dict:
    return _base_predict(item)


def rag_v4_hybrid(item: dict) -> dict:
    return _base_predict(item)


def rag_v5_rerank(item: dict) -> dict:
    return _base_predict(item)


def rag_v6_graphrag(item: dict) -> dict:
    return _base_predict(item)