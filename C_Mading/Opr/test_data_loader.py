import json
from pathlib import Path


def load_json(filepath: str):
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def validate_b_output_items(items):
    if not isinstance(items, list):
        raise ValueError("B output JSON은 list 형태여야 합니다.")

    required_keys = {"intent", "entities", "query"}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{idx}번째 항목이 dict가 아닙니다.")
        missing = required_keys - set(item.keys())
        if missing:
            raise ValueError(f"{idx}번째 항목에 누락된 키가 있습니다: {missing}")