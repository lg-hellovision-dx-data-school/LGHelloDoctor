# Opr/run_rag_eval.py

from pprint import pprint

from Opr.test_data_loader import load_json, validate_b_output_items
from Opr.result_saver import save_json_with_timestamp
from Opr.rag_eval_config import rag_b_meta
from Opr.rag_versions import (
    rag_v1_keyword_only,
    rag_v2_vector,
    rag_v3_rewrite,
    rag_v4_hybrid,
    rag_v5_rerank,
    rag_v6_graphrag,
)


RAG_FUNCTIONS = {
    "rag_v1_keyword_only": rag_v1_keyword_only,
    "rag_v2_vector": rag_v2_vector,
    "rag_v3_rewrite": rag_v3_rewrite,
    "rag_v4_hybrid": rag_v4_hybrid,
    "rag_v5_rerank": rag_v5_rerank,
    "rag_v6_graphrag": rag_v6_graphrag,
}


def normalize_label(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"", "null", "none"}:
            return None
    return value


def evaluate_single_version(items: list[dict], meta_row: tuple) -> dict:
    version_id, title, description, func_name, sample_size = meta_row
    fn = RAG_FUNCTIONS[func_name]

    eval_items = items[:sample_size]

    total = 0
    intent_correct = 0
    dept_total = 0
    dept_correct = 0

    samples = []

    for idx, item in enumerate(eval_items, start=1):
        pred = fn(item)

        predicted_intent = normalize_label(pred.get("predicted_intent"))
        predicted_dept = normalize_label(pred.get("predicted_dept"))

        true_intent = normalize_label(item.get("true_intent"))
        true_dept = normalize_label(item.get("true_dept"))

        total += 1

        intent_match = predicted_intent == true_intent
        if intent_match:
            intent_correct += 1

        dept_match = None
        if true_dept is not None:
            dept_total += 1
            dept_match = predicted_dept == true_dept
            if dept_match:
                dept_correct += 1

        samples.append({
            "idx": idx,
            "query": item.get("query"),
            "predicted_intent": predicted_intent,
            "true_intent": true_intent,
            "intent_match": intent_match,
            "predicted_dept": predicted_dept,
            "true_dept": true_dept,
            "dept_match": dept_match,
        })

    intent_accuracy = round(intent_correct / total, 4) if total else 0.0
    dept_accuracy = round(dept_correct / dept_total, 4) if dept_total else None

    return {
        "version_id": version_id,
        "title": title,
        "description": description,
        "function_name": func_name,
        "sample_size": sample_size,
        "total": total,
        "intent_correct": intent_correct,
        "intent_accuracy": intent_accuracy,
        "dept_total": dept_total,
        "dept_correct": dept_correct,
        "dept_accuracy": dept_accuracy,
        "samples": samples,
    }


def run_rag_eval(
    input_filepath: str = "b_output_1000.json",
    save_prefix: str = "rag_eval_result",
    verbose: bool = True,
):
    items = load_json(input_filepath)
    validate_b_output_items(items)

    all_results = []

    for meta_row in rag_b_meta:
        result = evaluate_single_version(items, meta_row)
        all_results.append(result)

        if verbose:
            print("\n==============================")
            print(f"{result['version_id']} - {result['title']}")
            print(f"설명: {result['description']}")
            print(f"샘플 수: {result['sample_size']}")
            print(f"Intent Accuracy: {result['intent_accuracy']}")
            print(f"Dept Accuracy: {result['dept_accuracy']}")
            print("==============================")
            pprint(result["samples"][:3])

    saved_path = save_json_with_timestamp(all_results, prefix=save_prefix)

    if verbose:
        print(f"\n평가 결과 저장 완료: {saved_path}")

    return all_results


if __name__ == "__main__":
    run_rag_eval()